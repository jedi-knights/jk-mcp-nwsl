"""SDPRetryingAdapter — exponential-backoff retry decorator for SDPAPIPort."""

import asyncio
import logging
from collections.abc import Callable

from ...domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from ...domain.models import PlayerSeasonStat, SeasonStanding, TeamSeasonStat
from ...ports.outbound import SDPAPIPort

logger = logging.getLogger(__name__)


class SDPRetryingAdapter:
    """Decorates an SDPAPIPort with exponential-backoff retry on UpstreamAPIError."""

    def __init__(
        self,
        inner: SDPAPIPort,
        max_attempts: int = 3,
        delay_seconds: float = 1.0,
        sleep: Callable[[float], object] = asyncio.sleep,
    ) -> None:
        """Initialize the retry adapter.

        Args:
            inner: The SDPAPIPort implementation to wrap.
            max_attempts: Total number of attempts (minimum 1).
            delay_seconds: Base delay; doubled on each retry.
            sleep: Async callable used to wait between retries. Injectable for tests.
        """
        self._inner = inner
        self._max_attempts = max(1, max_attempts)
        self._delay_seconds = delay_seconds
        self._sleep = sleep

    async def _retry(self, method_name: str, **kwargs: object) -> object:
        """Execute a port method with retry on UpstreamAPIError."""
        method = getattr(self._inner, method_name)
        last_error: UpstreamAPIError | None = None
        for attempt in range(self._max_attempts):
            try:
                return await method(**kwargs)
            except NWSLNotFoundError:
                raise
            except UpstreamAPIError as exc:
                last_error = exc
                if attempt < self._max_attempts - 1:
                    delay = self._delay_seconds * (2**attempt)
                    logger.warning(
                        "Attempt %d/%d failed for %s, retrying in %.1fs: %s",
                        attempt + 1,
                        self._max_attempts,
                        method_name,
                        delay,
                        exc,
                    )
                    await self._sleep(delay)
        raise last_error  # type: ignore[misc]

    async def get_player_stats(self, season_id: str, order_by: str, limit: int) -> list[PlayerSeasonStat]:
        return await self._retry(  # type: ignore[return-value]
            "get_player_stats", season_id=season_id, order_by=order_by, limit=limit
        )

    async def get_team_stats(self, season_id: str, order_by: str, limit: int) -> list[TeamSeasonStat]:
        return await self._retry(  # type: ignore[return-value]
            "get_team_stats", season_id=season_id, order_by=order_by, limit=limit
        )

    async def get_standings_for_season(self, season_id: str) -> list[SeasonStanding]:
        return await self._retry("get_standings_for_season", season_id=season_id)  # type: ignore[return-value]
