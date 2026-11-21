"""Audit comparison and regression detection engine."""

from pydantic import BaseModel, Field

from auditiq.models.audit import AuditRecord
from auditiq.models.finding import Finding, FindingStatus


class FindingSummaryItem(BaseModel):
    check_id: str
    url: str
    title: str
    severity: str
    layer: str


class AuditComparison(BaseModel):
    baseline_id: str
    current_id: str
    target_url: str
    baseline_date: str
    current_date: str
    baseline_grade: str
    current_grade: str
    baseline_score: float
    current_score: float
    score_delta: float
    layer_deltas: dict[str, float] = Field(default_factory=dict)
    resolved_count: int = 0
    new_issues_count: int = 0
    persistent_count: int = 0
    resolved_findings: list[FindingSummaryItem] = Field(default_factory=list)
    new_findings: list[FindingSummaryItem] = Field(default_factory=list)
    persistent_findings: list[FindingSummaryItem] = Field(default_factory=list)


def compare_audits(baseline: AuditRecord, current: AuditRecord) -> AuditComparison:
    """Computes exact diffs between two audits of the same domain."""
    b_card = baseline.score_card
    c_card = current.score_card

    b_score = b_card.composite_score if b_card else 0.0
    c_score = c_card.composite_score if c_card else 0.0
    delta = round(c_score - b_score, 1)

    # Layer score deltas
    layer_deltas: dict[str, float] = {}
    if c_card and b_card:
        for layer, score in c_card.layer_scores.items():
            if score is not None:
                b_layer_score = b_card.layer_scores.get(layer)
                if b_layer_score is not None:
                    layer_deltas[layer.value] = round(score - b_layer_score, 1)

    # Group issues by (check_id, url)
    def _key(f: Finding) -> tuple[str, str]:
        return (f.check_id, f.url)

    # Filter to actual failures and warnings
    b_failing = {
        _key(f): f
        for f in baseline.findings
        if f.status in (FindingStatus.FAIL, FindingStatus.WARNING)
    }
    c_failing = {
        _key(f): f
        for f in current.findings
        if f.status in (FindingStatus.FAIL, FindingStatus.WARNING)
    }

    resolved_keys = set(b_failing.keys()) - set(c_failing.keys())
    new_keys = set(c_failing.keys()) - set(b_failing.keys())
    persistent_keys = set(b_failing.keys()) & set(c_failing.keys())

    def _to_summary(f: Finding) -> FindingSummaryItem:
        return FindingSummaryItem(
            check_id=f.check_id,
            url=f.url,
            title=f.title,
            severity=f.severity.value,
            layer=f.layer.value,
        )

    resolved_items = [_to_summary(b_failing[k]) for k in sorted(resolved_keys)]
    new_items = [_to_summary(c_failing[k]) for k in sorted(new_keys)]
    persistent_items = [_to_summary(c_failing[k]) for k in sorted(persistent_keys)]

    return AuditComparison(
        baseline_id=baseline.id,
        current_id=current.id,
        target_url=current.config.target_url,
        baseline_date=baseline.created_at.strftime("%Y-%m-%d %H:%M"),
        current_date=current.created_at.strftime("%Y-%m-%d %H:%M"),
        baseline_grade=b_card.letter_grade if b_card else "N/A",
        current_grade=c_card.letter_grade if c_card else "N/A",
        baseline_score=b_score,
        current_score=c_score,
        score_delta=delta,
        layer_deltas=layer_deltas,
        resolved_count=len(resolved_items),
        new_issues_count=len(new_items),
        persistent_count=len(persistent_items),
        resolved_findings=resolved_items,
        new_findings=new_items,
        persistent_findings=persistent_items,
    )
