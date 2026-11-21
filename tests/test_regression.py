"""Unit tests for audit historical comparison and regression detection."""

from auditiq.models.audit import AuditConfig, AuditRecord, AuditStatus
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity
from auditiq.scoring.engine import calculate_score_card
from auditiq.scoring.regression import compare_audits


def test_compare_audits_regression_and_fixes() -> None:
    config = AuditConfig(target_url="https://example.com/", brand_name="Acme")

    # Baseline audit has 2 issues: f_fixed and f_persistent
    f_fixed = Finding(
        id="f1",
        check_id="TECH-TITLE-MISSING",
        layer=AuditLayer.TECHNICAL,
        url="https://example.com/p1",
        status=FindingStatus.FAIL,
        severity=Severity.HIGH,
        effort=Effort.SMALL,
        impact=5,
        title="Missing Title",
        why_it_matters="Critical",
        fix="Fix it",
    )
    f_persistent = Finding(
        id="f2",
        check_id="CONT-THIN-CONTENT",
        layer=AuditLayer.CONTENT,
        url="https://example.com/p2",
        status=FindingStatus.FAIL,
        severity=Severity.MEDIUM,
        effort=Effort.MEDIUM,
        impact=4,
        title="Thin Content",
        why_it_matters="Needs more text",
        fix="Add text",
    )

    baseline_score = calculate_score_card(findings=[f_fixed, f_persistent], total_pages_crawled=2)
    baseline_record = AuditRecord(
        id="audit_baseline",
        config=config,
        status=AuditStatus.COMPLETED,
        score_card=baseline_score,
        findings=[f_fixed, f_persistent],
    )

    # Current audit resolved f_fixed, kept f_persistent, but introduced new issue f_new
    f_new = Finding(
        id="f3",
        check_id="TECH-CANONICAL-MISSING",
        layer=AuditLayer.TECHNICAL,
        url="https://example.com/p3",
        status=FindingStatus.FAIL,
        severity=Severity.HIGH,
        effort=Effort.SMALL,
        impact=4,
        title="Missing Canonical",
        why_it_matters="Duplicate content risk",
        fix="Add canonical",
    )

    current_score = calculate_score_card(findings=[f_persistent, f_new], total_pages_crawled=2)
    current_record = AuditRecord(
        id="audit_current",
        config=config,
        status=AuditStatus.COMPLETED,
        score_card=current_score,
        findings=[f_persistent, f_new],
    )

    cmp = compare_audits(baseline_record, current_record)

    assert cmp.baseline_id == "audit_baseline"
    assert cmp.current_id == "audit_current"
    assert cmp.resolved_count == 1
    assert cmp.resolved_findings[0].check_id == "TECH-TITLE-MISSING"

    assert cmp.new_issues_count == 1
    assert cmp.new_findings[0].check_id == "TECH-CANONICAL-MISSING"

    assert cmp.persistent_count == 1
    assert cmp.persistent_findings[0].check_id == "CONT-THIN-CONTENT"
