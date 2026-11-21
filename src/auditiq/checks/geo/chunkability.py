"""Passage chunkability and RAG context optimization checks (GEO-*)."""

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class PassageChunkingCheck(BaseCheck):
    id = "GEO-PASSAGE-CHUNKING"
    layer = AuditLayer.GEO_READINESS
    title = "RAG & AI Passage Chunkability (Section Length & Coherence)"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "AI answer engines and RAG indexing pipelines chunk pages into 100–300 word passages delimited by "
        "subheadings. Monolithic walls of text (>500 words without subheadings) dilute embedding relevance "
        "and exceed optimal prompt retrieval windows."
    )
    fix_guidance = (
        "Break long content sections into discrete subsections using descriptive H2 and H3 subheadings. Aim for "
        "100 to 250 words per subheaded section with a clear topic sentence at the start."
    )
    references = [
        "https://www.anthropic.com/news/contextual-retrieval",
        "https://platform.openai.com/docs/guides/embeddings",
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        html = snap.raw_html
        if not html or snap.word_count < 200:
            return []

        try:
            parser = LexborHTMLParser(html)
            for tag in parser.css("script, style, noscript, nav, footer, header"):
                tag.decompose()

            # Identify headings and the text following them
            headings = parser.css("h1, h2, h3, h4")
            if not headings:
                if snap.word_count > 400:
                    return [
                        self.create_finding(
                            url=snap.url,
                            status=FindingStatus.WARNING,
                            severity_override=Severity.MEDIUM,
                            evidence=[
                                {
                                    "total_words": snap.word_count,
                                    "heading_count": 0,
                                    "issue": "Page has no subheadings to delimit passages for AI retrieval.",
                                }
                            ],
                            title_override="Monolithic content: 0 subheadings found on long page",
                        )
                    ]
                return []

            # Estimate words between headings
            # A healthy page has an average chunk length between 80 and 350 words per heading
            avg_chunk = snap.word_count / max(1, len(headings))

            if avg_chunk > 450:
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.MEDIUM,
                        evidence=[
                            {
                                "total_words": snap.word_count,
                                "heading_count": len(headings),
                                "avg_words_per_heading": round(avg_chunk, 1),
                                "recommendation": "Optimal chunk length for RAG retrieval is 100-300 words.",
                            }
                        ],
                        title_override=f"Dense passage structure: average {int(avg_chunk)} words per heading",
                        why_override="Long unbroken text sections reduce the retrieval precision of vector embeddings.",
                    )
                ]

            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {
                            "heading_count": len(headings),
                            "avg_words_per_heading": round(avg_chunk, 1),
                            "status": "Well-chunked passage distribution for RAG retrieval",
                        }
                    ],
                )
            ]
        except Exception:
            return []
