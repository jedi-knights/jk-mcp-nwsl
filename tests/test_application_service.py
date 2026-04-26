"""Unit tests for the NWSLService application layer.

Tests verify that the service delegates correctly to the outbound port and
enforces input validation before any port call is made.
"""

from unittest.mock import AsyncMock

import pytest

from nwsl.application.service import NWSLService
from nwsl.domain.exceptions import NWSLNotFoundError
from nwsl.domain.models import (
    AdjustedPointsPerGame,
    CMSArticle,
    Match,
    MatchCompetitor,
    MatchDetails,
    NewsArticle,
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


async def test_get_teams_delegates_to_repo(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    portland_thorns: Team,
) -> None:
    mock_repo.get_teams.return_value = [portland_thorns]
    result = await nwsl_service.get_teams()
    mock_repo.get_teams.assert_called_once()
    assert result == [portland_thorns]


async def test_get_team_delegates_to_repo(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    portland_thorns: Team,
) -> None:
    mock_repo.get_team.return_value = portland_thorns
    result = await nwsl_service.get_team("1899")
    mock_repo.get_team.assert_called_once_with("1899")
    assert result == portland_thorns


async def test_get_team_strips_whitespace(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    portland_thorns: Team,
) -> None:
    mock_repo.get_team.return_value = portland_thorns
    await nwsl_service.get_team("  1899  ")
    mock_repo.get_team.assert_called_once_with("1899")


@pytest.mark.parametrize("bad_id", ["", "   "])
async def test_get_team_rejects_empty_id(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    bad_id: str,
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        await nwsl_service.get_team(bad_id)
    mock_repo.get_team.assert_not_called()


async def test_get_scoreboard_delegates_to_repo(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    sample_match: Match,
) -> None:
    mock_repo.get_scoreboard.return_value = [sample_match]
    result = await nwsl_service.get_scoreboard("20250601")
    mock_repo.get_scoreboard.assert_called_once_with("20250601", None)
    assert result == [sample_match]


async def test_get_scoreboard_with_date_range(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    sample_match: Match,
) -> None:
    mock_repo.get_scoreboard.return_value = [sample_match]
    result = await nwsl_service.get_scoreboard("20260404", end_date="20260405")
    mock_repo.get_scoreboard.assert_called_once_with("20260404", "20260405")
    assert result == [sample_match]


async def test_get_scoreboard_rejects_end_date_without_start(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    with pytest.raises(ValueError, match="end_date requires"):
        await nwsl_service.get_scoreboard(None, end_date="20260405")
    mock_repo.get_scoreboard.assert_not_called()


@pytest.mark.parametrize("bad_end", ["2026-04-05", "2026040", "ABCDEFGH"])
async def test_get_scoreboard_rejects_invalid_end_date(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    bad_end: str,
) -> None:
    with pytest.raises(ValueError, match="YYYYMMDD"):
        await nwsl_service.get_scoreboard("20260404", end_date=bad_end)
    mock_repo.get_scoreboard.assert_not_called()


async def test_get_scoreboard_accepts_none_date(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    mock_repo.get_scoreboard.return_value = []
    await nwsl_service.get_scoreboard(None)
    mock_repo.get_scoreboard.assert_called_once_with(None, None)


@pytest.mark.parametrize("bad_date", ["2025-06-01", "20250", "ABCDEFGH", "2025060"])
async def test_get_scoreboard_rejects_invalid_date(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    bad_date: str,
) -> None:
    with pytest.raises(ValueError, match="YYYYMMDD"):
        await nwsl_service.get_scoreboard(bad_date)
    mock_repo.get_scoreboard.assert_not_called()


async def test_get_news_delegates_to_repo(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    sample_article: NewsArticle,
) -> None:
    mock_repo.get_news.return_value = [sample_article]
    result = await nwsl_service.get_news(5)
    mock_repo.get_news.assert_called_once_with(5)
    assert result == [sample_article]


async def test_get_news_defaults_to_ten(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    mock_repo.get_news.return_value = []
    await nwsl_service.get_news()
    mock_repo.get_news.assert_called_once_with(10)


@pytest.mark.parametrize("bad_limit", [0, -1, -100])
async def test_get_news_rejects_non_positive_limit(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    bad_limit: int,
) -> None:
    with pytest.raises(ValueError, match="positive"):
        await nwsl_service.get_news(bad_limit)
    mock_repo.get_news.assert_not_called()


async def test_get_roster_delegates_to_repo(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    sample_player: Player,
) -> None:
    mock_repo.get_roster.return_value = [sample_player]
    result = await nwsl_service.get_roster("15362")
    mock_repo.get_roster.assert_called_once_with("15362")
    assert result == [sample_player]


async def test_get_roster_strips_whitespace(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    mock_repo.get_roster.return_value = []
    await nwsl_service.get_roster("  15362  ")
    mock_repo.get_roster.assert_called_once_with("15362")


@pytest.mark.parametrize("bad_id", ["", "   "])
async def test_get_roster_rejects_empty_id(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    bad_id: str,
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        await nwsl_service.get_roster(bad_id)
    mock_repo.get_roster.assert_not_called()


async def test_get_match_details_delegates_to_repo(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    sample_match_details: MatchDetails,
) -> None:
    mock_repo.get_match_details.return_value = sample_match_details
    result = await nwsl_service.get_match_details("401853883")
    mock_repo.get_match_details.assert_called_once_with("401853883")
    assert result == sample_match_details


async def test_get_match_details_strips_whitespace(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    sample_match_details: MatchDetails,
) -> None:
    mock_repo.get_match_details.return_value = sample_match_details
    await nwsl_service.get_match_details("  401853883  ")
    mock_repo.get_match_details.assert_called_once_with("401853883")


@pytest.mark.parametrize("bad_id", ["", "   "])
async def test_get_match_details_rejects_empty_id(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    bad_id: str,
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        await nwsl_service.get_match_details(bad_id)
    mock_repo.get_match_details.assert_not_called()


async def test_get_team_schedule_delegates_to_repo(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    sample_match: Match,
) -> None:
    mock_repo.get_team_schedule.return_value = [sample_match]
    result = await nwsl_service.get_team_schedule("1899")
    mock_repo.get_team_schedule.assert_called_once_with("1899")
    assert result == [sample_match]


async def test_get_team_schedule_strips_whitespace(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    mock_repo.get_team_schedule.return_value = []
    await nwsl_service.get_team_schedule("  1899  ")
    mock_repo.get_team_schedule.assert_called_once_with("1899")


@pytest.mark.parametrize("bad_id", ["", "   "])
async def test_get_team_schedule_rejects_empty_id(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    bad_id: str,
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        await nwsl_service.get_team_schedule(bad_id)
    mock_repo.get_team_schedule.assert_not_called()


async def test_get_player_leaderboards_resolves_year_and_calls_sdp(
    nwsl_service: NWSLService,
    mock_sdp: AsyncMock,
    mock_discovery: AsyncMock,
    sample_season: Season,
    sample_player_season_stat: PlayerSeasonStat,
) -> None:
    mock_discovery.get_seasons.return_value = [sample_season]
    mock_sdp.get_player_stats.return_value = [sample_player_season_stat]

    result = await nwsl_service.get_player_leaderboards(season_year=2026, sort_by="goals", limit=10)

    mock_sdp.get_player_stats.assert_called_once_with(sample_season.id, "goals", 10)
    assert result == [sample_player_season_stat]


async def test_get_player_leaderboards_defaults_to_most_recent_year(
    nwsl_service: NWSLService,
    mock_sdp: AsyncMock,
    mock_discovery: AsyncMock,
) -> None:
    older = Season(id="old-id", year=2024, name="Regular Season 2024", competition="Regular Season")
    newer = Season(id="new-id", year=2026, name="Regular Season 2026", competition="Regular Season")
    mock_discovery.get_seasons.return_value = [older, newer]
    mock_sdp.get_player_stats.return_value = []

    await nwsl_service.get_player_leaderboards()

    mock_sdp.get_player_stats.assert_called_once_with("new-id", "goals", 20)


async def test_get_player_leaderboards_raises_when_year_missing(
    nwsl_service: NWSLService,
    mock_discovery: AsyncMock,
    sample_season: Season,
) -> None:
    mock_discovery.get_seasons.return_value = [sample_season]
    with pytest.raises(NWSLNotFoundError, match="2099"):
        await nwsl_service.get_player_leaderboards(season_year=2099)


@pytest.mark.parametrize("bad_limit", [0, -1])
async def test_get_player_leaderboards_rejects_non_positive_limit(
    nwsl_service: NWSLService,
    mock_discovery: AsyncMock,
    bad_limit: int,
) -> None:
    with pytest.raises(ValueError, match="positive"):
        await nwsl_service.get_player_leaderboards(limit=bad_limit)
    mock_discovery.get_seasons.assert_not_called()


async def test_get_award_articles_filters_by_title_keywords(
    nwsl_service: NWSLService,
    mock_cms: AsyncMock,
    sample_award_article: CMSArticle,
    sample_news_article: CMSArticle,
) -> None:
    mock_cms.get_recent_stories.return_value = [sample_news_article, sample_award_article]
    result = await nwsl_service.get_award_articles(limit=5)
    assert result == [sample_award_article]


async def test_get_award_articles_caps_at_limit(
    nwsl_service: NWSLService,
    mock_cms: AsyncMock,
    sample_award_article: CMSArticle,
) -> None:
    mock_cms.get_recent_stories.return_value = [sample_award_article] * 20
    result = await nwsl_service.get_award_articles(limit=3)
    assert len(result) == 3


async def test_get_award_articles_matches_player_of_the_month(
    nwsl_service: NWSLService,
    mock_cms: AsyncMock,
) -> None:
    article = CMSArticle(
        slug="potm",
        title="Sveindis Jonsdottir Named NWSL Player of the Month",
        summary="",
        published="",
        link="",
    )
    mock_cms.get_recent_stories.return_value = [article]
    result = await nwsl_service.get_award_articles()
    assert result == [article]


@pytest.mark.parametrize("bad_limit", [0, -1])
async def test_get_award_articles_rejects_non_positive_limit(
    nwsl_service: NWSLService,
    mock_cms: AsyncMock,
    bad_limit: int,
) -> None:
    with pytest.raises(ValueError, match="positive"):
        await nwsl_service.get_award_articles(limit=bad_limit)
    mock_cms.get_recent_stories.assert_not_called()


async def test_get_challenge_cup_standings_resolves_competition(
    nwsl_service: NWSLService,
    mock_sdp: AsyncMock,
    mock_discovery: AsyncMock,
) -> None:
    rs = Season(id="rs-2026", year=2026, name="Regular Season 2026", competition="Regular Season")
    cc = Season(id="cc-2026", year=2026, name="Challenge Cup 2026", competition="Challenge Cup")
    mock_discovery.get_seasons.return_value = [rs, cc]
    mock_sdp.get_standings_for_season.return_value = []

    await nwsl_service.get_challenge_cup_standings(season_year=2026)

    # Must use the Challenge Cup ID, not the Regular Season ID.
    mock_sdp.get_standings_for_season.assert_called_once_with("cc-2026")


async def test_get_challenge_cup_standings_defaults_to_most_recent(
    nwsl_service: NWSLService,
    mock_sdp: AsyncMock,
    mock_discovery: AsyncMock,
) -> None:
    cc_2024 = Season(id="cc-2024", year=2024, name="Challenge Cup 2024", competition="Challenge Cup")
    cc_2026 = Season(id="cc-2026", year=2026, name="Challenge Cup 2026", competition="Challenge Cup")
    mock_discovery.get_seasons.return_value = [cc_2024, cc_2026]
    mock_sdp.get_standings_for_season.return_value = []

    await nwsl_service.get_challenge_cup_standings()

    mock_sdp.get_standings_for_season.assert_called_once_with("cc-2026")


async def test_get_historical_standings_resolves_year_and_calls_sdp(
    nwsl_service: NWSLService,
    mock_sdp: AsyncMock,
    mock_discovery: AsyncMock,
) -> None:
    season_2018 = Season(id="s-2018", year=2018, name="Regular Season 2018", competition="Regular Season")
    standing = SeasonStanding(
        rank=1,
        team_id="t1",
        team_name="North Carolina Courage",
        points=57,
        matches_played=24,
        wins=17,
        draws=6,
        losses=1,
        goals_for=53,
        goals_against=18,
        goal_difference=35,
        team_abbreviation="NCC",
    )
    mock_discovery.get_seasons.return_value = [season_2018]
    mock_sdp.get_standings_for_season.return_value = [standing]

    result = await nwsl_service.get_historical_standings(season_year=2018)

    mock_sdp.get_standings_for_season.assert_called_once_with("s-2018")
    assert result == [standing]


async def test_get_historical_standings_raises_when_year_missing(
    nwsl_service: NWSLService,
    mock_discovery: AsyncMock,
    sample_season: Season,
) -> None:
    mock_discovery.get_seasons.return_value = [sample_season]
    with pytest.raises(NWSLNotFoundError, match="2050"):
        await nwsl_service.get_historical_standings(season_year=2050)


async def test_get_team_season_stats_resolves_year_and_calls_sdp(
    nwsl_service: NWSLService,
    mock_sdp: AsyncMock,
    mock_discovery: AsyncMock,
    sample_season: Season,
) -> None:
    team_stat = TeamSeasonStat(team_id="t1", name="Angel City", stats={"total-points": 9.0})
    mock_discovery.get_seasons.return_value = [sample_season]
    mock_sdp.get_team_stats.return_value = [team_stat]

    result = await nwsl_service.get_team_season_stats(season_year=2026, sort_by="goals", limit=16)

    mock_sdp.get_team_stats.assert_called_once_with(sample_season.id, "goals", 16)
    assert result == [team_stat]


@pytest.mark.parametrize("bad_limit", [0, -5])
async def test_get_team_season_stats_rejects_non_positive_limit(
    nwsl_service: NWSLService,
    mock_discovery: AsyncMock,
    bad_limit: int,
) -> None:
    with pytest.raises(ValueError, match="positive"):
        await nwsl_service.get_team_season_stats(limit=bad_limit)
    mock_discovery.get_seasons.assert_not_called()


async def test_get_standings_delegates_to_repo(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    sample_standing: Standing,
) -> None:
    mock_repo.get_standings.return_value = [sample_standing]
    result = await nwsl_service.get_standings()
    mock_repo.get_standings.assert_called_once()
    assert result == [sample_standing]


# ---------------------------------------------------------------------------
# Schedule-strength analytics — shared scaffolding
# ---------------------------------------------------------------------------


def _team(team_id: str, name: str, abbr: str) -> Team:
    """Build a minimal Team for analytics fixtures."""
    return Team(id=team_id, name=name, abbreviation=abbr, location=name, display_name=name)


def _standing(team: Team, w: int, l_: int, t: int, gf: int = 0, ga: int = 0) -> Standing:
    """Build a Standing row from W-L-T (points and GD derived)."""
    return Standing(
        team=team,
        wins=w,
        losses=l_,
        ties=t,
        points=3 * w + t,
        goals_for=gf,
        goals_against=ga,
        goal_difference=gf - ga,
    )


def _played(match_id: str, home: Team, away: Team, home_score: str, away_score: str) -> Match:
    """Build a completed Match (status_type='post') with declared winner."""
    home_won = int(home_score) > int(away_score)
    away_won = int(away_score) > int(home_score)
    return Match(
        id=match_id,
        date="2026-04-01T20:00Z",
        name=f"{away.display_name} at {home.display_name}",
        short_name=f"{away.abbreviation} @ {home.abbreviation}",
        status_type="post",
        status_detail="FT",
        competitors=[
            MatchCompetitor(team=home, home_away="home", score=home_score, winner=home_won),
            MatchCompetitor(team=away, home_away="away", score=away_score, winner=away_won),
        ],
    )


def _scheduled(match_id: str, home: Team, away: Team) -> Match:
    """Build an unplayed Match (status_type='pre') with no scores."""
    return Match(
        id=match_id,
        date="2026-05-01T20:00Z",
        name=f"{away.display_name} at {home.display_name}",
        short_name=f"{away.abbreviation} @ {home.abbreviation}",
        status_type="pre",
        status_detail="Scheduled",
        competitors=[
            MatchCompetitor(team=home, home_away="home"),
            MatchCompetitor(team=away, home_away="away"),
        ],
    )


# ---------------------------------------------------------------------------
# get_strength_of_schedule
# ---------------------------------------------------------------------------


async def test_get_strength_of_schedule_averages_played_opponents_ppg(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    sd = _team("sd", "San Diego Wave", "SD")
    por = _team("1899", "Portland Thorns", "POR")
    sea = _team("sea", "Seattle Reign", "SEA")
    chi = _team("chi", "Chicago Stars", "CHI")
    # 5 matches each — PPG: SD 12/5=2.4, POR 10/5=2.0, SEA 10/5=2.0, CHI 3/5=0.6
    mock_repo.get_standings.return_value = [
        _standing(sd, w=4, l_=1, t=0),
        _standing(por, w=3, l_=1, t=1),
        _standing(sea, w=3, l_=1, t=1),
        _standing(chi, w=1, l_=4, t=0),
    ]
    # Portland has played 3 of 4 opponents
    mock_repo.get_team_schedule.return_value = [
        _played("m1", home=sd, away=por, home_score="3", away_score="1"),
        _played("m2", home=por, away=sea, home_score="2", away_score="0"),
        _played("m3", home=por, away=chi, home_score="2", away_score="0"),
        _scheduled("m4", home=por, away=sd),
    ]

    result = await nwsl_service.get_strength_of_schedule("1899")

    assert isinstance(result, StrengthOfSchedule)
    assert result.team == por
    assert result.matches_played == 3
    assert {o.team.id for o in result.opponents} == {"sd", "sea", "chi"}
    assert result.average_opponent_ppg == pytest.approx((2.4 + 2.0 + 0.6) / 3)


async def test_get_strength_of_schedule_returns_zero_when_no_matches_played(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    por = _team("1899", "Portland Thorns", "POR")
    sd = _team("sd", "San Diego Wave", "SD")
    mock_repo.get_standings.return_value = [_standing(por, 0, 0, 0), _standing(sd, 0, 0, 0)]
    mock_repo.get_team_schedule.return_value = [_scheduled("m1", home=por, away=sd)]

    result = await nwsl_service.get_strength_of_schedule("1899")

    assert result.matches_played == 0
    assert result.opponents == []
    assert result.average_opponent_ppg == 0.0


async def test_get_strength_of_schedule_rejects_empty_team_id(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        await nwsl_service.get_strength_of_schedule("  ")
    mock_repo.get_standings.assert_not_called()


async def test_get_strength_of_schedule_skips_opponents_missing_from_standings(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    """An opponent that's in the schedule but absent from the live standings is skipped.

    Happens during expansion-team weeks or if the standings response lags the
    fixture data. The played match against the unranked team should not be
    included in the SoS aggregate.
    """
    sd = _team("sd", "San Diego", "SD")
    por = _team("1899", "Portland", "POR")
    ghost = _team("ghost", "New Expansion", "NEW")
    # `ghost` is absent from standings entirely.
    mock_repo.get_standings.return_value = [
        _standing(sd, w=4, l_=1, t=0),
        _standing(por, w=3, l_=1, t=1),
    ]
    mock_repo.get_team_schedule.return_value = [
        _played("m1", home=sd, away=por, home_score="3", away_score="1"),
        _played("m2", home=por, away=ghost, home_score="2", away_score="0"),
    ]

    result = await nwsl_service.get_strength_of_schedule("1899")

    # Only SD counts toward the average; ghost is silently skipped.
    assert {o.team.id for o in result.opponents} == {"sd"}
    assert result.matches_played == 1
    assert result.average_opponent_ppg == pytest.approx(12 / 5)


# ---------------------------------------------------------------------------
# get_results_by_opponent_tier
# ---------------------------------------------------------------------------


async def test_get_results_by_opponent_tier_splits_by_current_standings(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    # 6-team league. Por sits in the middle and has played one team in each tier.
    sd = _team("sd", "San Diego", "SD")
    sea = _team("sea", "Seattle", "SEA")
    por = _team("1899", "Portland", "POR")
    nc = _team("nc", "North Carolina", "NC")
    chi = _team("chi", "Chicago", "CHI")
    bos = _team("bos", "Boston", "BOS")
    # Standings order: SD, SEA, POR, NC, CHI, BOS  (rank 1..6)
    mock_repo.get_standings.return_value = [
        _standing(sd, w=4, l_=0, t=0),
        _standing(sea, w=3, l_=1, t=0),
        _standing(por, w=2, l_=2, t=0),
        _standing(nc, w=2, l_=2, t=0),
        _standing(chi, w=1, l_=3, t=0),
        _standing(bos, w=0, l_=4, t=0),
    ]
    # POR: lost to SD (top tier), tied NC (middle), beat BOS (bottom)
    mock_repo.get_team_schedule.return_value = [
        _played("m1", home=sd, away=por, home_score="2", away_score="0"),
        _played("m2", home=por, away=nc, home_score="1", away_score="1"),
        _played("m3", home=por, away=bos, home_score="3", away_score="0"),
        _scheduled("m4", home=por, away=chi),
    ]

    result = await nwsl_service.get_results_by_opponent_tier("1899", tier_size=2)

    assert isinstance(result, ResultsByOpponentTier)
    assert result.tier_size == 2
    by_label = {t.label: t for t in result.tiers}
    assert by_label["Top 2"].wins == 0
    assert by_label["Top 2"].losses == 1
    assert by_label["Top 2"].ties == 0
    assert by_label["Middle 2"].wins == 0
    assert by_label["Middle 2"].losses == 0
    assert by_label["Middle 2"].ties == 1  # Drew NC, who is rank 4 (middle)
    assert by_label["Bottom 2"].wins == 1
    assert by_label["Bottom 2"].losses == 0
    assert by_label["Bottom 2"].ties == 0


@pytest.mark.parametrize("bad_size", [0, -1, 4])
async def test_get_results_by_opponent_tier_rejects_invalid_tier_size(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    bad_size: int,
) -> None:
    # 6-team league means valid tier_size is 1..3 (2*tier_size <= league_size).
    teams = [_team(f"t{i}", f"Team {i}", f"T{i}") for i in range(6)]
    mock_repo.get_standings.return_value = [_standing(t, w=0, l_=0, t=0) for t in teams]
    mock_repo.get_team_schedule.return_value = []

    with pytest.raises(ValueError, match="tier_size"):
        await nwsl_service.get_results_by_opponent_tier("t0", tier_size=bad_size)


async def test_get_results_by_opponent_tier_rejects_empty_team_id(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        await nwsl_service.get_results_by_opponent_tier("", tier_size=2)
    mock_repo.get_standings.assert_not_called()


async def test_get_results_by_opponent_tier_accepts_max_tier_size(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    """At tier_size = league_size // 2, the middle tier is empty and gets filtered out."""
    teams = [_team(f"t{i}", f"Team {i}", f"T{i}") for i in range(6)]
    mock_repo.get_standings.return_value = [_standing(t, w=0, l_=0, t=0) for t in teams]
    mock_repo.get_team_schedule.return_value = []

    result = await nwsl_service.get_results_by_opponent_tier("t0", tier_size=3)

    # 6-team league, tier_size 3 -> Top 3 (1-3) + Bottom 3 (4-6); no middle.
    labels = [tier.label for tier in result.tiers]
    assert labels == ["Top 3", "Bottom 3"]


# ---------------------------------------------------------------------------
# get_adjusted_points_per_game
# ---------------------------------------------------------------------------


async def test_get_adjusted_points_per_game_scales_by_opponent_quality(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    sd = _team("sd", "San Diego", "SD")
    por = _team("1899", "Portland", "POR")
    sea = _team("sea", "Seattle", "SEA")
    chi = _team("chi", "Chicago", "CHI")
    # 5 matches each — total = 35 pts / 20 matches = 1.75 league avg PPG
    mock_repo.get_standings.return_value = [
        _standing(sd, w=4, l_=1, t=0),  # 12 pts → 2.4 PPG
        _standing(por, w=3, l_=1, t=1),  # 10 pts → 2.0 PPG
        _standing(sea, w=3, l_=1, t=1),  # 10 pts → 2.0 PPG
        _standing(chi, w=1, l_=4, t=0),  # 3 pts → 0.6 PPG
    ]
    # Portland's played opponents: SD, SEA, CHI → avg opp PPG = (2.4+2.0+0.6)/3 ≈ 1.667
    mock_repo.get_team_schedule.return_value = [
        _played("m1", home=sd, away=por, home_score="3", away_score="1"),
        _played("m2", home=por, away=sea, home_score="2", away_score="0"),
        _played("m3", home=por, away=chi, home_score="2", away_score="0"),
    ]

    result = await nwsl_service.get_adjusted_points_per_game("1899")

    assert isinstance(result, AdjustedPointsPerGame)
    assert result.team == por
    assert result.matches_played == 5
    assert result.points == 10
    assert result.raw_ppg == pytest.approx(2.0)
    expected_avg_opp = (2.4 + 2.0 + 0.6) / 3
    assert result.average_opponent_ppg == pytest.approx(expected_avg_opp)
    assert result.league_average_ppg == pytest.approx(35 / 20)
    assert result.adjusted_ppg == pytest.approx(2.0 * (expected_avg_opp / (35 / 20)))


async def test_get_adjusted_points_per_game_handles_zero_league_average(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    por = _team("1899", "Portland", "POR")
    sd = _team("sd", "San Diego", "SD")
    mock_repo.get_standings.return_value = [_standing(por, 0, 0, 0), _standing(sd, 0, 0, 0)]
    mock_repo.get_team_schedule.return_value = []

    result = await nwsl_service.get_adjusted_points_per_game("1899")

    assert result.raw_ppg == 0.0
    assert result.adjusted_ppg == 0.0
    assert result.league_average_ppg == 0.0


async def test_get_adjusted_points_per_game_rejects_empty_team_id(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        await nwsl_service.get_adjusted_points_per_game("")
    mock_repo.get_standings.assert_not_called()
