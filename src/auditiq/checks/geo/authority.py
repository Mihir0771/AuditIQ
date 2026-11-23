"""Entity Authority and Bot Latency checks for Generative AI (GEO-*)."""

import json

from selectolax.lexbor import LexborHTMLParser

from auditiq.checks.base import BaseCheck, PageContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class EntitySameAsCheck(BaseCheck):
    id = "GEO-ENTITY-SAMEAS"
    layer = AuditLayer.GEO_READINESS
    title = "Entity Disambiguation via JSON-LD sameAs Knowledge Graph Links"
    severity = Severity.HIGH
    effort = Effort.SMALL
    impact = 5
    why_it_matters = (
        "AI answer engines ground entity recognition using public knowledge graphs (Wikidata, Wikipedia, Crunchbase, "
        "LinkedIn). Providing 'sameAs' URIs in Organization or Brand structured data prevents AI models from conflating "
        "your company with similarly named entities."
    )
    fix_guidance = (
        "Add a 'sameAs' array to your primary Organization or WebSite JSON-LD schema linking to your verified Wikidata "
        "entry, Wikipedia page, LinkedIn company page, and official social profiles."
    )
    references = [
        "https://schema.org/sameAs",
        "https://www.wikidata.org/",
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        # Focus on homepage or primary landing page where Organization schema lives
        if snap.depth > 1:
            return []

        html = snap.raw_html
        if not html:
            return []

        try:
            parser = LexborHTMLParser(html)
            scripts = parser.css("script[type='application/ld+json']")
            if not scripts:
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.HIGH,
                        evidence=[{"error": "No JSON-LD structured data detected on primary landing page"}],
                        title_override="Missing Organization JSON-LD Schema with sameAs Knowledge Graph URIs",
                        why_override="AI answer engines need JSON-LD sameAs entity links (Wikidata, Wikipedia, LinkedIn) to ground brand recognition.",
                    )
                ]

            org_schemas = []
            same_as_links: list[str] = []

            for s in scripts:
                txt = s.text()
                if not txt:
                    continue
                try:
                    data = json.loads(txt)
                    items = data if isinstance(data, list) else [data]
                    # Check graph array if present
                    if isinstance(data, dict) and "@graph" in data:
                        items = data["@graph"]

                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        schema_type = item.get("@type")
                        if schema_type in ("Organization", "Corporation", "Brand", "LocalBusiness"):
                            org_schemas.append(item)
                            sa = item.get("sameAs", [])
                            if isinstance(sa, str):
                                same_as_links.append(sa)
                            elif isinstance(sa, list):
                                same_as_links.extend([str(x) for x in sa if isinstance(x, str)])
                except Exception:
                    continue

            if not org_schemas:
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.HIGH,
                        evidence=[{"error": "JSON-LD present but missing Organization or Brand entity schema"}],
                        title_override="No Organization or Brand entity schema detected for Knowledge Graph disambiguation",
                        why_override="Without an explicit Organization entity schema, AI models cannot disambiguate your brand identity.",
                    )
                ]

            authority_domains = ("wikidata.org", "wikipedia.org", "crunchbase.com", "linkedin.com")
            has_authority_link = any(
                any(domain in link.lower() for domain in authority_domains)
                for link in same_as_links
            )

            if not same_as_links:
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.MEDIUM,
                        evidence=[
                            {
                                "organization_schema_found": True,
                                "same_as_count": 0,
                                "recommendation": "Add sameAs links to Wikidata, LinkedIn, and Crunchbase.",
                            }
                        ],
                        title_override="Organization schema lacks 'sameAs' entity disambiguation links",
                        why_override="Without sameAs links, LLMs cannot reliably connect your brand to external knowledge graph nodes.",
                    )
                ]
            elif not has_authority_link:
                return [
                    self.create_finding(
                        url=snap.url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.LOW,
                        evidence=[
                            {
                                "same_as_links": same_as_links,
                                "missing_knowledge_graphs": [
                                    "wikidata.org",
                                    "wikipedia.org",
                                    "crunchbase.com",
                                ],
                            }
                        ],
                        title_override="sameAs links present but lack authoritative Knowledge Graph sources (Wikidata/LinkedIn)",
                    )
                ]

            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {
                            "same_as_links": same_as_links,
                            "knowledge_graph_connected": True,
                        }
                    ],
                )
            ]
        except Exception:
            return []


class BotTtfbCheck(BaseCheck):
    id = "GEO-BOT-LATENCY"
    layer = AuditLayer.GEO_READINESS
    title = "Bot Response Latency (TTFB < 800ms for Real-Time AI Search)"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 4
    why_it_matters = (
        "Real-time AI search bots (Perplexity, ChatGPT web search) operate on tight sub-second budgets while "
        "streaming answers to users. Pages with Time To First Byte (TTFB) > 800ms are frequently skipped or "
        "timed out during live search synthesis."
    )
    fix_guidance = (
        "Optimize edge CDN caching, enable HTTP/2 or HTTP/3, and optimize backend database queries so that "
        "bot requests respond with TTFB under 500ms."
    )
    references = [
        "https://web.dev/articles/ttfb",
    ]

    async def run_page(self, context: PageContext) -> list[Finding]:
        snap = context.snapshot
        ttfb = snap.ttfb_ms
        if ttfb <= 0:
            return []

        if ttfb > 1500:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    severity_override=Severity.HIGH,
                    evidence=[
                        {
                            "ttfb_ms": round(ttfb, 1),
                            "threshold_ms": 800,
                            "status": "High timeout risk for live AI search agents",
                        }
                    ],
                    title_override=f"Slow bot latency: {int(ttfb)}ms TTFB (exceeds 800ms real-time AI threshold)",
                )
            ]
        elif ttfb > 800:
            return [
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.WARNING,
                    severity_override=Severity.MEDIUM,
                    evidence=[
                        {
                            "ttfb_ms": round(ttfb, 1),
                            "threshold_ms": 800,
                        }
                    ],
                    title_override=f"Moderate bot latency: {int(ttfb)}ms TTFB",
                )
            ]

        return [
            self.create_finding(
                url=snap.url,
                status=FindingStatus.PASS,
                evidence=[{"ttfb_ms": round(ttfb, 1), "status": "Fast bot response"}],
            )
        ]
