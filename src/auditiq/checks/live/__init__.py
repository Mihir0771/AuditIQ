"""Live AI Visibility Check Suite Registration (Layer 4)."""

from auditiq.checks.live.checks import (
    LiveCitationRateCheck,
    LiveMentionRateCheck,
    LiveShareOfVoiceCheck,
    LiveTopCitedDomainsCheck,
)
from auditiq.checks.registry import CheckRegistry, default_registry

LIVE_CHECKS = [
    LiveMentionRateCheck,
    LiveCitationRateCheck,
    LiveShareOfVoiceCheck,
    LiveTopCitedDomainsCheck,
]


def register_live_checks(registry: CheckRegistry = default_registry) -> None:
    """Registers all Live AI Visibility (LIVE-*) checks into the provided registry."""
    for check_cls in LIVE_CHECKS:
        registry.register_class(check_cls)
