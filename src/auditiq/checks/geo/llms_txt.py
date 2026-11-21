"""/llms.txt standard file check for AI discovery (GEO-*)."""

from urllib.parse import urlparse

from auditiq.checks.base import BaseCheck, SiteContext
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity


class LlmsTxtCheck(BaseCheck):
    id = "GEO-LLMS-TXT"
    layer = AuditLayer.GEO_READINESS
    title = "/llms.txt Standard File for AI Agent & Search Context"
    severity = Severity.INFO
    effort = Effort.SMALL
    impact = 3
    why_it_matters = (
        "The /llms.txt standard (proposed by Jeremy Howard and adopted by Anthropic, Perplexity, Cursor, etc.) "
        "provides AI agents and answer engines with a curated, token-efficient map of your site's core content "
        "and documentation in clean Markdown format."
    )
    fix_guidance = (
        "Publish an /llms.txt file at your site root containing an H1 title, a concise blockquote summary, "
        "and markdown links to key documentation pages."
    )
    references = [
        "https://llmstxt.org/",
        "https://docs.anthropic.com/",
    ]

    async def run_site(self, context: SiteContext) -> list[Finding]:
        findings = []
        cr = context.crawl_result
        scheme = urlparse(cr.start_url).scheme or "https"
        llms_url = f"{scheme}://{cr.base_domain}/llms.txt"

        status_code = cr.llms_txt_status
        content = cr.llms_txt_content

        if status_code == 200 and content:
            # Verify it is actual markdown and not an HTML 404 page
            content_trimmed = content.strip()
            if content_trimmed.lower().startswith(("<!doctype", "<html")):
                findings.append(
                    self.create_finding(
                        url=llms_url,
                        status=FindingStatus.WARNING,
                        severity_override=Severity.LOW,
                        evidence=[
                            {
                                "status_code": status_code,
                                "issue": "/llms.txt returned HTML rather than plain text / markdown",
                            }
                        ],
                        title_override="/llms.txt returned HTML document instead of plain text",
                        why_override="AI agents expect markdown; HTML indicates a soft-404 or custom error page.",
                    )
                )
            else:
                has_h1 = any(line.startswith("# ") for line in content_trimmed.splitlines())
                has_links = "[" in content_trimmed and "](" in content_trimmed
                line_count = len(content_trimmed.splitlines())

                findings.append(
                    self.create_finding(
                        url=llms_url,
                        status=FindingStatus.PASS,
                        severity_override=Severity.INFO,
                        evidence=[
                            {
                                "status_code": 200,
                                "has_h1_title": has_h1,
                                "has_links": has_links,
                                "line_count": line_count,
                            }
                        ],
                        title_override="Valid /llms.txt file detected at site root",
                    )
                )
        else:
            findings.append(
                self.create_finding(
                    url=llms_url,
                    status=FindingStatus.PASS,
                    severity_override=Severity.INFO,
                    evidence=[
                        {
                            "status_code": status_code or 404,
                            "recommended": True,
                            "note": "Optional modern standard for AI agent context discovery.",
                        }
                    ],
                    title_override="No /llms.txt file detected (Optional modern AI standard)",
                )
            )

        return findings
