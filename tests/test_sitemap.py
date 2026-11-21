"""Unit tests for XML sitemap and sitemap index parsing."""

from auditiq.crawler.sitemap import SitemapParser

SAMPLE_URLSET = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>https://example.com/</loc>
      <lastmod>2026-01-01</lastmod>
   </url>
   <url>
      <loc>https://example.com/about</loc>
   </url>
</urlset>
"""

SAMPLE_INDEX = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <sitemap>
      <loc>https://example.com/sitemap-posts.xml</loc>
   </sitemap>
   <sitemap>
      <loc>https://example.com/sitemap-pages.xml</loc>
   </sitemap>
</sitemapindex>
"""


def test_parse_standard_sitemap() -> None:
    pages, sub_sitemaps = SitemapParser.parse_xml(SAMPLE_URLSET, "https://example.com/")
    assert len(pages) == 2
    assert "https://example.com/" in pages
    assert "https://example.com/about" in pages
    assert len(sub_sitemaps) == 0


def test_parse_sitemap_index() -> None:
    pages, sub_sitemaps = SitemapParser.parse_xml(SAMPLE_INDEX, "https://example.com/")
    assert len(pages) == 0
    assert len(sub_sitemaps) == 2
    assert "https://example.com/sitemap-posts.xml" in sub_sitemaps


def test_parse_malformed_xml() -> None:
    pages, sub_sitemaps = SitemapParser.parse_xml(
        b"<html>Not valid XML</html>", "https://example.com/"
    )
    assert len(pages) == 0
    assert len(sub_sitemaps) == 0
