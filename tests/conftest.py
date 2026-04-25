"""Shared fixtures for the NWSL test suite.

These fixtures act as the composition root for testing — they wire together
real domain models and mock/stub implementations of ports, mirroring the
dependency injection pattern used in the production server.py entry point.
"""

from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from nwsl.application.service import NWSLService
from nwsl.domain.models import Match, MatchCompetitor, Standing, Team
from nwsl.ports.outbound import NWSLAPIPort

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
def nwsl_service(mock_repo: AsyncMock) -> NWSLService:
    """NWSLService wired with a mock repo — the primary DI seam for service tests."""
    return NWSLService(repo=mock_repo)
