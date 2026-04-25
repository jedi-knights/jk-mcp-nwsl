"""Unit tests for RetryingAdapter.

Uses a no-op sleep callable so tests run at full speed.
"""

from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from nwsl.adapters.outbound.retry_adapter import RetryingAdapter
from nwsl.domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from nwsl.domain.models import Team
from nwsl.ports.outbound import NWSLAPIPort


@pytest.fixture
def mock_inner(mocker: MockerFixture) -> AsyncMock:
    return mocker.AsyncMock(spec=NWSLAPIPort)


async def _no_sleep(_: float) -> None:
    pass


async def test_success_on_first_attempt(mock_inner: AsyncMock, portland_thorns: Team) -> None:
    adapter = RetryingAdapter(mock_inner, sleep=_no_sleep)
    mock_inner.get_teams.return_value = [portland_thorns]
    result = await adapter.get_teams()
    assert result == [portland_thorns]
    mock_inner.get_teams.assert_called_once()


async def test_retries_on_upstream_error(mock_inner: AsyncMock, portland_thorns: Team) -> None:
    adapter = RetryingAdapter(mock_inner, max_attempts=3, sleep=_no_sleep)
    mock_inner.get_teams.side_effect = [UpstreamAPIError("503"), [portland_thorns]]
    result = await adapter.get_teams()
    assert result == [portland_thorns]
    assert mock_inner.get_teams.call_count == 2


async def test_raises_after_max_attempts(mock_inner: AsyncMock) -> None:
    adapter = RetryingAdapter(mock_inner, max_attempts=2, sleep=_no_sleep)
    mock_inner.get_teams.side_effect = UpstreamAPIError("503")
    with pytest.raises(UpstreamAPIError):
        await adapter.get_teams()
    assert mock_inner.get_teams.call_count == 2


async def test_not_found_is_not_retried(mock_inner: AsyncMock) -> None:
    adapter = RetryingAdapter(mock_inner, max_attempts=3, sleep=_no_sleep)
    mock_inner.get_team.side_effect = NWSLNotFoundError("Team not found: 9999")
    with pytest.raises(NWSLNotFoundError):
        await adapter.get_team("9999")
    mock_inner.get_team.assert_called_once()
