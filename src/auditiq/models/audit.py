"""Audit run and scoring models."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from auditiq.models.finding import AuditLayer, Finding


class AuditStatus(StrEnum):
    PENDING = "pending"
    CRAWLING = "crawling"
    CHECKING = "checking"
    SCORING = "scoring"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"


class PriorityQuadrant(StrEnum):
    QUICK_WINS = "Quick wins"
    MAJOR_PROJECTS = "Major projects"
    FILL_INS = "Fill-ins"
    DEPRIORITIZE = "Deprioritize"


class PriorityAction(BaseModel):
    title: str
    check_id: str
    layer: AuditLayer
    quadrant: PriorityQuadrant
    priority_score: float
    impact: int
    effort: str
    affected_pages_count: int
    fix_summary: str
    example_url: str


class ScoreCard(BaseModel):
    scoring_version: str = "2026.1"
    composite_score: float = Field(ge=0.0, le=100.0)
    letter_grade: str  # A, B, C, D, F
    layer_scores: dict[AuditLayer, float | None] = Field(default_factory=dict)
    active_layers: list[AuditLayer] = Field(default_factory=list)
    layer_weights: dict[AuditLayer, float] = Field(default_factory=dict)
    top_negative_drivers: list[str] = Field(default_factory=list)
    top_positive_drivers: list[str] = Field(default_factory=list)
    priority_actions: list[PriorityAction] = Field(default_factory=list)


class AuditConfig(BaseModel):
    target_url: str
    brand_name: str = ""
    competitors: list[str] = Field(default_factory=list)
    niche: str = ""
    country: str = "en-US"
    layers: list[AuditLayer] = Field(
        default_factory=lambda: [
            AuditLayer.TECHNICAL,
            AuditLayer.CONTENT,
            AuditLayer.GEO_READINESS,
            AuditLayer.LIVE_VISIBILITY,
        ]
    )
    max_pages: int = 200
    max_depth: int = 4
    render_sample: int = 5
    concurrency: int = 5
    respect_robots: bool = True


class AuditRecord(BaseModel):
    id: str
    config: AuditConfig
    status: AuditStatus = AuditStatus.PENDING
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    crawl_summary: dict[str, Any] = Field(default_factory=dict)
    score_card: ScoreCard | None = None
    findings: list[Finding] = Field(default_factory=list)
    error: str | None = None
