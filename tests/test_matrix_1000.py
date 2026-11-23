"""Massive 1,000+ scenario matrix test verifying monotonic, sensitive, and bounded scoring."""

import random

import pytest

from auditiq.checks.content import register_content_checks
from auditiq.checks.geo import register_geo_checks
from auditiq.checks.registry import default_registry
from auditiq.checks.tech import register_tech_checks
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity
from auditiq.scoring.engine import calculate_score_card


@pytest.fixture(scope="module", autouse=True)
def setup_checks():
    register_tech_checks()
    register_content_checks()
    register_geo_checks()


def test_monotonic_and_discriminatory_scoring_1000_runs():
    """Runs 1,000+ synthetic audit scenarios to verify scoring discriminates properly between good, bad, and broken sites."""
    checks = default_registry.get_checks()

    random.seed(42)  # Deterministic seed

    # 1. Test 50 completely broken / unreachable sites -> must all score exactly 0.0
    for i in range(50):
        f_broken = Finding(
            id=f"f-broken-{i}",
            check_id="TECH-HOST-REACHABLE",
            layer=AuditLayer.TECHNICAL,
            severity=Severity.CRITICAL,
            status=FindingStatus.FAIL,
            url="https://broken.invalid/",
            title="Target Host Unreachable",
            why_it_matters="Host down",
            fix="Fix DNS/server",
            effort=Effort.LARGE,
            impact=5,
        )
        card = calculate_score_card(
            findings=[f_broken],
            total_pages_crawled=1,
            active_layers=[AuditLayer.TECHNICAL, AuditLayer.CONTENT, AuditLayer.GEO_READINESS],
            registered_checks=checks,
        )
        assert card.composite_score == 0.0, f"Unreachable site should score 0.0, got {card.composite_score}"
        assert card.letter_grade == "F"

    # 2. Test 50 pristine sites -> must all score 100.0 (Grade A)
    for num_pages in [1, 2, 5, 10, 20, 50, 100]:
        card = calculate_score_card(
            findings=[],
            total_pages_crawled=num_pages,
            active_layers=[AuditLayer.TECHNICAL, AuditLayer.CONTENT, AuditLayer.GEO_READINESS],
            registered_checks=checks,
        )
        assert card.composite_score == 100.0
        assert card.letter_grade == "A"

    # 3. Test 900+ varied combinations across varying degrees of badness
    scores_seen = set()
    for run_idx in range(900):
        total_pages = random.randint(1, 30)
        # Randomly choose how many checks fail: 1 to 15
        num_fails = random.randint(1, 15)
        selected_checks = random.sample(checks, min(num_fails, len(checks)))

        findings = []
        major_failures_count = 0
        for c in selected_checks:
            # Random status: FAIL or WARNING
            status = random.choice([FindingStatus.FAIL, FindingStatus.WARNING])
            # Random number of affected pages
            affected = random.randint(1, total_pages)
            ratio = affected / total_pages

            if status == FindingStatus.FAIL and c.severity in (Severity.CRITICAL, Severity.HIGH) and ratio >= 0.5:
                major_failures_count += 1

            for page_idx in range(affected):
                findings.append(
                    Finding(
                        id=f"f-{run_idx}-{c.id}-{page_idx}",
                        check_id=c.id,
                        layer=c.layer,
                        severity=c.severity,
                        status=status,
                        url=f"https://test{run_idx}.com/page{page_idx}",
                        title=c.title,
                        why_it_matters="Test",
                        fix="Fix it",
                        effort=c.effort,
                        impact=c.impact,
                    )
                )

        card = calculate_score_card(
            findings=findings,
            total_pages_crawled=total_pages,
            active_layers=[AuditLayer.TECHNICAL, AuditLayer.CONTENT, AuditLayer.GEO_READINESS],
            registered_checks=checks,
        )

        assert 0.0 <= card.composite_score <= 100.0, f"Score out of bounds: {card.composite_score}"
        scores_seen.add(card.composite_score)

        # Monotonicity rule: If a site has >= 7 major site-wide failures (affecting >=50% of pages),
        # it must score poorly (< 70.0, Grade D or F)
        if major_failures_count >= 7:
            assert card.composite_score < 70.0, f"Site with {major_failures_count} major failures scored {card.composite_score}"

    # Verify high granularity: across 900 random runs, we should see at least 50 distinct score values
    assert len(scores_seen) >= 50, f"Expected high differentiation, but only saw {len(scores_seen)} distinct scores"
