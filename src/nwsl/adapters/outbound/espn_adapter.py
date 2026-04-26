"""Outbound adapter — translates domain calls into ESPN API HTTP requests.

This is the only place in the codebase that knows about:
- The ESPN API host and URL structure
- How to issue HTTP requests and translate non-2xx responses into domain errors

The wire-format → domain-model mapping lives in parsers.py so this module
stays focused on transport.
"""

import logging
from typing import Any

import httpx

from ...domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from ...domain.models import Match, MatchDetails, NewsArticle, Player, Standing, Team
from .parsers import (
    _parse_article,
    _parse_match,
    _parse_match_details,
    _parse_player,
    _parse_standing,
    _parse_team,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://site.api.espn.com"
_LEAGUE_PATH = "/apis/site/v2/sports/soccer/usa.nwsl"
# Standings live on the /apis/v2 surface — the /apis/site/v2 path returns an empty {}.
_STANDINGS_PATH = "/apis/v2/sports/soccer/usa.nwsl/standings"


def _check_response(response: httpx.Response, path: str) -> None:
    """Raise a domain exception for any non-2xx HTTP status.

    Args:
        response: The httpx response to inspect.
        path: The request path, included in exception messages for context.

    Raises:
        NWSLNotFoundError: If the server returned HTTP 404.
        UpstreamAPIError: If the server returned any other 4xx or 5xx status.
    """
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise NWSLNotFoundError(f"Not found: {path}") from exc
        raise UpstreamAPIError(f"Upstream error {exc.response.status_code}: {path}") from exc


class ESPNAdapter:
    """Calls the ESPN public API for NWSL data.

    The underlying httpx.AsyncClient is created once at construction and reused
    for all requests so the TCP connection pool is retained across calls — avoiding
    a fresh TCP+TLS handshake on every API call.
    """

    def __init__(self, base_url: str = _DEFAULT_BASE_URL, client: httpx.AsyncClient | None = None) -> None:
        """Initialize the adapter with an optional HTTP client.

        Args:
            base_url: Base URL of the ESPN API. Defaults to https://site.api.espn.com.
            client: An httpx.AsyncClient instance to reuse across all requests.
                Inject a pre-configured mock in tests.
        """
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GET request and return the parsed JSON body.

        Args:
            path: URL path relative to base_url.
            params: Optional query parameters.

        Returns:
            Parsed JSON response body as a dict.

        Raises:
            NWSLNotFoundError: If the server returns HTTP 404.
            UpstreamAPIError: If the server returns any other 4xx or 5xx response.
        """
        logger.debug("GET %s params=%s", path, params)
        response = await self._client.get(path, params=params or {})
        _check_response(response, path)
        return response.json()

    async def get_teams(self) -> list[Team]:
        """Return all active NWSL teams."""
        data = await self._get(f"{_LEAGUE_PATH}/teams", {"limit": 100})
        raw_teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        return [_parse_team(t) for t in raw_teams]

    async def get_team(self, team_id: str) -> Team:
        """Return a single team by its ESPN team ID.

        Raises:
            NWSLNotFoundError: If no team with that ID exists.
        """
        data = await self._get(f"{_LEAGUE_PATH}/teams/{team_id}")
        raw = data.get("team")
        if not raw:
            raise NWSLNotFoundError(f"Team not found: {team_id}")
        return _parse_team(raw)

    async def get_scoreboard(self, date: str | None = None, end_date: str | None = None) -> list[Match]:
        """Return matches on the given date or date range, or the current week if date is None.

        Args:
            date: Optional date string in YYYYMMDD format.
            end_date: Optional end date in YYYYMMDD format. When set, `date` is the start
                of the range and ESPN's `dates=START-END` parameter is used.
        """
        params: dict[str, Any] = {}
        if date and end_date:
            params["dates"] = f"{date}-{end_date}"
        elif date:
            params["dates"] = date
        data = await self._get(f"{_LEAGUE_PATH}/scoreboard", params)
        return [_parse_match(e) for e in data.get("events", [])]

    async def get_roster(self, team_id: str) -> list[Player]:
        """Return the active roster for a team.

        Args:
            team_id: ESPN numeric team ID.

        Raises:
            NWSLNotFoundError: If no team with that ID exists.
        """
        data = await self._get(f"{_LEAGUE_PATH}/teams/{team_id}/roster")
        return [_parse_player(p) for p in data.get("athletes", [])]

    async def get_match_details(self, match_id: str) -> MatchDetails:
        """Return detailed information for a single match.

        Args:
            match_id: ESPN numeric event ID.

        Raises:
            NWSLNotFoundError: If no match with that ID exists.
        """
        data = await self._get(f"{_LEAGUE_PATH}/summary", {"event": match_id})
        return _parse_match_details(data)

    async def get_team_schedule(self, team_id: str) -> list[Match]:
        """Return all scheduled and completed matches for a team in the current season.

        Args:
            team_id: ESPN numeric team ID.

        Raises:
            NWSLNotFoundError: If no team with that ID exists.
        """
        data = await self._get(f"{_LEAGUE_PATH}/teams/{team_id}/schedule")
        return [_parse_match(e) for e in data.get("events", [])]

    async def get_news(self, limit: int) -> list[NewsArticle]:
        """Return recent NWSL news articles.

        Args:
            limit: Maximum number of articles to return.
        """
        data = await self._get(f"{_LEAGUE_PATH}/news", {"limit": limit})
        return [_parse_article(a) for a in data.get("articles", [])]

    async def get_standings(self) -> list[Standing]:
        """Return the current NWSL league standings ordered by points descending."""
        data = await self._get(_STANDINGS_PATH)
        entries: list[dict[str, Any]] = []
        for season in data.get("children", []):
            for division in season.get("standings", {}).get("entries", []):
                entries.append(division)
        standings = [s for e in entries if (s := _parse_standing(e)) is not None]
        return sorted(standings, key=lambda s: s.points, reverse=True)
