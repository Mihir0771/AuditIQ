"""Asynchronous polite web crawler engine with robots.txt, sitemaps, and link graph builder."""

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from selectolax.lexbor import LexborHTMLParser

from auditiq.crawler.graph import LinkGraph
from auditiq.crawler.normalizer import is_internal_url, normalize_url
from auditiq.crawler.renderer import SelectiveRenderer
from auditiq.crawler.robots import RobotsTxtParser
from auditiq.crawler.sitemap import SitemapParser
from auditiq.crawler.ssrf import SSRFValidationError, validate_url_safety
from auditiq.models.snapshot import CrawlResult, PageSnapshot, RedirectHop

logger = logging.getLogger("auditiq.crawler.engine")


class HttpCrawler:
    """Production-grade asynchronous web crawler adhering to RFC 9309 and ethical politeness."""

    def __init__(
        self,
        start_url: str,
        max_pages: int = 200,
        max_depth: int = 4,
        concurrency: int = 5,
        timeout_sec: float = 15.0,
        respect_robots: bool = True,
        user_agent: str = "AuditIQBot/1.0 (+https://auditiq.dev/bot)",
        render_sample: int = 5,
    ) -> None:
        self.start_url = normalize_url(start_url)
        parsed = urlparse(self.start_url)
        self.base_domain = parsed.netloc.lower()
        self.base_scheme = parsed.scheme.lower()
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.concurrency = concurrency
        self.timeout_sec = timeout_sec
        self.respect_robots = respect_robots
        self.user_agent = user_agent
        self.render_sample = render_sample

        self.robots_parser: RobotsTxtParser | None = None
        self.llms_txt_content: str | None = None
        self.llms_txt_status: int | None = None
        self.link_graph = LinkGraph(start_url=self.start_url)
        self.snapshots: dict[str, PageSnapshot] = {}
        self.discovered_sitemaps: set[str] = set()
        self.sitemap_urls: set[str] = set()

        self._visited: set[str] = set()
        self._queue: list[tuple[str, int]] = []
        self._semaphore = asyncio.Semaphore(concurrency)
        self._renderer = SelectiveRenderer(timeout_sec=timeout_sec)
        self._last_request_time: float = 0.0
        self._crawl_delay: float = 0.2  # Default polite 200ms delay

    async def crawl(
        self,
        progress_callback: Callable[[str, int, int], None] | None = None,
        screenshot_dir: Path | None = None,
    ) -> CrawlResult:
        """Executes the complete crawl pipeline."""
        start_time = time.perf_counter()
        logger.info(
            "Starting crawl for %s (max_pages=%d, depth=%d)",
            self.start_url,
            self.max_pages,
            self.max_depth,
        )

        # Validate start URL against SSRF
        validate_url_safety(self.start_url)

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
        }

        async with httpx.AsyncClient(
            headers=headers, verify=False, timeout=self.timeout_sec
        ) as client:
            # 1. Fetch & parse robots.txt
            await self._fetch_robots_txt(client)

            # 2. Probe /llms.txt
            await self._fetch_llms_txt(client)

            # 3. Fetch & parse Sitemaps
            await self._discover_sitemaps(client)

            # 4. Seed queue with start_url and sitemap URLs (depth 1 for sitemaps)
            self._queue.append((self.start_url, 0))
            for s_url in list(self.sitemap_urls)[: self.max_pages]:
                if s_url not in [u for u, _ in self._queue]:
                    self._queue.append((s_url, 1))

            # 4. Asynchronous BFS crawl loop
            rendered_count = 0
            while self._queue and len(self.snapshots) < self.max_pages:
                batch_tasks: list[Coroutine[Any, Any, PageSnapshot]] = []
                # Drain next batch up to concurrency limit
                while (
                    self._queue
                    and len(batch_tasks) < self.concurrency
                    and len(self.snapshots) + len(batch_tasks) < self.max_pages
                ):
                    url, depth = self._queue.pop(0)
                    if url in self._visited or depth > self.max_depth:
                        continue
                    self._visited.add(url)

                    # Check robots.txt rules
                    if (
                        self.respect_robots
                        and self.robots_parser
                        and not self.robots_parser.is_allowed(self.user_agent, url)
                    ):
                        logger.info("Skipping robots-disallowed URL: %s", url)
                        self.snapshots[url] = PageSnapshot(
                            url=url,
                            status_code=403,
                            depth=depth,
                            error="Blocked by robots.txt",
                        )
                        continue

                    # Determine if this page should be rendered in headless browser
                    should_render = rendered_count < self.render_sample
                    if should_render:
                        rendered_count += 1

                    batch_tasks.append(
                        self._fetch_and_process_page(
                            client, url, depth, should_render, screenshot_dir
                        )
                    )

                if not batch_tasks:
                    break

                results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, PageSnapshot):
                        self.snapshots[res.url] = res
                        if progress_callback:
                            progress_callback(res.url, len(self.snapshots), self.max_pages)

            # 5. Compute graph metrics (depths and orphan pages)
            self.link_graph.compute_depths()
            for url, snap in self.snapshots.items():
                snap.inlinks_count = self.link_graph.get_inlinks_count(url)
                if url in self.link_graph.depths:
                    snap.depth = self.link_graph.depths[url]

        duration = round(time.perf_counter() - start_time, 2)
        logger.info("Crawl completed: %d pages in %.2fs", len(self.snapshots), duration)

        return CrawlResult(
            start_url=self.start_url,
            base_domain=self.base_domain,
            pages=self.snapshots,
            sitemap_urls=self.sitemap_urls,
            robots_txt_content=self.robots_parser.info.raw_content if self.robots_parser else None,
            robots_txt_status=200
            if self.robots_parser and self.robots_parser.info.raw_content
            else None,
            llms_txt_content=self.llms_txt_content,
            llms_txt_status=self.llms_txt_status,
            crawl_duration_sec=duration,
            total_urls_discovered=len(self._visited) + len(self._queue),
            total_pages_crawled=len(self.snapshots),
        )

    async def _fetch_robots_txt(self, client: httpx.AsyncClient) -> None:
        """Fetches and parses /robots.txt."""
        robots_url = f"{self.base_scheme}://{self.base_domain}/robots.txt"
        try:
            resp = await client.get(robots_url, timeout=10.0, follow_redirects=True)
            if resp.status_code == 200:
                self.robots_parser = RobotsTxtParser(resp.text)
                # Check for explicit crawl delay
                delay = self.robots_parser.get_crawl_delay(self.user_agent)
                if delay:
                    self._crawl_delay = min(5.0, max(0.2, delay))
                for sm in self.robots_parser.info.sitemaps:
                    self.discovered_sitemaps.add(sm)
        except Exception as e:
            logger.debug("Failed to fetch robots.txt for %s: %s", self.base_domain, e)
            self.robots_parser = RobotsTxtParser("")

    async def _fetch_llms_txt(self, client: httpx.AsyncClient) -> None:
        """Probes for /llms.txt standard file."""
        llms_url = f"{self.base_scheme}://{self.base_domain}/llms.txt"
        try:
            resp = await client.get(llms_url, timeout=10.0, follow_redirects=True)
            self.llms_txt_status = resp.status_code
            if resp.status_code == 200 and resp.text.strip():
                self.llms_txt_content = resp.text
        except Exception as e:
            logger.debug("Failed to fetch llms.txt for %s: %s", self.base_domain, e)
            self.llms_txt_status = None

    async def _discover_sitemaps(self, client: httpx.AsyncClient) -> None:
        """Discovers sitemaps from robots.txt or standard paths."""
        default_sitemaps = [
            f"{self.base_scheme}://{self.base_domain}/sitemap.xml",
            f"{self.base_scheme}://{self.base_domain}/sitemap_index.xml",
        ]
        to_probe = list(self.discovered_sitemaps) or default_sitemaps
        try:
            discovered = await SitemapParser.fetch_and_parse_all(client, to_probe, self.base_domain)
            self.sitemap_urls = discovered
            logger.info("Discovered %d URLs across sitemaps", len(self.sitemap_urls))
        except Exception as e:
            logger.debug("Sitemap discovery failed: %s", e)

    async def _fetch_and_process_page(
        self,
        client: httpx.AsyncClient,
        url: str,
        depth: int,
        should_render: bool,
        screenshot_dir: Path | None,
    ) -> PageSnapshot:
        """Fetches a single page politely, handles redirects, parses HTML, and enqueues outlinks."""
        async with self._semaphore:
            # Politeness throttle
            await asyncio.sleep(self._crawl_delay)

            start = time.perf_counter()
            try:
                # SSRF check on each URL
                validate_url_safety(url)

                # Fetch raw HTTP response
                resp = await client.get(url, follow_redirects=True)
                elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

                # Record redirect chain
                redirect_chain = [
                    RedirectHop(url=str(hop.url), status_code=hop.status_code)
                    for hop in resp.history
                ]

                final_url = normalize_url(str(resp.url))
                content_type = resp.headers.get("content-type", "").lower()
                headers_dict = dict(resp.headers)

                # Non-HTML content check
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    return PageSnapshot(
                        url=final_url,
                        status_code=resp.status_code,
                        headers=headers_dict,
                        content_type=content_type,
                        elapsed_ms=elapsed_ms,
                        depth=depth,
                        redirect_chain=redirect_chain,
                    )

                html_text = resp.text

                # Parse DOM with Selectolax
                parser = LexborHTMLParser(html_text)

                # Extract metadata
                title = ""
                title_node = parser.css_first("title")
                if title_node:
                    title = title_node.text(strip=True)

                meta_desc = ""
                desc_node = parser.css_first('meta[name="description"]')
                if desc_node:
                    meta_desc = desc_node.attributes.get("content") or ""

                canonical = ""
                canon_node = parser.css_first('link[rel="canonical"]')
                if canon_node:
                    canonical = canon_node.attributes.get("href") or ""

                h1s = [node.text(strip=True) for node in parser.css("h1") if node.text(strip=True)]

                # Extract headings hierarchy
                headings_hierarchy: list[dict[str, Any]] = []
                for h_node in parser.css("h1, h2, h3, h4, h5, h6"):
                    tag = str(h_node.tag)
                    text = str(h_node.text(strip=True))
                    if text:
                        headings_hierarchy.append({"tag": tag, "text": text})

                # Word count from body
                body_node = parser.css_first("body")
                word_count = (
                    len(body_node.text(separator=" ", strip=True).split()) if body_node else 0
                )

                # Extract outlinks and build link graph
                outlinks_list: list[str] = []
                for link in parser.css("a[href]"):
                    href = link.attributes.get("href") or ""
                    normalized_target = normalize_url(href, base_url=final_url)
                    if normalized_target:
                        anchor = link.text(strip=True)
                        is_internal = is_internal_url(normalized_target, self.base_domain)
                        if is_internal:
                            outlinks_list.append(normalized_target)
                            self.link_graph.add_edge(final_url, normalized_target, anchor)
                            # Enqueue next crawl candidates if within limits
                            if (
                                normalized_target not in self._visited
                                and normalized_target not in [u for u, _ in self._queue]
                                and depth + 1 <= self.max_depth
                            ):
                                self._queue.append((normalized_target, depth + 1))

                # Selective rendering
                rendered_html: str | None = None
                if should_render:
                    render_res = await self._renderer.render_page(
                        final_url, screenshot_dir=screenshot_dir
                    )
                    if render_res.rendered_html:
                        rendered_html = render_res.rendered_html

                return PageSnapshot(
                    url=final_url,
                    status_code=resp.status_code,
                    headers=headers_dict,
                    raw_html=html_text,
                    rendered_html=rendered_html,
                    is_rendered=bool(rendered_html),
                    ttfb_ms=elapsed_ms,
                    elapsed_ms=elapsed_ms,
                    content_type=content_type,
                    depth=depth,
                    redirect_chain=redirect_chain,
                    title=title,
                    meta_description=meta_desc,
                    canonical_url=canonical,
                    h1s=h1s,
                    headings_hierarchy=headings_hierarchy,
                    word_count=word_count,
                    outlinks=outlinks_list,
                )

            except (httpx.RequestError, SSRFValidationError) as exc:
                return PageSnapshot(
                    url=url,
                    status_code=0,
                    depth=depth,
                    error=str(exc),
                )
