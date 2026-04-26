"""Tests for the SDP caching and retry wrappers.

The SDP-specific wrappers mirror the structure of CachingAdapter and
RetryingAdapter for the ESPN-backed port — separate classes because the two
ports have different method shapes and we want type-safe forwarding.
"""

from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from nwsl.adapters.outbound.sdp_caching_adapter import SDPCachingAdapter
from nwsl.adapters.outbound.sdp_retry_adapter import SDPRetryingAdapter
from nwsl.domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from nwsl.domain.models import PlayerSeasonStat, TeamSeasonStat
from nwsl.ports.outbound import SDPAPIPort


@pytest.fixture
def mock_inner(mocker: MockerFixture) -> AsyncMock:
    return mocker.AsyncMock(spec=SDPAPIPort)


@pytest.fixture
def sample_player_stat() -> PlayerSeasonStat:
    return PlayerSeasonStat(
        player_id="nwsl::Football_Player::aaa",
        name="Barbra Banda",
        team="Orlando Pride",
        role="Forward",
        nationality="Zambia",
        stats={"goals": 5.0, "assists": 1.0},
    )


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------


def _stub_clock(state: list[float]):
    def _now() -> float:
        return state[0]

    return _now


async def test_caching_hit_skips_inner_call(
    mock_inner: AsyncMock,
    sample_player_stat: PlayerSeasonStat,
) -> None:
    clock = [0.0]
    adapter = SDPCachingAdapter(mock_inner, ttl_seconds=60.0, now=_stub_clock(clock))
    mock_inner.get_player_stats.return_value = [sample_player_stat]

    await adapter.get_player_stats("season-1", "goals", 10)
    await adapter.get_player_stats("season-1", "goals", 10)

    mock_inner.get_player_stats.assert_called_once_with(season_id="season-1", order_by="goals", limit=10)


async def test_caching_miss_after_ttl_expiry(
    mock_inner: AsyncMock,
    sample_player_stat: PlayerSeasonStat,
) -> None:
    clock = [0.0]
    adapter = SDPCachingAdapter(mock_inner, ttl_seconds=30.0, now=_stub_clock(clock))
    mock_inner.get_player_stats.return_value = [sample_player_stat]

    await adapter.get_player_stats("season-1", "goals", 10)
    clock[0] = 31.0
    await adapter.get_player_stats("season-1", "goals", 10)

    assert mock_inner.get_player_stats.call_count == 2


async def test_caching_separates_by_args(
    mock_inner: AsyncMock,
    sample_player_stat: PlayerSeasonStat,
) -> None:
    """Different (season_id, order_by, limit) tuples must not share a cache slot."""
    clock = [0.0]
    adapter = SDPCachingAdapter(mock_inner, ttl_seconds=300.0, now=_stub_clock(clock))
    mock_inner.get_player_stats.return_value = [sample_player_stat]

    await adapter.get_player_stats("season-1", "goals", 10)
    await adapter.get_player_stats("season-1", "assists", 10)
    await adapter.get_player_stats("season-2", "goals", 10)

    assert mock_inner.get_player_stats.call_count == 3


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------


async def _no_sleep(_: float) -> None:
    pass


async def test_retry_succeeds_on_first_attempt(
    mock_inner: AsyncMock,
    sample_player_stat: PlayerSeasonStat,
) -> None:
    adapter = SDPRetryingAdapter(mock_inner, sleep=_no_sleep)
    mock_inner.get_player_stats.return_value = [sample_player_stat]

    result = await adapter.get_player_stats("season-1", "goals", 10)

    assert result == [sample_player_stat]
    mock_inner.get_player_stats.assert_called_once()


async def test_retry_recovers_from_transient_error(
    mock_inner: AsyncMock,
    sample_player_stat: PlayerSeasonStat,
) -> None:
    adapter = SDPRetryingAdapter(mock_inner, max_attempts=3, sleep=_no_sleep)
    mock_inner.get_player_stats.side_effect = [UpstreamAPIError("503"), [sample_player_stat]]

    result = await adapter.get_player_stats("season-1", "goals", 10)

    assert result == [sample_player_stat]
    assert mock_inner.get_player_stats.call_count == 2


async def test_caching_get_team_stats(mock_inner: AsyncMock) -> None:
    clock = [0.0]
    adapter = SDPCachingAdapter(mock_inner, ttl_seconds=60.0, now=_stub_clock(clock))
    team = TeamSeasonStat(team_id="t1", name="Angel City", stats={"total-points": 9.0})
    mock_inner.get_team_stats.return_value = [team]

    await adapter.get_team_stats("s", "total-points", 16)
    await adapter.get_team_stats("s", "total-points", 16)

    mock_inner.get_team_stats.assert_called_once_with(season_id="s", order_by="total-points", limit=16)


async def test_retry_get_team_stats(mock_inner: AsyncMock) -> None:
    adapter = SDPRetryingAdapter(mock_inner, max_attempts=3, sleep=_no_sleep)
    team = TeamSeasonStat(team_id="t1", name="Angel City", stats={})
    mock_inner.get_team_stats.side_effect = [UpstreamAPIError("503"), [team]]

    result = await adapter.get_team_stats("s", "goals", 16)

    assert result == [team]
    assert mock_inner.get_team_stats.call_count == 2


async def test_retry_does_not_retry_not_found(
    mock_inner: AsyncMock,
) -> None:
    adapter = SDPRetryingAdapter(mock_inner, max_attempts=3, sleep=_no_sleep)
    mock_inner.get_player_stats.side_effect = NWSLNotFoundError("missing")

    with pytest.raises(NWSLNotFoundError):
        await adapter.get_player_stats("season-1", "goals", 10)
    mock_inner.get_player_stats.assert_called_once()
