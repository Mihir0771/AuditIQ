"""Technical SEO Crawlability & Indexability checks (TECH-*)."""

import asyncio
from typing import Any
from urllib.parse import urlparse

import httpx
from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext, SiteContext
from auditiq.crawler.normalizer import is_internal_url
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class HostReachabilityCheck(BaseCheck):
    id = "TECH-HOST-REACHABLE"
    layer = AuditLayer.TECHNICAL
    title = "Target Website Reachability & HTTP Availability"
    severity = Severity.CRITICAL
    effort = Effort.LARGE
    impact = 5
    scope = "site"
    why_it_matters = (
        "A website must be reachable and return valid HTTP 200 OK responses to be crawled, indexed, "
        "and cited by search engines and generative AI answer engines."
    )
    fix_guidance = "Resolve DNS resolution failures, server crashes, connection timeouts, or SSL certificate misconfigurations."
    references = ["https://developers.google.com/search/docs/crawling-indexing/http-network-errors"]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings: list[Finding] = []
        start_url = context.crawl_result.start_url
        root_snap = context.crawl_result.pages.get(start_url)
        if not root_snap:
            alt = start_url.rstrip("/") if start_url.endswith("/") else start_url + "/"
            root_snap = context.crawl_result.pages.get(alt)

        if not root_snap or root_snap.status_code >= 400 or root_snap.status_code == 0 or root_snap.error:
            status_code = root_snap.status_code if root_snap else 0
            err = root_snap.error if root_snap else "No response received"
            findings.append(
                self.create_finding(
                    url=start_url,
                    status=FindingStatus.FAIL,
                    severity_override=Severity.CRITICAL,
                    evidence=[{"status_code": status_code, "error": err}],
                    title_override=f"Target Host Unreachable (HTTP {status_code}: {err})",
                    why_override="Search and AI crawlers cannot index or cite this website because the start URL could not be reached.",
                    fix_override="Verify your DNS, hosting server, firewall, and reverse proxy settings.",
                )
            )
        else:
            findings.append(
                self.create_finding(
                    url=start_url,
                    status=FindingStatus.PASS,
                    evidence=[{"status_code": root_snap.status_code, "ttfb_ms": root_snap.ttfb_ms}],
                )
            )
        return findings


class RobotsPresenceCheck(BaseCheck):
    id = "TECH-ROBOTS-PRESENCE"
    layer = AuditLayer.TECHNICAL
    title = "robots.txt Presence & Accessibility"
    severity = Severity.HIGH
    effort = Effort.SMALL
    impact = 4
    scope = "site"
    why_it_matters = (
        "robots.txt is the universal entry point for all web crawlers. Without it, crawlers may "
        "waste crawl budget on non-canonical URLs, internal search parameters, or private endpoints."
    )
    fix_guidance = (
        "Create a valid /robots.txt file at your domain root following RFC 9309 with User-agent, "
        "Disallow, and Sitemap directives."
    )
    references = ["https://developers.google.com/search/docs/crawling-indexing/robots/intro"]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings: list[Finding] = []
        robots_content = context.crawl_result.robots_txt_content
        robots_url = f"{urlparse(context.crawl_result.start_url).scheme}://{context.crawl_result.base_domain}/robots.txt"

        if not robots_content:
            findings.append(
                self.create_finding(
                    url=robots_url,
                    status=FindingStatus.FAIL,
                    evidence=[
                        {"error": "robots.txt was not found or returned non-200 status code"}
                    ],
                    fix_override="Publish a valid /robots.txt file at the root of your domain.",
                )
            )
        else:
            findings.append(
                self.create_finding(
                    url=robots_url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {
                            "bytes": len(robots_content),
                            "snippet": robots_content[:200],
                            "sitemaps_declared": len(context.crawl_result.sitemap_urls),
                        }
                    ],
                )
            )
        return findings


