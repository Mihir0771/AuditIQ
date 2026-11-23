"""Trust, authorship, and content freshness checks (CONT-* / E-E-A-T)."""

import re
from datetime import UTC, datetime

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext, SiteContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class AuthorCredentialsCheck(BaseCheck):
    id = "CONT-AUTHOR-CREDENTIALS"
    layer = AuditLayer.CONTENT
    title = "Visible Author Bylines & E-E-A-T Signals"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Google's Search Quality Rater Guidelines (E-E-A-T: Experience, Expertise, Authoritativeness, "
        "Trustworthiness) emphasize named authorship. AI answer engines prioritize content written by "
        "identifiable subject matter experts."
    )
    fix_guidance = "Add named author bylines linked to biographical profiles detailing credentials and experience."
    references = ["https://developers.google.com/search/docs/fundamentals/creating-helpful-content"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or not snap.raw_html or snap.word_count < 400:
            return []

        parser = LexborHTMLParser(snap.raw_html)

        has_rel_author = bool(parser.css_first('a[rel*="author"]'))
        has_author_meta = bool(parser.css_first('meta[name="author"]'))
        has_author_class = bool(
            parser.css_first(
                '[class*="author"], [class*="byline"], [itemprop="author"], [rel="author"]'
            )
        )
        has_schema_author = '"author"' in snap.raw_html or '"Person"' in snap.raw_html

        has_author = has_rel_author or has_author_meta or has_author_class or has_schema_author

        if not has_author and snap.word_count >= 500:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "word_count": snap.word_count,
                            "has_author_byline": False,
                            "recommendation": "Publish explicit author bylines with bio links on articles.",
                        }
                    ],
                    title_override="Article lacks visible author byline or expert credentials (E-E-A-T)",
                )
            ]
        elif has_author:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[{"author_signals_detected": True}],
                )
            ]
        return []


class TrustPagesCheck(BaseCheck):
    id = "CONT-TRUST-PAGES"
    layer = AuditLayer.CONTENT
    title = "Essential Trust Pages (About, Contact, Privacy, Terms)"
    severity = Severity.HIGH
    effort = Effort.SMALL
    impact = 4
    scope = "site"
    why_it_matters = (
        "Clear institutional identity (About Us, Contact, Privacy Policy, Terms of Service) is a foundational "
        "trust requirement for both organic search ranking and AI knowledge graph verification."
    )
    fix_guidance = (
        "Ensure dedicated About, Contact, Privacy Policy, and Terms pages are linked in your main "
        "navigation or footer."
    )
    references = ["https://developers.google.com/search/docs/fundamentals/creating-helpful-content"]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings = []
        all_crawled = [u.lower() for u in context.crawl_result.pages]
        sitemap_all = [u.lower() for u in context.crawl_result.sitemap_urls]
        known_urls = set(all_crawled + sitemap_all)

        has_about = any("about" in u for u in known_urls)
        has_contact = any("contact" in u for u in known_urls)
        has_privacy = any("privacy" in u for u in known_urls)
        has_terms = any("terms" in u or "tos" in u for u in known_urls)

        missing = []
        if not has_about:
            missing.append("About Us")
        if not has_contact:
            missing.append("Contact")
        if not has_privacy:
            missing.append("Privacy Policy")
        if not has_terms:
            missing.append("Terms of Service")

        if missing:
            findings.append(
                self.create_finding(
                    url=context.crawl_result.start_url,
                    status=FindingStatus.WARNING,
                    evidence=[{"missing_pages": missing, "known_urls_evaluated": len(known_urls)}],
                    title_override=f"Missing essential trust pages: {', '.join(missing)}",
                )
            )
        else:
            findings.append(
                self.create_finding(
                    url=context.crawl_result.start_url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {
                            "message": "All essential trust pages detected (About, Contact, Privacy, Terms)"
                        }
                    ],
                )
            )
        return findings


class FreshnessDatesCheck(BaseCheck):
    id = "CONT-FRESHNESS-DATES"
    layer = AuditLayer.CONTENT
    title = "Content Freshness & Publication Timestamps"
    severity = Severity.MEDIUM
    effort = Effort.SMALL
    impact = 3
    why_it_matters = (
        "Visible publication and modification dates inform users and AI answer engines about content "
        "recency. Outdated content without recent update timestamps is deprioritized in AI citations."
    )
    fix_guidance = (
        "Display visible 'Last Updated' dates and include datePublished/dateModified schema markup."
    )
    references = ["https://developers.google.com/search/docs/appearance/publication-dates"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or not snap.raw_html or snap.word_count < 300:
            return []

        parser = LexborHTMLParser(snap.raw_html)

        # Check for visible time tag or meta tags
        time_node = parser.css_first("time, meta[property*='time'], meta[name*='date']")
        has_date_meta = (
            "datePublished" in snap.raw_html
            or "dateModified" in snap.raw_html
            or "article:published_time" in snap.raw_html
        )

        has_timestamp = bool(time_node) or has_date_meta

        # Detect stale year in text (>2 years ago without recent update)
        years = [
            int(y) for y in re.findall(r"\b(20[12]\d)\b", snap.raw_html) if 2015 <= int(y) <= 2030
        ]
        max_year = max(years) if years else None
        current_year = datetime.now(UTC).year

        if not has_timestamp and snap.word_count >= 500:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"has_structured_date": False, "word_count": snap.word_count}],
                    title_override="No visible or structured publication/modified timestamp found",
                )
            ]
        elif max_year and current_year - max_year >= 3 and snap.word_count >= 500:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {
                            "latest_detected_year": max_year,
                            "current_year": current_year,
                            "age_years": current_year - max_year,
                        }
                    ],
                    title_override=f"Potentially stale content: Latest referenced year is {max_year} ({current_year - max_year} years ago)",
                )
            ]
        elif has_timestamp:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[{"timestamp_signals_detected": True}],
                )
            ]
        return []
