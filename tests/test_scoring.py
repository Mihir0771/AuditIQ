"""Unit tests for the scoring engine and prioritization matrix."""

from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity
from auditiq.scoring.engine import calculate_score_card, prioritize_actions


def test_scoring_bounds_and_letter_grades() -> None:
    # 1. Zero failures should yield a 100 A
    card_perfect = calculate_score_card(
        findings=[],
        total_pages_crawled=10,
        active_layers=[AuditLayer.TECHNICAL],
    )
    assert card_perfect.composite_score == 100.0
    assert card_perfect.letter_grade == "A"
    assert card_perfect.layer_scores[AuditLayer.TECHNICAL] == 100.0

    # 2. Critical failures should lower the score into D or F
    critical_finding = Finding(
        id="f1",
        check_id="TECH-ROBOTS-BLOCKING",
        layer=AuditLayer.TECHNICAL,
        severity=Severity.CRITICAL,
        status=FindingStatus.FAIL,
        url="https://example.com/robots.txt",
        title="Accidental Critical Path Blocking",
        why_it_matters="Blocks search engines",
        fix="Fix robots.txt",
        effort=Effort.SMALL,
        impact=5,
    )
    card_failing = calculate_score_card(
        findings=[critical_finding],
        total_pages_crawled=1,
        active_layers=[AuditLayer.TECHNICAL],
    )
    assert card_failing.composite_score < 70.0
    assert card_failing.letter_grade in ("D", "F")


def test_proportional_weight_redistribution() -> None:
    # Only Technical and Content active; Live Visibility omitted
    card = calculate_score_card(
        findings=[],
        total_pages_crawled=5,
        active_layers=[AuditLayer.TECHNICAL, AuditLayer.CONTENT],
    )
    # Technical (0.25) and Content (0.20) => sum 0.45
    # Tech weight = 0.25 / 0.45 = 0.5556
    # Content weight = 0.20 / 0.45 = 0.4444
    assert round(sum(card.layer_weights.values()), 2) == 1.0
    assert card.layer_scores[AuditLayer.LIVE_VISIBILITY] is None


def test_action_prioritization_quadrants() -> None:
    f_quick_win = Finding(
        id="f1",
        check_id="TECH-CANONICAL-MISSING",
        layer=AuditLayer.TECHNICAL,
        severity=Severity.HIGH,
        status=FindingStatus.FAIL,
        url="https://example.com/",
        title="Missing Canonical",
        why_it_matters="",
        fix="",
        effort=Effort.SMALL,
        impact=4,
    )
    f_major = Finding(
        id="f2",
        check_id="TECH-CWV-LCP",
        layer=AuditLayer.TECHNICAL,
        severity=Severity.HIGH,
        status=FindingStatus.FAIL,
        url="https://example.com/",
        title="Slow LCP",
        why_it_matters="",
        fix="",
        effort=Effort.LARGE,
        impact=4,
    )

    actions = prioritize_actions([f_quick_win, f_major], total_pages=1)
    assert len(actions) == 2
    assert actions[0].check_id == "TECH-CANONICAL-MISSING"
    assert actions[0].quadrant.value == "Quick wins"
    assert actions[1].check_id == "TECH-CWV-LCP"
    assert actions[1].quadrant.value == "Major projects"
