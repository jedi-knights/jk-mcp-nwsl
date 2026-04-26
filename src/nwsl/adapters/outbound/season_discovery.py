"""Discovery adapter — extracts SDP season IDs from the public NWSL site.

The api-sdp.nwslsoccer.com endpoints take SDP entity IDs (e.g.
`nwsl::Football_Season::0b6761e4701749f593690c0f338da74c`) as path segments.
These IDs change yearly and aren't published in any documented form, so we
scrape them from the standings page's embedded widget config.

The page HTML embeds a `seasonIdJson` widget attribute containing a JSON
mapping of SDP IDs → human-readable names. We html-unescape, JSON-parse, and
extract the year from the name.

This is fragile by definition — the page is the only source. If the markup
changes, callers will see an empty list and SDP-backed tools will fail loudly.
"""

import asyncio
import html
import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

import httpx

from ...domain.exceptions import UpstreamAPIError
from ...domain.models import Season

logger = logging.getLogger(__name__)

_DEFAULT_PAGE_URLS: tuple[str, ...] = (
    "https://www.nwslsoccer.com/standings/index",
    "https://www.nwslsoccer.com/schedule/challenge-cup",
)
_DEFAULT_TTL_SECONDS = 3600.0  # SDP season IDs change once per year — 1 hour cache is plenty.
_SEASON_CONFIG_PATTERN = re.compile(r"seasonIdJson[^,]*?(\{[^}]*\})")
_YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")


def _parse_seasons_from_html(page_html: str) -> list[Season]:
    """Pull the seasonIdJson map out of a page HTML body.

    Args:
        page_html: Raw HTML from the standings page.

    Returns:
        A list of Season records, possibly empty if the widget config isn't found.
    """
    match = _SEASON_CONFIG_PATTERN.search(page_html)
    if not match:
        return []

    raw = html.unescape(match.group(1)).replace("\\", "")
    try:
        mapping: dict[str, str] = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Could not decode seasonIdJson payload: %r", raw[:200])
        return []

    return [s for entry in mapping.items() if (s := _build_season(*entry)) is not None]


def _build_season(season_id: str, name: str) -> Season | None:
    """Construct a Season from an (id, name) pair, or None if the year can't be parsed."""
    year_match = _YEAR_PATTERN.search(name)
    if not year_match:
        return None
    competition = name[: year_match.start()].strip()
    return Season(id=season_id, year=int(year_match.group(1)), name=name, competition=competition)


class SeasonDiscoveryAdapter:
    """Fetches and parses season IDs from the public NWSL site.

    Different competitions surface their seasonIdJson on different pages
    (Regular Season on /standings/index, Challenge Cup on
    /schedule/challenge-cup). The adapter scans each configured page and
    merges the results, deduping by season ID.
    """

    def __init__(
        self,
        page_urls: tuple[str, ...] | list[str] = _DEFAULT_PAGE_URLS,
        client: httpx.AsyncClient | None = None,
        ttl_seconds: float = _DEFAULT_TTL_SECONDS,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize the adapter.

        Args:
            page_urls: URLs to scan for seasonIdJson widget configs.
            client: Injectable httpx.AsyncClient. A default is created if omitted.
            ttl_seconds: How long to keep parsed seasons cached. SDP IDs change
                yearly so the default of 1 hour is intentionally long.
            now: Callable returning monotonic time. Injectable for tests.
        """
        self._page_urls = tuple(page_urls)
        self._client = client or httpx.AsyncClient(timeout=30.0)
        self._ttl = ttl_seconds
        self._now = now
        self._cached: list[Season] | None = None
        self._expires_at: float = 0.0

    async def get_seasons(self) -> list[Season]:
        """Return the merged list of seasons advertised across all configured pages.

        Results are cached for `ttl_seconds`. On a cold cache, pages are
        fetched concurrently via asyncio.gather — discovery is on the critical
        path for SDP-backed tools, so halving the latency matters.

        Raises:
            UpstreamAPIError: If any configured page request fails.
        """
        if self._cached is not None and self._now() < self._expires_at:
            logger.debug("Discovery cache hit (%d seasons)", len(self._cached))
            return self._cached

        results = await asyncio.gather(*(self._fetch_seasons_from(url) for url in self._page_urls))
        merged: dict[str, Season] = {}
        for seasons in results:
            for season in seasons:
                merged.setdefault(season.id, season)
        self._cached = list(merged.values())
        self._expires_at = self._now() + self._ttl
        return self._cached

    async def _fetch_seasons_from(self, url: str) -> list[Season]:
        """Fetch and parse season IDs from a single configured page.

        Raises:
            UpstreamAPIError: If the page request fails, or if a 200 response
                lacks the seasonIdJson widget config (indicating a markup
                change rather than a transient outage).
        """
        logger.debug("GET %s", url)
        try:
            response: Any = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise UpstreamAPIError(f"Discovery page returned {exc.response.status_code}") from exc
        if not _SEASON_CONFIG_PATTERN.search(response.text):
            raise UpstreamAPIError(f"No seasonIdJson found at {url} — markup may have changed")
        return _parse_seasons_from_html(response.text)
