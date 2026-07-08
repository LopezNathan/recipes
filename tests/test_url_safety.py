"""Tests for the SSRF guard on user-supplied URLs."""

import pytest

from app.url_safety import is_public_http_url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/recipe",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "not a url",
        "",
        "http://",
    ],
)
def test_rejects_non_http_or_malformed(url):
    assert is_public_http_url(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/recipe",
        "http://127.0.0.1:8001/recipes",
        "http://localhost/recipe",
        "http://[::1]/recipe",
    ],
)
def test_rejects_loopback(url):
    assert is_public_http_url(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "http://10.0.0.1/",
        "http://172.16.0.5/",
        "http://192.168.1.1/admin",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
        "http://0.0.0.0/",
    ],
)
def test_rejects_private_and_link_local(url):
    assert is_public_http_url(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "http://8.8.8.8/",
        "https://1.1.1.1/recipe",
    ],
)
def test_accepts_public_addresses(url):
    assert is_public_http_url(url) is True


def test_rejects_unresolvable_host():
    assert is_public_http_url("https://definitely-not-a-real-host.invalid/") is False
