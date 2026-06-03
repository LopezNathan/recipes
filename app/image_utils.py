"""Image URL validation utilities."""

from typing import Optional
import httpx


async def validate_image_url(url: Optional[str], timeout: float = 4.0) -> Optional[str]:
    """Return the URL if it serves an image, otherwise None."""
    if not url or not url.startswith("http"):
        return None
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.head(url, timeout=timeout, follow_redirects=True)
            content_type = resp.headers.get("content-type", "")
            if resp.status_code == 200 and "image" in content_type:
                return url
            # Some servers don't support HEAD — fall back to a small GET
            if resp.status_code in (405, 403):
                resp = await client.get(url, timeout=timeout, follow_redirects=True,
                                        headers={"Range": "bytes=0-0"})
                content_type = resp.headers.get("content-type", "")
                if "image" in content_type:
                    return url
    except Exception:
        pass
    return None
