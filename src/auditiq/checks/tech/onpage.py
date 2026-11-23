"""Technical SEO On-Page Content & Hygiene checks (TECH-*)."""

from urllib.parse import parse_qsl, urlparse

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class TitleMissingCheck(BaseCheck):
    id = "TECH-TITLE-MISSING"
    layer = AuditLayer.TECHNICAL
    title = "Missing or Empty <title> Tag"
    severity = Severity.CRITICAL
    effort = Effort.SMALL
    impact = 5
    why_it_matters = (
        "The <title> tag is one of the most critical on-page ranking signals and provides the clickable "
        "headline in search engine results and AI answer cards."
    )
    fix_guidance = "Add a unique, descriptive <title> tag inside the <head> of every HTML page."
    references = ["https://developers.google.com/search/docs/appearance/title-link"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or "text/html" not in snap.content_type:
            return []

        if not snap.title or not snap.title.strip():
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    evidence=[{"error": "Title tag is missing or whitespace only"}],
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"title": snap.title, "length": len(snap.title)}],
            )
        ]


class TitleLengthCheck(BaseCheck):
    id = "TECH-TITLE-LENGTH"
    layer = AuditLayer.TECHNICAL
    title = "Title Tag Length Optimization (30–65 Chars)"
    severity = Severity.LOW
    effort = Effort.SMALL
    impact = 2
    why_it_matters = (
        "Titles under 30 characters underutilize ranking keywords; titles over 65 characters get truncated "
        "in SERPs (or rewritten by Google)."
    )
    fix_guidance = "Format titles to be between 30 and 65 characters (approx. 200–600 pixels)."
    references = ["https://developers.google.com/search/docs/appearance/title-link"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.title or snap.status_code != 200:
            return []

        length = len(snap.title)
        if length < 30:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {"title": snap.title, "length": length, "recommended": "30-65 chars"}
                    ],
                    title_override="Title tag is too short (<30 characters)",
                )
            ]
        elif length > 65:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[
                        {"title": snap.title, "length": length, "recommended": "30-65 chars"}
                    ],
                    title_override="Title tag is too long (>65 characters; risk of truncation)",
                )
            ]
        return []


class MetaDescMissingCheck(BaseCheck):
    id = "TECH-META-DESC-MISSING"
    layer = AuditLayer.TECHNICAL
    title = "Missing Meta Description"
    severity = Severity.MEDIUM
    effort = Effort.SMALL
    impact = 3
    why_it_matters = (
        "Meta descriptions provide the summary snippet in search results and help AI crawlers understand "
        "page intent before full parsing."
    )
    fix_guidance = "Add an enticing, descriptive <meta name='description' content='...'> tag."
    references = ["https://developers.google.com/search/docs/appearance/snippet"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or "text/html" not in snap.content_type:
            return []

        if not snap.meta_description or not snap.meta_description.strip():
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    evidence=[{"error": "No meta description tag found"}],
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[
                    {
                        "description": snap.meta_description[:80] + "...",
                        "length": len(snap.meta_description),
                    }
                ],
            )
        ]


class MetaDescLengthCheck(BaseCheck):
    id = "TECH-META-DESC-LENGTH"
    layer = AuditLayer.TECHNICAL
    title = "Meta Description Length Hygiene (70–160 Chars)"
    severity = Severity.LOW
    effort = Effort.SMALL
    impact = 2
    why_it_matters = (
        "Descriptions shorter than 70 characters offer poor click-through incentive; descriptions over "
        "160 characters get truncated in search snippets."
    )
    fix_guidance = "Craft meta descriptions to be between 70 and 160 characters with a clear value proposition."
    references = ["https://developers.google.com/search/docs/appearance/snippet"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.meta_description or snap.status_code != 200:
            return []

        length = len(snap.meta_description)
        if length < 70 or length > 160:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"length": length, "recommended": "70-160 characters"}],
                    title_override=f"Meta description length ({length} chars) is outside optimal range (70–160 chars)",
                )
            ]
        return []


