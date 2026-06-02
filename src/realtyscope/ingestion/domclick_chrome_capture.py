from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from contextlib import nullcontext, suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from realtyscope.ingestion.contracts import canonical_json
from realtyscope.ingestion.domclick import DomclickCollectorConfig, parse_domclick_payload
from realtyscope.ingestion.domclick_live import (
    DOMCLICK_BASE_URL,
    DomclickAccessBlocked,
    is_qrator_challenge,
)

CHROME_CAPTURE_VERSION = "realtyscope-domclick-chrome-ssr-capture-v1"
DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE = (
    "https://domclick.ru/search?deal_type=sale&category=living&offer_type=flat"
    "&offer_type=layout&aids=2299&offset={offset}"
)
DEFAULT_CAPTURE_MODE = "chrome_assisted_ssr_compact_json"
DEFAULT_CHROME_PROFILE_DIRECTORY = "Default"
DEFAULT_OUTPUT_ROOT = Path("data/raw/domclick")
DEFAULT_OFFSET_START = 0
DEFAULT_OFFSET_STOP = 1980
DEFAULT_OFFSET_STEP = 20
DEFAULT_MAX_PAGES = 100
DEFAULT_DELAY_SECONDS = 3.0
DEFAULT_TIMEOUT_SECONDS = 90.0
DEFAULT_VIRTUAL_TIME_BUDGET_MS = 10_000
DOMCLICK_BLOCKED_MARKERS = (
    "captcha",
    "403 | домклик",
    "похоже, ваш запрос выглядит необычно",
    "капча",
    "подтвердите, что вы не робот",
    "авторизуйтесь",
    "войдите в аккаунт",
    "login wall",
)


@dataclass(frozen=True)
class DomclickChromeCaptureResult:
    snapshot_dir: Path
    manifest_path: Path
    files_written: int
    records_seen: int


