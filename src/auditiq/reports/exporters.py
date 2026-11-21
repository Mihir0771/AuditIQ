"""Structured JSON and CSV exporters for audit findings."""

import csv
import json
from pathlib import Path

from auditiq.models.audit import AuditRecord


def export_json(record: AuditRecord, output_path: Path) -> Path:
    """Exports complete audit record to JSON format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(record.model_dump_json(indent=2))
    return output_path


def export_csv(record: AuditRecord, output_path: Path) -> Path:
    """Exports audit findings into a flat, spreadsheet-friendly CSV table."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "finding_id",
        "check_id",
        "layer",
        "status",
        "severity",
        "impact",
        "effort",
        "url",
        "title",
        "why_it_matters",
        "fix",
        "evidence_json",
    ]

    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for finding in record.findings:
            writer.writerow(
                {
                    "finding_id": finding.id,
                    "check_id": finding.check_id,
                    "layer": finding.layer.value,
                    "status": finding.status.value,
                    "severity": finding.severity.value,
                    "impact": finding.impact,
                    "effort": finding.effort.value,
                    "url": finding.url,
                    "title": finding.title,
                    "why_it_matters": finding.why_it_matters,
                    "fix": finding.fix,
                    "evidence_json": json.dumps(finding.evidence, ensure_ascii=False),
                }
            )

    return output_path
