"""AI Bot Access Matrix and CDN/WAF Challenge checks (GEO-*)."""

from pathlib import Path
from urllib.parse import urlparse

import yaml

from auditiq.checks.base import BaseCheck, SiteContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class AiBotMatrixCheck(BaseCheck):
    id = "GEO-BOT-ACCESS"
    layer = AuditLayer.GEO_READINESS
    title = "AI Bot & Crawler Access Matrix (Training vs. Search Bots)"
    severity = Severity.HIGH
    effort = Effort.SMALL
    impact = 5
    why_it_matters = (
        "AI vendors operate distinct web crawlers. Blocking training bots (GPTBot, ClaudeBot) protects "
        "copyright, but blocking search crawlers (OAI-SearchBot, PerplexityBot) destroys real-time citations "
        "and brand visibility in generative AI answers."
    )
    fix_guidance = (
        "Configure robots.txt to explicitly permit AI search crawlers (OAI-SearchBot, PerplexityBot) "
        "while selectively enforcing policy for training bots based on your intellectual property strategy."
    )
    references = [
        "https://platform.openai.com/docs/bots",
        "https://docs.perplexity.ai/docs/perplexitybot",
        "https://docs.anthropic.com/en/docs/resources/claudebot",
    ]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings: list[Finding] = []
        robots_parser = context.crawl_result.robots_txt_content
        robots_url = f"{urlparse(context.crawl_result.start_url).scheme}://{context.crawl_result.base_domain}/robots.txt"

        # Load verified bot taxonomy
        bot_cfg_path = Path("config/ai_bots.yaml")
        bots = []
        if bot_cfg_path.exists():
            with open(bot_cfg_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                bots = data.get("bots", [])

        if not bots:
            bots = [
                {"name": "GPTBot", "user_agent": "GPTBot", "type": "training"},
                {"name": "OAI-SearchBot", "user_agent": "OAI-SearchBot", "type": "search"},
                {"name": "ChatGPT-User", "user_agent": "ChatGPT-User", "type": "user"},
                {"name": "PerplexityBot", "user_agent": "PerplexityBot", "type": "search"},
                {"name": "ClaudeBot", "user_agent": "ClaudeBot", "type": "training"},
                {"name": "Google-Extended", "user_agent": "Google-Extended", "type": "training"},
            ]

        from auditiq.crawler.robots import RobotsTxtParser

        parser = RobotsTxtParser(robots_parser or "")

        search_blocked = []
        training_blocked = []
        search_allowed = []

        for b in bots:
            ua = b.get("user_agent", b["name"])
            bot_type = b.get("type", "training")
            is_allowed = parser.is_allowed(ua, "/")

            if not is_allowed:
                if bot_type == "search":
                    search_blocked.append(ua)
                else:
                    training_blocked.append(ua)
            else:
                if bot_type == "search":
                    search_allowed.append(ua)

        # Critical severity if search bots are blocked
        if search_blocked:
            findings.append(
                self.create_finding(
                    url=robots_url,
                    status=FindingStatus.FAIL,
                    severity_override=Severity.CRITICAL,
                    evidence=[
                        {
                            "blocked_search_bots": search_blocked,
                            "allowed_search_bots": search_allowed,
                            "impact": "Destroys real-time citations in ChatGPT Search and Perplexity.",
                        }
                    ],
                    title_override=f"Critical AI search crawlers blocked in robots.txt: {', '.join(search_blocked)}",
                    why_override="Blocking AI search bots prevents generative engines from indexing your pages or citing your domain as a source.",
                    fix_override=f"Add 'User-agent: {search_blocked[0]}\\nAllow: /' to your robots.txt file.",
                )
            )

        # Informational note if training bots are blocked (legitimate business choice)
        if training_blocked:
            findings.append(
                self.create_finding(
                    url=robots_url,
                    status=FindingStatus.PASS,
                    severity_override=Severity.INFO,
                    evidence=[
                        {
                            "blocked_training_bots": training_blocked,
                            "policy": "Model Training Protection",
                            "note": "Blocking training bots prevents data ingestion without harming live search citations.",
                        }
                    ],
                    title_override=f"Training crawlers restricted ({', '.join(training_blocked)}) [Copyright Protection Active]",
                )
            )
        elif not search_blocked:
            findings.append(
                self.create_finding(
                    url=robots_url,
                    status=FindingStatus.PASS,
                    evidence=[
                        {"message": "All primary AI search bots are allowed access to the site."}
                    ],
                )
            )

        return findings


class BotFirewallCheck(BaseCheck):
    id = "GEO-FIREWALL-BLOCKS"
    layer = AuditLayer.GEO_READINESS
    title = "CDN / WAF Bot Challenge or 403 Page Detection"
    severity = Severity.HIGH
    effort = Effort.MEDIUM
    impact = 5
    why_it_matters = (
        "Aggressive Cloudflare, CloudFront, or Akamai WAF rules often return JS challenge (CAPTCHA) pages "
        "or 403 Forbidden to non-browser requests, making content completely invisible to automated AI engines."
    )
    fix_guidance = (
        "Configure CDN / Firewall rules to allow verified AI crawler IP ranges and user-agents without "
        "triggering managed browser challenges."
    )
    references = ["https://developers.cloudflare.com/waf/managed-rules/"]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings: list[Finding] = []
        snap = context.crawl_result.pages.get(context.crawl_result.start_url)
        if not snap:
            return findings

        # Check for typical CDN challenge markers in raw HTML
        is_challenge = False
        challenge_signatures = [
            "cf-chl-bypass",
            "just a moment...",
            "checking your browser before accessing",
            "security verification",
            "access denied - error 403",
        ]
        text_lower = (snap.raw_html or "").lower()
        for sig in challenge_signatures:
            if sig in text_lower:
                is_challenge = True
                break

        if snap.status_code == 403 or is_challenge:
            findings.append(
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.FAIL,
                    severity_override=Severity.CRITICAL,
                    evidence=[
                        {
                            "status_code": snap.status_code,
                            "waf_challenge_detected": is_challenge,
                            "server": snap.headers.get("server", "unknown"),
                        }
                    ],
                    title_override="Firewall or CDN WAF blocks automated crawler access",
                )
            )
        else:
            findings.append(
                self.create_finding(
                    url=snap.url,
                    status=FindingStatus.PASS,
                    evidence=[{"status_code": snap.status_code, "waf_clear": True}],
                )
            )
        return findings
