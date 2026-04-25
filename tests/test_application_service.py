"""Unit tests for the NWSLService application layer.

Tests verify that the service delegates correctly to the outbound port and
enforces input validation before any port call is made.
"""

from unittest.mock import AsyncMock

import pytest

from nwsl.application.service import NWSLService
from nwsl.domain.models import Match, Standing, Team


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
    mock_repo.get_scoreboard.assert_called_once_with("20250601")
    assert result == [sample_match]


async def test_get_scoreboard_accepts_none_date(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
) -> None:
    mock_repo.get_scoreboard.return_value = []
    await nwsl_service.get_scoreboard(None)
    mock_repo.get_scoreboard.assert_called_once_with(None)


@pytest.mark.parametrize("bad_date", ["2025-06-01", "20250", "ABCDEFGH", "2025060"])
async def test_get_scoreboard_rejects_invalid_date(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    bad_date: str,
) -> None:
    with pytest.raises(ValueError, match="YYYYMMDD"):
        await nwsl_service.get_scoreboard(bad_date)
    mock_repo.get_scoreboard.assert_not_called()


async def test_get_standings_delegates_to_repo(
    nwsl_service: NWSLService,
    mock_repo: AsyncMock,
    sample_standing: Standing,
) -> None:
    mock_repo.get_standings.return_value = [sample_standing]
    result = await nwsl_service.get_standings()
    mock_repo.get_standings.assert_called_once()
    assert result == [sample_standing]
