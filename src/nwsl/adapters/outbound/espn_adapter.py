"""Outbound adapter — translates domain calls into ESPN API HTTP requests.

This is the only place in the codebase that knows about:
- The ESPN API host and URL structure
- ESPN's JSON wire format (camelCase, nested objects)
- How to map ESPN responses to domain models

Everything else in the system talks to the NWSLAPIPort protocol.
"""

import logging
from typing import Any

import httpx

from ...domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from ...domain.models import Match, MatchCompetitor, Standing, Team

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "https://site.api.espn.com"
_LEAGUE_PATH = "/apis/site/v2/sports/soccer/usa.nwsl"


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


def _parse_team(raw: dict[str, Any]) -> Team:
    """Map a raw ESPN team object to a domain Team.

    Args:
        raw: The team dict from the ESPN API (may be nested under "team" key).
    """
    team = raw.get("team", raw)
    logos = team.get("logos", [])
    logo_url = logos[0].get("href") if logos else None
    return Team(
        id=str(team.get("id", "")),
        name=team.get("name", ""),
        abbreviation=team.get("abbreviation", ""),
        location=team.get("location", ""),
        display_name=team.get("displayName", ""),
        logo_url=logo_url,
    )


def _parse_competitor(raw: dict[str, Any]) -> MatchCompetitor:
    """Map a raw ESPN competitor object to a domain MatchCompetitor.

    Args:
        raw: A competitor dict from a scoreboard event.
    """
    score = raw.get("score")
    winner = raw.get("winner")
    return MatchCompetitor(
        team=_parse_team(raw),
        home_away=raw.get("homeAway", ""),
        score=str(score) if score is not None else None,
        winner=bool(winner) if winner is not None else None,
    )


def _parse_match(event: dict[str, Any]) -> Match:
    """Map a raw ESPN scoreboard event to a domain Match.

    Args:
        event: An event dict from the ESPN scoreboard response.
    """
    competition = event.get("competitions", [{}])[0]
    status = competition.get("status", {})
    status_type = status.get("type", {})
    competitors = [_parse_competitor(c) for c in competition.get("competitors", [])]
    return Match(
        id=str(event.get("id", "")),
        date=event.get("date", ""),
        name=event.get("name", ""),
        short_name=event.get("shortName", ""),
        status_type=status_type.get("name", ""),
        status_detail=status.get("displayClock", status_type.get("description", "")),
        competitors=competitors,
    )


def _parse_standing(entry: dict[str, Any]) -> Standing | None:
    """Map a raw ESPN standings entry to a domain Standing.

    Returns None for entries that lack the required team data.

    Args:
        entry: A standings entry dict from the ESPN standings response.
    """
    team_raw = entry.get("team")
    if not team_raw:
        return None

    stats: dict[str, Any] = {s["name"]: s.get("value", 0) for s in entry.get("stats", [])}
    return Standing(
        team=_parse_team(team_raw),
        wins=int(stats.get("wins", 0)),
        losses=int(stats.get("losses", 0)),
        ties=int(stats.get("ties", 0)),
        points=int(stats.get("points", 0)),
        goals_for=int(stats.get("pointsFor", 0)),
        goals_against=int(stats.get("pointsAgainst", 0)),
        goal_difference=int(stats.get("pointDifferential", 0)),
    )


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

    async def get_scoreboard(self, date: str | None = None) -> list[Match]:
        """Return matches on the given date (YYYYMMDD) or the current week if date is None.

        Args:
            date: Optional date string in YYYYMMDD format.
        """
        params: dict[str, Any] = {}
        if date:
            params["dates"] = date
        data = await self._get(f"{_LEAGUE_PATH}/scoreboard", params)
        return [_parse_match(e) for e in data.get("events", [])]

    async def get_standings(self) -> list[Standing]:
        """Return the current NWSL league standings ordered by points descending."""
        data = await self._get(f"{_LEAGUE_PATH}/standings")
        entries: list[dict[str, Any]] = []
        for season in data.get("children", []):
            for division in season.get("standings", {}).get("entries", []):
                entries.append(division)
        standings = [s for e in entries if (s := _parse_standing(e)) is not None]
        return sorted(standings, key=lambda s: s.points, reverse=True)
