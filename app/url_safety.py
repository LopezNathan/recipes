"""SSRF guard for user-supplied URLs fetched server-side."""

import ipaddress
import socket
from urllib.parse import urlparse


def is_public_http_url(url: str) -> bool:
    """Return True if url is http(s) and its host resolves only to public addresses.

    Rejects loopback, private (RFC 1918), link-local (incl. cloud metadata at
    169.254.169.254), and other non-global ranges so a crafted URL can't be
    used to probe the internal network. Does DNS resolution — call it off the
    event loop (asyncio.to_thread) from async code.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        for info in socket.getaddrinfo(parsed.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if not ip.is_global:
                return False
        return True
    except (socket.gaierror, ValueError, UnicodeError):
        return False
