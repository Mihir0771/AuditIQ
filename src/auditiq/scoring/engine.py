"""Mathematical scoring engine and action prioritizer."""

from collections import defaultdict
from typing import Any

from auditiq.models.audit import PriorityAction, PriorityQuadrant, ScoreCard
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity

# Severity deduction values (points out of 100 per check failure)
SEVERITY_DEDUCTIONS: dict[Severity, float] = {
    Severity.CRITICAL: 35.0,
    Severity.HIGH: 15.0,
    Severity.MEDIUM: 7.5,
    Severity.LOW: 3.0,
    Severity.INFO: 0.0,
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

    Implements industry-standard deduction penalties based on severity and page impact,
    with proportional weight redistribution for unmeasured vectors.
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

        # If live_visibility is requested, only score it if real or mock evaluations occurred
        if layer == AuditLayer.LIVE_VISIBILITY:
            live_findings = [f for f in findings if f.layer == AuditLayer.LIVE_VISIBILITY]
            has_live = any(
                f.status != FindingStatus.NOT_MEASURED
                for f in live_findings
            )
            if not has_live:
                layer_scores[layer] = None
                continue

        # If the crawl failed completely or host was unreachable, layers cannot pass
        host_unreachable = any(
            f.check_id == "TECH-HOST-REACHABLE" and f.status == FindingStatus.FAIL
            for f in findings
        )
        if total_pages_crawled == 0 or host_unreachable:
            layer_scores[layer] = 0.0
            continue

        total_deduction = 0.0

        # Preferred path: evaluate registered checks
        if registered_checks:
            checks_to_eval = [
                c for c in registered_checks if getattr(c, "layer", None) == layer
            ]
        else:
            checks_to_eval = [
                f for c_id, f in check_metadata.items() if f.layer == layer
            ]

        if not checks_to_eval:
            layer_scores[layer] = 100.0
            continue

        for check in checks_to_eval:
            if isinstance(check, Finding):
                check_id = check.check_id
            else:
                raw_id = getattr(check, "id", None) or getattr(check, "check_id", None)
                check_id = str(raw_id) if raw_id is not None else ""
            if not check_id:
                continue
            severity = check.severity
            title = check.title
            base_deduction = SEVERITY_DEDUCTIONS.get(severity, 0.0)
            if base_deduction == 0.0:
                continue

            check_findings = findings_by_check.get(check_id, [])
            failures = [f for f in check_findings if f.status == FindingStatus.FAIL]
            warnings = [f for f in check_findings if f.status == FindingStatus.WARNING]

            if not failures and not warnings:
                if severity in (Severity.CRITICAL, Severity.HIGH):
                    top_positive.append(f"{title} passed cleanly.")
            else:
                fail_count = len(failures)
                warn_count = len(warnings)
                is_site_scope = getattr(check, "scope", "page") == "site"
                if is_site_scope:
                    fail_ratio = 1.0 if fail_count > 0 else 0.0
                    warn_ratio = 1.0 if warn_count > 0 else 0.0
                else:
                    fail_ratio = min(1.0, fail_count / total_pages)
                    warn_ratio = min(1.0, warn_count / total_pages)

                deduction = (base_deduction * fail_ratio) + (base_deduction * 0.5 * warn_ratio)
                total_deduction += deduction

                if deduction > 2.0:
                    top_negative.append(
                        f"{title} affected {fail_count + warn_count} page(s) (-{deduction:.1f} pts)"
                    )

        raw_layer_score = round(max(0.0, 100.0 - total_deduction), 1)
        layer_scores[layer] = raw_layer_score

    # Calculate proportional redistribution weights across measured layers
    measured_layers = [lyr for lyr in effective_layers if layer_scores.get(lyr) is not None]
    active_weight_sum = (
        sum(DEFAULT_LAYER_WEIGHTS[layer_item] for layer_item in measured_layers) or 1.0
    )
    normalized_weights: dict[AuditLayer, float] = {}
    composite_score = 0.0

    for layer in effective_layers:
        if layer_scores.get(layer) is None:
            normalized_weights[layer] = 0.0
            continue
        norm_w = DEFAULT_LAYER_WEIGHTS[layer] / active_weight_sum
        normalized_weights[layer] = round(norm_w, 4)
        layer_s = layer_scores.get(layer)
        if layer_s is not None:
            composite_score += norm_w * layer_s

    composite_score = round(max(0.0, min(100.0, composite_score)), 1)

    # Pillar integrity: Grade cannot exceed the strength of the weakest foundation.
    has_critical_failure = any(
        f.status == FindingStatus.FAIL and f.severity == Severity.CRITICAL
        for f in findings
    )
    measured_scores = [s for s in layer_scores.values() if s is not None]
    min_layer_score = min(measured_scores) if measured_scores else 100.0

    if min_layer_score < 50.0:
        # A failing pillar drops the entire site to failing (Grade F)
        composite_score = min(composite_score, 49.0)
    elif has_critical_failure or min_layer_score < 70.0:
        # Critical blocker or sub-70 pillar caps overall grade at Grade D
        composite_score = min(composite_score, 69.0)
    elif min_layer_score < 80.0:
        # A sub-80 pillar prevents Grade A
        composite_score = min(composite_score, 79.0)

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
