"""Unit tests for the MCP inbound adapter formatters and tool handlers.

Tests the formatting functions and safe_call error handling directly,
without spinning up a full MCP server.
"""

from pytest_mock import MockerFixture

from nwsl.adapters.inbound.formatters import (
    _fmt_adjusted_ppg,
    _fmt_match_details,
    _fmt_news,
    _fmt_player_leaderboards,
    _fmt_results_by_tier,
    _fmt_roster,
    _fmt_scoreboard,
    _fmt_standings,
    _fmt_strength_of_schedule,
    _fmt_team,
    _fmt_team_schedule,
    _fmt_teams,
)
from nwsl.adapters.inbound.mcp_adapter import _safe_call, create_mcp_server
from nwsl.application.service import NWSLService
from nwsl.domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from nwsl.domain.models import (
    AdjustedPointsPerGame,
    Match,
    MatchDetails,
    NewsArticle,
    OpponentPPG,
    Player,
    PlayerSeasonStat,
    ResultsByOpponentTier,
    Standing,
    StrengthOfSchedule,
    Team,
    TierRecord,
)


async def test_safe_call_returns_formatted_result(portland_thorns: Team) -> None:
    async def _coro() -> Team:
        return portland_thorns

    result = await _safe_call(_coro(), _fmt_team)
    assert "Portland Thorns FC" in result
    assert "POR" in result


async def test_safe_call_handles_not_found() -> None:
    async def _coro() -> list[Team]:
        raise NWSLNotFoundError("Team not found: 9999")

    result = await _safe_call(_coro(), _fmt_teams)
    assert "Not found" in result


async def test_safe_call_handles_upstream_error() -> None:
    async def _coro() -> list[Team]:
        raise UpstreamAPIError("503")

    result = await _safe_call(_coro(), _fmt_teams)
    assert "Upstream error" in result


async def test_safe_call_handles_value_error() -> None:
    async def _coro() -> list[Match]:
        raise ValueError("date must be YYYYMMDD")

    result = await _safe_call(_coro(), _fmt_scoreboard)
    assert "Invalid request" in result


def test_fmt_teams_empty() -> None:
    assert _fmt_teams([]) == "No teams found."


def test_fmt_teams_lists_all(portland_thorns: Team, north_carolina_courage: Team) -> None:
    result = _fmt_teams([portland_thorns, north_carolina_courage])
    assert "Portland Thorns FC" in result
    assert "North Carolina Courage" in result
    assert "1." in result
    assert "2." in result


def test_fmt_scoreboard_empty() -> None:
    assert "No matches found" in _fmt_scoreboard([])


def test_fmt_scoreboard_shows_score(sample_match: Match) -> None:
    result = _fmt_scoreboard([sample_match])
    assert "Portland Thorns FC" in result
    assert "2" in result
    assert "FT" in result


def test_fmt_player_leaderboards_empty() -> None:
    assert "No players" in _fmt_player_leaderboards([], sort_by="goals")


def test_fmt_player_leaderboards_shows_sort_stat(sample_player_season_stat: PlayerSeasonStat) -> None:
    result = _fmt_player_leaderboards([sample_player_season_stat], sort_by="goals")
    assert "Barbra Banda" in result
    assert "Orlando Pride" in result
    assert "5" in result  # goal count
    assert "goals" in result.lower()


def test_fmt_news_empty() -> None:
    assert "No news" in _fmt_news([])


def test_fmt_news_lists_articles(sample_article: NewsArticle) -> None:
    result = _fmt_news([sample_article])
    assert "Chicago Stars" in result
    assert "2026-04-26" in result
    assert "espn.com" in result


def test_fmt_roster_empty() -> None:
    assert "No players" in _fmt_roster([])


def test_fmt_roster_lists_players(sample_player: Player) -> None:
    result = _fmt_roster([sample_player])
    assert "Mackenzie Arnold" in result
    assert "#18" in result
    assert "Goalkeeper" in result
    assert "Australia" in result


def test_fmt_match_details_includes_teams_score_venue(sample_match_details: MatchDetails) -> None:
    result = _fmt_match_details(sample_match_details)
    assert "North Carolina Courage" in result
    assert "Portland Thorns FC" in result
    assert "2 - 2" in result
    assert "WakeMed Soccer Park" in result
    assert "7,018" in result or "7018" in result


