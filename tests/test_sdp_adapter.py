"""Unit tests for the SDPAdapter outbound adapter.

The SDP adapter calls api-sdp.nwslsoccer.com (Stats Perform / Opta data) and
parses richer per-player and per-team stats than the ESPN-backed adapter.
Tests use a mock httpx.AsyncClient.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from nwsl.adapters.outbound.sdp_adapter import SDPAdapter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RAW_STANDINGS_RESPONSE = {
    "standings": [
        {
            "type": "table",
            "competition": {"officialName": "NWSL"},
            "teams": [
                {
                    "teamId": "nwsl::Football_Team::sd",
                    "officialName": "San Diego Wave",
                    "acronymName": "SD",
                    "stats": [
                        {"statsId": "rank", "statsValue": 1},
                        {"statsId": "points", "statsValue": 13},
                        {"statsId": "matches-played", "statsValue": 6},
                        {"statsId": "win", "statsValue": 4},
                        {"statsId": "draw", "statsValue": 1},
                        {"statsId": "lose", "statsValue": 1},
                        {"statsId": "goals-for", "statsValue": 8},
                        {"statsId": "goals-against", "statsValue": 3},
                    ],
                }
            ],
        },
        {"type": "home", "teams": []},
        {"type": "away", "teams": []},
    ],
}


_RAW_TEAM_STATS_RESPONSE = {
    "teams": [
        {
            "teamId": "nwsl::Football_Team::angelcity",
            "officialName": "Angel City",
            "shortName": "Angel City",
            "stats": [
                {"statsId": "total-points", "statsLabel": "Total points", "statsValue": 9},
                {"statsId": "goals", "statsLabel": "Goals", "statsValue": 10},
                {"statsId": "goals-against", "statsLabel": "Goals against", "statsValue": 4},
            ],
        }
    ],
}


_RAW_PLAYER_STATS_RESPONSE = {
    "players": [
        {
            "playerId": "nwsl::Football_Player::aaa",
            "shortName": "B. Banda",
            "mediaFirstName": "Barbra",
            "mediaLastName": "Banda",
            "role": 4,
            "roleLabel": "Forward",
            "team": {"shortName": "Pride", "officialName": "Orlando Pride"},
            "nationality": "Zambia",
            "stats": [
                {"statsId": "goals", "statsLabel": "Goals", "statsValue": 5},
                {"statsId": "assists", "statsLabel": "Assists", "statsValue": 1},
                {"statsId": "minutes-played", "statsLabel": "Minutes played", "statsValue": 450},
            ],
        }
    ],
    "pagination": {"totalPages": 1, "currentPage": 1, "isLastPage": True},
}


@pytest.fixture
def mock_client() -> AsyncMock:
    """Mock httpx.AsyncClient returning 200 by default."""
    client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    client.get.return_value = response
    return client


@pytest.fixture
def adapter(mock_client: AsyncMock) -> SDPAdapter:
    return SDPAdapter(client=mock_client)


# ---------------------------------------------------------------------------
# get_player_stats
# ---------------------------------------------------------------------------


async def test_get_player_stats_returns_parsed_players(adapter: SDPAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = _RAW_PLAYER_STATS_RESPONSE
    players = await adapter.get_player_stats(
        season_id="nwsl::Football_Season::xyz",
        order_by="goals",
        limit=10,
    )
    assert len(players) == 1
    p = players[0]
    assert p.player_id == "nwsl::Football_Player::aaa"
    assert p.name == "Barbra Banda"
    assert p.team == "Orlando Pride"
    assert p.role == "Forward"
    assert p.nationality == "Zambia"
    assert p.stats["goals"] == 5
    assert p.stats["minutes-played"] == 450


async def test_get_player_stats_url_encodes_season_id(adapter: SDPAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"players": []}
    await adapter.get_player_stats(season_id="nwsl::Football_Season::xyz", order_by="goals", limit=10)
    requested_path = mock_client.get.call_args.args[0]
    # Colons must be percent-encoded in the path segment.
    assert "%3A%3A" in requested_path
    assert "/stats/players" in requested_path


async def test_get_player_stats_passes_query_params(adapter: SDPAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"players": []}
    await adapter.get_player_stats(season_id="nwsl::Football_Season::xyz", order_by="assists", limit=15)
    params = mock_client.get.call_args.kwargs.get("params", {})
    assert params.get("orderBy") == "assists"
    assert params.get("direction") == "desc"
    assert params.get("pageNumElement") == 15
    assert params.get("locale") == "en-US"


async def test_get_player_stats_falls_back_to_short_name_when_media_names_missing(
    adapter: SDPAdapter, mock_client: AsyncMock
) -> None:
    response = {
        "players": [
            {
                "playerId": "x",
                "shortName": "L. LaBonta",
                "mediaFirstName": None,
                "mediaLastName": None,
                "team": {"officialName": "KC Current"},
                "stats": [],
            }
        ]
    }
    mock_client.get.return_value.json.return_value = response
    players = await adapter.get_player_stats(season_id="s", order_by="goals", limit=10)
    assert players[0].name == "L. LaBonta"


async def test_get_standings_for_season_parses_overall_table(adapter: SDPAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = _RAW_STANDINGS_RESPONSE
    standings = await adapter.get_standings_for_season(season_id="nwsl::Football_Season::xyz")
    assert len(standings) == 1
    s = standings[0]
    assert s.rank == 1
    assert s.team_name == "San Diego Wave"
    assert s.team_abbreviation == "SD"
    assert s.points == 13
    assert s.matches_played == 6
    assert s.wins == 4
    assert s.draws == 1
    assert s.losses == 1
    assert s.goals_for == 8
    assert s.goals_against == 3
    assert s.goal_difference == 5


async def test_get_standings_for_season_targets_correct_path(adapter: SDPAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"standings": []}
    await adapter.get_standings_for_season(season_id="s")
    requested_path = mock_client.get.call_args.args[0]
    assert "/standings/overall" in requested_path


async def test_get_standings_for_season_returns_empty_for_modern_challenge_cup(
    adapter: SDPAdapter, mock_client: AsyncMock
) -> None:
    """Modern Challenge Cup (2024+) is a single-match format with no standings.
    The SDP API returns three entries with `type: null` and empty teams.
    The adapter must surface this as an empty list, not crash."""
    response_with_null_types = {
        "standings": [
            {"type": None, "teams": []},
            {"type": None, "teams": []},
            {"type": None, "teams": []},
        ],
    }
    mock_client.get.return_value.json.return_value = response_with_null_types
    standings = await adapter.get_standings_for_season(season_id="cc-2024")
    assert standings == []


async def test_get_standings_for_season_skips_home_away_tables(adapter: SDPAdapter, mock_client: AsyncMock) -> None:
    """Only the type='table' (overall) standings should be returned."""
    mock_client.get.return_value.json.return_value = _RAW_STANDINGS_RESPONSE
    standings = await adapter.get_standings_for_season(season_id="s")
    # The fixture has 1 team in 'table' and 0 in 'home'/'away' — total should be 1.
    assert len(standings) == 1


async def test_get_team_stats_returns_parsed_teams(adapter: SDPAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = _RAW_TEAM_STATS_RESPONSE
    teams = await adapter.get_team_stats(
        season_id="nwsl::Football_Season::xyz",
        order_by="total-points",
        limit=16,
    )
    assert len(teams) == 1
    t = teams[0]
    assert t.team_id == "nwsl::Football_Team::angelcity"
    assert t.name == "Angel City"
    assert t.stats["total-points"] == 9
    assert t.stats["goals"] == 10


async def test_get_team_stats_passes_query_params(adapter: SDPAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"teams": []}
    await adapter.get_team_stats(season_id="s", order_by="goals", limit=5)
    params = mock_client.get.call_args.kwargs.get("params", {})
    assert params.get("orderBy") == "goals"
    assert params.get("direction") == "desc"
    assert params.get("pageNumElement") == 5


async def test_get_player_stats_raises_upstream_error_on_500(
    adapter: SDPAdapter, mock_client: AsyncMock, mocker: MockerFixture
) -> None:
    import httpx

    from nwsl.domain.exceptions import UpstreamAPIError

    mock_response = MagicMock()
    mock_response.status_code = 500
    http_error = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)
    mock_client.get.return_value.raise_for_status.side_effect = http_error
    with pytest.raises(UpstreamAPIError):
        await adapter.get_player_stats(season_id="s", order_by="goals", limit=10)
