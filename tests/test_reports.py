"""Unit tests for HTML, PDF, JSON, and CSV report generators."""

from pathlib import Path

import pytest

from auditiq.models.audit import AuditConfig, AuditRecord, AuditStatus
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity
from auditiq.reports.exporters import export_csv, export_json
from auditiq.reports.html import generate_html_report, load_branding_config
from auditiq.reports.pdf import generate_pdf_report
from auditiq.scoring.engine import calculate_score_card


@pytest.fixture
def sample_record() -> AuditRecord:
    config = AuditConfig(target_url="https://example.com/", brand_name="ExampleBrand")
    findings = [
        Finding(
            id="f1",
            check_id="TECH-ROBOTS-PRESENCE",
            layer=AuditLayer.TECHNICAL,
            url="https://example.com/robots.txt",
            status=FindingStatus.PASS,
            severity=Severity.INFO,
            effort=Effort.SMALL,
            impact=4,
            title="robots.txt is accessible",
            why_it_matters="Controls bot indexing.",
            fix="None needed.",
        ),
        Finding(
            id="f2",
            check_id="TECH-TITLE-MISSING",
            layer=AuditLayer.TECHNICAL,
            url="https://example.com/missing-title",
            status=FindingStatus.FAIL,
            severity=Severity.HIGH,
            effort=Effort.SMALL,
            impact=5,
            title="Missing or Empty <title> Tag",
            why_it_matters="Title tag is critical for CTR and AI recognition.",
            fix="Add a descriptive title tag.",
        ),
    ]
    score_card = calculate_score_card(findings=findings, total_pages_crawled=2)
    return AuditRecord(
        id="test_audit_123",
        config=config,
        status=AuditStatus.COMPLETED,
        score_card=score_card,
        findings=findings,
        crawl_summary={"total_pages": 2, "duration_sec": 1.2},
    )


def test_branding_config_loader() -> None:
    branding = load_branding_config()
    assert "agency" in branding
    assert "colors" in branding
    assert "typography" in branding


def test_html_report_generation(sample_record: AuditRecord, tmp_path: Path) -> None:
    out_html = tmp_path / "test_report.html"
    res_path = generate_html_report(sample_record, output_path=out_html)

    assert res_path.exists()
    content = res_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert sample_record.config.target_url in content
    assert "test_audit_123" in content
    assert "Priority Remediation Matrix" in content
    assert "TECH-TITLE-MISSING" in content or "Missing or Empty <title> Tag" in content


def test_json_and_csv_exporters(sample_record: AuditRecord, tmp_path: Path) -> None:
    out_json = tmp_path / "test.json"
    out_csv = tmp_path / "test.csv"

    export_json(sample_record, out_json)
    assert out_json.exists()
    assert "test_audit_123" in out_json.read_text(encoding="utf-8")

    export_csv(sample_record, out_csv)
    assert out_csv.exists()
    lines = out_csv.read_text(encoding="utf-8-sig").splitlines()
    assert len(lines) >= 3  # Header + 2 findings
    assert "finding_id,check_id,layer,status" in lines[0]


def test_pdf_report_generation(sample_record: AuditRecord, tmp_path: Path) -> None:
    out_pdf = tmp_path / "test_report.pdf"
    res_path = generate_pdf_report(sample_record, output_path=out_pdf)

    assert res_path.exists()
    # Check that PDF is a valid non-empty file (Playwright generated binary)
    size_bytes = res_path.stat().st_size
    assert size_bytes > 5000
    with open(res_path, "rb") as f:
        header = f.read(4)
        assert header == b"%PDF"