class RobotsBlockingCheck(BaseCheck):
    id = "TECH-ROBOTS-BLOCKING"
    layer = AuditLayer.TECHNICAL
    title = "Accidental Critical Path Blocking in robots.txt"
    severity = Severity.CRITICAL
    effort = Effort.SMALL
    impact = 5
    scope = "site"
    why_it_matters = (
        "Accidental 'Disallow: /' or disallowing core CSS/JS/images prevents search engines and AI "
        "crawlers from indexing content or rendering pages properly."
    )
    fix_guidance = (
        "Audit Disallow rules in robots.txt to ensure the homepage ('/') and primary content paths "
        "remain accessible."
    )
    references = ["https://developers.google.com/search/docs/crawling-indexing/robots/robots_txt"]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings: list[Finding] = []
        robots_content = context.crawl_result.robots_txt_content or ""
        robots_url = f"{urlparse(context.crawl_result.start_url).scheme}://{context.crawl_result.base_domain}/robots.txt"

        # Check for Disallow: / under User-agent: *
        lines = [line_item.strip().lower() for line_item in robots_content.splitlines()]
        current_ua = ""
        is_wildcard = False
        for line in lines:
            if line.startswith("user-agent:"):
                current_ua = line.split(":", 1)[1].strip()
                is_wildcard = current_ua == "*"
            elif line.startswith("disallow:") and is_wildcard:
                val = line.split(":", 1)[1].strip()
                if val == "/":
                    findings.append(
                        self.create_finding(
                            url=robots_url,
                            status=FindingStatus.FAIL,
                            severity_override=Severity.CRITICAL,
                            evidence=[{"line": line, "user_agent": "*", "disallow": "/"}],
                            why_override="A 'Disallow: /' rule for all robots blocks entire search and AI discovery.",
                            fix_override="Remove 'Disallow: /' from the User-agent: * block in /robots.txt.",
                        )
                    )
                    return findings

        findings.append(
            self.create_finding(
                url=robots_url,
                status=FindingStatus.PASS,
                evidence=[{"message": "No catastrophic global Disallow: / rule found."}],
            )
        )
        return findings


class SitemapPresenceCheck(BaseCheck):
    id = "TECH-SITEMAP-PRESENCE"
    layer = AuditLayer.TECHNICAL
    title = "XML Sitemap Discovery & Validity"
    severity = Severity.HIGH
    effort = Effort.SMALL
    impact = 4
    scope = "site"
    why_it_matters = (
        "XML sitemaps provide a roadmap of all canonical, high-value pages, ensuring search engines "
        "discover new and updated content rapidly."
    )
    fix_guidance = "Publish an XML sitemap at /sitemap.xml and reference it in /robots.txt."
    references = ["https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview"]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings: list[Finding] = []
        base = context.crawl_result.base_domain
        scheme = urlparse(context.crawl_result.start_url).scheme
        sitemap_url = f"{scheme}://{base}/sitemap.xml"

        if not context.crawl_result.sitemap_urls:
            findings.append(
                self.create_finding(
                    url=sitemap_url,
                    status=FindingStatus.FAIL,
                    evidence=[{"error": "No valid XML sitemaps discovered or sitemap was empty"}],
                )
            )
        else:
            findings.append(
                self.create_finding(
                    url=sitemap_url,
                    status=FindingStatus.PASS,
                    evidence=[{"discovered_urls_count": len(context.crawl_result.sitemap_urls)}],
                )
            )
        return findings


class SitemapCoverageCheck(BaseCheck):
    id = "TECH-SITEMAP-COVERAGE"
    layer = AuditLayer.TECHNICAL
    title = "Sitemap vs. Crawl Coverage Discrepancies"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 3
    why_it_matters = (
        "Pages discovered during crawling that are missing from sitemaps signal incomplete indexing "
        "coverage, while non-working URLs in sitemaps waste crawler resources."
    )
    fix_guidance = "Regenerate sitemaps dynamically to include all indexable, canonical URLs."
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap"
    ]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings: list[Finding] = []
        sitemap_urls = set(context.crawl_result.sitemap_urls)
        crawled_urls = set(context.crawl_result.pages.keys())

        if not sitemap_urls:
            return findings

        missing_from_sitemap = [
            u
            for u in crawled_urls
            if u not in sitemap_urls and context.crawl_result.pages[u].status_code == 200
        ]
        if missing_from_sitemap:
            findings.append(
                self.create_finding(
                    url=f"https://{context.crawl_result.base_domain}/sitemap.xml",
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "missing_count": len(missing_from_sitemap),
                            "sample_missing": missing_from_sitemap[:5],
                        }
                    ],
                    fix_override="Ensure your automated sitemap generator adds all public indexable pages.",
                )
            )
        return findings


