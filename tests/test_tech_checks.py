"""Unit tests for Technical SEO (TECH-*) check plugins."""

import pytest

from auditiq.checks.base import PageContext, SiteContext
from auditiq.checks.tech.crawlability import (
    CanonicalMissingCheck,
    RobotsBlockingCheck,
    RobotsPresenceCheck,
)
from auditiq.checks.tech.onpage import (
    H1MissingMultiCheck,
    TitleMissingCheck,
)
from auditiq.checks.tech.schema import SchemaSyntaxCheck
from auditiq.crawler.graph import LinkGraph
from auditiq.models.audit import AuditConfig
from auditiq.models.finding import FindingStatus
from auditiq.models.snapshot import CrawlResult, PageSnapshot


@pytest.fixture
def base_site_context() -> SiteContext:
    crawl_result = CrawlResult(
        start_url="https://example.com/",
        base_domain="example.com",
        robots_txt_content="User-agent: *\nDisallow: /admin/",
        robots_txt_status=200,
    )
    graph = LinkGraph(start_url="https://example.com/")
    config = AuditConfig(target_url="https://example.com/")
    return SiteContext(crawl_result=crawl_result, link_graph=graph, config=config)


@pytest.mark.asyncio
async def test_robots_checks(base_site_context: SiteContext) -> None:
    # 1. Presence check with content
    presence_check = RobotsPresenceCheck()
    findings = await presence_check.run_site(base_site_context)
    assert len(findings) == 1
    assert findings[0].status == FindingStatus.PASS

    # 2. Presence check when robots is missing
    base_site_context.crawl_result.robots_txt_content = None
    findings = await presence_check.run_site(base_site_context)
    assert findings[0].status == FindingStatus.FAIL

    # 3. Blocking check with catastrophic rule
    blocking_check = RobotsBlockingCheck()
    base_site_context.crawl_result.robots_txt_content = "User-agent: *\nDisallow: /"
    findings = await blocking_check.run_site(base_site_context)
    assert findings[0].status == FindingStatus.FAIL


@pytest.mark.asyncio
async def test_canonical_checks(base_site_context: SiteContext) -> None:
    canon_check = CanonicalMissingCheck()

    # Page with canonical
    snap_good = PageSnapshot(
        url="https://example.com/page",
        status_code=200,
        content_type="text/html",
        canonical_url="https://example.com/page",
    )
    ctx_good = PageContext(snapshot=snap_good, site=base_site_context)
    f_good = await canon_check.run_page(ctx_good)
    assert f_good[0].status == FindingStatus.PASS

    # Page missing canonical
    snap_bad = PageSnapshot(
        url="https://example.com/page2",
        status_code=200,
        content_type="text/html",
        canonical_url="",
    )
    ctx_bad = PageContext(snapshot=snap_bad, site=base_site_context)
    f_bad = await canon_check.run_page(ctx_bad)
    assert f_bad[0].status == FindingStatus.FAIL


@pytest.mark.asyncio
async def test_title_and_h1_checks(base_site_context: SiteContext) -> None:
    title_check = TitleMissingCheck()
    h1_check = H1MissingMultiCheck()

    snap_missing = PageSnapshot(
        url="https://example.com/",
        status_code=200,
        content_type="text/html",
        title="",
        h1s=[],
    )
    ctx = PageContext(snapshot=snap_missing, site=base_site_context)

    f_title = await title_check.run_page(ctx)
    assert f_title[0].status == FindingStatus.FAIL

    f_h1 = await h1_check.run_page(ctx)
    assert f_h1[0].status == FindingStatus.FAIL


@pytest.mark.asyncio
async def test_schema_checks(base_site_context: SiteContext) -> None:
    syntax_check = SchemaSyntaxCheck()

    # Good JSON-LD
    snap_good = PageSnapshot(
        url="https://example.com/",
        status_code=200,
        content_type="text/html",
        raw_html='<html><head><script type="application/ld+json">{"@context": "https://schema.org", "@type": "Organization", "name": "Acme"}</script></head><body></body></html>',
    )
    f_good = await syntax_check.run_page(PageContext(snapshot=snap_good, site=base_site_context))
    assert f_good[0].status == FindingStatus.PASS

    # Malformed JSON-LD
    snap_bad = PageSnapshot(
        url="https://example.com/broken",
        status_code=200,
        content_type="text/html",
        raw_html='<html><head><script type="application/ld+json">{malformed json here}</script></head><body></body></html>',
    )
    f_bad = await syntax_check.run_page(PageContext(snapshot=snap_bad, site=base_site_context))
    assert f_bad[0].status == FindingStatus.FAIL
