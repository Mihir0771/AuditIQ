"""Content structure, answer-first layouts, and question-heading checks (CONT-*)."""

import re

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class AnswerFirstCheck(BaseCheck):
    id = "CONT-ANSWER-FIRST"
    layer = AuditLayer.CONTENT
    title = "Answer-First Structure (Inverted Pyramid)"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 5
    why_it_matters = (
        "Generative AI models and featured snippet extractors strongly favor content that provides "
        "a direct, succinct answer in the opening 100–150 words rather than burying conclusions."
    )
    fix_guidance = (
        "Open informational articles with a clear definition, immediate summary, or direct answer "
        "to the primary query before delving into history or background."
    )
    references = ["https://developers.google.com/search/docs/fundamentals/creating-helpful-content"]

    DEFINITION_TRIGGERS = [
        r"\bis (?:a|an|the|defined as|often|typically)\b",
        r"\brefers to\b",
        r"\bmeans that\b",
        r"\bconsists of\b",
        r"\bin summary\b",
        r"\bthe answer is\b",
        r"\bto (?:fix|solve|configure|install|calculate)\b",
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or not snap.raw_html or snap.word_count < 250:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        paragraphs = [
            p.text(strip=True)
            for p in parser.css("article p, main p, body p")
            if len(p.text(strip=True)) > 30
        ]
        if not paragraphs:
            return []

        # Analyze the opening paragraph (first 120 words)
        opening_text = " ".join(paragraphs[:2])[:600].lower()

        has_definition = any(re.search(pat, opening_text) for pat in self.DEFINITION_TRIGGERS)
        has_metrics = bool(re.search(r"(\$?\d+(?:\.\d+)?%?|\b\d{4}\b)", opening_text))

        if not has_definition and not has_metrics:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "opening_snippet": opening_text[:180] + "...",
                            "recommendation": "Lead with a direct answer or definition within the first 100 words.",
                        }
                    ],
                    title_override="Content lacks an immediate, direct answer in the opening paragraph",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"snippet": opening_text[:120] + "..."}],
            )
        ]


class QuestionHeadingsCheck(BaseCheck):
    id = "CONT-QUESTION-HEADINGS"
    layer = AuditLayer.CONTENT
    title = "Question-Form Subheadings (User-Intent Mapping)"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Subheadings phrased as direct user questions ('How do I...', 'What is...', 'Why does...') "
        "strongly align with prompt formulations in ChatGPT, Perplexity, and Google AI Overviews."
    )
    fix_guidance = (
        "Structure H2 and H3 subheadings around real natural language questions users ask."
    )
    references = ["https://developers.google.com/search/docs/crawling-indexing/heading-tags"]

    QUESTION_WORDS = (
        "how",
        "what",
        "why",
        "when",
        "where",
        "who",
        "which",
        "can",
        "is",
        "should",
        "does",
    )

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.headings_hierarchy or snap.word_count < 250:
            return []

        subheadings = [
            h["text"]
            for h in snap.headings_hierarchy
            if h.get("tag", "").lower() in ("h2", "h3") and h.get("text")
        ]
        if not subheadings:
            return []

        question_headings = []
        for sh in subheadings:
            first_word = sh.strip().split()[0].lower().rstrip("?:,") if sh.strip().split() else ""
            if sh.strip().endswith("?") or first_word in self.QUESTION_WORDS:
                question_headings.append(sh)

        ratio = len(question_headings) / max(1, len(subheadings))
        if ratio < 0.20 and len(subheadings) >= 3:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "total_subheadings": len(subheadings),
                            "question_headings_count": len(question_headings),
                            "sample_subheadings": subheadings[:3],
                        }
                    ],
                    title_override="Subheadings rarely use question formulations (missed generative search alignment)",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"question_headings": question_headings[:3]}],
            )
        ]


class FaqMarkupCheck(BaseCheck):
    id = "CONT-FAQ-MARKUP"
    layer = AuditLayer.CONTENT
    title = "FAQ / Q&A Structured Data Markup"
    severity = Severity.MEDIUM
    effort = Effort.SMALL
    impact = 3
    why_it_matters = (
        "Content structured as questions and answers benefits from FAQPage Schema markup, providing "
        "explicit question-answer tuples directly digestible by AI models."
    )
    fix_guidance = "Add FAQPage or HowTo JSON-LD schema markup to pages containing Q&A sections."
    references = ["https://developers.google.com/search/docs/appearance/structured-data/faqpage"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.raw_html or snap.status_code != 200:
            return []

        has_qa_keywords = bool(
            re.search(r"\b(faq|frequently asked questions|q&a)\b", snap.raw_html, re.I)
        )
        has_faq_schema = "FAQPage" in snap.raw_html or "HowTo" in snap.raw_html

        if has_qa_keywords and not has_faq_schema:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "message": "FAQ content detected in text, but no FAQPage schema is present."
                        }
                    ],
                    title_override="FAQ content detected without FAQPage structured data markup",
                )
            ]
        return []