def test_fmt_match_details_lists_key_events(sample_match_details: MatchDetails) -> None:
    result = _fmt_match_details(sample_match_details)
    assert "12'" in result
    assert "Reilyn Turner" in result


def test_fmt_team_schedule_empty() -> None:
    assert "No scheduled matches" in _fmt_team_schedule([])


def test_fmt_team_schedule_lists_matches(sample_match: Match) -> None:
    result = _fmt_team_schedule([sample_match])
    assert "Portland Thorns FC" in result
    assert "FT" in result


def test_fmt_standings_empty() -> None:
    assert "No standings data" in _fmt_standings([])


def test_fmt_standings_shows_points(sample_standing: Standing) -> None:
    result = _fmt_standings([sample_standing])
    assert "38 pts" in result
    assert "Portland Thorns FC" in result
    assert "+22" in result


def test_create_mcp_server_returns_fastmcp(mocker: MockerFixture) -> None:
    mock_service = mocker.MagicMock(spec=NWSLService)
    server = create_mcp_server(mock_service)
    assert server is not None


# ---------------------------------------------------------------------------
# Schedule-strength analytics formatters
# ---------------------------------------------------------------------------


def test_fmt_strength_of_schedule_empty(portland_thorns: Team) -> None:
    sos = StrengthOfSchedule(team=portland_thorns, matches_played=0, opponents=[], average_opponent_ppg=0.0)
    result = _fmt_strength_of_schedule(sos)
    assert "Portland Thorns FC" in result
    assert "no matches played" in result.lower() or "0 matches" in result.lower()


def test_fmt_strength_of_schedule_lists_opponents(portland_thorns: Team, north_carolina_courage: Team) -> None:
    sos = StrengthOfSchedule(
        team=portland_thorns,
        matches_played=1,
        opponents=[OpponentPPG(team=north_carolina_courage, matches_played=5, points=10, points_per_game=2.0)],
        average_opponent_ppg=2.0,
    )
    result = _fmt_strength_of_schedule(sos)
    assert "Portland Thorns FC" in result
    assert "North Carolina Courage" in result
    assert "2.00" in result  # average PPG rounded to 2 decimals


def test_fmt_strength_of_schedule_collapses_repeat_opponents(
    portland_thorns: Team, north_carolina_courage: Team
) -> None:
    """When the same opponent appears twice, the formatter collapses to one row with x2."""
    opp = OpponentPPG(team=north_carolina_courage, matches_played=5, points=10, points_per_game=2.0)
    sos = StrengthOfSchedule(
        team=portland_thorns,
        matches_played=2,
        opponents=[opp, opp],
        average_opponent_ppg=2.0,
    )
    result = _fmt_strength_of_schedule(sos)
    # Opponent listed once, with a meeting count
    assert result.count("North Carolina Courage") == 1
    assert "x2" in result or "×2" in result or "(2 meetings)" in result


def test_fmt_results_by_tier(portland_thorns: Team) -> None:
    rbt = ResultsByOpponentTier(
        team=portland_thorns,
        tier_size=2,
        tiers=[
            TierRecord(label="Top 2", rank_low=1, rank_high=2, wins=0, losses=1, ties=0),
            TierRecord(label="Middle 2", rank_low=3, rank_high=4, wins=0, losses=0, ties=1),
            TierRecord(label="Bottom 2", rank_low=5, rank_high=6, wins=1, losses=0, ties=0),
        ],
    )
    result = _fmt_results_by_tier(rbt)
    assert "Portland Thorns FC" in result
    assert "Top 2" in result
    assert "Middle 2" in result
    assert "Bottom 2" in result
    # Should show W-L-T splits
    assert "0-1-0" in result
    assert "1-0-0" in result


def test_fmt_adjusted_ppg(portland_thorns: Team) -> None:
    a = AdjustedPointsPerGame(
        team=portland_thorns,
        matches_played=5,
        points=10,
        raw_ppg=2.0,
        average_opponent_ppg=1.667,
        league_average_ppg=1.75,
        adjusted_ppg=1.905,
    )
    result = _fmt_adjusted_ppg(a)
    assert "Portland Thorns FC" in result
    assert "2.00" in result  # raw_ppg
    assert "1.90" in result or "1.91" in result  # adjusted_ppg rounded
