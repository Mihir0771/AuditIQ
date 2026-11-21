"""Unit tests for URL normalization and internal URL validation."""

from auditiq.crawler.normalizer import is_internal_url, normalize_url


def test_normalize_url_basic() -> None:
    assert normalize_url("https://Example.com/Path") == "https://example.com/Path"
    assert normalize_url("http://example.com:80/") == "http://example.com/"
    assert normalize_url("https://example.com:443/docs") == "https://example.com/docs"


def test_normalize_url_fragment_and_slashes() -> None:
    assert normalize_url("https://example.com/page#section") == "https://example.com/page"
    assert normalize_url("https://example.com//deep///path/") == "https://example.com/deep/path/"


def test_normalize_url_tracking_params_stripped() -> None:
    raw = "https://example.com/landing?utm_source=google&utm_medium=cpc&b=2&a=1&fbclid=xyz"
    clean = normalize_url(raw)
    assert clean == "https://example.com/landing?a=1&b=2"
    assert "utm_source" not in clean
    assert "fbclid" not in clean


def test_normalize_url_relative_resolution() -> None:
    base = "https://example.com/blog/article-1"
    assert normalize_url("../about", base_url=base) == "https://example.com/about"
    assert normalize_url("/contact", base_url=base) == "https://example.com/contact"


def test_is_internal_url() -> None:
    base = "example.com"
    assert is_internal_url("https://example.com/page", base) is True
    assert is_internal_url("https://sub.example.com/page", base) is True
    assert is_internal_url("https://otherdomain.com/page", base) is False
    assert is_internal_url("https://notexample.com", base) is False
