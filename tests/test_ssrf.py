"""Unit tests for Server-Side Request Forgery (SSRF) validation."""

import pytest

from auditiq.crawler.ssrf import SSRFValidationError, validate_url_safety


def test_ssrf_blocks_private_ips() -> None:
    blocked = [
        "http://127.0.0.1/",
        "http://localhost/",
        "http://10.0.0.5/api",
        "http://192.168.1.1/",
        "http://172.16.0.1/",
        "http://169.254.169.254/latest/meta-data/",
    ]
    for url in blocked:
        with pytest.raises(SSRFValidationError):
            validate_url_safety(url)


def test_ssrf_allows_public_urls() -> None:
    # Public URLs should validate cleanly
    validate_url_safety("https://docs.python.org/3/")
    validate_url_safety("https://techcrunch.com/")


def test_ssrf_blocks_invalid_schemes() -> None:
    with pytest.raises(SSRFValidationError):
        validate_url_safety("ftp://example.com/file")
    with pytest.raises(SSRFValidationError):
        validate_url_safety("file:///etc/passwd")
