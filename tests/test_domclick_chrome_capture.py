import json
from datetime import date
from pathlib import Path

import pytest

from realtyscope.ingestion.domclick_chrome_capture import (
    DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE,
    build_domclick_search_urls,
    capture_domclick_chrome_ssr_snapshots,
    dump_dom_with_chrome,
    extract_domclick_ssr_state_payload,
)
from realtyscope.ingestion.domclick_live import DomclickAccessBlocked


def test_build_domclick_search_urls_uses_bounded_moscow_offsets() -> None:
    urls = build_domclick_search_urls()

    assert len(urls) == 100
    assert urls[0] == (0, DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE.format(offset=0))
    assert urls[-1] == (1980, DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE.format(offset=1980))
    assert "aids=2299" in urls[0][1]


def test_chrome_capture_writes_bulk_compact_json_and_manifest(tmp_path: Path) -> None:
    requested_urls: list[str] = []

    def capture_page_dom(url: str) -> str:
        requested_urls.append(url)
        offset = int(url.rsplit("offset=", maxsplit=1)[1])
        listing_id = f"capture-{offset}"
        payload = {
            "search": {
                "pages": {
                    str(offset): {
                        "ids": [listing_id],
                        "entities": {
                            listing_id: {
                                "id": listing_id,
                                "url": f"https://domclick.ru/card/sale__flat__{listing_id}/",
                                "address": f"Москва, Тестовая улица, {offset}",
                                "price": 12_000_000 + offset,
                                "area": 40.0,
                                "rooms": 2,
                                "lat": 55.75,
                                "lng": 37.61,
                            }
                        },
                    }
                }
            }
        }
        return f"<html><script>window.__SSR_STATE__={json.dumps(payload)};</script></html>"

    result = capture_domclick_chrome_ssr_snapshots(
        output_root=tmp_path / "data" / "raw" / "domclick",
        collection_date=date(2026, 6, 2),
        offset_start=0,
        offset_stop=20,
        offset_step=20,
        max_pages=2,
        delay_seconds=0,
        chrome_profile_directory="Default",
        capture_page_dom=capture_page_dom,
        sleep=lambda _seconds: None,
    )

    assert requested_urls == [
        DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE.format(offset=0),
        DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE.format(offset=20),
    ]
    assert result.snapshot_dir == tmp_path / "data" / "raw" / "domclick" / "2026-06-02-bulk"
    assert result.files_written == 2
    assert result.records_seen == 2

    first_payload_text = (result.snapshot_dir / "payloads" / "search-offset-000000.json").read_text(
        encoding="utf-8"
    )
    assert ": " not in first_payload_text
    assert json.loads(first_payload_text)["search"]["pages"]["0"]["ids"] == ["capture-0"]

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["collection_date"] == "2026-06-02"
    assert manifest["capture_mode"] == "chrome_assisted_ssr_compact_json"
    assert manifest["search_scope"] == "moscow_sale_apartments"
    assert manifest["area_id"] == "2299"
    assert manifest["chrome_profile_directory"] == "Default"
    assert manifest["files_written"] == 2
    assert manifest["records_seen"] == 2
    assert [entry["offset"] for entry in manifest["entries"]] == [0, 20]
    assert [entry["path"] for entry in manifest["entries"]] == [
        "payloads/search-offset-000000.json",
        "payloads/search-offset-000020.json",
    ]
    assert all(entry["content_sha256"] for entry in manifest["entries"])


def test_chrome_capture_stops_on_qrator_boundary(tmp_path: Path) -> None:
    with pytest.raises(DomclickAccessBlocked, match="QRATOR"):
        capture_domclick_chrome_ssr_snapshots(
            output_root=tmp_path / "data" / "raw" / "domclick",
            collection_date=date(2026, 6, 2),
            offset_start=0,
            offset_stop=0,
            max_pages=1,
            delay_seconds=0,
            capture_page_dom=lambda _url: (
                '<script src="/__qrator/qauth_utm_v2d_v9118.js"></script>'
            ),
            sleep=lambda _seconds: None,
        )


def test_chrome_capture_stops_on_domclick_unusual_request_boundary(tmp_path: Path) -> None:
    with pytest.raises(DomclickAccessBlocked, match="unusual request"):
        capture_domclick_chrome_ssr_snapshots(
            output_root=tmp_path / "data" / "raw" / "domclick",
            collection_date=date(2026, 6, 2),
            offset_start=0,
            offset_stop=0,
            max_pages=1,
            delay_seconds=0,
            capture_page_dom=lambda _url: (
                "<html><head><title>403 | Домклик</title></head>"
                "<body>Похоже, ваш запрос выглядит необычно</body></html>"
            ),
            sleep=lambda _seconds: None,
        )


