"""GEO Readiness Check Suite Registration (Layer 3)."""

from auditiq.checks.geo.authority import BotTtfbCheck, EntitySameAsCheck
from auditiq.checks.geo.bot_matrix import AiBotMatrixCheck, BotFirewallCheck
from auditiq.checks.geo.chunkability import PassageChunkingCheck
from auditiq.checks.geo.extractability import DataTablesCheck, SemanticHtmlCheck, TextTrappedCheck
from auditiq.checks.geo.llms_txt import LlmsTxtCheck
from auditiq.checks.geo.render_diff import RenderDiffLinksCheck, RenderDiffTextCheck
from auditiq.checks.registry import CheckRegistry, default_registry

GEO_CHECKS = [
    AiBotMatrixCheck,
    BotFirewallCheck,
    RenderDiffTextCheck,
    RenderDiffLinksCheck,
    SemanticHtmlCheck,
    TextTrappedCheck,
    DataTablesCheck,
    PassageChunkingCheck,
    LlmsTxtCheck,
    EntitySameAsCheck,
    BotTtfbCheck,
]


def register_geo_checks(registry: CheckRegistry = default_registry) -> None:
    """Registers all GEO Readiness (GEO-*) checks into the provided registry."""
    for check_cls in GEO_CHECKS:
        registry.register_class(check_cls)
