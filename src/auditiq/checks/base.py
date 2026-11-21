"""Base classes and execution context for pluggable audit checks."""

from abc import ABC
from typing import Any

from pydantic import BaseModel, ConfigDict

from auditiq.crawler.graph import LinkGraph
from auditiq.models.audit import AuditConfig
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity
from auditiq.models.snapshot import CrawlResult, PageSnapshot


class SiteContext(BaseModel):
    """Site-wide context containing the entire crawl result and link graph."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    crawl_result: CrawlResult
    link_graph: LinkGraph
    config: AuditConfig


class PageContext(BaseModel):
    """Page-level context containing the specific snapshot and site-wide metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    snapshot: PageSnapshot
    site: SiteContext


class BaseCheck(ABC):
    """Abstract base class for all pluggable audit checks."""

    id: str
    layer: AuditLayer
    title: str
    severity: Severity
    effort: Effort
    impact: int
    why_it_matters: str
    fix_guidance: str
    references: list[str] = []

    def create_finding(
        self,
        url: str,
        status: FindingStatus,
        evidence: list[dict[str, Any]],
        title_override: str | None = None,
        why_override: str | None = None,
        fix_override: str | None = None,
        severity_override: Severity | None = None,
    ) -> Finding:
        """Helper to create a typed, immutable Finding object with consistent metadata."""
        import hashlib

        finding_hash = hashlib.sha256(f"{self.id}:{url}".encode()).hexdigest()[:12]
        return Finding(
            id=f"{self.id}-{finding_hash}",
            check_id=self.id,
            layer=self.layer,
            severity=severity_override or self.severity,
            status=status,
            url=url,
            title=title_override or self.title,
            evidence=evidence,
            why_it_matters=why_override or self.why_it_matters,
            fix=fix_override or self.fix_guidance,
            effort=self.effort,
            impact=self.impact,
            references=self.references,
        )

    async def run_site(self, context: SiteContext) -> list[Finding]:
        """Runs site-wide checks (e.g. robots.txt presence, sitemap coverage).

        Override for checks that evaluate the site as a whole.
        """
        return []

    async def run_page(self, context: PageContext) -> list[Finding]:
        """Runs page-level checks (e.g. title tags, canonicals, H1s, schema).

        Override for checks that evaluate individual page snapshots.
        """
        return []
