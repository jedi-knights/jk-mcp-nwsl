"""Unit tests for the MCP inbound adapter formatters and tool handlers.

Tests the formatting functions and safe_call error handling directly,
without spinning up a full MCP server.
"""

from pytest_mock import MockerFixture

from nwsl.adapters.inbound.mcp_adapter import (
    _fmt_scoreboard,
    _fmt_standings,
    _fmt_team,
    _fmt_teams,
    _safe_call,
    create_mcp_server,
)
from nwsl.application.service import NWSLService
from nwsl.domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from nwsl.domain.models import Match, Standing, Team


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
