"""Unit and integration tests for FastAPI REST API endpoints."""

import pytest
from starlette.testclient import TestClient

from auditiq.models.audit import AuditConfig, AuditRecord, AuditStatus
from auditiq.models.finding import AuditLayer, Effort, Finding, FindingStatus, Severity
from auditiq.scoring.engine import calculate_score_card
from auditiq.server.app import app
from auditiq.server.jobs import AuditJob, job_manager


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_doctor_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/system/doctor")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["registered_checks_count"] >= 50


def test_dashboard_root_html(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AuditIQ" in resp.text
    assert "Target Website URL" in resp.text


def test_create_and_get_audit_job(client: TestClient) -> None:
    payload = {
        "url": "https://example.com/",
        "brand_name": "TestBrand",
        "layers": ["tech", "content"],
        "max_pages": 5,
        "mock_ai": True,
    }
    resp = client.post("/api/v1/audits", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Fetch status
    get_resp = client.get(f"/api/v1/audits/{job_id}")
    assert get_resp.status_code == 200
    job_data = get_resp.json()
    assert job_data["id"] == job_id
    assert job_data["url"] == "https://example.com/"


def test_list_audits(client: TestClient) -> None:
    resp = client.get("/api/v1/audits")
    assert resp.status_code == 200
    data = resp.json()
    assert "audits" in data
    assert isinstance(data["audits"], list)


def test_compare_endpoint(client: TestClient) -> None:
    # Seed 2 completed jobs in job_manager
    config = AuditConfig(target_url="https://example.com/", brand_name="Acme")
    f1 = Finding(
        id="f1",
        check_id="TECH-TITLE-MISSING",
        layer=AuditLayer.TECHNICAL,
        url="https://example.com/",
        status=FindingStatus.FAIL,
        severity=Severity.HIGH,
        effort=Effort.SMALL,
        impact=5,
        title="Missing Title",
        why_it_matters="Critical",
        fix="Fix it",
    )
    score1 = calculate_score_card(findings=[f1], total_pages_crawled=1)
    rec1 = AuditRecord(
        id="job_a", config=config, status=AuditStatus.COMPLETED, score_card=score1, findings=[f1]
    )

    score2 = calculate_score_card(findings=[], total_pages_crawled=1)
    rec2 = AuditRecord(
        id="job_b", config=config, status=AuditStatus.COMPLETED, score_card=score2, findings=[]
    )

    job_manager.jobs["job_a"] = AuditJob(
        id="job_a", url="https://example.com/", status=AuditStatus.COMPLETED, record=rec1
    )
    job_manager.jobs["job_b"] = AuditJob(
        id="job_b", url="https://example.com/", status=AuditStatus.COMPLETED, record=rec2
    )

    resp = client.post("/api/v1/compare", json={"baseline_id": "job_a", "current_id": "job_b"})
    assert resp.status_code == 200
    cmp_data = resp.json()
    assert cmp_data["baseline_id"] == "job_a"
    assert cmp_data["current_id"] == "job_b"
    assert cmp_data["resolved_count"] == 1
    assert cmp_data["score_delta"] > 0


def test_badge_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/audits/job_a/badge.svg")
    assert resp.status_code == 200
    assert "image/svg+xml" in resp.headers["content-type"]
    assert "AuditIQ" in resp.text
    assert "<svg" in resp.text


def test_bundle_endpoint(client: TestClient) -> None:
    resp = client.get("/api/v1/audits/job_a/bundle.zip")
    assert resp.status_code == 200
    assert "application/zip" in resp.headers["content-type"]
    assert len(resp.content) > 100


def test_cancel_nonexistent_or_done_job(client: TestClient) -> None:
    resp = client.post("/api/v1/audits/nonexistent/cancel")
    assert resp.status_code == 400
