"""SDPCachingAdapter — TTL-cache decorator for SDPAPIPort.

Mirrors the structure of CachingAdapter (for NWSLAPIPort) but wraps a separate
port type since the SDP API has a different method shape and we want explicit,
type-checkable forwarding rather than a generic `__getattr__` proxy.
"""

import json
import logging
import time
from collections.abc import Callable
from typing import Any

from ...domain.models import PlayerSeasonStat, SeasonStanding, TeamSeasonStat
from ...ports.outbound import SDPAPIPort

logger = logging.getLogger(__name__)


def _cache_key(method: str, kwargs: dict[str, Any]) -> str:
    """Build a deterministic cache key from method name and kwargs."""
    return json.dumps({"method": method, "params": kwargs}, sort_keys=True, default=str)


class SDPCachingAdapter:
    """Decorates an SDPAPIPort with a TTL-based in-memory cache."""

    def __init__(
        self,
        inner: SDPAPIPort,
        ttl_seconds: float = 300.0,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        """Initialize the caching adapter.

        Args:
            inner: The SDPAPIPort implementation to wrap.
            ttl_seconds: Time-to-live for cached entries in seconds.
            now: Callable returning the current monotonic time. Injectable for tests.
        """
        self._inner = inner
        self._ttl = ttl_seconds
        self._now = now
        self._cache: dict[str, tuple[float, Any]] = {}

    async def _get_or_fetch(self, method_name: str, **kwargs: Any) -> Any:
        """Return a cached result or fetch from the inner adapter."""
        key = _cache_key(method_name, kwargs)
        entry = self._cache.get(key)
        if entry is not None:
            expiry, result = entry
            if self._now() < expiry:
                logger.debug("Cache hit for %s", method_name)
                return result
            del self._cache[key]

        logger.debug("Cache miss for %s, fetching from inner adapter", method_name)
        method = getattr(self._inner, method_name)
        result = await method(**kwargs)
        self._cache[key] = (self._now() + self._ttl, result)
        return result

    async def get_player_stats(self, season_id: str, order_by: str, limit: int) -> list[PlayerSeasonStat]:
        return await self._get_or_fetch("get_player_stats", season_id=season_id, order_by=order_by, limit=limit)

    async def get_team_stats(self, season_id: str, order_by: str, limit: int) -> list[TeamSeasonStat]:
        return await self._get_or_fetch("get_team_stats", season_id=season_id, order_by=order_by, limit=limit)

    async def get_standings_for_season(self, season_id: str) -> list[SeasonStanding]:
        return await self._get_or_fetch("get_standings_for_season", season_id=season_id)
