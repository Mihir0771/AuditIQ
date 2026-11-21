"""Content factual density and authoritative outbound citation checks (CONT-*)."""

import re
from urllib.parse import urlparse

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity

AUTHORITY_TLDS = (".gov", ".edu", ".org", ".ac.uk")
AUTHORITY_DOMAINS = (
    "wikipedia.org",
    "github.com",
    "w3.org",
    "nih.gov",
    "cdc.gov",
    "arxiv.org",
    "nature.com",
    "science.org",
    "ieee.org",
)


class EvidenceDensityCheck(BaseCheck):
    id = "CONT-EVIDENCE-DENSITY"
    layer = AuditLayer.CONTENT
    title = "Factual & Statistical Evidence Density"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Generative answer engines (Perplexity, ChatGPT Search, Claude) favor content that contains "
        "concrete data points, statistics, dates, and named studies over generic hand-waving."
    )
    fix_guidance = "Ground claims in empirical statistics, specific percentages, dates, and named primary sources."
    references = ["https://developers.google.com/search/docs/fundamentals/creating-helpful-content"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or not snap.raw_html or snap.word_count < 250:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        body = parser.css_first("body")
        if not body:
            return []

        text = body.text(separator=" ", strip=True)

        # Detect percentages (e.g. 45%, 12.5%)
        percentages = re.findall(r"\b\d+(?:\.\d+)?%", text)
        # Detect currency figures (e.g. $500, €40)
        currency = re.findall(r"[\$€£]\s?\d+(?:,\d{3})*(?:\.\d+)?", text)
        # Detect 4-digit years (e.g. 2024, 2025, 2026)
        years = re.findall(r"\b20[12]\d\b", text)

        total_evidence_points = len(percentages) + len(currency) + len(years)
        # Normalized rate per 500 words
        rate_per_500 = round((total_evidence_points / max(1, snap.word_count)) * 500, 1)

        if rate_per_500 < 1.0 and snap.word_count >= 500:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "word_count": snap.word_count,
                            "evidence_points_found": total_evidence_points,
                            "rate_per_500_words": rate_per_500,
                            "recommendation": "Incorporate verifiable statistics, benchmark numbers, or dates.",
                        }
                    ],
                    title_override="Low factual evidence density (few statistics, numbers, or dates)",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[
                    {
                        "evidence_points_count": total_evidence_points,
                        "rate_per_500_words": rate_per_500,
                    }
                ],
            )
        ]


class OutboundCitationsCheck(BaseCheck):
    id = "CONT-OUTBOUND-CITATIONS"
    layer = AuditLayer.CONTENT
    title = "Authoritative Outbound Citations"
    severity = Severity.MEDIUM
    effort = Effort.SMALL
    impact = 3
    why_it_matters = (
        "Outbound citations to authoritative external primary sources (.gov, .edu, Wikipedia, official docs) "
        "signal thorough research, build domain trust, and match citation networks indexed by LLMs."
    )
    fix_guidance = "Cite primary institutional, scientific, or official vendor documentation when stating facts."
    references = ["https://developers.google.com/search/docs/fundamentals/creating-helpful-content"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or not snap.raw_html or snap.word_count < 400:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        outbound_authorities = []

        for link in parser.css("article a[href], main a[href], body a[href]"):
            href = link.attributes.get("href") or ""
            parsed = urlparse(href)
            host = parsed.netloc.lower()
            if not host or host == context.site.crawl_result.base_domain:
                continue

            if any(host.endswith(tld) for tld in AUTHORITY_TLDS) or any(
                dom in host for dom in AUTHORITY_DOMAINS
            ):
                outbound_authorities.append(href)

        if not outbound_authorities and snap.word_count >= 600:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"outbound_authoritative_links": 0, "word_count": snap.word_count}],
                    title_override="Long-form content lacks outbound citations to authoritative primary sources",
                )
            ]
        elif outbound_authorities:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[{"authorities_cited": outbound_authorities[:3]}],
                )
            ]
        return []