class Status4xx5xxCheck(BaseCheck):
    id = "TECH-STATUS-4XX-5XX"
    layer = AuditLayer.TECHNICAL
    title = "Broken Internal Links (4xx/5xx Client/Server Errors)"
    severity = Severity.CRITICAL
    effort = Effort.MEDIUM
    impact = 5
    why_it_matters = "Broken links deliver poor user experience, waste crawler budget, and cause link equity to drop off a cliff."
    fix_guidance = "Fix the broken source link href or implement a 301 redirect to the correct replacement destination."
    references = ["https://developers.google.com/search/docs/crawling-indexing/http-network-errors"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        findings = []
        snap = context.snapshot
        if snap.status_code >= 400 or snap.status_code == 0 or snap.error:
            inlinks = list(context.site.link_graph.inlinks.get(snap.url, set()))
            status_desc = f"HTTP {snap.status_code}" if snap.status_code > 0 else f"Error: {snap.error or 'Failed connection'}"
            findings.append(
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    severity_override=Severity.CRITICAL
                    if (snap.status_code in (0, 500, 502, 503, 504) or snap.error)
                    else Severity.HIGH,
                    evidence=[
                        {
                            "status_code": snap.status_code,
                            "error": snap.error,
                            "referring_pages": inlinks[:5],
                            "inlinks_count": len(inlinks),
                        }
                    ],
                    title_override=f"Broken Internal Link ({status_desc}) on {snap.url}",
                )
            )
        return findings


class RedirectChainsCheck(BaseCheck):
    id = "TECH-REDIRECT-CHAINS"
    layer = AuditLayer.TECHNICAL
    title = "Redirect Chains & Loops (>1 Hop)"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Each redirect hop adds latency, burns crawl budget, and increases the likelihood that a crawler "
        "gives up before reaching the final destination."
    )
    fix_guidance = (
        "Point links directly to the final 200 OK destination URL, eliminating intermediary hops."
    )
    references = ["https://developers.google.com/search/docs/crawling-indexing/301-redirects"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        findings = []
        chain = context.snapshot.redirect_chain
        if len(chain) > 1:
            findings.append(
                self.create_finding(
                    url=context.snapshot.url,
                    status=FindingStatus.FAIL,
                    evidence=[
                        {
                            "hop_count": len(chain),
                            "chain": [{"url": h.url, "status": h.status_code} for h in chain],
                        }
                    ],
                    fix_override="Update internal links to target the final destination directly.",
                )
            )
        return findings


class OrphanPagesCheck(BaseCheck):
    id = "TECH-ORPHAN-PAGES"
    layer = AuditLayer.TECHNICAL
    title = "Sitemap Orphan Pages (Zero Internal Inlinks)"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 3
    scope = "site"
    why_it_matters = (
        "Pages with zero internal links receive no internal PageRank and are rarely discovered by "
        "crawlers unless specified in sitemaps."
    )
    fix_guidance = "Add contextual internal links from parent category or navigation pages."
    references = ["https://developers.google.com/search/docs/crawling-indexing/links-crawlable"]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings: list[Finding] = []
        orphans = context.link_graph.find_orphan_pages(
            sitemap_urls=context.crawl_result.sitemap_urls,
            crawled_urls=set(context.crawl_result.pages.keys()),
        )
        if orphans:
            findings.append(
                self.create_finding(
                    url=context.crawl_result.start_url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "orphan_count": len(orphans),
                            "sample_orphans": list(orphans)[:5],
                        }
                    ],
                )
            )
        return findings


class CrawlDepthCheck(BaseCheck):
    id = "TECH-CRAWL-DEPTH"
    layer = AuditLayer.TECHNICAL
    title = "Excessive Crawl Click Depth (>4 Clicks)"
    severity = Severity.LOW
    effort = Effort.MEDIUM
    impact = 2
    why_it_matters = (
        "Pages deeper than 4 clicks from the homepage are crawled less frequently and rank poorly "
        "due to diminished link equity distribution."
    )
    fix_guidance = "Flatten the site architecture by introducing topic hub pages, breadcrumbs, and category links."
    references = ["https://developers.google.com/search/docs/crawling-indexing/site-structure"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        findings = []
        if context.snapshot.depth > 4 and context.snapshot.status_code == 200:
            findings.append(
                self.create_finding(
                    url=context.snapshot.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"depth": context.snapshot.depth, "max_recommended": 4}],
                )
            )
        return findings


