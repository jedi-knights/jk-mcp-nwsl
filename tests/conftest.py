"""Shared fixtures for the NWSL test suite.

These fixtures act as the composition root for testing — they wire together
real domain models and mock/stub implementations of ports, mirroring the
dependency injection pattern used in the production server.py entry point.
"""

from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from nwsl.application.service import NWSLService
from nwsl.domain.models import (
    CMSArticle,
    Match,
    MatchCompetitor,
    MatchDetails,
    MatchEvent,
    NewsArticle,
    Player,
    PlayerSeasonStat,
    Season,
    Standing,
    Team,
)
from nwsl.ports.outbound import CMSAPIPort, NWSLAPIPort, SDPAPIPort, SeasonDiscoveryPort

# ---------------------------------------------------------------------------
# Domain model fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def portland_thorns() -> Team:
    """Portland Thorns FC sample team."""
    return Team(
        id="1899",
        name="Thorns",
        abbreviation="POR",
        location="Portland",
        display_name="Portland Thorns FC",
        logo_url="https://a.espncdn.com/i/teamlogos/soccer/500/1899.png",
    )


@pytest.fixture
def north_carolina_courage() -> Team:
    """North Carolina Courage sample team."""
    return Team(
        id="2695",
        name="Courage",
        abbreviation="NCC",
        location="North Carolina",
        display_name="North Carolina Courage",
        logo_url="https://a.espncdn.com/i/teamlogos/soccer/500/2695.png",
    )


@pytest.fixture
def sample_match(portland_thorns: Team, north_carolina_courage: Team) -> Match:
    """A completed match between Portland and North Carolina."""
    return Match(
        id="701123",
        date="2025-06-01T20:00Z",
        name="Portland Thorns FC vs North Carolina Courage",
        short_name="POR vs NCC",
        status_type="post",
        status_detail="FT",
        competitors=[
            MatchCompetitor(team=portland_thorns, home_away="home", score="2", winner=True),
            MatchCompetitor(team=north_carolina_courage, home_away="away", score="1", winner=False),
        ],
    )


@pytest.fixture
def sample_match_details() -> MatchDetails:
    """A completed match with venue, attendance, and key events."""
    return MatchDetails(
        id="401853883",
        date="2026-04-04T22:30Z",
        status_detail="Full Time",
        home_team="North Carolina Courage",
        away_team="Portland Thorns FC",
        home_score="2",
        away_score="2",
        venue="WakeMed Soccer Park",
        venue_city="Cary, North Carolina",
        attendance=7018,
        key_events=[
            MatchEvent(
                clock="12'",
                period=1,
                type="goal---header",
                scoring=True,
                text="Goal! NC 0, POR 1. Reilyn Turner.",
                team_name="Portland Thorns FC",
            ),
        ],
    )


@pytest.fixture
def sample_article() -> NewsArticle:
    """A sample news article."""
    return NewsArticle(
        id="48595550",
        headline="Chicago Stars vs. Boston Legacy FC - Game Highlights",
        description="Watch the Game Highlights from Chicago Stars vs. Boston Legacy FC, 04/26/2026",
        published="2026-04-26T00:48:46Z",
        link="https://www.espn.com/video/clip?id=48595550",
    )


@pytest.fixture
def sample_player() -> Player:
    """A sample roster player."""
    return Player(
        id="219821",
        full_name="Mackenzie Arnold",
        jersey="18",
        position="Goalkeeper",
        position_abbr="G",
        citizenship="Australia",
        age=32,
    )


@pytest.fixture
def sample_standing(portland_thorns: Team) -> Standing:
    """A sample standings entry for Portland Thorns."""
    return Standing(
        team=portland_thorns,
        wins=12,
        losses=4,
        ties=2,
        points=38,
        goals_for=40,
        goals_against=18,
        goal_difference=22,
    )


# ---------------------------------------------------------------------------
# Port mock and service fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repo(mocker: MockerFixture) -> AsyncMock:
    """AsyncMock that satisfies the NWSLAPIPort protocol."""
    return mocker.AsyncMock(spec=NWSLAPIPort)


@pytest.fixture
def mock_sdp(mocker: MockerFixture) -> AsyncMock:
    """AsyncMock that satisfies the SDPAPIPort protocol."""
    return mocker.AsyncMock(spec=SDPAPIPort)


@pytest.fixture
def mock_discovery(mocker: MockerFixture) -> AsyncMock:
    """AsyncMock that satisfies the SeasonDiscoveryPort protocol."""
    return mocker.AsyncMock(spec=SeasonDiscoveryPort)


@pytest.fixture
def mock_cms(mocker: MockerFixture) -> AsyncMock:
    """AsyncMock that satisfies the CMSAPIPort protocol."""
    return mocker.AsyncMock(spec=CMSAPIPort)


@pytest.fixture
def sample_award_article() -> CMSArticle:
    """A sample award-related CMS article."""
    return CMSArticle(
        slug="march-best-xi-2026",
        title="NWSL Announces March Best XI of the Month",
        summary="Best players in March.",
        published="2026-04-01T12:00:00Z",
        link="https://www.nwslsoccer.com/news/march-best-xi-2026",
        tags=["awards", "best-xi"],
    )


@pytest.fixture
def sample_news_article() -> CMSArticle:
    """A sample non-award CMS article."""
    return CMSArticle(
        slug="random-news",
        title="Match recap from Saturday",
        summary="Recap.",
        published="2026-04-02T12:00:00Z",
        link="https://www.nwslsoccer.com/news/random-news",
        tags=[],
    )


@pytest.fixture
def sample_season() -> Season:
    """A sample current-season Season."""
    return Season(
        id="nwsl::Football_Season::current",
        year=2026,
        name="Regular Season 2026",
        competition="Regular Season",
    )


@pytest.fixture
def sample_player_season_stat() -> PlayerSeasonStat:
    """A sample PlayerSeasonStat for the top scorer."""
    return PlayerSeasonStat(
        player_id="nwsl::Football_Player::aaa",
        name="Barbra Banda",
        team="Orlando Pride",
        role="Forward",
        nationality="Zambia",
        stats={"goals": 5.0, "assists": 1.0, "minutes-played": 450.0},
    )


@pytest.fixture
def nwsl_service(
    mock_repo: AsyncMock,
    mock_sdp: AsyncMock,
    mock_discovery: AsyncMock,
    mock_cms: AsyncMock,
) -> NWSLService:
    """NWSLService wired with mock ports — the primary DI seam for service tests."""
    return NWSLService(repo=mock_repo, sdp=mock_sdp, discovery=mock_discovery, cms=mock_cms)
