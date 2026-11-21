"""Entity disambiguation, brand consistency, and Simhash duplicate detection (CONT-*)."""

import re

from simhash import Simhash

from auditiq.checks.base import BaseCheck, PageContext, SiteContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


def clean_tokens(text: str) -> list[str]:
    """Tokenizes and cleans body text for Simhash calculation."""
    text = text.lower()
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text)
    # Filter common stop words
    stop_words = {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "are",
        "have",
        "not",
        "you",
        "your",
    }
    return [w for w in words if w not in stop_words]


class SimhashDuplicateCheck(BaseCheck):
    id = "CONT-DUPLICATE-SIMHASH"
    layer = AuditLayer.CONTENT
    title = "Near-Duplicate Content Detection (Simhash LSH)"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Near-duplicate pages (e.g. identical content with minor city/keyword swaps) cause keyword "
        "cannibalization, waste crawl budget, and dilute entity authority in answer engines."
    )
    fix_guidance = "Consolidate duplicate variations using 301 redirects or canonicalize them to a single authoritative URL."
    references = [
        "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"
    ]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings = []
        pages = context.crawl_result.pages

        # Calculate Simhash for all indexable HTML pages with word count > 100
        hashes: dict[str, Simhash] = {}
        for url, snap in pages.items():
            if snap.status_code == 200 and snap.raw_html and snap.word_count >= 100:
                tokens = clean_tokens(snap.raw_html)
                if tokens:
                    hashes[url] = Simhash(tokens)

        urls = list(hashes.keys())
        duplicate_pairs = []

        # Pairwise Hamming distance comparison
        for i in range(len(urls)):
            for j in range(i + 1, len(urls)):
                url_a = urls[i]
                url_b = urls[j]
                distance = hashes[url_a].distance(hashes[url_b])
                # Hamming distance <= 3 indicates >=85% content similarity in 64-bit hash
                if distance <= 3:
                    duplicate_pairs.append((url_a, url_b, distance))

        if duplicate_pairs:
            for url_a, url_b, dist in duplicate_pairs[:5]:
                findings.append(
                    self.create_finding(
                        url=url_a,
                        status=FindingStatus.FAIL,
                        evidence=[
                            {
                                "duplicate_pair_url": url_b,
                                "hamming_distance": dist,
                                "similarity": f">= {round((64 - dist) / 64 * 100, 1)}%",
                            }
                        ],
                        title_override=f"Near-duplicate content detected with {url_b} (Hamming distance {dist})",
                    )
                )
        return findings


class BrandConsistencyCheck(BaseCheck):
    id = "CONT-ENTITY-BRAND"
    layer = AuditLayer.CONTENT
    title = "Brand Name Consistency in Metadata & Schema"
    severity = Severity.MEDIUM
    effort = Effort.SMALL
    impact = 3
    why_it_matters = (
        "Inconsistent brand name spellings (e.g. Acme Corp vs. Acme LLC vs. Acme) confuse AI models "
        "and prevent consistent entity graph clustering in generative search engines."
    )
    fix_guidance = "Adopt a standard, uniform brand name across all page titles, footer copyrights, and Schema.org markup."
    references = ["https://schema.org/Organization"]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        brand = context.site.config.brand_name
        if not brand or snap.status_code != 200 or "text/html" not in snap.content_type:
            return []

        # On the homepage, verify the brand name appears in title
        if snap.url == context.site.config.target_url:
            if brand.lower() not in snap.title.lower():
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        evidence=[
                            {
                                "configured_brand": brand,
                                "homepage_title": snap.title,
                                "error": f"Brand name '{brand}' was not found in the homepage title.",
                            }
                        ],
                        title_override=f"Target brand '{brand}' missing from homepage title",
                    )
                ]
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[{"brand": brand, "title": snap.title}],
                )
            ]
        return []
