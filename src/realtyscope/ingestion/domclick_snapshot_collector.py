from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib import request
from urllib.parse import urlparse

from realtyscope.ingestion.domclick_live import (
    DEFAULT_USER_AGENT,
    DOMCLICK_BASE_URL,
    DOMCLICK_ROBOTS_URL,
    DomclickAccessBlocked,
    can_fetch_url,
    is_qrator_challenge,
)
from realtyscope.ingestion.domclick_live import (
    fetch_text as fetch_domclick_text,
)

COLLECTOR_VERSION = "realtyscope-domclick-snapshot-collector-v1"


@dataclass(frozen=True)
class FetchedDomclickSnapshot:
    url: str
    status_code: int
    headers: Mapping[str, str]
    body: bytes

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", self.headers.get("Content-Type", ""))


@dataclass(frozen=True)
class DomclickSnapshotCollectionResult:
    snapshot_dir: Path
    manifest_path: Path
    files_written: int


def fetch_domclick_snapshot(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout_seconds: float = 20.0,
) -> FetchedDomclickSnapshot:
    req = request.Request(url, headers={"User-Agent": user_agent})
    with request.urlopen(req, timeout=timeout_seconds) as response:
        return FetchedDomclickSnapshot(
            url=url,
            status_code=int(response.status),
            headers={key: value for key, value in response.headers.items()},
            body=response.read(),
        )


def collect_domclick_snapshots(
    urls: Iterable[str],
    *,
    output_root: Path,
    collection_date: date | None = None,
    fetch_text: Callable[[str], str] | None = None,
    fetch_snapshot: Callable[[str], FetchedDomclickSnapshot] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout_seconds: float = 20.0,
    delay_seconds: float = 1.0,
    max_urls: int = 100,
    collector_version: str = COLLECTOR_VERSION,
    capture_mode: str = "bounded_url_capture",
    batch_run_id: str | None = None,
    operator_note: str | None = None,
) -> DomclickSnapshotCollectionResult:
    if max_urls <= 0:
        raise ValueError("max_urls must be greater than zero")
    if delay_seconds < 0:
        raise ValueError("delay_seconds must be zero or greater")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")

    url_list = [url.strip() for url in urls if url.strip()]
    if not url_list:
        raise ValueError("At least one Domclick URL is required")
    if len(url_list) > max_urls:
        raise ValueError(f"Refusing to collect {len(url_list)} URLs; max_urls={max_urls}")

    for url in url_list:
        _validate_domclick_url(url)

    fetch_text = fetch_text or (
        lambda url: fetch_domclick_text(
            url,
            user_agent=user_agent,
            timeout_seconds=timeout_seconds,
        )
    )
    fetch_snapshot = fetch_snapshot or (
        lambda url: fetch_domclick_snapshot(
            url,
            user_agent=user_agent,
            timeout_seconds=timeout_seconds,
        )
    )

    robots_txt = fetch_text(DOMCLICK_ROBOTS_URL)
    for url in url_list:
        if not can_fetch_url(robots_txt, url, user_agent=user_agent):
            raise DomclickAccessBlocked(f"Domclick robots.txt does not allow {url!r}")

    collection_date = collection_date or datetime.now(UTC).date()
    snapshot_dir = output_root / collection_date.isoformat()
    pages_dir = snapshot_dir / "pages"
    payloads_dir = snapshot_dir / "payloads"
    pages_dir.mkdir(parents=True, exist_ok=True)
    payloads_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, object]] = []
    for index, url in enumerate(url_list, start=1):
        fetched = fetch_snapshot(url)
        if fetched.status_code >= 400:
            raise RuntimeError(f"Domclick returned HTTP {fetched.status_code} for {url!r}")

        body_text = fetched.body.decode("utf-8", errors="replace")
        if is_qrator_challenge(body_text):
            raise DomclickAccessBlocked(f"Domclick returned a QRATOR challenge for {url!r}")

        source_type, relative_path = _target_snapshot_path(index, fetched)
        output_path = snapshot_dir / relative_path
        output_path.write_bytes(fetched.body)
        entries.append(
            {
                "source_url": fetched.url,
                "source_type": source_type,
                "path": relative_path.as_posix(),
                "fetched_at": _utc_now_iso(),
                "http_status": fetched.status_code,
                "content_type": fetched.content_type,
                "content_bytes": len(fetched.body),
                "content_sha256": hashlib.sha256(fetched.body).hexdigest(),
            }
        )

        if index < len(url_list) and delay_seconds > 0:
            sleep(delay_seconds)

    manifest_path = snapshot_dir / "manifest.json"
    manifest = {
        "source_name": "domclick",
        "collection_date": collection_date.isoformat(),
        "collector_version": collector_version,
        "capture_mode": capture_mode,
        "batch_run_id": batch_run_id,
        "base_url": DOMCLICK_BASE_URL,
        "user_agent": user_agent,
        "max_urls": max_urls,
        "delay_seconds": delay_seconds,
        "timeout_seconds": timeout_seconds,
        "entries": entries,
    }
    if operator_note:
        manifest["operator_note"] = operator_note
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return DomclickSnapshotCollectionResult(
        snapshot_dir=snapshot_dir,
        manifest_path=manifest_path,
        files_written=len(entries),
    )