class H1MissingMultiCheck(BaseCheck):
    id = "TECH-H1-MISSING-MULTI"
    layer = AuditLayer.TECHNICAL
    title = "H1 Heading Presence & Singularity"
    severity = Severity.MEDIUM
    effort = Effort.SMALL
    impact = 3
    why_it_matters = (
        "Every indexable page should have exactly one descriptive <h1> tag serving as the main topic header "
        "for users, search crawlers, and screen readers."
    )
    fix_guidance = (
        "Ensure each page contains exactly one <h1> element accurately describing the page subject."
    )
    references = ["https://developers.google.com/search/docs/crawling-indexing/heading-tags"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or "text/html" not in snap.content_type:
            return []

        count = len(snap.h1s)
        if count == 0:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    evidence=[{"h1_count": 0, "error": "No <h1> heading tag found in page HTML"}],
                    title_override="Missing <h1> heading tag",
                )
            ]
        elif count > 1:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"h1_count": count, "h1_samples": snap.h1s[:3]}],
                    title_override=f"Multiple <h1> headings found ({count} tags)",
                    why_override="Multiple H1 tags dilute the primary topical focus for search engines and assistive technologies.",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"h1": snap.h1s[0]}],
            )
        ]


class HeadingSkipsCheck(BaseCheck):
    id = "TECH-HEADING-SKIPS"
    layer = AuditLayer.TECHNICAL
    title = "Heading Hierarchy Level Skips"
    severity = Severity.LOW
    effort = Effort.SMALL
    impact = 2
    why_it_matters = (
        "Skipping heading levels (e.g. from H1 directly to H3 or H4) breaks semantic document outlines, "
        "harming accessibility and confusing automated passage extractors."
    )
    fix_guidance = "Nest headings logically in descending order: H1 -> H2 -> H3."
    references = ["https://www.w3.org/WAI/tutorials/page-structure/headings/"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.headings_hierarchy or snap.status_code != 200:
            return []

        skips = []
        last_level = 0
        for item in snap.headings_hierarchy:
            tag = item.get("tag", "").lower()
            if tag.startswith("h") and tag[1:].isdigit():
                current_level = int(tag[1:])
                if last_level > 0 and current_level > last_level + 1:
                    skips.append(
                        {
                            "from": f"h{last_level}",
                            "to": f"h{current_level}",
                            "text": item.get("text", "")[:40],
                        }
                    )
                last_level = current_level

        if skips:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"skips_detected": skips[:3], "total_skips": len(skips)}],
                )
            ]
        return []


class ImageAltMissingCheck(BaseCheck):
    id = "TECH-IMAGE-ALT-MISSING"
    layer = AuditLayer.TECHNICAL
    title = "Missing Image Alt Attributes"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 3
    why_it_matters = (
        "Alt attributes provide crucial context for image search, screen readers for accessibility (a11y), "
        "and AI multimodal models that parse web content."
    )
    fix_guidance = "Add meaningful, descriptive alt attributes to all informative <img> tags."
    references = ["https://developers.google.com/search/docs/appearance/google-images"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if not snap.raw_html or snap.status_code != 200:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        missing_images = []
        total_images = 0

        for img in parser.css("img"):
            total_images += 1
            src = img.attributes.get("src") or ""
            alt = img.attributes.get("alt", None)
            if alt is None or not alt.strip():
                # Ignore tiny tracking pixels
                missing_images.append(src[:80])

        if missing_images:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    evidence=[
                        {
                            "missing_alt_count": len(missing_images),
                            "total_images": total_images,
                            "sample_images": missing_images[:5],
                        }
                    ],
                )
            ]
        return []


class UrlHygieneCheck(BaseCheck):
    id = "TECH-URL-HYGIENE"
    layer = AuditLayer.TECHNICAL
    title = "URL Hygiene & Structure Standards"
    severity = Severity.LOW
    effort = Effort.SMALL
    impact = 2
    why_it_matters = (
        "Clean, lowercase, parameter-free URLs are easier to index, less prone to duplicate content issues, "
        "and more trustworthy for users to click."
    )
    fix_guidance = "Use lowercase words separated by hyphens; avoid uppercase characters and excessive parameters."
    references = ["https://developers.google.com/search/docs/crawling-indexing/url-structure"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        parsed = urlparse(snap.url)
        issues = []

        if any(c.isupper() for c in parsed.path):
            issues.append("Contains uppercase characters in path")

        params = parse_qsl(parsed.query)
        if len(params) > 3:
            issues.append(f"Excessive query parameters ({len(params)} parameters)")

        if len(snap.url) > 100:
            issues.append(f"URL exceeds 100 characters ({len(snap.url)} chars)")

        if issues:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"issues": issues, "url": snap.url}],
                )
            ]
        return []


