"""Outbound ports — interfaces the application layer depends on.

These are the contracts that secondary/driven adapters must satisfy. The
application layer only imports these protocols; it never references concrete
implementations. This is what makes the hexagonal boundary testable and
swap-able (e.g. real HTTP adapter vs. an in-memory stub).
"""

from typing import Protocol

from ..domain.models import (
    CMSArticle,
    Match,
    MatchDetails,
    NewsArticle,
    Player,
    PlayerSeasonStat,
    Season,
    SeasonStanding,
    Standing,
    Team,
    TeamSeasonStat,
)


class NWSLAPIPort(Protocol):
    """Contract for the upstream NWSL data source (ESPN API)."""

    async def get_teams(self) -> list[Team]:
        """Return all active NWSL teams."""
        ...

    async def get_team(self, team_id: str) -> Team:
        """Return a single team by its ESPN team ID.

        Raises:
            NWSLNotFoundError: If no team with that ID exists.
        """
        ...

    async def get_scoreboard(self, date: str | None = None, end_date: str | None = None) -> list[Match]:
        """Return matches on the given date or date range, or today if date is None.

        When `end_date` is provided, `date` is the start of the range and the
        upstream is queried with `dates=START-END`.
        """
        ...

    async def get_news(self, limit: int) -> list[NewsArticle]:
        """Return up to `limit` recent NWSL news articles."""
        ...

    async def get_roster(self, team_id: str) -> list[Player]:
        """Return the active roster for a team.

        Raises:
            NWSLNotFoundError: If no team with that ID exists.
        """
        ...

    async def get_match_details(self, match_id: str) -> MatchDetails:
        """Return detailed information for a single match.

        Raises:
            NWSLNotFoundError: If no match with that ID exists.
        """
        ...

    async def get_team_schedule(self, team_id: str) -> list[Match]:
        """Return all scheduled and completed matches for a team in the current season.

        Raises:
            NWSLNotFoundError: If no team with that ID exists.
        """
        ...

    async def get_standings(self) -> list[Standing]:
        """Return the current NWSL league standings, ordered by points descending."""
        ...


class SDPAPIPort(Protocol):
    """Contract for the unofficial SDP/Opta-backed data source (api-sdp.nwslsoccer.com).

    Carries richer per-player and historical data than the ESPN feed. IDs are
    SDP entity IDs (e.g. `nwsl::Football_Season::{uuid}`) sourced from
    SeasonDiscoveryPort.
    """

    async def get_player_stats(self, season_id: str, order_by: str, limit: int) -> list[PlayerSeasonStat]:
        """Return the top `limit` players in a season, sorted by `order_by` descending."""
        ...

    async def get_team_stats(self, season_id: str, order_by: str, limit: int) -> list[TeamSeasonStat]:
        """Return the top `limit` teams in a season, sorted by `order_by` descending."""
        ...

    async def get_standings_for_season(self, season_id: str) -> list[SeasonStanding]:
        """Return the overall standings table for a season, ordered by rank."""
        ...


class SeasonDiscoveryPort(Protocol):
    """Contract for finding SDP season IDs from the public NWSL site."""

    async def get_seasons(self) -> list[Season]:
        """Return the list of seasons advertised by the standings page."""
        ...


class CMSAPIPort(Protocol):
    """Contract for the official site's content API (dapi.nwslsoccer.com).

    Used by the awards and draft tools to surface editorial content the
    structured stats APIs don't expose.
    """

    async def get_recent_stories(self, limit: int) -> list[CMSArticle]:
        """Return the most recent `limit` stories ordered by publication date."""
        ...
