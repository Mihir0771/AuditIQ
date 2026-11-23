"""Technical SEO check registrations."""

from auditiq.checks.registry import CheckRegistry, default_registry
from auditiq.checks.tech.crawlability import (
    BrokenOutboundLinksCheck,
    CanonicalConflictCheck,
    CanonicalMissingCheck,
    CrawlDepthCheck,
    HostReachabilityCheck,
    HttpConsistencyCheck,
    NoindexAccidentalCheck,
    OrphanPagesCheck,
    RedirectChainsCheck,
    RobotsBlockingCheck,
    RobotsPresenceCheck,
    SitemapCoverageCheck,
    SitemapPresenceCheck,
    Status4xx5xxCheck,
    WwwConsistencyCheck,
)
from auditiq.checks.tech.onpage import (
    DomHygieneCheck,
    H1MissingMultiCheck,
    HeadingSkipsCheck,
    ImageAltMissingCheck,
    MetaDescLengthCheck,
    MetaDescMissingCheck,
    OpenGraphCheck,
    TitleLengthCheck,
    TitleMissingCheck,
    UrlHygieneCheck,
)
from auditiq.checks.tech.performance import (
    PageSizeCheck,
    SecurityHeadersCheck,
    TtfbCheck,
    ViewportCheck,
)
from auditiq.checks.tech.schema import SchemaSyntaxCheck, SchemaTypesCheck


def register_tech_checks(registry: CheckRegistry = default_registry) -> None:
    """Registers all Technical SEO (TECH-*) checks into the provided registry."""
    checks = [
        HostReachabilityCheck,
        RobotsPresenceCheck,
        RobotsBlockingCheck,
        SitemapPresenceCheck,
        SitemapCoverageCheck,
        Status4xx5xxCheck,
        RedirectChainsCheck,
        OrphanPagesCheck,
        CrawlDepthCheck,
        CanonicalMissingCheck,
        CanonicalConflictCheck,
        NoindexAccidentalCheck,
        HttpConsistencyCheck,
        WwwConsistencyCheck,
        TitleMissingCheck,
        TitleLengthCheck,
        MetaDescMissingCheck,
        MetaDescLengthCheck,
        H1MissingMultiCheck,
        HeadingSkipsCheck,
        ImageAltMissingCheck,
        UrlHygieneCheck,
        OpenGraphCheck,
        DomHygieneCheck,
        BrokenOutboundLinksCheck,
        SchemaSyntaxCheck,
        SchemaTypesCheck,
        TtfbCheck,
        PageSizeCheck,
        ViewportCheck,
        SecurityHeadersCheck,
    ]
    for check_cls in checks:
        registry.register_class(check_cls)


# Automatically register on import
register_tech_checks()
