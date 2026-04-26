"""Application service — the core of the hexagonal architecture.

This layer orchestrates work by delegating to outbound ports. It knows nothing
about MCP, HTTP, or JSON — those are adapter concerns.
"""

import re

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
from ..ports.outbound import CMSAPIPort, NWSLAPIPort, SDPAPIPort, SeasonDiscoveryPort
from ._helpers import (
    _AWARD_TITLE_KEYWORDS,
    _DRAFT_TITLE_KEYWORDS,
    _MAX_CMS_FETCH,
    _matches_keywords,
    _select_season,
    _validate_yyyymmdd,
)


class NWSLService:
    """Coordinates NWSL data lookups through the outbound ports.

    Three driven ports are injected: the ESPN-backed `repo` (read-only league
    feeds), the SDP-backed `sdp` (richer Opta data), and `discovery` (extracts
    SDP season IDs from the public site so SDP calls can be year-addressed).
    """

    def __init__(
        self,
        repo: NWSLAPIPort,
        sdp: SDPAPIPort,
        discovery: SeasonDiscoveryPort,
        cms: CMSAPIPort,
    ) -> None:
        self._repo = repo
        self._sdp = sdp
        self._discovery = discovery
        self._cms = cms

    async def _resolve_season(self, year: int | None, competition: str = "Regular Season") -> Season:
        """Find the SDP season matching the given year (or the most recent season).

        Args:
            year: Calendar year (e.g. 2026) or None for the most recent season.
            competition: "Regular Season" or "Challenge Cup".

        Raises:
            NWSLNotFoundError: If no matching season is advertised by the discovery source.
        """
        seasons = await self._discovery.get_seasons()
        candidates = [s for s in seasons if s.competition == competition]
        return _select_season(candidates, year, competition)

    async def get_teams(self) -> list[Team]:
        """Return all active NWSL teams."""
        return await self._repo.get_teams()

    async def get_team(self, team_id: str) -> Team:
        """Return a single team by its ESPN team ID.

        Args:
            team_id: ESPN numeric team ID or team abbreviation.

        Raises:
            ValueError: If team_id is empty.
            NWSLNotFoundError: If no team with that ID exists.
        """
        if not team_id or not team_id.strip():
            raise ValueError("team_id must not be empty")
        return await self._repo.get_team(team_id.strip())

    async def get_scoreboard(self, date: str | None = None, end_date: str | None = None) -> list[Match]:
        """Return matches for a date, a date range, or today if date is None.

        Args:
            date: Optional date string in YYYYMMDD format (e.g. "20250601").
            end_date: Optional end of a range in YYYYMMDD format. Requires `date`
                to be provided as the start of the range.

        Raises:
            ValueError: If either argument is malformed, or if end_date is given
                without a starting date.
        """
        if end_date is not None and date is None:
            raise ValueError("end_date requires a starting date")
        if date is not None:
            date = _validate_yyyymmdd(date.strip(), "date")
        if end_date is not None:
            end_date = _validate_yyyymmdd(end_date.strip(), "end_date")
        return await self._repo.get_scoreboard(date, end_date)

    async def get_news(self, limit: int = 10) -> list[NewsArticle]:
        """Return up to `limit` recent NWSL news articles.

        Args:
            limit: Maximum number of articles to return (must be positive).

        Raises:
            ValueError: If limit is not a positive integer.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        return await self._repo.get_news(limit)

    async def get_roster(self, team_id: str) -> list[Player]:
        """Return the active roster for a team.

        Args:
            team_id: ESPN numeric team ID.

        Raises:
            ValueError: If team_id is empty.
            NWSLNotFoundError: If no team with that ID exists.
        """
        if not team_id or not team_id.strip():
            raise ValueError("team_id must not be empty")
        return await self._repo.get_roster(team_id.strip())

    async def get_match_details(self, match_id: str) -> MatchDetails:
        """Return detailed information for a single match.

        Args:
            match_id: ESPN numeric event ID.

        Raises:
            ValueError: If match_id is empty.
            NWSLNotFoundError: If no match with that ID exists.
        """
        if not match_id or not match_id.strip():
            raise ValueError("match_id must not be empty")
        return await self._repo.get_match_details(match_id.strip())

    async def get_team_schedule(self, team_id: str) -> list[Match]:
        """Return all scheduled and completed matches for a team in the current season.

        Args:
            team_id: ESPN numeric team ID.

        Raises:
            ValueError: If team_id is empty.
            NWSLNotFoundError: If no team with that ID exists.
        """
        if not team_id or not team_id.strip():
            raise ValueError("team_id must not be empty")
        return await self._repo.get_team_schedule(team_id.strip())

    async def get_standings(self) -> list[Standing]:
        """Return the current NWSL league standings ordered by points descending."""
        return await self._repo.get_standings()

    async def get_player_leaderboards(
        self,
        season_year: int | None = None,
        sort_by: str = "goals",
        limit: int = 20,
    ) -> list[PlayerSeasonStat]:
        """Return the top players in a season, sorted by `sort_by` descending.

        Args:
            season_year: Calendar year (e.g. 2026). Omit for the most recent season.
            sort_by: SDP stat ID to rank by (e.g. "goals", "assists", "saves",
                "tackles-won", "minutes-played").
            limit: Number of players to return.

        Raises:
            ValueError: If limit is not positive.
            NWSLNotFoundError: If `season_year` doesn't match any advertised season.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        season = await self._resolve_season(season_year)
        return await self._sdp.get_player_stats(season.id, sort_by, limit)

    async def get_draft_articles(self, year: int | None = None, limit: int = 10) -> list[CMSArticle]:
        """Return recent NWSL draft articles, optionally filtered to a specific year.

        Draft results are published as CMS articles. Filtering by year matches
        articles whose title mentions that year — useful for "2025 draft picks"
        but not exhaustive (some articles omit the year in the title).

        Args:
            year: Calendar year (e.g. 2025). Omit for all draft articles.
            limit: Maximum number of articles to return.

        Raises:
            ValueError: If limit is not positive.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        articles = await self._cms.get_recent_stories(_MAX_CMS_FETCH)
        matches = [a for a in articles if _matches_keywords(a.title, _DRAFT_TITLE_KEYWORDS)]
        if year is not None:
            year_pattern = re.compile(rf"\b{year}\b")
            matches = [a for a in matches if year_pattern.search(a.title)]
        return matches[:limit]

    async def get_award_articles(self, limit: int = 10) -> list[CMSArticle]:
        """Return recent NWSL award-related articles.

        Award winners (Best XI, Player of the Month, Rookie of the Month, etc.)
        are published as CMS articles rather than a structured endpoint. This
        method fetches recent stories and filters by title keywords.

        Args:
            limit: Maximum number of award articles to return.

        Raises:
            ValueError: If limit is not positive.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        articles = await self._cms.get_recent_stories(_MAX_CMS_FETCH)
        matches = [a for a in articles if _matches_keywords(a.title, _AWARD_TITLE_KEYWORDS)]
        return matches[:limit]

    async def get_challenge_cup_standings(self, season_year: int | None = None) -> list[SeasonStanding]:
        """Return the standings table for an NWSL Challenge Cup season.

        Args:
            season_year: Calendar year. Omit for the most recent Challenge Cup.

        Raises:
            NWSLNotFoundError: If `season_year` doesn't match any advertised
                Challenge Cup season.
        """
        season = await self._resolve_season(season_year, competition="Challenge Cup")
        return await self._sdp.get_standings_for_season(season.id)

    async def get_historical_standings(self, season_year: int) -> list[SeasonStanding]:
        """Return the final or in-progress standings table for a given year.

        Backed by SDP/Opta data — covers all seasons advertised on the public
        site (currently 2016 through the current year).

        Args:
            season_year: Calendar year (e.g. 2018, 2024, 2026).

        Raises:
            NWSLNotFoundError: If `season_year` doesn't match any advertised season.
        """
        season = await self._resolve_season(season_year)
        return await self._sdp.get_standings_for_season(season.id)

    async def get_team_season_stats(
        self,
        season_year: int | None = None,
        sort_by: str = "total-points",
        limit: int = 20,
    ) -> list[TeamSeasonStat]:
        """Return team season aggregates ranked by `sort_by` descending.

        Args:
            season_year: Calendar year. Omit for the most recent season.
            sort_by: SDP stat ID to rank by (e.g. "total-points", "goals",
                "passes-accuracy", "goals-against").
            limit: Number of teams to return. NWSL has 16 teams currently.

        Raises:
            ValueError: If limit is not positive.
            NWSLNotFoundError: If `season_year` doesn't match any advertised season.
        """
        if limit <= 0:
            raise ValueError("limit must be positive")
        season = await self._resolve_season(season_year)
        return await self._sdp.get_team_stats(season.id, sort_by, limit)
