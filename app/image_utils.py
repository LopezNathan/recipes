"""Image URL validation utilities."""

import asyncio
from urllib.parse import urljoin

import httpx

from app.url_safety import is_public_http_url

_MAX_REDIRECTS = 5


async def validate_image_url(url: str | None, timeout: float = 4.0) -> str | None:
    """Return the URL if it serves an image from a public host, otherwise None.

    Redirects are followed manually so every hop is re-checked against
    is_public_http_url — a public URL that redirects to an internal address
    is rejected, not fetched.
    """
    if not url or not url.startswith("http"):
        return None
    try:
        target = url
        async with httpx.AsyncClient() as client:
            for _ in range(_MAX_REDIRECTS + 1):
                if not await asyncio.to_thread(is_public_http_url, target):
                    return None
                resp = await client.head(target, timeout=timeout)
                # Some servers don't support HEAD — fall back to a small GET
                if resp.status_code in (405, 403):
                    resp = await client.get(
                        target, timeout=timeout, headers={"Range": "bytes=0-0"}
                    )
                if resp.is_redirect:
                    location = resp.headers.get("location")
                    if not location:
                        return None
                    target = urljoin(target, location)
                    continue
                content_type = resp.headers.get("content-type", "")
                if resp.status_code in (200, 206) and "image" in content_type:
                    return url
                return None
    except Exception:
        pass
    return None
