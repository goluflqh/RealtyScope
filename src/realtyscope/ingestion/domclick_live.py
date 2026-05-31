from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from urllib import request, robotparser
from xml.etree import ElementTree

DOMCLICK_BASE_URL = "https://domclick.ru"
DOMCLICK_ROBOTS_URL = f"{DOMCLICK_BASE_URL}/robots.txt"
DOMCLICK_REALTY_SITEMAP_INDEX_URL = f"{DOMCLICK_BASE_URL}/sitemaps/realty/domclick.ru/sitemap.xml"
DEFAULT_USER_AGENT = "RealtyScope semester project ingestion contact: local-development"


class DomclickAccessBlocked(RuntimeError):
    """Raised when Domclick blocks a controlled public-source acquisition path."""


@dataclass(frozen=True)
class DomclickAccessProbe:
    robots_url: str = DOMCLICK_ROBOTS_URL
    sitemap_index_url: str = DOMCLICK_REALTY_SITEMAP_INDEX_URL
    user_agent: str = DEFAULT_USER_AGENT
    timeout_seconds: float = 20.0


def fetch_text(
    url: str,
    *,
    user_agent: str = DEFAULT_USER_AGENT,
    timeout_seconds: float = 20.0,
) -> str:
    req = request.Request(url, headers={"User-Agent": user_agent})
    with request.urlopen(req, timeout=timeout_seconds) as response:
        return response.read().decode("utf-8", errors="replace")


def can_fetch_url(robots_txt: str, url: str, *, user_agent: str = DEFAULT_USER_AGENT) -> bool:
    parser = robotparser.RobotFileParser()
    parser.parse(robots_txt.splitlines())
    return parser.can_fetch(user_agent, url)


def is_qrator_challenge(text: str) -> bool:
    lowered = text.lower()
    return "/__qrator/" in lowered or "qauth_" in lowered


def extract_sitemap_locations(sitemap_index_xml: str) -> list[str]:
    root = ElementTree.fromstring(sitemap_index_xml)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [node.text.strip() for node in root.findall(".//sm:loc", namespace) if node.text]
    if locations:
        return locations
    return [node.text.strip() for node in root.findall(".//loc") if node.text]


def collect_domclick_sitemap_locations(
    *,
    fetch_text: Callable[[str], str],
    probe: DomclickAccessProbe | None = None,
    max_sitemaps: int = 10,
) -> list[str]:
    probe = probe or DomclickAccessProbe()
    robots_txt = fetch_text(probe.robots_url)
    if not can_fetch_url(robots_txt, probe.sitemap_index_url, user_agent=probe.user_agent):
        raise DomclickAccessBlocked(
            f"Domclick robots.txt does not allow {probe.sitemap_index_url!r}"
        )

    sitemap_index = fetch_text(probe.sitemap_index_url)
    if is_qrator_challenge(sitemap_index):
        raise DomclickAccessBlocked("Domclick returned a QRATOR challenge for the sitemap index")

    return extract_sitemap_locations(sitemap_index)[:max_sitemaps]


def collect_live_domclick_sitemap_locations(
    *,
    probe: DomclickAccessProbe | None = None,
    max_sitemaps: int = 10,
) -> list[str]:
    probe = probe or DomclickAccessProbe()

    def fetch_with_probe(url: str) -> str:
        return fetch_text(
            url,
            user_agent=probe.user_agent,
            timeout_seconds=probe.timeout_seconds,
        )

    return collect_domclick_sitemap_locations(
        fetch_text=fetch_with_probe,
        probe=probe,
        max_sitemaps=max_sitemaps,
    )