class OpenGraphCheck(BaseCheck):
    id = "TECH-OPENGRAPH-MISSING"
    layer = AuditLayer.TECHNICAL
    title = "OpenGraph Social & AI Preview Metadata"
    severity = Severity.MEDIUM
    effort = Effort.SMALL
    impact = 3
    why_it_matters = (
        "OpenGraph tags (og:title, og:description, og:image) control preview cards across social networks "
        "and are used by AI agents to generate structured snippet previews."
    )
    fix_guidance = "Add <meta property='og:title'>, <meta property='og:description'>, and <meta property='og:image'> tags."
    references = ["https://ogp.me/"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or not snap.raw_html or "text/html" not in snap.content_type:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        og_title = parser.css_first("meta[property='og:title'], meta[name='og:title']")
        og_desc = parser.css_first("meta[property='og:description'], meta[name='og:description']")
        og_image = parser.css_first("meta[property='og:image'], meta[name='og:image']")

        missing = []
        if not og_title or not og_title.attributes.get("content"):
            missing.append("og:title")
        if not og_desc or not og_desc.attributes.get("content"):
            missing.append("og:description")
        if not og_image or not og_image.attributes.get("content"):
            missing.append("og:image")

        if missing:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    evidence=[{"missing_tags": missing}],
                    title_override=f"Missing OpenGraph metadata: {', '.join(missing)}",
                    why_override="Without complete OpenGraph tags, social platforms and AI summary cards display generic previews.",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"og_tags": ["og:title", "og:description", "og:image"]}],
            )
        ]


class DomHygieneCheck(BaseCheck):
    id = "TECH-DOM-HYGIENE"
    layer = AuditLayer.TECHNICAL
    title = "DOM Element Hygiene & Legacy Tag Deprecation"
    severity = Severity.MEDIUM
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Excessive DOM elements (>1,500) and obsolete layout tags (<font>, <center>, <marquee>, nested tables) "
        "degrade browser rendering speed, crush mobile performance, and obstruct AI parser extraction."
    )
    fix_guidance = "Refactor legacy HTML templates to modern CSS layout and reduce total DOM element count."
    references = ["https://web.dev/articles/dom-size-and-interactive"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        if snap.status_code != 200 or not snap.raw_html or "text/html" not in snap.content_type:
            return []

        parser = LexborHTMLParser(snap.raw_html)
        issues = []

        # Count total DOM elements
        all_elements = parser.css("*")
        elem_count = len(all_elements)
        if elem_count > 2500:
            issues.append(f"Excessive DOM size ({elem_count} elements > 2,500 threshold)")
        elif elem_count > 1500:
            issues.append(f"High DOM size ({elem_count} elements > 1,500 threshold)")

        # Check for obsolete/deprecated tags
        deprecated_tags = ["font", "center", "marquee", "blink", "basefont", "applet"]
        found_deprecated = []
        for tag in deprecated_tags:
            nodes = parser.css(tag)
            if nodes:
                found_deprecated.append(f"<{tag}> ({len(nodes)})")

        if found_deprecated:
            issues.append(f"Deprecated HTML tags in use: {', '.join(found_deprecated)}")

        # Check for nested layout tables (table inside table)
        nested_tables = parser.css("table table")
        if len(nested_tables) > 3:
            issues.append(f"Legacy nested table layout detected ({len(nested_tables)} nested tables)")

        if issues:
            sev = Severity.HIGH if (elem_count > 2500 or found_deprecated) else Severity.MEDIUM
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL if sev == Severity.HIGH else FindingStatus.WARNING,
                    severity_override=sev,
                    evidence=[{"issues": issues, "total_elements": elem_count}],
                    title_override=f"DOM Clutter & Legacy Structure Detected ({len(issues)} hygiene issues)",
                    why_override="Obsolete HTML structures slow down rendering and impede AI web crawlers.",
                )
            ]
        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"total_elements": elem_count, "deprecated_tags": 0}],
            )
        ]
