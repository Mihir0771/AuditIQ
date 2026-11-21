"""Core finding models and taxonomies."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AuditLayer(StrEnum):
    TECHNICAL = "technical"
    CONTENT = "content"
    GEO_READINESS = "geo_readiness"
    LIVE_VISIBILITY = "live_visibility"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Effort(StrEnum):
    SMALL = "S"
    MEDIUM = "M"
    LARGE = "L"


class FindingStatus(StrEnum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    NOT_MEASURED = "not_measured"


class Finding(BaseModel):
    id: str = Field(description="Unique finding identifier (e.g. check_id:url_hash)")
    check_id: str = Field(description="Immutable check code (e.g. TECH-ROBOTS-PRESENCE)")
    layer: AuditLayer
    severity: Severity
    status: FindingStatus
    url: str
    title: str
    evidence: list[dict[str, Any]] = Field(
        default_factory=list, description="Concrete proof (snippets, headers, tags)"
    )
    why_it_matters: str
    fix: str
    effort: Effort
    impact: int = Field(ge=1, le=5, description="Impact scale 1 to 5")
    references: list[str] = Field(default_factory=list, description="Official documentation links")
