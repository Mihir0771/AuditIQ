"""Mathematical scoring engine and action prioritizer."""

from collections import defaultdict
from typing import Any

from auditiq.models.audit import PriorityAction, PriorityQuadrant, ScoreCard
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity

# Severity multipliers
SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.CRITICAL: 1.00,
    Severity.HIGH: 0.70,
    Severity.MEDIUM: 0.40,
    Severity.LOW: 0.20,
    Severity.INFO: 0.00,
}

# Base layer weights
DEFAULT_LAYER_WEIGHTS: dict[AuditLayer, float] = {
    AuditLayer.TECHNICAL: 0.25,
    AuditLayer.CONTENT: 0.20,
    AuditLayer.GEO_READINESS: 0.25,
    AuditLayer.LIVE_VISIBILITY: 0.30,
}

# Effort numerical dividers
EFFORT_DIVIDERS: dict[Effort, float] = {
    Effort.SMALL: 1.0,
    Effort.MEDIUM: 2.5,
    Effort.LARGE: 5.0,
}


def calculate_score_card(
    findings: list[Finding],
    total_pages_crawled: int,
    active_layers: list[AuditLayer] | None = None,
    scoring_version: str = "2026.1",
    registered_checks: list[Any] | None = None,
) -> ScoreCard:
    """Calculates reproducible, explainable layer scores and overall composite score.

    Implements proportional weight redistribution when layers are not measured.
    When registered_checks is provided, all registered checks are included in the denominator
    so that silent passes (returning []) are credited with 100% score equity.
    """
    effective_layers = active_layers or list(AuditLayer)
    total_pages = max(1, total_pages_crawled)

    # Group findings by check_id
    findings_by_check: dict[str, list[Finding]] = defaultdict(list)
    check_metadata: dict[str, Finding] = {}
    for f in findings:
        findings_by_check[f.check_id].append(f)
        if f.check_id not in check_metadata:
            check_metadata[f.check_id] = f

    # Calculate score per layer
    layer_scores: dict[AuditLayer, float | None] = {}
    top_negative: list[str] = []
    top_positive: list[str] = []

    for layer in AuditLayer:
        if layer not in effective_layers:
            layer_scores[layer] = None
            continue

        total_weight = 0.0
        weighted_score_sum = 0.0

        # Preferred path: Use registered checks to avoid denominator skew
        layer_registered = [
            c for c in (registered_checks or []) if getattr(c, "layer", None) == layer
        ]

        if layer_registered:
            for check in layer_registered:
                check_id = check.id
                severity = check.severity
                title = check.title
                weight = SEVERITY_WEIGHTS.get(severity, 0.4)
                if weight == 0.0:
                    continue

                total_weight += weight
                failures = [
                    f
                    for f in findings_by_check.get(check_id, [])
                    if f.status in (FindingStatus.FAIL, FindingStatus.WARNING)
                ]
                if not failures:
                    weighted_score_sum += weight * 1.0
                    if severity in (Severity.CRITICAL, Severity.HIGH):
                        top_positive.append(f"{title} passed cleanly.")
                else:
                    affected_count = len(failures)
                    ratio_affected = min(1.0, affected_count / total_pages)
                    severity_penalty = (
                        1.0
                        if severity == Severity.CRITICAL
                        else 0.7
                        if severity == Severity.HIGH
                        else 0.4
                    )
                    check_score = max(0.0, 1.0 - (ratio_affected * severity_penalty))
                    weighted_score_sum += weight * check_score

                    deduction_pts = (1.0 - check_score) * weight * 100.0
                    if deduction_pts > 2.0:
                        top_negative.append(
                            f"{title} affected {affected_count} page(s) (-{deduction_pts:.1f} pts)"
                        )
        else:
            # Fallback path: Infer checks from findings (for isolated unit tests)
            layer_checks = [c_id for c_id, f in check_metadata.items() if f.layer == layer]
            if not layer_checks:
                layer_scores[layer] = 100.0
                continue

            for check_id in layer_checks:
                sample_finding = check_metadata[check_id]
                weight = SEVERITY_WEIGHTS[sample_finding.severity]
                if weight == 0.0:
                    continue

                total_weight += weight
                check_findings = findings_by_check[check_id]
                failures = [
                    f
                    for f in check_findings
                    if f.status in (FindingStatus.FAIL, FindingStatus.WARNING)
                ]
                if not failures:
                    weighted_score_sum += weight * 1.0
                    if sample_finding.severity in (Severity.CRITICAL, Severity.HIGH):
                        top_positive.append(f"{sample_finding.title} passed cleanly.")
                else:
                    affected_count = len(failures)
                    ratio_affected = min(1.0, affected_count / total_pages)
                    severity_penalty = (
                        1.0
                        if sample_finding.severity == Severity.CRITICAL
                        else 0.7
                        if sample_finding.severity == Severity.HIGH
                        else 0.4
                    )
                    check_score = max(0.0, 1.0 - (ratio_affected * severity_penalty))
                    weighted_score_sum += weight * check_score

                    deduction_pts = (1.0 - check_score) * weight * 100.0
                    if deduction_pts > 2.0:
                        top_negative.append(
                            f"{sample_finding.title} affected {affected_count} page(s) (-{deduction_pts:.1f} pts)"
                        )

        if total_weight > 0:
            raw_layer_score = round((weighted_score_sum / total_weight) * 100.0, 1)
        else:
            raw_layer_score = 100.0

        layer_scores[layer] = max(0.0, min(100.0, raw_layer_score))

    # Calculate proportional redistribution weights
    active_weight_sum = sum(DEFAULT_LAYER_WEIGHTS[layer_item] for layer_item in effective_layers)
    normalized_weights: dict[AuditLayer, float] = {}
    composite_score = 0.0

    for layer in effective_layers:
        norm_w = DEFAULT_LAYER_WEIGHTS[layer] / active_weight_sum
        normalized_weights[layer] = round(norm_w, 4)
        layer_s = layer_scores.get(layer)
        if layer_s is not None:
            composite_score += norm_w * layer_s

    composite_score = round(max(0.0, min(100.0, composite_score)), 1)

    # Determine letter grade
    if composite_score >= 90.0:
        grade = "A"
    elif composite_score >= 80.0:
        grade = "B"
    elif composite_score >= 70.0:
        grade = "C"
    elif composite_score >= 60.0:
        grade = "D"
    else:
        grade = "F"

    # Prioritize actions (Impact x Confidence / Effort)
    priority_actions = prioritize_actions(findings, total_pages)

    return ScoreCard(
        scoring_version=scoring_version,
        composite_score=composite_score,
        letter_grade=grade,
        layer_scores=layer_scores,
        active_layers=effective_layers,
        layer_weights=normalized_weights,
        top_negative_drivers=top_negative[:5],
        top_positive_drivers=top_positive[:5],
        priority_actions=priority_actions[:10],
    )


