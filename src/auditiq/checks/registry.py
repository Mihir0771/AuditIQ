"""Central registry and executor for pluggable audit checks."""

import asyncio
import logging

from auditiq.checks.base import BaseCheck, PageContext, SiteContext
from auditiq.models.audit import AuditConfig
from auditiq.models.finding import AuditLayer, Finding
from auditiq.models.snapshot import CrawlResult

logger = logging.getLogger("auditiq.checks.registry")


class CheckRegistry:
    """Manages check registration, filtering by layer, and asynchronous execution."""

    def __init__(self) -> None:
        self._checks: dict[str, BaseCheck] = {}

    def register(self, check: BaseCheck) -> None:
        """Registers a check instance."""
        if check.id in self._checks:
            return  # Already registered
        self._checks[check.id] = check

    def register_class(self, check_cls: type[BaseCheck]) -> None:
        """Instantiates and registers a check class."""
        self.register(check_cls())

    def get_checks(self, layers: list[AuditLayer] | None = None) -> list[BaseCheck]:
        """Returns checks optionally filtered by active layers."""
        if not layers:
            return list(self._checks.values())
        return [c for c in self._checks.values() if c.layer in layers]

    async def run_checks(
        self,
        crawl_result: CrawlResult,
        config: AuditConfig,
        active_layers: list[AuditLayer] | None = None,
    ) -> list[Finding]:
        """Executes site-wide and page-level checks across the crawled result."""
        layers = active_layers or config.layers
        applicable_checks = self.get_checks(layers)
        logger.info(
            "Running %d checks across layers: %s",
            len(applicable_checks),
            [layer_item.value for layer_item in layers],
        )

        from auditiq.crawler.graph import LinkGraph

        graph = LinkGraph(start_url=crawl_result.start_url)
        for url, snap in crawl_result.pages.items():
            for outlink in snap.outlinks:
                graph.add_edge(url, outlink)
        graph.compute_depths()

        site_context = SiteContext(
            crawl_result=crawl_result,
            link_graph=graph,
            config=config,
        )

        all_findings: list[Finding] = []

        # 1. Run site-wide checks
        site_tasks = [check.run_site(site_context) for check in applicable_checks]
        if site_tasks:
            site_results = await asyncio.gather(*site_tasks, return_exceptions=True)
            for res in site_results:
                if isinstance(res, list):
                    all_findings.extend(res)
                elif isinstance(res, Exception):
                    logger.error("Error in site-level check: %s", res)

        # 2. Run page-level checks across all crawled pages
        page_tasks = []
        for _url, snapshot in crawl_result.pages.items():
            page_context = PageContext(snapshot=snapshot, site=site_context)
            for check in applicable_checks:
                page_tasks.append(check.run_page(page_context))

        if page_tasks:
            # Chunk or gather all page checks
            page_results = await asyncio.gather(*page_tasks, return_exceptions=True)
            for res in page_results:
                if isinstance(res, list):
                    all_findings.extend(res)
                elif isinstance(res, Exception):
                    logger.error("Error in page-level check: %s", res)

        logger.info("Check execution finished: produced %d findings", len(all_findings))
        return all_findings


# Global singleton registry instance
default_registry = CheckRegistry()
