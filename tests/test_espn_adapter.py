"""Unit tests for the ESPNAdapter outbound adapter.

Uses a mock httpx.AsyncClient to avoid real network calls, keeping tests
fast and deterministic.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from nwsl.adapters.outbound.espn_adapter import ESPNAdapter, _parse_match, _parse_standing, _parse_team
from nwsl.domain.exceptions import NWSLNotFoundError, UpstreamAPIError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RAW_TEAM = {
    "id": "1899",
    "name": "Thorns",
    "abbreviation": "POR",
    "location": "Portland",
    "displayName": "Portland Thorns FC",
    "logos": [{"href": "https://a.espncdn.com/i/teamlogos/soccer/500/1899.png"}],
}

_RAW_EVENT = {
    "id": "701123",
    "date": "2025-06-01T20:00Z",
    "name": "Portland Thorns FC vs North Carolina Courage",
    "shortName": "POR vs NCC",
    "competitions": [
        {
            "status": {
                "displayClock": "FT",
                "type": {"name": "post", "description": "Final"},
            },
            "competitors": [
                {
                    "homeAway": "home",
                    "score": "2",
                    "winner": True,
                    "team": _RAW_TEAM,
                    "id": "1899",
                    "name": "Thorns",
                    "abbreviation": "POR",
                    "location": "Portland",
                    "displayName": "Portland Thorns FC",
                    "logos": [{"href": "https://a.espncdn.com/i/teamlogos/soccer/500/1899.png"}],
                },
            ],
        }
    ],
}

_RAW_STANDING_ENTRY = {
    "team": _RAW_TEAM,
    "stats": [
        {"name": "wins", "value": 12},
        {"name": "losses", "value": 4},
        {"name": "ties", "value": 2},
        {"name": "points", "value": 38},
        {"name": "pointsFor", "value": 40},
        {"name": "pointsAgainst", "value": 18},
        {"name": "pointDifferential", "value": 22},
    ],
}


@pytest.fixture
def mock_client() -> AsyncMock:
    """A mock httpx.AsyncClient that returns 200 by default."""
    client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    client.get.return_value = response
    return client


@pytest.fixture
def adapter(mock_client: AsyncMock) -> ESPNAdapter:
    return ESPNAdapter(client=mock_client)


# ---------------------------------------------------------------------------
# Helper parser tests (pure unit — no network)
# ---------------------------------------------------------------------------


def test_parse_team_maps_fields() -> None:
    team = _parse_team(_RAW_TEAM)
    assert team.id == "1899"
    assert team.abbreviation == "POR"
    assert team.logo_url == "https://a.espncdn.com/i/teamlogos/soccer/500/1899.png"


def test_parse_team_no_logos() -> None:
    raw = {**_RAW_TEAM, "logos": []}
    team = _parse_team(raw)
    assert team.logo_url is None


def test_parse_match_maps_fields() -> None:
    match = _parse_match(_RAW_EVENT)
    assert match.id == "701123"
    assert match.status_type == "post"
    assert match.status_detail == "FT"
    assert len(match.competitors) == 1
    assert match.competitors[0].score == "2"
    assert match.competitors[0].winner is True


def test_parse_standing_maps_stats() -> None:
    standing = _parse_standing(_RAW_STANDING_ENTRY)
    assert standing is not None
    assert standing.wins == 12
    assert standing.points == 38
    assert standing.goal_difference == 22


def test_parse_standing_returns_none_without_team() -> None:
    result = _parse_standing({"stats": []})
    assert result is None


# ---------------------------------------------------------------------------
# Adapter method tests (mock httpx client)
# ---------------------------------------------------------------------------


async def test_get_teams_returns_team_list(adapter: ESPNAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"sports": [{"leagues": [{"teams": [{"team": _RAW_TEAM}]}]}]}
    teams = await adapter.get_teams()
    assert len(teams) == 1
    assert teams[0].id == "1899"


async def test_get_team_returns_single_team(adapter: ESPNAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"team": _RAW_TEAM}
    team = await adapter.get_team("1899")
    assert team.display_name == "Portland Thorns FC"


async def test_get_team_raises_not_found_when_missing(adapter: ESPNAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {}
    with pytest.raises(NWSLNotFoundError):
        await adapter.get_team("9999")


async def test_get_scoreboard_returns_matches(adapter: ESPNAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"events": [_RAW_EVENT]}
    matches = await adapter.get_scoreboard("20250601")
    assert len(matches) == 1
    assert matches[0].id == "701123"


async def test_get_scoreboard_without_date(adapter: ESPNAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"events": []}
    matches = await adapter.get_scoreboard(None)
    assert matches == []


async def test_get_standings_returns_sorted_list(adapter: ESPNAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"children": [{"standings": {"entries": [_RAW_STANDING_ENTRY]}}]}
    standings = await adapter.get_standings()
    assert len(standings) == 1
    assert standings[0].points == 38


async def test_get_teams_raises_upstream_error_on_500(
    adapter: ESPNAdapter, mock_client: AsyncMock, mocker: MockerFixture
) -> None:
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 500
    http_error = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)
    mock_client.get.return_value.raise_for_status.side_effect = http_error
    with pytest.raises(UpstreamAPIError):
        await adapter.get_teams()


async def test_get_team_raises_not_found_on_404(
    adapter: ESPNAdapter, mock_client: AsyncMock, mocker: MockerFixture
) -> None:
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 404
    http_error = httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)
    mock_client.get.return_value.raise_for_status.side_effect = http_error
    with pytest.raises(NWSLNotFoundError):
        await adapter.get_team("9999")