def prioritize_actions(findings: list[Finding], total_pages: int) -> list[PriorityAction]:
    """Generates prioritized action recommendations using the Impact x Effort matrix."""
    actions: list[PriorityAction] = []
    seen_checks: set[str] = set()

    for f in findings:
        if f.status not in (FindingStatus.FAIL, FindingStatus.WARNING):
            continue
        if f.check_id in seen_checks:
            continue
        seen_checks.add(f.check_id)

        # Count all occurrences of this check failure
        related = [
            x
            for x in findings
            if x.check_id == f.check_id and x.status in (FindingStatus.FAIL, FindingStatus.WARNING)
        ]
        affected_count = len(related)

        effort_val = EFFORT_DIVIDERS.get(f.effort, 2.5)
        confidence = 1.0 if f.layer == AuditLayer.TECHNICAL else 0.8
        score = round((f.impact * confidence) / effort_val, 2)

        # Quadrant assignment
        if f.impact >= 3 and f.effort == Effort.SMALL:
            quadrant = PriorityQuadrant.QUICK_WINS
        elif f.impact >= 4 and f.effort in (Effort.MEDIUM, Effort.LARGE):
            quadrant = PriorityQuadrant.MAJOR_PROJECTS
        elif f.impact <= 2 and f.effort == Effort.SMALL:
            quadrant = PriorityQuadrant.FILL_INS
        else:
            quadrant = PriorityQuadrant.DEPRIORITIZE

        actions.append(
            PriorityAction(
                title=f.title,
                check_id=f.check_id,
                layer=f.layer,
                quadrant=quadrant,
                priority_score=score,
                impact=f.impact,
                effort=f.effort.value,
                affected_pages_count=affected_count,
                fix_summary=f.fix,
                example_url=f.url,
            )
        )

    # Sort descending by priority_score
    actions.sort(key=lambda a: (a.priority_score, a.impact), reverse=True)
    return actions