def build_domclick_search_urls(
    *,
    url_template: str = DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE,
    offset_start: int = DEFAULT_OFFSET_START,
    offset_stop: int = DEFAULT_OFFSET_STOP,
    offset_step: int = DEFAULT_OFFSET_STEP,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> list[tuple[int, str]]:
    if "{offset}" not in url_template:
        raise ValueError("url_template must contain {offset}")
    if offset_start < 0:
        raise ValueError("offset_start must be zero or greater")
    if offset_stop < offset_start:
        raise ValueError("offset_stop must be greater than or equal to offset_start")
    if offset_step <= 0:
        raise ValueError("offset_step must be greater than zero")
    if max_pages <= 0:
        raise ValueError("max_pages must be greater than zero")

    urls: list[tuple[int, str]] = []
    for offset in range(offset_start, offset_stop + 1, offset_step):
        urls.append((offset, url_template.format(offset=offset)))
        if len(urls) >= max_pages:
            break
    return urls


def capture_domclick_chrome_ssr_snapshots(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    collection_date: date | None = None,
    url_template: str = DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE,
    offset_start: int = DEFAULT_OFFSET_START,
    offset_stop: int = DEFAULT_OFFSET_STOP,
    offset_step: int = DEFAULT_OFFSET_STEP,
    max_pages: int = DEFAULT_MAX_PAGES,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    virtual_time_budget_ms: int = DEFAULT_VIRTUAL_TIME_BUDGET_MS,
    chrome_path: Path | None = None,
    chrome_user_data_dir: Path | None = None,
    chrome_profile_directory: str = DEFAULT_CHROME_PROFILE_DIRECTORY,
    capture_mode: str = DEFAULT_CAPTURE_MODE,
    min_records: int = 1,
    operator_note: str | None = None,
    capture_page_dom: Callable[[str], str] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> DomclickChromeCaptureResult:
    if delay_seconds < 0:
        raise ValueError("delay_seconds must be zero or greater")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")
    if virtual_time_budget_ms <= 0:
        raise ValueError("virtual_time_budget_ms must be greater than zero")
    if min_records < 0:
        raise ValueError("min_records must be zero or greater")
    if not chrome_profile_directory.strip():
        raise ValueError("chrome_profile_directory must not be blank")

    urls = build_domclick_search_urls(
        url_template=url_template,
        offset_start=offset_start,
        offset_stop=offset_stop,
        offset_step=offset_step,
        max_pages=max_pages,
    )
    for _offset, url in urls:
        _validate_domclick_search_url(url)

    resolved_chrome_path: Path | None = chrome_path
    resolved_user_data_dir: Path | None = chrome_user_data_dir
    devtools_dumper: ChromeDevToolsDomDumper | None = None
    if capture_page_dom is None:
        resolved_chrome_path = _resolve_chrome_path(chrome_path)
        resolved_user_data_dir = _resolve_chrome_user_data_dir(chrome_user_data_dir)
        _validate_chrome_profile(resolved_user_data_dir, chrome_profile_directory)
        devtools_dumper = ChromeDevToolsDomDumper(
            chrome_path=resolved_chrome_path,
            chrome_user_data_dir=resolved_user_data_dir,
            chrome_profile_directory=chrome_profile_directory,
            timeout_seconds=timeout_seconds,
            virtual_time_budget_ms=virtual_time_budget_ms,
        )
        capture_page_dom = devtools_dumper.dump_dom

    collection_date = collection_date or datetime.now(UTC).date()
    snapshot_dir = output_root / f"{collection_date.isoformat()}-bulk"
    _ensure_fresh_snapshot_dir(snapshot_dir)
    payloads_dir = snapshot_dir / "payloads"
    payloads_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, object]] = []
    total_records_seen = 0
    capture_context = devtools_dumper if devtools_dumper is not None else nullcontext()
    with capture_context:
        for index, (offset, url) in enumerate(urls, start=1):
            page_dom = capture_page_dom(url)
            _raise_if_blocked_page(page_dom, url)
            payload = extract_domclick_ssr_state_payload(page_dom)
            if payload is None:
                raise ValueError(f"Domclick page does not contain parseable SSR state: {url}")

            records_seen = _count_records_seen(payload, source_url=url)
            total_records_seen += records_seen
            relative_path = Path("payloads") / f"search-offset-{offset:06d}.json"
            compact_text = canonical_json(payload) + "\n"
            output_path = snapshot_dir / relative_path
            output_path.write_text(compact_text, encoding="utf-8")
            content_bytes = compact_text.encode("utf-8")
            entries.append(
                {
                    "source_url": url,
                    "source_type": "domclick_json",
                    "path": relative_path.as_posix(),
                    "offset": offset,
                    "fetched_at": _utc_now_iso(),
                    "capture_status": "rendered",
                    "records_seen": records_seen,
                    "content_bytes": len(content_bytes),
                    "content_sha256": hashlib.sha256(content_bytes).hexdigest(),
                }
            )

            if index < len(urls) and delay_seconds > 0:
                sleep(delay_seconds)

    if total_records_seen < min_records:
        raise RuntimeError(
            "Domclick Chrome capture count is below threshold: "
            f"records_seen={total_records_seen} min_records={min_records}"
        )

    manifest_path = snapshot_dir / "manifest.json"
    manifest = _build_manifest(
        collection_date=collection_date,
        capture_mode=capture_mode,
        url_template=url_template,
        offset_start=offset_start,
        offset_stop=offset_stop,
        offset_step=offset_step,
        max_pages=max_pages,
        delay_seconds=delay_seconds,
        timeout_seconds=timeout_seconds,
        virtual_time_budget_ms=virtual_time_budget_ms,
        chrome_path=resolved_chrome_path,
        chrome_user_data_dir=resolved_user_data_dir,
        chrome_profile_directory=chrome_profile_directory,
        entries=entries,
        records_seen=total_records_seen,
        operator_note=operator_note,
    )
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return DomclickChromeCaptureResult(
        snapshot_dir=snapshot_dir,
        manifest_path=manifest_path,
        files_written=len(entries),
        records_seen=total_records_seen,
    )