def test_dump_dom_with_chrome_uses_devtools_fallback_when_stdout_is_empty(monkeypatch) -> None:
    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    fallback_calls: list[dict[str, object]] = []

    def fake_run(*_args, **_kwargs):
        return Completed()

    def fake_fallback(**kwargs):
        fallback_calls.append(kwargs)
        return "<html><body>fallback-ok</body></html>"

    monkeypatch.setattr("realtyscope.ingestion.domclick_chrome_capture.subprocess.run", fake_run)
    monkeypatch.setattr(
        "realtyscope.ingestion.domclick_chrome_capture.dump_dom_with_chrome_devtools",
        fake_fallback,
    )

    page_dom = dump_dom_with_chrome(
        "https://example.com",
        chrome_path=Path("chrome.exe"),
        chrome_user_data_dir=Path("User Data"),
        chrome_profile_directory="Default",
        timeout_seconds=10,
        virtual_time_budget_ms=1000,
    )

    assert page_dom == "<html><body>fallback-ok</body></html>"
    assert fallback_calls == [
        {
            "url": "https://example.com",
            "chrome_path": Path("chrome.exe"),
            "chrome_user_data_dir": Path("User Data"),
            "chrome_profile_directory": "Default",
            "timeout_seconds": 10,
            "virtual_time_budget_ms": 1000,
        }
    ]


def test_chrome_capture_reuses_one_devtools_session_for_real_chrome(
    tmp_path: Path, monkeypatch
) -> None:
    class FakeDevToolsDumper:
        instances: list["FakeDevToolsDumper"] = []

        def __init__(self, **_kwargs):
            self.urls: list[str] = []
            self.closed = False
            FakeDevToolsDumper.instances.append(self)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.closed = True

        def dump_dom(self, url: str) -> str:
            self.urls.append(url)
            offset = int(url.rsplit("offset=", maxsplit=1)[1])
            payload = {
                "items": [
                    {
                        "id": f"reuse-{offset}",
                        "url": f"https://domclick.ru/card/sale__flat__reuse-{offset}/",
                        "address": f"Москва, Session Street, {offset}",
                        "price": 12_000_000 + offset,
                        "area": 40.0,
                        "rooms": 2,
                    }
                ]
            }
            return f"<html><script>window.__SSR_STATE__={json.dumps(payload)};</script></html>"

    def fail_per_page_chrome_dump(*_args, **_kwargs):
        raise AssertionError("capture should reuse one DevTools session")

    monkeypatch.setattr(
        "realtyscope.ingestion.domclick_chrome_capture.ChromeDevToolsDomDumper",
        FakeDevToolsDumper,
        raising=False,
    )
    monkeypatch.setattr(
        "realtyscope.ingestion.domclick_chrome_capture.dump_dom_with_chrome",
        fail_per_page_chrome_dump,
    )
    monkeypatch.setattr(
        "realtyscope.ingestion.domclick_chrome_capture._resolve_chrome_path",
        lambda _path: Path("chrome.exe"),
    )
    monkeypatch.setattr(
        "realtyscope.ingestion.domclick_chrome_capture._resolve_chrome_user_data_dir",
        lambda _path: Path("User Data"),
    )
    monkeypatch.setattr(
        "realtyscope.ingestion.domclick_chrome_capture._validate_chrome_profile",
        lambda *_args: None,
    )

    result = capture_domclick_chrome_ssr_snapshots(
        output_root=tmp_path / "data" / "raw" / "domclick",
        collection_date=date(2026, 6, 2),
        offset_start=0,
        offset_stop=20,
        offset_step=20,
        max_pages=2,
        delay_seconds=0,
        chrome_profile_directory="Default",
        sleep=lambda _seconds: None,
    )

    assert result.files_written == 2
    assert len(FakeDevToolsDumper.instances) == 1
    assert FakeDevToolsDumper.instances[0].urls == [
        DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE.format(offset=0),
        DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE.format(offset=20),
    ]
    assert FakeDevToolsDumper.instances[0].closed is True


def test_extract_domclick_ssr_state_payload_handles_undefined_values() -> None:
    payload = extract_domclick_ssr_state_payload(
        '<script>window.__SSR_STATE__={"items":[{"id":"1","description":undefined}]};</script>'
    )

    assert payload == {"items": [{"id": "1", "description": None}]}


def test_scheduled_batch_script_calls_chrome_capture_before_url_file_fallback() -> None:
    script = Path("scripts/run_domclick_scheduled_batch.ps1").read_text(encoding="utf-8")

    chrome_capture_index = script.index("realtyscope.ingestion.domclick_chrome_capture")
    url_file_fallback_index = script.index("Test-Path $UrlFile -PathType Leaf")
    assert chrome_capture_index < url_file_fallback_index
    assert "[switch]$SkipCapture" in script
    assert '"--profile-directory", $ChromeProfileDirectory' in script
    assert '"--offset-stop", "$CaptureOffsetStop"' in script
    assert "[int]$MinCleanRecords = 1000" in script
    assert '"--min-normalized-records", "$MinCleanRecords"' in script
    assert "$CaptureOutput = & $Python @CaptureArgs" in script
    assert "$CaptureOutput | ForEach-Object { Write-Host $_ }" in script
