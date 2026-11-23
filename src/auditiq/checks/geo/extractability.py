"""HTML Extractability and Information Structure checks for AI engines (GEO-*)."""

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class SemanticHtmlCheck(BaseCheck):
    id = "GEO-SEMANTIC-HTML"
    layer = AuditLayer.GEO_READINESS
    title = "Semantic HTML Structure vs. Non-Semantic Div Soup"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 3
    why_it_matters = (
        "AI parsing pipelines strip boilerplate and prune DOM trees using semantic tags like <main>, <article>, "
        "<section>, <header>, and <p>. Heavy 'div soup' makes it difficult for LLMs to distinguish primary content "
        "from peripheral chrome and widgets."
    )
    fix_guidance = (
        "Refactor template layout to use standard semantic HTML5 landmarks (<main>, <article>, <section>, <nav>) "
        "and replace styling-only <div> tags with semantic elements."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Glossary/Semantics",
        "https://html.spec.whatwg.org/multipage/sections.html",
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        html = snap.raw_html
        if not html:
            return []

        try:
            parser = LexborHTMLParser(html)
            divs = len(parser.css("div"))
            spans = len(parser.css("span"))
            semantics = len(
                parser.css(
                    "main, article, section, header, nav, aside, p, h1, h2, h3, h4, h5, h6, ul, ol, dl, table, figure"
                )
            )

            total_structural = divs + spans + semantics
            if total_structural < 20 and semantics > 0:
                return []

            if semantics == 0:
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.MEDIUM,
                        evidence=[{"div_count": divs, "span_count": spans, "semantic_count": 0}],
                        title_override="Page lacks semantic HTML5 landmarks (<main>, <article>, <header>, <section>)",
                        why_override="AI web scrapers struggle to segment primary article content without semantic landmarks.",
                    )
                ]

            semantic_ratio = semantics / total_structural

            if semantic_ratio < 0.20 and divs > 40:
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.MEDIUM,
                        evidence=[
                            {
                                "div_count": divs,
                                "span_count": spans,
                                "semantic_element_count": semantics,
                                "semantic_ratio": f"{round(semantic_ratio * 100, 1)}%",
                            }
                        ],
                        title_override=f"Low semantic HTML density ({round(semantic_ratio * 100, 1)}% semantic tags)",
                        why_override="AI web scrapers struggle to segment primary article content from layout containers.",
                    )
                ]

            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {
                            "semantic_ratio": f"{round(semantic_ratio * 100, 1)}%",
                            "semantic_count": semantics,
                        }
                    ],
                )
            ]
        except Exception:
            return []


class TextTrappedCheck(BaseCheck):
    id = "GEO-TRAPPED-TEXT"
    layer = AuditLayer.GEO_READINESS
    title = "Text Trapped in Canvas, Iframes, or Complex SVGs"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Text rendered inside <canvas> elements or loaded inside third-party <iframe> embeds is completely invisible "
        "to standard text extractors used by LLM search agents."
    )
    fix_guidance = (
        "Provide server-rendered HTML text transcripts, data tables, or accessible DOM text alternatives alongside "
        "canvas visualizations or iframes."
    )
    references = [
        "https://www.w3.org/WAI/WCAG21/Understanding/non-text-content.html",
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        html = snap.raw_html
        if not html:
            return []

        try:
            parser = LexborHTMLParser(html)
            canvases = parser.css("canvas")
            iframes = parser.css("iframe")

            issues = []
            if len(canvases) > 2:
                issues.append(f"{len(canvases)} <canvas> elements without verified text fallback")
            if len(iframes) > 3:
                issues.append(f"{len(iframes)} <iframe> embeds containing external content")

            if issues:
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.MEDIUM,
                        evidence=[
                            {
                                "canvas_count": len(canvases),
                                "iframe_count": len(iframes),
                                "issues": issues,
                            }
                        ],
                        title_override=f"Trapped text risk: {', '.join(issues)}",
                    )
                ]

            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[{"canvas_count": len(canvases), "iframe_count": len(iframes)}],
                )
            ]
        except Exception:
            return []


class DataTablesCheck(BaseCheck):
    id = "GEO-DATA-TABLES"
    layer = AuditLayer.GEO_READINESS
    title = "Data Presentation Semantics (Tables vs. Fake Div Grids)"
    severity = Severity.LOW
    effort = Effort.SMALL
    impact = 3
    why_it_matters = (
        "Tabular data encoded in semantic <table> elements with proper <thead> and <th> headers is parsed with high "
        "fidelity into markdown tables by LLMs. Grid-based <div> structures often lose column-row relationships in AI summaries."
    )
    fix_guidance = (
        "Use semantic HTML <table>, <thead>, <tbody>, and <th> tags with 'scope' attributes when displaying tabular data, "
        "pricing comparisons, or technical specifications."
    )
    references = [
        "https://developer.mozilla.org/en-US/docs/Web/HTML/Element/table",
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        html = snap.raw_html
        if not html:
            return []

        try:
            parser = LexborHTMLParser(html)
            tables = parser.css("table")
            if not tables:
                return []

            malformed_tables = 0
            for tbl in tables:
                ths = tbl.css("th")
                if not ths:
                    malformed_tables += 1

            if malformed_tables > 0:
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.LOW,
                        evidence=[
                            {
                                "total_tables": len(tables),
                                "tables_missing_headers": malformed_tables,
                            }
                        ],
                        title_override=f"{malformed_tables} table(s) missing header <th> tags",
                        why_override="AI answer engines parse tables into markdown; missing headers cause column misalignment in answers.",
                    )
                ]

            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[{"table_count": len(tables), "status": "All tables use header tags"}],
                )
            ]
        except Exception:
            return []
