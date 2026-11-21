"""Unit tests for Live AI Visibility engine, stats, generator, and checks (Layer 4)."""

import pytest

from auditiq.checks.base import SiteContext
from auditiq.checks.live.checks import (
    LiveCitationRateCheck,
    LiveMentionRateCheck,
    LiveShareOfVoiceCheck,
    LiveTopCitedDomainsCheck,
)
from auditiq.crawler.graph import LinkGraph
from auditiq.models.audit import AuditConfig
from auditiq.models.finding import FindingStatus, Severity
from auditiq.models.snapshot import CrawlResult, PageSnapshot
from auditiq.visibility.estimator import BudgetEstimator
from auditiq.visibility.generator import PromptGenerator
from auditiq.visibility.providers.mock import MockAnswerEngine
from auditiq.visibility.runner import VisibilityRunner
from auditiq.visibility.stats import compute_wilson_interval


def test_wilson_interval_math() -> None:
    # 0 out of 0
    empty = compute_wilson_interval(0, 0)
    assert empty.point_estimate == 0.0
    assert empty.lower_bound == 0.0
    assert empty.upper_bound == 0.0
    assert "n=0" in empty.display

    # 10 out of 20 (50%)
    res = compute_wilson_interval(10, 20)
    assert res.point_estimate == 0.50
    assert 0.29 < res.lower_bound < 0.35
    assert 0.65 < res.upper_bound < 0.71
    assert "50.0%" in res.display
    assert "95% CI:" in res.display
    assert "n=20" in res.display

    # Edge case 0 out of 20
    zero = compute_wilson_interval(0, 20)
    assert zero.point_estimate == 0.0
    assert zero.lower_bound == 0.0
    assert zero.upper_bound > 0.0  # Wilson upper bound is positive even at 0 successes

    # Edge case 20 out of 20
    full = compute_wilson_interval(20, 20)
    assert full.point_estimate == 1.0
    assert full.lower_bound < 1.0
    assert full.upper_bound == 1.0


def test_prompt_generator() -> None:
    snap = PageSnapshot(
        url="https://acme.org/",
        status_code=200,
        title="Acme Analytics - Intelligent Data Solutions",
        meta_description="Enterprise data analytics platform.",
    )
    cr = CrawlResult(
        start_url="https://acme.org/",
        base_domain="acme.org",
        pages={"https://acme.org/": snap},
    )

    queries = PromptGenerator.generate_queries(cr, brand_name="Acme", max_queries=15)
    assert len(queries) == 15

    archetypes = {q.archetype for q in queries}
    assert "discovery" in archetypes
    assert "comparison" in archetypes
    assert "problem_solution" in archetypes
    assert "how_to" in archetypes
    assert "brand" in archetypes

    for q in queries:
        assert q.expected_brand == "Acme"
        assert q.target_domain == "acme.org"
        assert len(q.query) > 10


def test_budget_estimator() -> None:
    estimate = BudgetEstimator.estimate(
        num_queries=20,
        engines=["openai", "perplexity", "gemini", "anthropic"],
        max_budget_usd=1.00,
    )
    assert estimate.total_queries == 20
    assert estimate.engines_count == 4
    assert estimate.estimated_cost_usd > 0.0
    assert estimate.is_within_budget is True


@pytest.mark.asyncio
async def test_mock_engine_and_runner() -> None:
    mock_engine = MockAnswerEngine(name="mock-test")
    assert mock_engine.is_available() is True

    runner = VisibilityRunner(engines=[mock_engine])
    cr = CrawlResult(start_url="https://mybrand.io/", base_domain="mybrand.io")
    queries = PromptGenerator.generate_queries(cr, brand_name="MyBrand", max_queries=10)

    summary = await runner.run(queries)
    assert summary.total_evaluations == 10
    assert summary.active_engines == ["mock-test"]
    assert 0.0 <= summary.mention_rate.point_estimate <= 1.0
    assert 0.0 <= summary.citation_rate.point_estimate <= 1.0
    assert len(summary.responses) == 10
    assert len(summary.top_cited_domains) > 0


@pytest.mark.asyncio
async def test_live_checks_not_measured_when_summary_missing() -> None:
    mention_check = LiveMentionRateCheck()
    citation_check = LiveCitationRateCheck()
    sov_check = LiveShareOfVoiceCheck()
    top_domains_check = LiveTopCitedDomainsCheck()

    cr = CrawlResult(start_url="https://example.com/", base_domain="example.com")
    graph = LinkGraph(start_url="https://example.com/")
    config = AuditConfig(target_url="https://example.com/")
    context = SiteContext(crawl_result=cr, link_graph=graph, config=config, visibility_summary=None)

    # All checks must return NOT_MEASURED status
    for check in (mention_check, citation_check, sov_check, top_domains_check):
        findings = await check.run_site(context)
        assert len(findings) == 1
        assert findings[0].status == FindingStatus.NOT_MEASURED
        assert findings[0].severity == Severity.INFO


@pytest.mark.asyncio
async def test_live_checks_with_measured_summary() -> None:
    mention_check = LiveMentionRateCheck()
    citation_check = LiveCitationRateCheck()

    mock_engine = MockAnswerEngine(name="mock-ai")
    runner = VisibilityRunner(engines=[mock_engine])
    cr = CrawlResult(start_url="https://example.com/", base_domain="example.com")
    queries = PromptGenerator.generate_queries(cr, brand_name="ExampleBrand", max_queries=10)
    summary = await runner.run(queries)

    graph = LinkGraph(start_url="https://example.com/")
    config = AuditConfig(target_url="https://example.com/")
    context = SiteContext(
        crawl_result=cr,
        link_graph=graph,
        config=config,
        visibility_summary=summary,
    )

    mention_findings = await mention_check.run_site(context)
    assert len(mention_findings) == 1
    assert mention_findings[0].status in (
        FindingStatus.PASS,
        FindingStatus.WARNING,
        FindingStatus.FAIL,
    )
    assert "95% CI:" in mention_findings[0].title

    citation_findings = await citation_check.run_site(context)
    assert len(citation_findings) == 1
    assert citation_findings[0].status in (
        FindingStatus.PASS,
        FindingStatus.WARNING,
        FindingStatus.FAIL,
    )
    assert "95% CI:" in citation_findings[0].title
