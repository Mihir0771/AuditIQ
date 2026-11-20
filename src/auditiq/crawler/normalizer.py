"""Strict URL normalization and canonicalization engine."""

from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

# Common tracking / noise query parameters to strip for deduplication
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "fbclid",
    "gclid",
    "gclsrc",
    "dclid",
    "msclkid",
    "_ga",
    "_gl",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}


def normalize_url(raw_url: str, base_url: str | None = None) -> str:
    """Normalizes an arbitrary URL for deduplication and crawling.

    - Resolves relative URLs if base_url is provided
    - Lowercases scheme and hostname
    - Strips URL fragments (#...)
    - Filters out marketing tracking query parameters
    - Alphabetically sorts remaining query parameters
    - Normalizes empty path to '/'
    - Removes default ports (:80 for HTTP, :443 for HTTPS)
    """
    if not raw_url:
        return ""

    raw_url = raw_url.strip()
    if base_url:
        raw_url = urljoin(base_url, raw_url)

    parsed = urlparse(raw_url)

    # Allow only http and https
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return ""

    netloc = parsed.netloc.lower()

    # Strip default ports
    if scheme == "http" and netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif scheme == "https" and netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = parsed.path
    if not path:
        path = "/"

    # Collapse multiple consecutive slashes
    while "//" in path:
        path = path.replace("//", "/")

    # Normalize query parameters: strip tracking and sort
    clean_params: list[tuple[str, str]] = []
    if parsed.query:
        for k, v in parse_qsl(parsed.query, keep_blank_values=True):
            if k.lower() not in TRACKING_PARAMS:
                clean_params.append((k, v))
        clean_params.sort(key=lambda x: (x[0], x[1]))

    new_query = urlencode(clean_params)

    # Reassemble URL without fragment
    return urlunparse((scheme, netloc, path, "", new_query, ""))


def is_internal_url(candidate_url: str, base_domain: str) -> bool:
    """Determines whether candidate_url belongs to the base_domain or its subdomains."""
    parsed = urlparse(candidate_url)
    host = parsed.netloc.lower()
    base = base_domain.lower()

    # Exact match or subdomain
    return host == base or host.endswith(f".{base}")
