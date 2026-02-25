"""FastAPI router for short link redirects.

Story 7-2, Task 4: GET /l/{code} endpoint.
Resolves short links and records clicks via fire-and-forget.

The redirect endpoint is designed for speed:
- Click recording is fire-and-forget (asyncio.create_task)
- 307 Temporary Redirect preserves request method
- 404 for unknown codes (DEBUG log, not error -- expected bot traffic)
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

from core.analytics.utm_service import ShortLinkService

logger = logging.getLogger(__name__)

redirect_router = APIRouter()


async def _get_short_link_service() -> ShortLinkService:
    """Dependency injection placeholder for ShortLinkService.

    Overridden in application startup and tests.
    """
    raise NotImplementedError(
        "ShortLinkService dependency must be configured at application startup"
    )


def _extract_client_ip(request: Request) -> str:
    """Extract client IP from request, considering reverse proxy.

    Task 4.5: X-Forwarded-For takes priority over request.client.host.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address string
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the chain is the original client
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return "unknown"


@redirect_router.get("/l/{code}")
async def redirect_short_link(
    code: str,
    request: Request,
    service: ShortLinkService = Depends(_get_short_link_service),
) -> RedirectResponse:
    """Resolve short link and redirect to destination URL.

    Task 4.2: GET /l/{code} -- resolves short link, records click, returns 307.
    Task 4.3: Click recording is fire-and-forget via resolve_and_track.
    Task 4.4: 404 for unknown codes (no error logging).

    Args:
        code: Short link code
        request: FastAPI request for IP/headers extraction
        service: ShortLinkService (injected)

    Returns:
        307 Temporary Redirect to destination URL

    Raises:
        HTTPException: 404 if code is not found
    """
    ip = _extract_client_ip(request)
    user_agent: Optional[str] = request.headers.get("User-Agent")
    referer: Optional[str] = request.headers.get("Referer")

    destination_url = await service.resolve_and_track(
        code=code,
        ip=ip,
        user_agent=user_agent,
        referer=referer,
    )

    if destination_url is None:
        logger.debug("Short link not found: code=%s", code)
        raise HTTPException(status_code=404, detail="Link not found")

    return RedirectResponse(url=destination_url, status_code=307)


__all__ = [
    "redirect_router",
]
