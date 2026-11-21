"""XML Sitemap and Sitemap Index parser with recursive discovery and gzip decompression."""

import contextlib
import gzip
import xml.etree.ElementTree as ET

import httpx

from auditiq.crawler.normalizer import normalize_url


class SitemapParser:
    """Parses standard XML sitemaps and sitemap indexes."""

    XML_NAMESPACES = {
        "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "image": "http://www.google.com/schemas/sitemap-image/1.1",
        "news": "http://www.google.com/schemas/sitemap-news/0.9",
    }

    @classmethod
    def parse_xml(cls, xml_bytes: bytes, base_url: str) -> tuple[set[str], set[str]]:
        """Parses sitemap XML content.

        Returns:
            (discovered_page_urls, discovered_sub_sitemap_urls)
        """
        # Decompress if gzipped
        if xml_bytes.startswith(b"\x1f\x8b"):
            with contextlib.suppress(Exception):
                xml_bytes = gzip.decompress(xml_bytes)

        page_urls: set[str] = set()
        sub_sitemaps: set[str] = set()

        try:
            root = ET.fromstring(xml_bytes)
        except ET.ParseError:
            # Malformed XML
            return page_urls, sub_sitemaps

        # Tag name without namespace
        tag_name = root.tag.split("}")[-1] if "}" in root.tag else root.tag

        if tag_name == "sitemapindex":
            # Sitemap Index containing references to other sitemaps
            for sitemap in root.findall(".//sm:sitemap", cls.XML_NAMESPACES) or root.findall(
                ".//sitemap"
            ):
                loc_node = (
                    sitemap.find("sm:loc", cls.XML_NAMESPACES)
                    if "sm" in cls.XML_NAMESPACES
                    else None
                )
                if loc_node is None:
                    loc_node = sitemap.find("loc")
                if loc_node is not None and loc_node.text:
                    sub_url = normalize_url(loc_node.text.strip(), base_url=base_url)
                    if sub_url:
                        sub_sitemaps.add(sub_url)

        elif tag_name == "urlset":
            # Standard URL set
            for url_node in root.findall(".//sm:url", cls.XML_NAMESPACES) or root.findall(".//url"):
                loc_node = (
                    url_node.find("sm:loc", cls.XML_NAMESPACES)
                    if "sm" in cls.XML_NAMESPACES
                    else None
                )
                if loc_node is None:
                    loc_node = url_node.find("loc")
                if loc_node is not None and loc_node.text:
                    clean_url = normalize_url(loc_node.text.strip(), base_url=base_url)
                    if clean_url:
                        page_urls.add(clean_url)

        return page_urls, sub_sitemaps

    @classmethod
    async def fetch_and_parse_all(
        cls,
        client: httpx.AsyncClient,
        sitemap_urls: list[str],
        base_domain: str,
        max_sitemaps: int = 10,
    ) -> set[str]:
        """Recursively fetches and parses sitemaps and nested sitemap indexes."""
        all_discovered_urls: set[str] = set()
        pending_sitemaps: list[str] = list(sitemap_urls)
        visited_sitemaps: set[str] = set()

        while pending_sitemaps and len(visited_sitemaps) < max_sitemaps:
            current_sitemap = pending_sitemaps.pop(0)
            if current_sitemap in visited_sitemaps:
                continue
            visited_sitemaps.add(current_sitemap)

            try:
                resp = await client.get(current_sitemap, timeout=10.0, follow_redirects=True)
                if resp.status_code == 200:
                    pages, sub_sitemaps = cls.parse_xml(resp.content, base_url=current_sitemap)
                    all_discovered_urls.update(pages)
                    for sub in sub_sitemaps:
                        if sub not in visited_sitemaps and sub not in pending_sitemaps:
                            pending_sitemaps.append(sub)
            except Exception:
                continue

        return all_discovered_urls
