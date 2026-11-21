"""Unit tests for GEO Readiness checks (Layer 3)."""

import pytest

from auditiq.checks.base import PageContext, SiteContext
from auditiq.checks.geo.authority import BotTtfbCheck, EntitySameAsCheck
from auditiq.checks.geo.bot_matrix import AiBotMatrixCheck, BotFirewallCheck
from auditiq.checks.geo.chunkability import PassageChunkingCheck
from auditiq.checks.geo.extractability import SemanticHtmlCheck, TextTrappedCheck
from auditiq.checks.geo.llms_txt import LlmsTxtCheck
from auditiq.checks.geo.render_diff import RenderDiffLinksCheck, RenderDiffTextCheck
from auditiq.crawler.graph import LinkGraph
from auditiq.models.audit import AuditConfig
from auditiq.models.finding import FindingStatus, Severity
from auditiq.models.snapshot import CrawlResult, PageSnapshot


@pytest.fixture
def base_context() -> SiteContext:
    cr = CrawlResult(start_url="https://example.com/", base_domain="example.com")
    graph = LinkGraph(start_url="https://example.com/")
    config = AuditConfig(target_url="https://example.com/", brand_name="Acme Corp")
    return SiteContext(crawl_result=cr, link_graph=graph, config=config)


@pytest.mark.asyncio
async def test_ai_bot_matrix_check(base_context: SiteContext) -> None:
    check = AiBotMatrixCheck()
    robots_txt = """
    User-agent: OAI-SearchBot
    Disallow: /

    User-agent: GPTBot
    Disallow: /
    """
    base_context.crawl_result.robots_txt_content = robots_txt
    findings = await check.run_site(base_context)

    # Must contain critical failure for search bot
    critical_findings = [f for f in findings if f.severity == Severity.CRITICAL]
    assert len(critical_findings) == 1
    assert "OAI-SearchBot" in critical_findings[0].title

    # Must contain informational note for training bot
    info_findings = [f for f in findings if f.severity == Severity.INFO]
    assert len(info_findings) == 1
    assert "GPTBot" in info_findings[0].title


@pytest.mark.asyncio
async def test_bot_firewall_check(base_context: SiteContext) -> None:
    check = BotFirewallCheck()
    snap_blocked = PageSnapshot(
        url="https://example.com/",
        status_code=403,
        raw_html="<html><body>Cloudflare Just a moment... cf-chl-bypass</body></html>",
    )
    base_context.crawl_result.pages = {"https://example.com/": snap_blocked}
    findings = await check.run_site(base_context)
    assert len(findings) == 1
    assert findings[0].status == FindingStatus.FAIL
    assert findings[0].severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_render_diff_checks(base_context: SiteContext) -> None:
    text_check = RenderDiffTextCheck()
    links_check = RenderDiffLinksCheck()

    raw_html = "<html><body><div id='root'></div><script src='app.js'></script></body></html>"
    rendered_html = (
        "<html><body><div id='root'><h1>Dashboard</h1><p>"
        + " ".join(["content"] * 300)
        + "</p><a href='/page1'>P1</a><a href='/page2'>P2</a><a href='/page3'>P3</a>"
        + "<a href='/page4'>P4</a><a href='/page5'>P5</a><a href='/page6'>P6</a></div></body></html>"
    )

    snap = PageSnapshot(
        url="https://example.com/",
        status_code=200,
        raw_html=raw_html,
        rendered_html=rendered_html,
        is_rendered=True,
    )
    context = PageContext(snapshot=snap, site=base_context)

    text_findings = await text_check.run_page(context)
    assert len(text_findings) == 1
    assert text_findings[0].status == FindingStatus.FAIL
    assert text_findings[0].severity == Severity.CRITICAL

    links_findings = await links_check.run_page(context)
    assert len(links_findings) == 1
    assert links_findings[0].status == FindingStatus.WARNING


@pytest.mark.asyncio
async def test_semantic_html_and_trapped_text(base_context: SiteContext) -> None:
    sem_check = SemanticHtmlCheck()
    trapped_check = TextTrappedCheck()

    div_soup = (
        "<html><body>"
        + "".join([f"<div class='box{i}'><span>text</span></div>" for i in range(50)])
        + "<canvas></canvas><canvas></canvas><canvas></canvas>"
        + "</body></html>"
    )
    snap = PageSnapshot(url="https://example.com/page", status_code=200, raw_html=div_soup)
    context = PageContext(snapshot=snap, site=base_context)

    sem_findings = await sem_check.run_page(context)
    assert len(sem_findings) == 1
    assert sem_findings[0].status == FindingStatus.WARNING

    trapped_findings = await trapped_check.run_page(context)
    assert len(trapped_findings) == 1
    assert "canvas" in trapped_findings[0].title.lower()


@pytest.mark.asyncio
async def test_passage_chunking_check(base_context: SiteContext) -> None:
    check = PassageChunkingCheck()
    html = "<html><body><article><p>" + " ".join(["word"] * 600) + "</p></article></body></html>"
    snap = PageSnapshot(
        url="https://example.com/article",
        status_code=200,
        raw_html=html,
        word_count=600,
    )
    context = PageContext(snapshot=snap, site=base_context)
    findings = await check.run_page(context)
    assert len(findings) == 1
    assert findings[0].status == FindingStatus.WARNING
    assert "Monolithic content" in findings[0].title


@pytest.mark.asyncio
async def test_llms_txt_check(base_context: SiteContext) -> None:
    check = LlmsTxtCheck()
    valid_markdown = """# Project AuditIQ
> Production grade AI SEO and GEO audit engine.

## Documentation
- [Architecture](https://example.com/docs/arch)
- [API Reference](https://example.com/docs/api)
"""
    base_context.crawl_result.llms_txt_status = 200
    base_context.crawl_result.llms_txt_content = valid_markdown

    findings = await check.run_site(base_context)
    assert len(findings) == 1
    assert findings[0].status == FindingStatus.PASS
    assert "Valid /llms.txt" in findings[0].title


@pytest.mark.asyncio
async def test_entity_sameas_and_ttfb(base_context: SiteContext) -> None:
    sameas_check = EntitySameAsCheck()
    ttfb_check = BotTtfbCheck()

    schema_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "AuditIQ Tech",
          "url": "https://example.com",
          "sameAs": [
            "https://www.wikidata.org/wiki/Q12345",
            "https://www.linkedin.com/company/auditiq"
          ]
        }
        </script>
      </head>
      <body><h1>Home</h1></body>
    </html>
    """
    snap = PageSnapshot(
        url="https://example.com/",
        status_code=200,
        raw_html=schema_html,
        ttfb_ms=1650.0,
        depth=0,
    )
    context = PageContext(snapshot=snap, site=base_context)

    sameas_findings = await sameas_check.run_page(context)
    assert len(sameas_findings) == 1
    assert sameas_findings[0].status == FindingStatus.PASS

    ttfb_findings = await ttfb_check.run_page(context)
    assert len(ttfb_findings) == 1
    assert ttfb_findings[0].status == FindingStatus.FAIL
    assert ttfb_findings[0].severity == Severity.HIGH