def dump_dom_with_chrome(
    url: str,
    *,
    chrome_path: Path,
    chrome_user_data_dir: Path,
    chrome_profile_directory: str,
    timeout_seconds: float,
    virtual_time_budget_ms: int,
) -> str:
    command = [
        str(chrome_path),
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={chrome_user_data_dir}",
        f"--profile-directory={chrome_profile_directory}",
        f"--virtual-time-budget={virtual_time_budget_ms}",
        "--dump-dom",
        url,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()[:1000]
        raise RuntimeError(f"Chrome DOM dump failed for {url!r}: {stderr}")
    page_dom = completed.stdout.strip()
    if not page_dom:
        try:
            return dump_dom_with_chrome_devtools(
                url=url,
                chrome_path=chrome_path,
                chrome_user_data_dir=chrome_user_data_dir,
                chrome_profile_directory=chrome_profile_directory,
                timeout_seconds=timeout_seconds,
                virtual_time_budget_ms=virtual_time_budget_ms,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Chrome DOM dump returned an empty document for {url!r}; "
                f"DevTools fallback failed: {exc}"
            ) from exc
    return page_dom


def dump_dom_with_chrome_devtools(
    *,
    url: str,
    chrome_path: Path,
    chrome_user_data_dir: Path,
    chrome_profile_directory: str,
    timeout_seconds: float,
    virtual_time_budget_ms: int,
) -> str:
    with ChromeDevToolsDomDumper(
        chrome_path=chrome_path,
        chrome_user_data_dir=chrome_user_data_dir,
        chrome_profile_directory=chrome_profile_directory,
        timeout_seconds=timeout_seconds,
        virtual_time_budget_ms=virtual_time_budget_ms,
    ) as dumper:
        return dumper.dump_dom(url)


class ChromeDevToolsDomDumper:
    def __init__(
        self,
        *,
        chrome_path: Path,
        chrome_user_data_dir: Path,
        chrome_profile_directory: str,
        timeout_seconds: float,
        virtual_time_budget_ms: int,
    ) -> None:
        self.chrome_path = chrome_path
        self.chrome_user_data_dir = chrome_user_data_dir
        self.chrome_profile_directory = chrome_profile_directory
        self.timeout_seconds = timeout_seconds
        self.virtual_time_budget_ms = virtual_time_budget_ms
        self.port: int | None = None
        self.browser_ws_url: str | None = None
        self.process: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> ChromeDevToolsDomDumper:
        self.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def start(self) -> None:
        if self.port is not None:
            return
        self.port = _reserve_local_port()
        command = [
            str(self.chrome_path),
            f"--user-data-dir={self.chrome_user_data_dir}",
            f"--profile-directory={self.chrome_profile_directory}",
            f"--remote-debugging-port={self.port}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-position=-32000,-32000",
            "--window-size=1280,900",
            "about:blank",
        ]
        self.process = _start_chrome_devtools_browser(command)
        version = asyncio.run(
            _wait_for_devtools_json(self.port, "/json/version", self.timeout_seconds)
        )
        self.browser_ws_url = _string_value(version.get("webSocketDebuggerUrl"))

    def dump_dom(self, url: str) -> str:
        if self.port is None:
            self.start()
        if self.port is None:
            raise RuntimeError("Chrome DevTools was not started")
        return asyncio.run(
            _dump_dom_from_devtools_page(
                port=self.port,
                url=url,
                timeout_seconds=self.timeout_seconds,
                virtual_time_budget_ms=self.virtual_time_budget_ms,
            )
        )

    def close(self) -> None:
        if self.browser_ws_url:
            asyncio.run(_close_devtools_browser(self.browser_ws_url))
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            with suppress(subprocess.TimeoutExpired):
                self.process.wait(timeout=5)
        if self.process is not None and self.process.poll() is None:  # pragma: no cover
            self.process.kill()
        if os.name == "nt" and self.port is not None:
            _stop_windows_chrome_devtools_processes(self.port)
        self.port = None
        self.browser_ws_url = None
        self.process = None


async def _dump_dom_from_devtools_page(
    *,
    port: int,
    url: str,
    timeout_seconds: float,
    virtual_time_budget_ms: int,
) -> str:
    try:
        import websockets
    except ImportError as exc:  # pragma: no cover - depends on installed extras.
        raise RuntimeError("websockets is required for Chrome DevTools fallback") from exc

    pages = await _wait_for_devtools_page_list(port, timeout_seconds)
    page = next((item for item in pages if item.get("type") == "page"), None)
    if page is None:
        raise RuntimeError("Chrome DevTools did not expose a page target")
    page_ws_url = _string_value(page.get("webSocketDebuggerUrl"))
    if page_ws_url is None:
        raise RuntimeError("Chrome DevTools page target has no websocket URL")

    async with websockets.connect(page_ws_url, open_timeout=5, max_size=None) as websocket:
        next_id = 0

        async def send(method: str, params: Mapping[str, object] | None = None) -> dict[str, Any]:
            nonlocal next_id
            next_id += 1
            message_id = next_id
            await websocket.send(
                json.dumps({"id": message_id, "method": method, "params": params or {}})
            )
            while True:
                response = json.loads(await websocket.recv())
                if response.get("id") == message_id:
                    if "error" in response:
                        raise RuntimeError(f"Chrome DevTools {method} failed: {response['error']}")
                    return response

        await send("Page.enable")
        await send("Runtime.enable")
        await send("Page.navigate", {"url": url})

        deadline = time.monotonic() + timeout_seconds
        render_seconds = max(1.0, min(virtual_time_budget_ms / 1000.0, timeout_seconds))
        render_deadline = time.monotonic() + render_seconds
        latest_html = ""
        while time.monotonic() < deadline:
            ssr_result = await send(
                "Runtime.evaluate",
                {
                    "expression": (
                        "(() => { const state = window.__SSR_STATE__; "
                        "return state == null ? null : JSON.stringify(state); })()"
                    ),
                    "returnByValue": True,
                },
            )
            ssr_json = _devtools_value(ssr_result).strip()
            if ssr_json:
                return f"<html><script>window.__SSR_STATE__={ssr_json};</script></html>"

            result = await send(
                "Runtime.evaluate",
                {
                    "expression": "document.documentElement.outerHTML",
                    "returnByValue": True,
                },
            )
            latest_html = _devtools_value(result).strip()
            if latest_html and extract_domclick_ssr_state_payload(latest_html) is not None:
                return latest_html
            if latest_html and _page_has_blocked_marker(latest_html):
                return latest_html
            if (
                latest_html
                and not url.startswith("https://domclick.ru/search?")
                and time.monotonic() >= render_deadline
            ):
                return latest_html
            await asyncio.sleep(0.5)
        if latest_html:
            return latest_html
        raise RuntimeError("Chrome DevTools returned an empty document")


def _start_chrome_devtools_browser(command: Sequence[str]) -> subprocess.Popen[bytes] | None:
    if os.name != "nt":
        return subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    powershell = shutil.which("powershell.exe") or "powershell.exe"
    ps_args = ",".join(_powershell_single_quote(argument) for argument in command[1:])
    ps_command = (
        "Start-Process -FilePath "
        f"{_powershell_single_quote(command[0])} "
        f"-ArgumentList @({ps_args}) -WindowStyle Hidden"
    )
    completed = subprocess.run(
        [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"PowerShell Start-Process failed for Chrome: {stderr[:1000]}")
    return None


def _powershell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _stop_windows_chrome_devtools_processes(port: int) -> None:
    escaped = f"remote-debugging-port={port}"
    ps_command = (
        "Get-CimInstance Win32_Process -Filter \"name = 'chrome.exe'\" | "
        f"Where-Object {{ $_.CommandLine -like '*{escaped}*' }} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    with suppress(Exception):
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _reserve_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


async def _wait_for_devtools_json(port: int, path: str, timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                return payload
            raise RuntimeError(f"Chrome DevTools {path} did not return an object")
        except Exception as exc:  # noqa: BLE001 - polling endpoint readiness.
            last_error = exc
            await asyncio.sleep(0.2)
    raise RuntimeError(f"Chrome DevTools endpoint did not become ready: {last_error}")


async def _wait_for_devtools_page_list(port: int, timeout_seconds: float) -> list[dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with suppress(Exception):
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/list", timeout=2
            ) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, list):
                return [item for item in payload if isinstance(item, dict)]
        await asyncio.sleep(0.2)
    raise RuntimeError("Chrome DevTools page list did not become ready")


async def _close_devtools_browser(browser_ws_url: str) -> None:
    with suppress(Exception):
        import websockets

        async with websockets.connect(browser_ws_url, open_timeout=5) as websocket:
            await websocket.send(json.dumps({"id": 1, "method": "Browser.close", "params": {}}))


def _devtools_value(response: Mapping[str, object]) -> str:
    result = response.get("result")
    if not isinstance(result, Mapping):
        return ""
    nested = result.get("result")
    if not isinstance(nested, Mapping):
        return ""
    value = nested.get("value")
    return value if isinstance(value, str) else ""


def _string_value(value: object) -> str | None:
    return value if isinstance(value, str) else None


def extract_domclick_ssr_state_payload(page_text: str) -> dict[str, Any] | list[Any] | None:
    marker = re.search(r"window\.__SSR_STATE__\s*=", page_text)
    if marker is None:
        return None

    object_start = page_text.find("{", marker.end())
    if object_start < 0:
        return None
    object_end = _find_balanced_json_object_end(page_text, object_start)
    if object_end is None:
        return None

    object_text = page_text[object_start : object_end + 1]
    object_text = re.sub(r"(?<=[\[:,])\s*undefined\s*(?=[,}\]])", "null", object_text)
    for candidate in (object_text, _html_unescape(object_text)):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict | list):
            return payload
    return None


def _find_balanced_json_object_end(text: str, start: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _html_unescape(text: str) -> str:
    # Avoid importing html.parser for a single entity-unescape fallback.
    import html

    return html.unescape(text)


def _count_records_seen(payload: dict[str, Any] | list[Any], *, source_url: str) -> int:
    batch = parse_domclick_payload(
        payload,
        source_url=source_url,
        observed_at=datetime.now(UTC),
        config=DomclickCollectorConfig(max_records=10_000),
    )
    return batch.records_seen


def _validate_domclick_search_url(url: str) -> None:
    if not url.startswith("https://domclick.ru/search?"):
        raise ValueError(f"Expected a Domclick search URL, got {url!r}")


def _raise_if_blocked_page(page_dom: str, url: str) -> None:
    if is_qrator_challenge(page_dom):
        raise DomclickAccessBlocked(f"Domclick returned a QRATOR challenge for {url!r}")
    if _page_has_blocked_marker(page_dom):
        raise DomclickAccessBlocked(
            f"Domclick browser capture hit a CAPTCHA/login/unusual request boundary for {url!r}"
        )


def _page_has_blocked_marker(page_dom: str) -> bool:
    lowered = page_dom.lower()
    return any(marker in lowered for marker in DOMCLICK_BLOCKED_MARKERS)


def _ensure_fresh_snapshot_dir(snapshot_dir: Path) -> None:
    if not snapshot_dir.exists():
        return
    if any(snapshot_dir.iterdir()):
        raise FileExistsError(
            f"Refusing to write Chrome capture into a non-empty snapshot directory: {snapshot_dir}"
        )


def _build_manifest(
    *,
    collection_date: date,
    capture_mode: str,
    url_template: str,
    offset_start: int,
    offset_stop: int,
    offset_step: int,
    max_pages: int,
    delay_seconds: float,
    timeout_seconds: float,
    virtual_time_budget_ms: int,
    chrome_path: Path | None,
    chrome_user_data_dir: Path | None,
    chrome_profile_directory: str,
    entries: Sequence[Mapping[str, object]],
    records_seen: int,
    operator_note: str | None,
) -> dict[str, object]:
    manifest: dict[str, object] = {
        "source_name": "domclick",
        "collection_date": collection_date.isoformat(),
        "collector_version": CHROME_CAPTURE_VERSION,
        "capture_mode": capture_mode,
        "base_url": DOMCLICK_BASE_URL,
        "search_scope": "moscow_sale_apartments",
        "area_id": "2299",
        "url_template": url_template,
        "offset_start": offset_start,
        "offset_stop": offset_stop,
        "offset_step": offset_step,
        "max_pages": max_pages,
        "delay_seconds": delay_seconds,
        "timeout_seconds": timeout_seconds,
        "virtual_time_budget_ms": virtual_time_budget_ms,
        "chrome_path": str(chrome_path) if chrome_path is not None else None,
        "chrome_user_data_dir": (
            str(chrome_user_data_dir) if chrome_user_data_dir is not None else None
        ),
        "chrome_profile_directory": chrome_profile_directory,
        "blocked_boundary_policy": "stop_on_qrator_captcha_login_wall",
        "files_written": len(entries),
        "records_seen": records_seen,
        "entries": list(entries),
    }
    if operator_note:
        manifest["operator_note"] = operator_note
    return manifest


def _resolve_chrome_path(chrome_path: Path | None) -> Path:
    candidates: list[Path] = []
    env_path = os.environ.get("REALTYSCOPE_CHROME_PATH")
    if chrome_path is not None:
        candidates.append(chrome_path)
    if env_path:
        candidates.append(Path(env_path))
    for executable in ("chrome.exe", "chrome", "google-chrome", "google-chrome-stable"):
        found = shutil.which(executable)
        if found:
            candidates.append(Path(found))
    for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        root = os.environ.get(env_var)
        if root:
            candidates.append(Path(root) / "Google" / "Chrome" / "Application" / "chrome.exe")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Could not find Chrome. Pass --chrome-path or set REALTYSCOPE_CHROME_PATH."
    )


def _resolve_chrome_user_data_dir(chrome_user_data_dir: Path | None) -> Path:
    if chrome_user_data_dir is not None:
        return chrome_user_data_dir
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "Google" / "Chrome" / "User Data"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    return Path.home() / ".config" / "google-chrome"


def _validate_chrome_profile(user_data_dir: Path, profile_directory: str) -> None:
    if not user_data_dir.is_dir():
        raise FileNotFoundError(f"Chrome user data directory does not exist: {user_data_dir}")
    profile_path = user_data_dir / profile_directory
    if not profile_path.is_dir():
        raise FileNotFoundError(
            f"Chrome profile directory does not exist: {profile_path}. "
            "For Person 1 on this workstation, use --profile-directory Default."
        )


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _print_json(payload: Mapping[str, object]) -> None:
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture bounded Domclick search SSR state with Chrome and write compact JSON "
            "snapshots. This stops on QRATOR/CAPTCHA/login boundaries."
        )
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--collection-date", type=date.fromisoformat, default=None)
    parser.add_argument("--url-template", default=DEFAULT_DOMCLICK_SEARCH_URL_TEMPLATE)
    parser.add_argument("--offset-start", type=int, default=DEFAULT_OFFSET_START)
    parser.add_argument("--offset-stop", type=int, default=DEFAULT_OFFSET_STOP)
    parser.add_argument("--offset-step", type=int, default=DEFAULT_OFFSET_STEP)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--delay-seconds", type=float, default=DEFAULT_DELAY_SECONDS)
    parser.add_argument("--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--virtual-time-budget-ms", type=int, default=DEFAULT_VIRTUAL_TIME_BUDGET_MS
    )
    parser.add_argument("--chrome-path", type=Path, default=None)
    parser.add_argument("--chrome-user-data-dir", type=Path, default=None)
    parser.add_argument("--profile-directory", default=DEFAULT_CHROME_PROFILE_DIRECTORY)
    parser.add_argument("--capture-mode", default=DEFAULT_CAPTURE_MODE)
    parser.add_argument("--min-records", type=int, default=1)
    parser.add_argument("--operator-note", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = capture_domclick_chrome_ssr_snapshots(
        output_root=args.output_root,
        collection_date=args.collection_date,
        url_template=args.url_template,
        offset_start=args.offset_start,
        offset_stop=args.offset_stop,
        offset_step=args.offset_step,
        max_pages=args.max_pages,
        delay_seconds=args.delay_seconds,
        timeout_seconds=args.timeout_seconds,
        virtual_time_budget_ms=args.virtual_time_budget_ms,
        chrome_path=args.chrome_path,
        chrome_user_data_dir=args.chrome_user_data_dir,
        chrome_profile_directory=args.profile_directory,
        capture_mode=args.capture_mode,
        min_records=args.min_records,
        operator_note=args.operator_note,
    )
    payload = {
        "snapshot_dir": str(result.snapshot_dir),
        "manifest_path": str(result.manifest_path),
        "files_written": result.files_written,
        "records_seen": result.records_seen,
    }
    if args.json:
        _print_json(payload)
    else:
        print(
            "Captured Domclick Chrome SSR snapshots "
            f"files_written={result.files_written} records_seen={result.records_seen} "
            f"snapshot_dir={result.snapshot_dir}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
