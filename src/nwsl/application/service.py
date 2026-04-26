"""Application service — the core of the hexagonal architecture.

This layer orchestrates work by delegating to outbound ports. It knows nothing
about MCP, HTTP, or JSON — those are adapter concerns.
"""

from ..domain.models import (
    AdjustedPointsPerGame,
    CMSArticle,
    Match,
    MatchDetails,
    NewsArticle,
    OpponentPPG,
    Player,
    PlayerSeasonStat,
    ResultsByOpponentTier,
    Season,
    SeasonStanding,
    Standing,
    StrengthOfSchedule,
    Team,
    TeamSeasonStat,
)
from ..ports.outbound import CMSAPIPort, NWSLAPIPort, SDPAPIPort, SeasonDiscoveryPort
from ._analytics_helpers import (
    _build_ppg_index,
    _build_tier_record,
    _build_tier_specs,
    _league_average_ppg,
    _mean,
    _opponent_ppgs,
    _played_opponents,
    _resolve_team,
    _safe_ratio,
    _self_record,
    _tally_tier_results,
    _validate_team_id,
    _validate_tier_size,
)
from ._helpers import (
    _AWARD_TITLE_KEYWORDS,
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

    async def get_strength_of_schedule(self, team_id: str) -> StrengthOfSchedule:
        """Return the average current PPG of opponents this team has faced.

        Walks the team's completed matches and aggregates each opponent's
        league-table points-per-game (no self-exclusion). Useful for "who has
        played the tougher schedule so far?" questions.

        Args:
            team_id: ESPN numeric team ID.

        Raises:
            ValueError: If team_id is empty.
            NWSLNotFoundError: If no team with that ID exists.
        """
        team_id = _validate_team_id(team_id)
        standings = await self._repo.get_standings()
        schedule = await self._repo.get_team_schedule(team_id)
        ppg_index = _build_ppg_index(standings)
        team = _resolve_team(standings, schedule, team_id)
        opponents = [
            OpponentPPG(
                team=opp,
                matches_played=ppg_index[opp.id].matches_played,
                points=ppg_index[opp.id].points,
                points_per_game=ppg_index[opp.id].ppg,
            )
            for opp in _played_opponents(schedule, team_id)
            if opp.id in ppg_index
        ]
        return StrengthOfSchedule(
            team=team,
            matches_played=len(opponents),
            opponents=opponents,
            average_opponent_ppg=_mean([o.points_per_game for o in opponents]),
        )

    async def get_results_by_opponent_tier(self, team_id: str, tier_size: int = 5) -> ResultsByOpponentTier:
        """Return W-L-T splits against current top-tier, middle, and bottom-tier teams.

        Tiers are derived from the current league standings: the top `tier_size`,
        the bottom `tier_size`, and everyone in between. Draws (no declared winner)
        count as ties; matches against teams not in the current standings are
        skipped.

        Args:
            team_id: ESPN numeric team ID.
            tier_size: Number of teams in each of the top and bottom tiers.
                Defaults to 5. Must be at least 1, and 2*tier_size must not
                exceed the league size.

        Raises:
            ValueError: If team_id is empty or tier_size is invalid.
            NWSLNotFoundError: If no team with that ID exists.
        """
        team_id = _validate_team_id(team_id)
        standings = await self._repo.get_standings()
        _validate_tier_size(tier_size, len(standings))
        schedule = await self._repo.get_team_schedule(team_id)
        rank_by_id = {s.team.id: i + 1 for i, s in enumerate(standings)}
        team = _resolve_team(standings, schedule, team_id)
        tier_specs = _build_tier_specs(tier_size, len(standings))
        tally = _tally_tier_results(schedule, team_id, rank_by_id, tier_specs)
        tiers = [_build_tier_record(name, low, high, tally) for name, low, high in tier_specs if high >= low]
        return ResultsByOpponentTier(team=team, tier_size=tier_size, tiers=tiers)

    async def get_adjusted_points_per_game(self, team_id: str) -> AdjustedPointsPerGame:
        """Return raw PPG plus a schedule-strength-adjusted PPG.

        Adjusted PPG = raw_ppg * (avg_opponent_ppg / league_average_ppg). Values
        above raw_ppg mean the team has earned points against a tougher
        schedule than league average.

        Args:
            team_id: ESPN numeric team ID.

        Raises:
            ValueError: If team_id is empty.
            NWSLNotFoundError: If no team with that ID exists.
        """
        team_id = _validate_team_id(team_id)
        standings = await self._repo.get_standings()
        schedule = await self._repo.get_team_schedule(team_id)
        ppg_index = _build_ppg_index(standings)
        team = _resolve_team(standings, schedule, team_id)
        matches_played, points, raw_ppg = _self_record(ppg_index, team_id)
        opp_entries = _opponent_ppgs(schedule, team_id, ppg_index)
        avg_opp_ppg = _mean([e.ppg for e in opp_entries])
        league_avg = _league_average_ppg(standings)
        return AdjustedPointsPerGame(
            team=team,
            matches_played=matches_played,
            points=points,
            raw_ppg=raw_ppg,
            average_opponent_ppg=avg_opp_ppg,
            league_average_ppg=league_avg,
            adjusted_ppg=raw_ppg * _safe_ratio(avg_opp_ppg, league_avg),
        )

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
