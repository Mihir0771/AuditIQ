"""Content and Entity check registrations (CONT-*)."""

from auditiq.checks.content.entity import BrandConsistencyCheck, SimhashDuplicateCheck
from auditiq.checks.content.evidence import EvidenceDensityCheck, OutboundCitationsCheck
from auditiq.checks.content.readability import (
    ReadabilityCheck,
    SentenceVarietyCheck,
    ThinContentCheck,
)
from auditiq.checks.content.structure import (
    AnswerFirstCheck,
    FaqMarkupCheck,
    QuestionHeadingsCheck,
)
from auditiq.checks.content.trust import (
    AuthorCredentialsCheck,
    FreshnessDatesCheck,
    TrustPagesCheck,
)
from auditiq.checks.registry import CheckRegistry, default_registry


def register_content_checks(registry: CheckRegistry = default_registry) -> None:
    """Registers all Content & Entity (CONT-*) checks into the provided registry."""
    checks = [
        ReadabilityCheck,
        SentenceVarietyCheck,
        ThinContentCheck,
        AnswerFirstCheck,
        QuestionHeadingsCheck,
        FaqMarkupCheck,
        EvidenceDensityCheck,
        OutboundCitationsCheck,
        AuthorCredentialsCheck,
        TrustPagesCheck,
        FreshnessDatesCheck,
        SimhashDuplicateCheck,
        BrandConsistencyCheck,
    ]
    for check_cls in checks:
        registry.register_class(check_cls)


# Automatically register on import
register_content_checks()