def _validate_domclick_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc != "domclick.ru":
        raise ValueError(f"Expected a domclick.ru URL, got {url!r}")


def _target_snapshot_path(index: int, fetched: FetchedDomclickSnapshot) -> tuple[str, Path]:
    content_type = fetched.content_type.lower()
    body_start = fetched.body.lstrip()[:1]
    if "json" in content_type or body_start in {b"{", b"["}:
        return "domclick_json", Path("payloads") / f"snapshot-{index:06d}.json"
    if "html" in content_type or b"<" in body_start:
        return "domclick_html", Path("pages") / f"snapshot-{index:06d}.html"
    raise ValueError(f"Unsupported Domclick response content type: {fetched.content_type!r}")


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _load_urls(urls: Sequence[str] | None, url_file: Path | None) -> list[str]:
    loaded_urls = list(urls or [])
    if url_file is not None:
        loaded_urls.extend(
            line.strip()
            for line in url_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    return loaded_urls


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect Domclick HTML/JSON snapshots into a daily raw-data directory."
    )
    parser.add_argument("--url", action="append", default=[], help="Domclick URL to collect.")
    parser.add_argument("--url-file", type=Path, help="Text file with one Domclick URL per line.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/raw/domclick"),
        help="Root directory for daily Domclick snapshots.",
    )
    parser.add_argument(
        "--collection-date",
        type=date.fromisoformat,
        default=None,
        help="Collection date in YYYY-MM-DD format. Defaults to today in UTC.",
    )
    parser.add_argument("--max-urls", type=int, default=100, help="Maximum URLs per run.")
    parser.add_argument("--delay-seconds", type=float, default=1.0, help="Delay between URLs.")
    parser.add_argument("--timeout-seconds", type=float, default=20.0, help="HTTP timeout.")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="HTTP User-Agent.")
    parser.add_argument(
        "--capture-mode",
        default="bounded_url_capture",
        help="Manifest label for how URLs/snapshots were prepared.",
    )
    parser.add_argument(
        "--operator-note",
        default=None,
        help="Optional manifest note, for example the RU route or Chrome profile used.",
    )
    parser.add_argument("--json", action="store_true", help="Print a JSON summary.")
    args = parser.parse_args(argv)

    result = collect_domclick_snapshots(
        _load_urls(args.url, args.url_file),
        output_root=args.output_root,
        collection_date=args.collection_date,
        user_agent=args.user_agent,
        timeout_seconds=args.timeout_seconds,
        delay_seconds=args.delay_seconds,
        max_urls=args.max_urls,
        capture_mode=args.capture_mode,
        operator_note=args.operator_note,
    )

    payload = {
        "snapshot_dir": str(result.snapshot_dir),
        "manifest_path": str(result.manifest_path),
        "files_written": result.files_written,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "Collected Domclick snapshots "
            f"files_written={result.files_written} snapshot_dir={result.snapshot_dir}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
