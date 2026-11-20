"""Server-Side Request Forgery (SSRF) validation filter."""

import ipaddress
import socket
from urllib.parse import urlparse

# Private, loopback, and cloud metadata network ranges that must never be crawled
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),       # IPv4 loopback
    ipaddress.ip_network("10.0.0.0/8"),        # RFC 1918 Private
    ipaddress.ip_network("172.16.0.0/12"),     # RFC 1918 Private
    ipaddress.ip_network("192.168.0.0/16"),    # RFC 1918 Private
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local & Cloud Metadata (AWS, GCP, Azure)
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]


class SSRFValidationError(ValueError):
    """Raised when a URL resolves to a forbidden private or loopback IP address."""


def validate_url_safety(target_url: str) -> None:
    """Validates that a URL does not target loopback, private networks, or metadata services."""
    parsed = urlparse(target_url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFValidationError(f"Invalid URL scheme: '{parsed.scheme}'. Only http and https allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL contains no valid hostname.")

    # Reject localhost directly
    if hostname.lower() in ("localhost", "localhost.localdomain"):
        raise SSRFValidationError("Access to localhost is forbidden.")

    # Resolve IP addresses
    try:
        # Check if hostname is an immediate IP literal
        ip = ipaddress.ip_address(hostname)
        ip_addresses = [ip]
    except ValueError:
        # Hostname is a domain name; resolve DNS
        try:
            addr_info = socket.getaddrinfo(hostname, None)
            ip_addresses = [ipaddress.ip_address(item[4][0]) for item in addr_info]
        except socket.gaierror as e:
            # DNS resolution failure; let caller handle during fetch
            return

    for ip_obj in ip_addresses:
        for net in BLOCKED_NETWORKS:
            if ip_obj in net:
                raise SSRFValidationError(
                    f"Forbidden IP resolution: '{hostname}' resolves to private/internal IP {ip_obj} in {net}"
                )
