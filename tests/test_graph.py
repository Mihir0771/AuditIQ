"""Unit tests for the directed internal link graph."""

from auditiq.crawler.graph import LinkGraph


def test_link_graph_depths_and_orphans() -> None:
    graph = LinkGraph(start_url="https://example.com/")

    # Setup structure:
    # home -> blog -> post1
    # home -> about
    # orphan is in sitemap, but has 0 inlinks
    graph.add_edge("https://example.com/", "https://example.com/blog", "Blog")
    graph.add_edge("https://example.com/", "https://example.com/about", "About Us")
    graph.add_edge("https://example.com/blog", "https://example.com/blog/post1", "Post 1")

    graph.compute_depths()

    assert graph.depths["https://example.com/"] == 0
    assert graph.depths["https://example.com/blog"] == 1
    assert graph.depths["https://example.com/about"] == 1
    assert graph.depths["https://example.com/blog/post1"] == 2

    assert graph.get_inlinks_count("https://example.com/blog") == 1
    assert graph.get_outlinks_count("https://example.com/") == 2

    # Test orphan detection
    sitemap_urls = {
        "https://example.com/",
        "https://example.com/blog",
        "https://example.com/about",
        "https://example.com/orphan-landing-page",
    }
    crawled_urls = {
        "https://example.com/",
        "https://example.com/blog",
        "https://example.com/about",
    }

    orphans = graph.find_orphan_pages(sitemap_urls, crawled_urls)
    assert "https://example.com/orphan-landing-page" in orphans
    assert "https://example.com/blog" not in orphans
