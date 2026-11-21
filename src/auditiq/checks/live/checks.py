"""Live AI Visibility checks (Layer 4)."""

from auditiq.checks.base import BaseCheck, SiteContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class LiveMentionRateCheck(BaseCheck):
    id = "LIVE-MENTION-RATE"
    layer = AuditLayer.LIVE_VISIBILITY
    title = "Brand Mention Rate in Generative AI Answers"
    severity = Severity.HIGH
    effort = Effort.LARGE
    impact = 5
    why_it_matters = (
        "Measures how frequently your brand name is recommended or cited across multiple queries in generative "
        "engines (ChatGPT, Perplexity, Gemini, Claude). High mention rates indicate strong entity saliency."
    )
    fix_guidance = (
        "Strengthen topical authority, earn citations in industry review publications (G2, Trustpilot, Forbes), "
        "and optimize passage structure so generative models associate your brand with high-intent solution queries."
    )
    references = [
        "https://platform.openai.com/",
        "https://docs.perplexity.ai/",
    ]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        summary = context.visibility_summary
        url = context.crawl_result.start_url

        if summary is None or summary.total_evaluations == 0:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.NOT_MEASURED,
                    severity_override=Severity.INFO,
                    evidence=[
                        {
                            "reason": "No live answer engine evaluations were run (missing API keys or skipped).",
                            "status": "Not measured",
                        }
                    ],
                    title_override="Brand Mention Rate: Not measured (API keys unconfigured)",
                )
            ]

        m_rate = summary.mention_rate

        if m_rate.point_estimate >= 0.50:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {
                            "mention_rate": m_rate.display,
                            "evaluations": summary.total_evaluations,
                            "engines": summary.active_engines,
                        }
                    ],
                    title_override=f"Strong AI brand mention rate: {m_rate.display}",
                )
            ]
        elif m_rate.point_estimate >= 0.20:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.WARNING,
                    severity_override=Severity.MEDIUM,
                    evidence=[
                        {
                            "mention_rate": m_rate.display,
                            "evaluations": summary.total_evaluations,
                            "engines": summary.active_engines,
                        }
                    ],
                    title_override=f"Moderate AI brand mention rate: {m_rate.display}",
                )
            ]
        else:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.FAIL,
                    severity_override=Severity.HIGH,
                    evidence=[
                        {
                            "mention_rate": m_rate.display,
                            "evaluations": summary.total_evaluations,
                            "engines": summary.active_engines,
                        }
                    ],
                    title_override=f"Low AI brand mention rate: {m_rate.display}",
                    why_override="Your brand is largely absent from synthesized generative answers for target keywords.",
                )
            ]


class LiveCitationRateCheck(BaseCheck):
    id = "LIVE-CITATION-RATE"
    layer = AuditLayer.LIVE_VISIBILITY
    title = "Domain Citation Rate (Direct Source Backlinks from AI Answers)"
    severity = Severity.HIGH
    effort = Effort.LARGE
    impact = 5
    why_it_matters = (
        "Live generative engines cite primary sources in web cards and footnotes. A high citation rate drives "
        "direct referral traffic from users exploring AI-synthesized responses."
    )
    fix_guidance = (
        "Ensure robots.txt permits AI search crawlers, provide original statistics and data tables, and structure "
        "authoritative answer-first passages with clear citation anchors."
    )
    references = [
        "https://docs.perplexity.ai/docs/perplexitybot",
    ]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        summary = context.visibility_summary
        url = context.crawl_result.start_url

        if summary is None or summary.total_evaluations == 0:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.NOT_MEASURED,
                    severity_override=Severity.INFO,
                    evidence=[
                        {
                            "reason": "No live answer engine evaluations were run (missing API keys or skipped).",
                            "status": "Not measured",
                        }
                    ],
                    title_override="Domain Citation Rate: Not measured (API keys unconfigured)",
                )
            ]

        c_rate = summary.citation_rate

        if c_rate.point_estimate >= 0.30:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {
                            "citation_rate": c_rate.display,
                            "evaluations": summary.total_evaluations,
                            "engines": summary.active_engines,
                        }
                    ],
                    title_override=f"High AI citation rate: {c_rate.display}",
                )
            ]
        elif c_rate.point_estimate >= 0.10:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.WARNING,
                    severity_override=Severity.MEDIUM,
                    evidence=[
                        {
                            "citation_rate": c_rate.display,
                            "evaluations": summary.total_evaluations,
                            "engines": summary.active_engines,
                        }
                    ],
                    title_override=f"Moderate AI citation rate: {c_rate.display}",
                )
            ]
        else:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.FAIL,
                    severity_override=Severity.HIGH,
                    evidence=[
                        {
                            "citation_rate": c_rate.display,
                            "evaluations": summary.total_evaluations,
                            "engines": summary.active_engines,
                        }
                    ],
                    title_override=f"Low AI citation rate: {c_rate.display}",
                    why_override="AI answer engines rarely cite your domain as an authoritative source link.",
                )
            ]