class CanonicalMissingCheck(BaseCheck):
    id = "TECH-CANONICAL-MISSING"
    layer = AuditLayer.TECHNICAL
    title = "Missing rel='canonical' Link Tag"
    severity = Severity.HIGH
    effort = Effort.SMALL
    impact = 4
    why_it_matters = (
        "Without an explicit canonical tag, search engines must guess which version of a page to index, "
        "leading to duplicate content dilution across trailing slashes, HTTP/HTTPS, and query params."
    )
    fix_guidance = (
        "Add a self-referencing <link rel='canonical' href='https://...'> tag in the <head>."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        findings = []
        snap = context.snapshot
        if snap.status_code == 200 and "text/html" in snap.content_type:
            if not snap.canonical_url:
                findings.append(
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.FAIL,
                        evidence=[{"error": "No rel='canonical' tag found in page HTML"}],
                    )
                )
            else:
                findings.append(
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.PASS,
                        evidence=[{"canonical_url": snap.canonical_url}],
                    )
                )
        return findings


class CanonicalConflictCheck(BaseCheck):
    id = "TECH-CANONICAL-CONFLICT"
    layer = AuditLayer.TECHNICAL
    title = "Conflicting or Unresolvable Canonical Tag"
    severity = Severity.CRITICAL
    effort = Effort.SMALL
    impact = 5
    why_it_matters = (
        "Pointing a canonical to a 404 URL, a redirecting URL, or an unresolvable domain causes "
        "search engines to ignore the canonical directive entirely."
    )
    fix_guidance = (
        "Ensure every canonical tag points to an accessible 200 OK URL on the intended domain."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        findings = []
        snap = context.snapshot
        canon = snap.canonical_url
        if canon and canon in context.site.crawl_result.pages:
            canon_snap = context.site.crawl_result.pages[canon]
            if canon_snap.status_code >= 400:
                findings.append(
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.FAIL,
                        evidence=[
                            {
                                "canonical_target": canon,
                                "target_status": canon_snap.status_code,
                            }
                        ],
                        why_override=f"Canonical points to a broken URL (HTTP {canon_snap.status_code}).",
                    )
                )
            elif len(canon_snap.redirect_chain) > 0:
                findings.append(
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        evidence=[
                            {
                                "canonical_target": canon,
                                "redirects_to": [h.url for h in canon_snap.redirect_chain],
                            }
                        ],
                        why_override="Canonical URL redirects to another destination instead of returning 200 OK directly.",
                    )
                )
        return findings


class NoindexAccidentalCheck(BaseCheck):
    id = "TECH-NOINDEX-ACCIDENTAL"
    layer = AuditLayer.TECHNICAL
    title = "Accidental noindex Directive on Crawled Pages"
    severity = Severity.CRITICAL
    effort = Effort.SMALL
    impact = 5
    why_it_matters = (
        "A 'noindex' directive instructs search engines not to show the page in search results, completely "
        "removing it from organic indexation."
    )
    fix_guidance = "Remove the <meta name='robots' content='noindex'> or X-Robots-Tag: noindex header from public pages."
    references = ["https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        findings = []
        snap = context.snapshot
        x_robots = snap.headers.get("x-robots-tag", "").lower()

        # Check raw html for meta robots noindex
        has_meta_noindex = False
        if snap.raw_html:
            import re

            if re.search(
                r'<meta[^>]+name=["\']robots["\'][^>]+content=["\'][^"\']*noindex',
                snap.raw_html,
                re.I,
            ):
                has_meta_noindex = True

        if (
            "noindex" in x_robots or has_meta_noindex
        ) and snap.url == context.site.config.target_url:
            findings.append(
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    severity_override=Severity.CRITICAL,
                    evidence=[
                        {
                            "meta_noindex": has_meta_noindex,
                            "x_robots_tag": x_robots,
                        }
                    ],
                    why_override="The primary target landing page has an active 'noindex' directive preventing search indexing.",
                )
            )
        return findings


