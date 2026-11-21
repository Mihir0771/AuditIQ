"""Technical SEO Performance & Security Hygiene checks (TECH-*)."""

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class TtfbCheck(BaseCheck):
    id = "TECH-TTFB"
    layer = AuditLayer.TECHNICAL
    title = "Time to First Byte (TTFB) Latency"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "High server response latency slows down crawling, burns crawl budget, degrades Core Web Vitals, "
        "and causes AI bots with short timeout thresholds (e.g. 800ms) to abort requests."
    )
    fix_guidance = "Optimize database queries, enable server-side caching, and utilize edge CDNs (Cloudflare/Fastly)."
    references = ["https://web.dev/articles/ttfb"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200:
            return []

        ttfb = snap.ttfb_ms
        if ttfb > 1200:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    severity_override=Severity.HIGH,
                    evidence=[{"ttfb_ms": ttfb, "threshold_ms": 800}],
                    title_override=f"Critical server latency: TTFB is {ttfb:.0f}ms (>1200ms)",
                )
            ]
        elif ttfb > 800:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"ttfb_ms": ttfb, "threshold_ms": 800}],
                    title_override=f"Slow server response: TTFB is {ttfb:.0f}ms (>800ms)",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"ttfb_ms": ttfb}],
            )
        ]


class PageSizeCheck(BaseCheck):
    id = "TECH-PAGE-SIZE"
    layer = AuditLayer.TECHNICAL
    title = "Uncompressed HTML Document Size"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 3
    why_it_matters = (
        "Excessive HTML page weight (>500KB) causes slower DOM parsing, wastes mobile bandwidth, "
        "and risks truncation by web crawlers."
    )
    fix_guidance = "Minify HTML, remove inlined base64 images, and paginate large lists."
    references = [
        "https://web.dev/articles/optimizing-content-efficiency-loading-third-party-javascript"
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.raw_html or snap.status_code != 200:
            return []

        size_kb = len(snap.raw_html.encode("utf-8")) / 1024.0
        if size_kb > 500:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"size_kb": round(size_kb, 1), "recommended_max_kb": 500}],
                    title_override=f"Large HTML document size ({size_kb:.1f} KB > 500 KB)",
                )
            ]
        return []


class ViewportCheck(BaseCheck):
    id = "TECH-VIEWPORT"
    layer = AuditLayer.TECHNICAL
    title = "Mobile Responsive Viewport Configuration"
    severity = Severity.HIGH
    effort = Effort.SMALL
    impact = 4
    why_it_matters = (
        "Mobile-first indexing requires a responsive viewport tag so pages render correctly across "
        "smartphones, tablets, and mobile crawlers."
    )
    fix_guidance = (
        "Add <meta name='viewport' content='width=device-width, initial-scale=1.0'> in the <head>."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing"
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.raw_html or snap.status_code != 200:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        viewport_node = parser.css_first('meta[name="viewport"]')
        if not viewport_node or not viewport_node.attributes.get("content"):
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    evidence=[{"error": "No valid viewport meta tag found"}],
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"content": viewport_node.attributes.get("content")}],
            )
        ]


class SecurityHeadersCheck(BaseCheck):
    id = "TECH-SECURITY-HEADERS"
    layer = AuditLayer.TECHNICAL
    title = "Core Security Headers Hygiene"
    severity = Severity.INFO
    effort = Effort.SMALL
    impact = 1
    why_it_matters = (
        "Security headers (HSTS, X-Content-Type-Options) protect visitors from clickjacking, MIME sniffing, "
        "and man-in-the-middle downgrade attacks."
    )
    fix_guidance = "Configure web server or CDN to send Strict-Transport-Security and X-Content-Type-Options headers."
    references = ["https://web.dev/articles/security-headers"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200:
            return []

        missing_headers = []
        if "strict-transport-security" not in snap.headers:
            missing_headers.append("Strict-Transport-Security (HSTS)")
        if "x-content-type-options" not in snap.headers:
            missing_headers.append("X-Content-Type-Options: nosniff")

        if missing_headers:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"missing_headers": missing_headers}],
                    title_override="Missing recommended security headers (HSTS / nosniff)",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"message": "Security headers present"}],
            )
        ]
