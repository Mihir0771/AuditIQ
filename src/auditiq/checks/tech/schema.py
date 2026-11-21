"""Technical SEO Structured Data & Schema.org validation checks (TECH-*)."""

import json

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class SchemaSyntaxCheck(BaseCheck):
    id = "TECH-SCHEMA-SYNTAX"
    layer = AuditLayer.TECHNICAL
    title = "JSON-LD Structured Data Syntax Validity"
    severity = Severity.HIGH
    effort = Effort.SMALL
    impact = 4
    why_it_matters = (
        "Syntax errors or unescaped characters in JSON-LD script tags render structured data completely "
        "invisible to search engines, causing loss of rich snippets and AI entity recognition."
    )
    fix_guidance = (
        "Validate and sanitize JSON-LD blocks to ensure standard RFC 8259 JSON formatting."
    )
    references = [
        "https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data"
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.raw_html or snap.status_code != 200:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        errors = []
        valid_blocks = 0

        for script in parser.css('script[type="application/ld+json"]'):
            text = script.text(strip=True)
            if not text:
                continue
            try:
                json.loads(text)
                valid_blocks += 1
            except json.JSONDecodeError as err:
                errors.append({"error": str(err), "snippet": text[:100]})

        if errors:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    evidence=[{"syntax_errors": errors, "valid_blocks": valid_blocks}],
                    why_override="Search engines and AI crawlers cannot parse malformed JSON-LD structured data.",
                )
            ]
        elif valid_blocks > 0:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[{"valid_json_ld_blocks": valid_blocks}],
                )
            ]
        return []


class SchemaTypesCheck(BaseCheck):
    id = "TECH-SCHEMA-TYPES"
    layer = AuditLayer.TECHNICAL
    title = "Core Schema.org Type Coverage"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Providing explicit Schema.org entities (Organization, WebSite, BreadcrumbList, Article, Product) "
        "helps search and answer engines build Knowledge Graph connections for your brand."
    )
    fix_guidance = "Deploy relevant Schema.org JSON-LD templates based on page intent."
    references = ["https://schema.org/docs/schemas.html"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.raw_html or snap.status_code != 200:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        detected_types: set[str] = set()

        for script in parser.css('script[type="application/ld+json"]'):
            text = script.text(strip=True)
            if not text:
                continue
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    t = data.get("@type")
                    if isinstance(t, str):
                        detected_types.add(t)
                    elif isinstance(t, list):
                        detected_types.update([str(x) for x in t])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "@type" in item:
                            t = item["@type"]
                            if isinstance(t, str):
                                detected_types.add(t)
            except Exception:
                continue

        if not detected_types:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"detected_types": []}],
                    why_override="No Schema.org entity types were detected on this page.",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"types": list(detected_types)}],
            )
        ]
