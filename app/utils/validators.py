"""URL validation and SSRF guarding.

Blocks requests to loopback, private, link-local, and cloud-metadata
addresses. Must be re-checked after every redirect hop, not just on the
original hostname, since DNS/redirects can repoint to internal addresses.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURLError(ValueError):
    pass


_ALLOWED_SCHEMES = {"http", "https"}

# Cloud metadata endpoints are not always caught by private-IP checks.
_BLOCKED_HOSTS = {
    "metadata.google.internal",
    "169.254.169.254",
}


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparsable -> treat as unsafe
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_url(url: str) -> str:
    """Validate scheme/host and resolve DNS to block internal targets.

    Returns the normalized URL string on success, raises UnsafeURLError
    otherwise.
    """
    parsed = urlparse(url)

    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise UnsafeURLError(f"Unsupported URL scheme: {parsed.scheme!r}")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL is missing a hostname")

    if hostname.lower() in _BLOCKED_HOSTS:
        raise UnsafeURLError("Target host is not allowed")

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve hostname: {hostname}") from exc

    for family, _, _, _, sockaddr in resolved:
        ip_str = sockaddr[0]
        if _is_blocked_ip(ip_str):
            raise UnsafeURLError(
                f"Resolved address {ip_str} for host {hostname} is not a public address"
            )

    return url