class HttpConsistencyCheck(BaseCheck):
    id = "TECH-HTTP-CONSISTENCY"
    layer = AuditLayer.TECHNICAL
    title = "HTTPS Enforcement & Mixed Content"
    severity = Severity.HIGH
    effort = Effort.SMALL
    impact = 4
    why_it_matters = (
        "HTTPS is a mandatory security baseline and Google ranking signal. Mixed HTTP content triggers "
        "browser security warnings and breaks user trust."
    )
    fix_guidance = "Serve all assets over HTTPS and enforce a 301 redirect from HTTP to HTTPS."
    references = ["https://developers.google.com/search/docs/crawling-indexing/https"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        findings = []
        snap = context.snapshot
        parsed = urlparse(snap.url)
        if parsed.scheme == "http":
            findings.append(
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    evidence=[{"scheme": "http", "secure": False}],
                    fix_override="Enforce HSTS and 301 redirection from http:// to https://.",
                )
            )
        return findings


class WwwConsistencyCheck(BaseCheck):
    id = "TECH-WWW-CONSISTENCY"
    layer = AuditLayer.TECHNICAL
    title = "www vs. non-www Redirection Consistency"
    severity = Severity.MEDIUM
    effort = Effort.SMALL
    impact = 3
    scope = "site"
    why_it_matters = (
        "Allowing both www and non-www versions of a website to return 200 OK splits link authority "
        "and creates duplicate content across domains."
    )
    fix_guidance = "Configure web server or CDN (Cloudflare/Vercel) to redirect the non-canonical host with a 301 status."
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"
    ]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings: list[Finding] = []
        base = context.crawl_result.base_domain
        findings.append(
            self.create_finding(
                url=context.crawl_result.start_url,
                status=FindingStatus.PASS,
                evidence=[{"canonical_host": base}],
            )
        )
        return findings


class BrokenOutboundLinksCheck(BaseCheck):
    id = "TECH-BROKEN-OUTBOUND"
    layer = AuditLayer.TECHNICAL
    title = "Broken Outbound External Links (HTTP 4xx/5xx or Dead Hosts)"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Linking to dead websites, 404 pages, or unresolvable domains signals decayed content to search engines "
        "and damages the user and AI citation experience."
    )
    fix_guidance = "Audit external outbound links and update or remove destinations that return 4xx/5xx or connection errors."
    references = ["https://developers.google.com/search/docs/crawling-indexing/links-crawlable"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or not snap.raw_html or "text/html" not in snap.content_type:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        base_domain = context.site.crawl_result.base_domain

        external_links: set[str] = set()
        for node in parser.css("a[href]"):
            href = (node.attributes.get("href") or "").strip()
            if not href.startswith(("http://", "https://")):
                continue
            if not is_internal_url(href, base_domain):
                external_links.add(href)
            if len(external_links) >= 12:
                break

        if not external_links:
            return []

        broken_links: list[dict[str, Any]] = []

        async def _check_target(client: httpx.AsyncClient, link_url: str) -> None:
            try:
                r = await client.head(link_url)
                if r.status_code in (404, 410, 500, 502, 503, 504):
                    broken_links.append({"url": link_url, "status": r.status_code})
            except Exception as e:
                # DNS failure, connection refused, or timeout
                err_str = str(e) or type(e).__name__
                broken_links.append({"url": link_url, "error": err_str[:80]})

        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                follow_redirects=True,
                timeout=3.0,
                verify=False,
            ) as client:
                await asyncio.gather(
                    *[_check_target(client, link) for link in external_links],
                    return_exceptions=True,
                )
        except Exception:
            pass

        if broken_links:
            sev = Severity.HIGH if len(broken_links) >= 3 else Severity.MEDIUM
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL if len(broken_links) >= 3 else FindingStatus.WARNING,
                    severity_override=sev,
                    evidence=[
                        {
                            "broken_outbound_count": len(broken_links),
                            "tested_count": len(external_links),
                            "broken_targets": broken_links[:5],
                        }
                    ],
                    title_override=f"Broken Outbound Links Detected ({len(broken_links)} unreachable external links)",
                    why_override="Outbound links returning 4xx/5xx or DNS connection errors harm search quality ratings.",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"tested_external_links": len(external_links), "status": "All tested links reachable"}],
            )
        ]
