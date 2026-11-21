"""Unit tests for RFC 9309 robots.txt parser and AI bot matrix evaluator."""

from auditiq.crawler.robots import RobotsTxtParser

SAMPLE_ROBOTS = """
User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /private/public-preview
Crawl-delay: 1.5

User-agent: GPTBot
Disallow: /

User-agent: PerplexityBot
Allow: /

Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap-news.xml
"""


def test_robots_parser_basic_rules() -> None:
    parser = RobotsTxtParser(SAMPLE_ROBOTS)
    assert len(parser.info.sitemaps) == 2
    assert "https://example.com/sitemap.xml" in parser.info.sitemaps

    # Wildcard user-agent rules
    assert parser.is_allowed("Googlebot", "https://example.com/blog/article") is True
    assert parser.is_allowed("Googlebot", "https://example.com/admin/settings") is False
    # Allow override on longest match
    assert parser.is_allowed("Googlebot", "https://example.com/private/public-preview") is True
    assert parser.is_allowed("Googlebot", "https://example.com/private/secret") is False


def test_robots_parser_ai_bot_rules() -> None:
    parser = RobotsTxtParser(SAMPLE_ROBOTS)
    # GPTBot is disallowed globally
    assert parser.is_allowed("GPTBot", "https://example.com/blog") is False
    # PerplexityBot is allowed globally
    assert parser.is_allowed("PerplexityBot", "https://example.com/blog") is True


def test_robots_crawl_delay() -> None:
    parser = RobotsTxtParser(SAMPLE_ROBOTS)
    assert parser.get_crawl_delay("Googlebot") == 1.5


def test_robots_ai_matrix_evaluation() -> None:
    parser = RobotsTxtParser(SAMPLE_ROBOTS)
    bots = [
        {"name": "GPTBot", "user_agent": "GPTBot"},
        {"name": "PerplexityBot", "user_agent": "PerplexityBot"},
    ]
    matrix = parser.evaluate_ai_bot_matrix(bots, ["/", "/admin/", "/blog"])
    assert matrix["GPTBot"]["/"] is False
    assert matrix["PerplexityBot"]["/"] is True
