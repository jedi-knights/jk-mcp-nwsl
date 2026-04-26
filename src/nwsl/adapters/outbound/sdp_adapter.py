"""Outbound adapter for the unofficial SDP / Opta data API.

Hits api-sdp.nwslsoccer.com, the same backend the public nwslsoccer.com
widgets call. No documented contract exists — paths and ID formats were
reverse-engineered from the standings widget bundle. The host carries far
richer data than the ESPN feed (per-player Opta stats, historical seasons,
Challenge Cup competitions) but the wire format is fragile.

Season IDs are SDP entity IDs of the form `nwsl::Football_Season::{uuid}`.
The colons must be percent-encoded as path segments.
"""

import logging
from typing import Any
from urllib.parse import quote

import httpx

from ...domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from ...domain.models import PlayerSeasonStat, SeasonStanding, TeamSeasonStat
from .sdp_parsers import _parse_player_season_stat, _parse_season_standing, _parse_team_season_stat

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://api-sdp.nwslsoccer.com"
_API_PREFIX = "/v1/nwsl/football"
_LOCALE = "en-US"


def _check_response(response: httpx.Response, path: str) -> None:
    """Raise a domain exception for any non-2xx HTTP status."""
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise NWSLNotFoundError(f"Not found: {path}") from exc
        raise UpstreamAPIError(f"Upstream error {exc.response.status_code}: {path}") from exc


class SDPAdapter:
    """Calls api-sdp.nwslsoccer.com for richer NWSL data than ESPN exposes."""

    def __init__(self, base_url: str = _DEFAULT_BASE_URL, client: httpx.AsyncClient | None = None) -> None:
        """Initialize the adapter.

        Args:
            base_url: Base URL of the SDP API. Defaults to api-sdp.nwslsoccer.com.
            client: An httpx.AsyncClient instance to reuse across all requests.
        """
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GET request, layer the locale param in, return parsed JSON."""
        merged: dict[str, Any] = {"locale": _LOCALE}
        if params:
            merged.update(params)
        logger.debug("GET %s params=%s", path, merged)
        response = await self._client.get(path, params=merged)
        _check_response(response, path)
        return response.json()

    async def get_standings_for_season(self, season_id: str) -> list[SeasonStanding]:
        """Return the overall standings table for a season.

        SDP returns three tables (overall, home, away) — only the overall
        ('table') variant is surfaced.

        Args:
            season_id: Full SDP season ID.
        """
        path = f"{_API_PREFIX}/seasons/{quote(season_id, safe='')}/standings/overall"
        data = await self._get(path)
        rows: list[SeasonStanding] = []
        for table in data.get("standings", []):
            if table.get("type") != "table":
                continue
            rows.extend(_parse_season_standing(t) for t in table.get("teams") or [])
        return sorted(rows, key=lambda r: r.rank)

    async def get_team_stats(self, season_id: str, order_by: str, limit: int) -> list[TeamSeasonStat]:
        """Return the top `limit` teams for a season, sorted by `order_by` descending.

        Args:
            season_id: Full SDP season ID.
            order_by: Stat ID to sort by (e.g. "total-points", "goals", "passes-accuracy").
            limit: Number of teams to return.
        """
        path = f"{_API_PREFIX}/seasons/{quote(season_id, safe='')}/stats/teams"
        params: dict[str, Any] = {
            "orderBy": order_by,
            "direction": "desc",
            "page": 1,
            "pageNumElement": limit,
        }
        data = await self._get(path, params)
        return [_parse_team_season_stat(t) for t in data.get("teams", [])]

    async def get_player_stats(self, season_id: str, order_by: str, limit: int) -> list[PlayerSeasonStat]:
        """Return the top `limit` players for a season, sorted by `order_by` descending.

        Args:
            season_id: Full SDP season ID (e.g. `nwsl::Football_Season::0b6761e4...`).
            order_by: Stat ID to sort by (e.g. "goals", "assists").
            limit: Number of players to return per page.
        """
        path = f"{_API_PREFIX}/seasons/{quote(season_id, safe='')}/stats/players"
        params: dict[str, Any] = {
            "orderBy": order_by,
            "direction": "desc",
            "page": 1,
            "pageNumElement": limit,
        }
        data = await self._get(path, params)
        return [_parse_player_season_stat(p) for p in data.get("players", [])]
