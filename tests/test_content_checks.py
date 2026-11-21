"""Unit tests for Content & Entity (CONT-*) check plugins."""

import pytest

from auditiq.checks.base import PageContext, SiteContext
from auditiq.checks.content.entity import BrandConsistencyCheck, SimhashDuplicateCheck
from auditiq.checks.content.readability import (
    SentenceVarietyCheck,
    ThinContentCheck,
    calculate_flesch_reading_ease,
    count_syllables,
)
from auditiq.checks.content.structure import AnswerFirstCheck
from auditiq.checks.content.trust import TrustPagesCheck
from auditiq.crawler.graph import LinkGraph
from auditiq.models.audit import AuditConfig
from auditiq.models.finding import FindingStatus
from auditiq.models.snapshot import CrawlResult, PageSnapshot


@pytest.fixture
def base_context() -> SiteContext:
    crawl_result = CrawlResult(
        start_url="https://example.com/",
        base_domain="example.com",
    )
    graph = LinkGraph(start_url="https://example.com/")
    config = AuditConfig(target_url="https://example.com/", brand_name="Acme Corp")
    return SiteContext(crawl_result=crawl_result, link_graph=graph, config=config)


def test_syllable_counter_and_flesch_math() -> None:
    assert count_syllables("cat") == 1
    assert count_syllables("syllable") == 3
    assert count_syllables("optimization") == 5

    words = ["This", "is", "a", "simple", "test", "sentence"]
    sentences = ["This is a simple test sentence."]
    ease = calculate_flesch_reading_ease(words, sentences)
    assert ease > 70.0  # Simple sentences score high ease


@pytest.mark.asyncio
async def test_thin_content_and_sentence_variety(base_context: SiteContext) -> None:
    thin_check = ThinContentCheck()
    variety_check = SentenceVarietyCheck()

    # Thin page
    snap_thin = PageSnapshot(
        url="https://example.com/thin",
        status_code=200,
        content_type="text/html",
        word_count=120,
    )
    f_thin = await thin_check.run_page(PageContext(snapshot=snap_thin, site=base_context))
    assert f_thin[0].status == FindingStatus.FAIL

    # Long wall-of-text paragraph (>150 words)
    long_p = "word " * 160
    snap_wall = PageSnapshot(
        url="https://example.com/wall",
        status_code=200,
        content_type="text/html",
        raw_html=f"<html><body><p>{long_p}</p></body></html>",
        word_count=300,
    )
    f_wall = await variety_check.run_page(PageContext(snapshot=snap_wall, site=base_context))
    assert f_wall[0].status == FindingStatus.WARNING


@pytest.mark.asyncio
async def test_answer_first_check(base_context: SiteContext) -> None:
    check = AnswerFirstCheck()

    # Good: opens with a definition
    snap_good = PageSnapshot(
        url="https://example.com/guide",
        status_code=200,
        content_type="text/html",
        raw_html="<html><body><main><p>Search Engine Optimization is a methodology designed to increase organic traffic by 45%.</p><p>Second paragraph details.</p></main></body></html>",
        word_count=350,
    )
    f_good = await check.run_page(PageContext(snapshot=snap_good, site=base_context))
    assert f_good[0].status == FindingStatus.PASS

    # Bad: hand-waving opening without facts or definitions
    snap_bad = PageSnapshot(
        url="https://example.com/vague",
        status_code=200,
        content_type="text/html",
        raw_html="<html><body><main><p>Welcome to our blog where we talk about many interesting things in the world today.</p><p>Another generic sentence.</p></main></body></html>",
        word_count=350,
    )
    f_bad = await check.run_page(PageContext(snapshot=snap_bad, site=base_context))
    assert f_bad[0].status == FindingStatus.WARNING


@pytest.mark.asyncio
async def test_simhash_near_duplicate_detection(base_context: SiteContext) -> None:
    check = SimhashDuplicateCheck()

    base_text = (
        "This is a comprehensive guide to generative engine optimization covering crawlers, schemas, and AI citations. "
        * 15
    )
    text_a = f"<html><body><p>{base_text} Keyword variant Boston.</p></body></html>"
    text_b = f"<html><body><p>{base_text} Keyword variant Chicago.</p></body></html>"

    base_context.crawl_result.pages = {
        "https://example.com/page-boston": PageSnapshot(
            url="https://example.com/page-boston",
            status_code=200,
            content_type="text/html",
            raw_html=text_a,
            word_count=200,
        ),
        "https://example.com/page-chicago": PageSnapshot(
            url="https://example.com/page-chicago",
            status_code=200,
            content_type="text/html",
            raw_html=text_b,
            word_count=200,
        ),
    }

    findings = await check.run_site(base_context)
    assert len(findings) >= 1
    assert findings[0].status == FindingStatus.FAIL
    assert "Near-duplicate content detected" in findings[0].title


@pytest.mark.asyncio
async def test_trust_pages_and_brand_consistency(base_context: SiteContext) -> None:
    trust_check = TrustPagesCheck()
    brand_check = BrandConsistencyCheck()

    # 1. Trust pages missing
    base_context.crawl_result.pages = {
        "https://example.com/": PageSnapshot(url="https://example.com/", status_code=200)
    }
    f_trust = await trust_check.run_site(base_context)
    assert f_trust[0].status == FindingStatus.WARNING
    assert "Missing essential trust pages" in f_trust[0].title

    # 2. Brand consistency on homepage
    snap_brand_good = PageSnapshot(
        url="https://example.com/",
        status_code=200,
        content_type="text/html",
        title="Acme Corp — Leading Enterprise Solutions",
    )
    f_brand_good = await brand_check.run_page(
        PageContext(snapshot=snap_brand_good, site=base_context)
    )
    assert f_brand_good[0].status == FindingStatus.PASS

    snap_brand_bad = PageSnapshot(
        url="https://example.com/",
        status_code=200,
        content_type="text/html",
        title="Home Page | Enterprise Solutions",
    )
    f_brand_bad = await brand_check.run_page(
        PageContext(snapshot=snap_brand_bad, site=base_context)
    )
    assert f_brand_bad[0].status == FindingStatus.WARNING
