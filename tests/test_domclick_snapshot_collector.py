import json
from datetime import date
from pathlib import Path

import pytest

from realtyscope.ingestion.domclick_live import DomclickAccessBlocked
from realtyscope.ingestion.domclick_snapshot_collector import (
    FetchedDomclickSnapshot,
    collect_domclick_snapshots,
)

ROBOTS_TXT = """
User-agent: *
Disallow: /search
Disallow: /*?*
Allow: /sitemaps/
Allow: /card/
"""


def test_collect_domclick_snapshots_writes_daily_directory_and_manifest(tmp_path: Path) -> None:
    urls = [
        "https://domclick.ru/card/sale__flat__html-1/",
        "https://domclick.ru/card/sale__flat__json-1/",
    ]

    def fetch_text(url: str) -> str:
        assert url == "https://domclick.ru/robots.txt"
        return ROBOTS_TXT

    def fetch_snapshot(url: str) -> FetchedDomclickSnapshot:
        if url.endswith("html-1/"):
            return FetchedDomclickSnapshot(
                url=url,
                status_code=200,
                headers={"content-type": "text/html; charset=utf-8"},
                body=b"<html><title>Domclick listing</title></html>",
            )
        return FetchedDomclickSnapshot(
            url=url,
            status_code=200,
            headers={"content-type": "application/json"},
            body=json.dumps({"items": []}).encode("utf-8"),
        )

    result = collect_domclick_snapshots(
        urls,
        output_root=tmp_path / "data" / "raw" / "domclick",
        collection_date=date(2026, 5, 31),
        fetch_text=fetch_text,
        fetch_snapshot=fetch_snapshot,
        sleep=lambda _seconds: None,
    )

    assert result.files_written == 2
    assert result.snapshot_dir == tmp_path / "data" / "raw" / "domclick" / "2026-05-31"
    assert (
        (result.snapshot_dir / "pages" / "snapshot-000001.html")
        .read_text(encoding="utf-8")
        .startswith("<html>")
    )
    assert json.loads(
        (result.snapshot_dir / "payloads" / "snapshot-000002.json").read_text(encoding="utf-8")
    ) == {"items": []}

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_name"] == "domclick"
    assert manifest["collection_date"] == "2026-05-31"
    assert [entry["source_type"] for entry in manifest["entries"]] == [
        "domclick_html",
        "domclick_json",
    ]
    assert [entry["path"] for entry in manifest["entries"]] == [
        "pages/snapshot-000001.html",
        "payloads/snapshot-000002.json",
    ]
    assert all(entry["content_sha256"] for entry in manifest["entries"])


def test_collect_domclick_snapshots_rejects_robots_disallowed_url(tmp_path: Path) -> None:
    def fetch_snapshot(_url: str) -> FetchedDomclickSnapshot:  # pragma: no cover
        raise AssertionError("collector must not fetch robots-disallowed URLs")

    with pytest.raises(DomclickAccessBlocked, match="robots.txt"):
        collect_domclick_snapshots(
            ["https://domclick.ru/search?deal_type=sale"],
            output_root=tmp_path / "data" / "raw" / "domclick",
            collection_date=date(2026, 5, 31),
            fetch_text=lambda _url: ROBOTS_TXT,
            fetch_snapshot=fetch_snapshot,
            sleep=lambda _seconds: None,
        )


def test_collect_domclick_snapshots_rejects_qrator_challenge(tmp_path: Path) -> None:
    def fetch_snapshot(url: str) -> FetchedDomclickSnapshot:
        return FetchedDomclickSnapshot(
            url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            body=b'<script src="/__qrator/qauth_utm_v2d_v9118.js"></script>',
        )

    with pytest.raises(DomclickAccessBlocked, match="QRATOR"):
        collect_domclick_snapshots(
            ["https://domclick.ru/card/sale__flat__blocked-1/"],
            output_root=tmp_path / "data" / "raw" / "domclick",
            collection_date=date(2026, 5, 31),
            fetch_text=lambda _url: ROBOTS_TXT,
            fetch_snapshot=fetch_snapshot,
            sleep=lambda _seconds: None,
        )