class LiveShareOfVoiceCheck(BaseCheck):
    id = "LIVE-SHARE-OF-VOICE"
    layer = AuditLayer.LIVE_VISIBILITY
    title = "AI Share of Voice (Competitive Visibility Share)"
    severity = Severity.MEDIUM
    effort = Effort.LARGE
    impact = 4
    why_it_matters = "Measures the proportion of queries where your brand is recognized versus competing products in the same niche."
    fix_guidance = "Create high-value comparison pages and case studies addressing alternative solutions to capture conversational share."
    references = []

    async def run_site(self, context: SiteContext) -> list[Finding]:
        summary = context.visibility_summary
        url = context.crawl_result.start_url

        if summary is None or summary.total_evaluations == 0:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.NOT_MEASURED,
                    severity_override=Severity.INFO,
                    evidence=[{"status": "Not measured"}],
                    title_override="AI Share of Voice: Not measured",
                )
            ]

        sov = summary.share_of_voice
        if sov >= 40.0:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {"share_of_voice": f"{sov}%", "evaluations": summary.total_evaluations}
                    ],
                    title_override=f"Leading AI Share of Voice: {sov}%",
                )
            ]
        else:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.WARNING,
                    severity_override=Severity.MEDIUM,
                    evidence=[
                        {"share_of_voice": f"{sov}%", "evaluations": summary.total_evaluations}
                    ],
                    title_override=f"Moderate AI Share of Voice: {sov}%",
                )
            ]


class LiveTopCitedDomainsCheck(BaseCheck):
    id = "LIVE-TOP-CITED-DOMAINS"
    layer = AuditLayer.LIVE_VISIBILITY
    title = "Top Cited Domain Authority Benchmark"
    severity = Severity.INFO
    effort = Effort.MEDIUM
    impact = 3
    why_it_matters = (
        "Identifies which third-party domains (e.g. Reddit, Wikipedia, G2, TechCrunch) AI engines prioritize "
        "when synthesizing recommendations for your category."
    )
    fix_guidance = "Prioritize digital PR and organic presence on the specific domains winning citations for your target queries."
    references = []

    async def run_site(self, context: SiteContext) -> list[Finding]:
        summary = context.visibility_summary
        url = context.crawl_result.start_url

        if summary is None or summary.total_evaluations == 0:
            return [
                self.create_finding(
                    url=url,
                    status=FindingStatus.NOT_MEASURED,
                    severity_override=Severity.INFO,
                    evidence=[{"status": "Not measured"}],
                    title_override="Top Cited Domains: Not measured",
                )
            ]

        top_domains = summary.top_cited_domains
        return [
            self.create_finding(
                url=url,
                status=FindingStatus.PASS,
                severity_override=Severity.INFO,
                evidence=[
                    {"top_cited_domains": top_domains, "target_domain": summary.target_domain}
                ],
                title_override=f"Identified {len(top_domains)} top cited third-party domains in AI answers",
            )
        ]
