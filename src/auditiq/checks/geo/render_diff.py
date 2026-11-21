"""Render difference checks (Raw HTTP vs Rendered DOM) for AI Crawlability."""

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


def _extract_visible_text(html: str) -> str:
    """Extract clean visible text excluding scripts, styles, and comments."""
    if not html:
        return ""
    try:
        parser = LexborHTMLParser(html)
        for tag in parser.css("script, style, noscript, svg, template"):
            tag.decompose()
        body = parser.body
        return body.text(separator=" ", strip=True) if body else parser.text()
    except Exception:
        return ""


def _extract_links(html: str) -> set[str]:
    """Extract all href targets from HTML string."""
    if not html:
        return set()
    links = set()
    try:
        parser = LexborHTMLParser(html)
        for node in parser.css("a[href]"):
            href = node.attributes.get("href")
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                links.add(href.strip())
    except Exception:
        pass
    return links


class RenderDiffTextCheck(BaseCheck):
    id = "GEO-RENDER-DIFF-TEXT"
    layer = AuditLayer.GEO_READINESS
    title = "Client-Side Render Text Loss (Raw HTTP vs Headless DOM)"
    severity = Severity.HIGH
    effort = Effort.LARGE
    impact = 5
    why_it_matters = (
        "Many AI crawlers and indexing pipelines (e.g. GPTBot, PerplexityBot, Common Crawl) fetch raw HTML "
        "without running a full headless JavaScript browser. If key content requires client-side JavaScript "
        "to render, generative engines will completely miss that text."
    )
    fix_guidance = (
        "Implement Server-Side Rendering (SSR), Static Site Generation (SSG), or Incremental Static "
        "Regeneration (ISR) so that primary content is present in the initial HTTP response payload."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics",
        "https://platform.openai.com/docs/bots",
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.is_rendered or not snap.rendered_html:
            return []

        raw_text = _extract_visible_text(snap.raw_html)
        rendered_text = _extract_visible_text(snap.rendered_html)

        raw_word_count = len(raw_text.split())
        rendered_word_count = len(rendered_text.split())

        if rendered_word_count == 0:
            return []

        ratio = raw_word_count / rendered_word_count

        # If rendered text is substantially richer than raw HTML
        if ratio < 0.50:
            missing_pct = round((1.0 - ratio) * 100, 1)
            sev = Severity.CRITICAL if ratio < 0.20 else Severity.HIGH
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    severity_override=sev,
                    evidence=[
                        {
                            "raw_word_count": raw_word_count,
                            "rendered_word_count": rendered_word_count,
                            "content_missing_pct": f"{missing_pct}%",
                            "ssr_status": "Client-Side Rendered (CSR)",
                        }
                    ],
                    title_override=f"Severe client-side render dependency: {missing_pct}% of text missing in raw HTML",
                    why_override="AI crawlers without JavaScript execution will see a nearly empty page.",
                    fix_override="Enable Server-Side Rendering (SSR) so full content is sent in the initial HTML response.",
                )
            ]
        elif ratio < 0.80:
            missing_pct = round((1.0 - ratio) * 100, 1)
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    severity_override=Severity.MEDIUM,
                    evidence=[
                        {
                            "raw_word_count": raw_word_count,
                            "rendered_word_count": rendered_word_count,
                            "content_missing_pct": f"{missing_pct}%",
                        }
                    ],
                    title_override=f"Moderate client-side text hydration: {missing_pct}% of text rendered via JS",
                )
            ]
        else:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {
                            "raw_word_count": raw_word_count,
                            "rendered_word_count": rendered_word_count,
                            "raw_to_rendered_ratio": round(ratio, 2),
                        }
                    ],
                )
            ]


class RenderDiffLinksCheck(BaseCheck):
    id = "GEO-RENDER-DIFF-LINKS"
    layer = AuditLayer.GEO_READINESS
    title = "Client-Side Render Link Discovery (DOM Hydrated Links)"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "If navigation and internal links are inserted exclusively via JavaScript (e.g. single-page application "
        "routers or dynamic menu widgets), lightweight AI crawlers cannot follow links or discover your site's hierarchy."
    )
    fix_guidance = (
        "Ensure standard HTML `<a href>` elements are pre-rendered in the server HTML for all internal navigation "
        "and pagination links."
    )
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/links-crawlable",
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.is_rendered or not snap.rendered_html:
            return []

        raw_links = _extract_links(snap.raw_html)
        rendered_links = _extract_links(snap.rendered_html)

        if not rendered_links:
            return []

        diff_links = rendered_links - raw_links
        # If more than 5 links or 30% of links only appear after JS execution
        if len(rendered_links) > 5 and len(diff_links) / len(rendered_links) > 0.30:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    severity_override=Severity.HIGH,
                    evidence=[
                        {
                            "raw_link_count": len(raw_links),
                            "rendered_link_count": len(rendered_links),
                            "js_only_links_count": len(diff_links),
                            "sample_js_only_links": sorted(diff_links)[:5],
                        }
                    ],
                    title_override=f"{len(diff_links)} links require JavaScript to discover",
                    why_override="AI and fast search crawlers that parse raw HTML will fail to discover these linked pages.",
                )
            ]

        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[
                    {
                        "raw_link_count": len(raw_links),
                        "rendered_link_count": len(rendered_links),
                    }
                ],
            )
        ]
