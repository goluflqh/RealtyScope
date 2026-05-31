import pytest

from realtyscope.ingestion.domclick_live import (
    DomclickAccessBlocked,
    can_fetch_url,
    collect_domclick_sitemap_locations,
    is_qrator_challenge,
)

ROBOTS_TXT = """
User-agent: *
Disallow: /search
Disallow: /*?*
Allow: /sitemaps/
"""


def test_domclick_robot_rules_block_search_but_allow_sitemap() -> None:
    assert can_fetch_url(ROBOTS_TXT, "https://domclick.ru/search?deal_type=sale") is False
    assert (
        can_fetch_url(
            ROBOTS_TXT,
            "https://domclick.ru/sitemaps/realty/domclick.ru/sitemap.xml",
        )
        is True
    )


def test_qrator_challenge_detection_matches_domclick_block_page() -> None:
    html = """
    <!DOCTYPE html>
    <script src="/__qrator/qauth_utm_v2d_v9118.js" charset="utf-8"></script>
    """

    assert is_qrator_challenge(html) is True


def test_collect_domclick_sitemap_locations_extracts_limited_sitemaps() -> None:
    sitemap_index = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://domclick.ru/sitemaps/realty/domclick.ru/sitemap-page-1.xml.gz</loc></sitemap>
      <sitemap><loc>https://domclick.ru/sitemaps/realty/domclick.ru/sitemap-page-2.xml.gz</loc></sitemap>
    </sitemapindex>
    """

    def fetch_text(url: str) -> str:
        if url.endswith("robots.txt"):
            return ROBOTS_TXT
        return sitemap_index

    locations = collect_domclick_sitemap_locations(fetch_text=fetch_text, max_sitemaps=1)

    assert locations == ["https://domclick.ru/sitemaps/realty/domclick.ru/sitemap-page-1.xml.gz"]


def test_collect_domclick_sitemap_locations_reports_qrator_block() -> None:
    challenge_page = """
    <!DOCTYPE html>
    <script src="/__qrator/qauth_utm_v2d_v9118.js" charset="utf-8"></script>
    """

    def fetch_text(url: str) -> str:
        if url.endswith("robots.txt"):
            return ROBOTS_TXT
        return challenge_page

    with pytest.raises(DomclickAccessBlocked, match="QRATOR"):
        collect_domclick_sitemap_locations(fetch_text=fetch_text)
