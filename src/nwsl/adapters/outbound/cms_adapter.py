"""CMS adapter for the official NWSL site's content API (dapi.nwslsoccer.com).

The CMS exposes editorial articles — stories about awards, transactions,
match recaps, etc. The `$filter` query param is silently ignored, so callers
must filter the returned list client-side. Used by the awards tool.
"""

import logging
from typing import Any

import httpx

from ...domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from ...domain.models import CMSArticle

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://dapi.nwslsoccer.com"
_STORIES_PATH = "/v2/content/en-us/stories"
_PUBLIC_NEWS_BASE = "https://www.nwslsoccer.com/news"


def _check_response(response: httpx.Response, path: str) -> None:
    """Raise a domain exception for any non-2xx HTTP status."""
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise NWSLNotFoundError(f"Not found: {path}") from exc
        raise UpstreamAPIError(f"CMS error {exc.response.status_code}: {path}") from exc


def _parse_article(raw: dict[str, Any]) -> CMSArticle:
    """Map a raw stories[] entry to a domain CMSArticle."""
    slug = str(raw.get("slug", ""))
    raw_tags = raw.get("tags") or []
    tags = [t.get("slug") for t in raw_tags if isinstance(t, dict) and t.get("slug")]
    return CMSArticle(
        slug=slug,
        title=raw.get("title", ""),
        summary=raw.get("summary", ""),
        published=raw.get("contentDate", ""),
        link=f"{_PUBLIC_NEWS_BASE}/{slug}" if slug else "",
        tags=tags,
    )


class CMSAdapter:
    """Calls the official site's CMS for editorial content."""

    def __init__(self, base_url: str = _DEFAULT_BASE_URL, client: httpx.AsyncClient | None = None) -> None:
        """Initialize the adapter.

        Args:
            base_url: Base URL of the CMS API.
            client: Injectable httpx.AsyncClient. A default is created if omitted.
        """
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        logger.debug("GET %s params=%s", path, params)
        response = await self._client.get(path, params=params or {})
        _check_response(response, path)
        return response.json()

    async def get_recent_stories(self, limit: int) -> list[CMSArticle]:
        """Return the most recent `limit` stories ordered by publication date.

        Args:
            limit: Maximum number of stories to fetch (CMS caps at ~100).
        """
        data = await self._get(_STORIES_PATH, {"$top": limit})
        return [_parse_article(item) for item in data.get("items", [])]
