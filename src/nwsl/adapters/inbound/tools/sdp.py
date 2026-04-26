"""SDP/Opta-backed MCP tools — leaderboards, season aggregates, historical standings."""

import logging
from functools import partial

from mcp.server.fastmcp import FastMCP

from ....application.service import NWSLService
from ..formatters import (
    _fmt_challenge_cup_standings,
    _fmt_historical_standings,
    _fmt_player_leaderboards,
    _fmt_team_season_stats,
)
from ._base import _READ_ANNOTATIONS, _safe_call

logger = logging.getLogger(__name__)


def register_sdp_tools(mcp: FastMCP, service: NWSLService) -> None:
    """Register the four SDP/Opta-backed tools on `mcp`."""

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_player_leaderboards(
        season_year: int | None = None,
        sort_by: str = "goals",
        limit: int = 20,
    ) -> str:
        """Get top NWSL players for a season, ranked by a chosen stat.

        Sourced from the unofficial SDP/Opta data feed (richer than ESPN).
        Common sort_by values: "goals", "assists", "minutes-played", "saves",
        "tackles-won", "Xg", "goal-involvements".

        Args:
            season_year: Calendar year (e.g. 2026). Omit for the most recent season.
            sort_by: SDP stat ID to rank by. Defaults to "goals".
            limit: Number of players to return. Defaults to 20.
        """
        logger.info("tool=get_player_leaderboards year=%r sort=%r limit=%r", season_year, sort_by, limit)
        return await _safe_call(
            service.get_player_leaderboards(season_year, sort_by, limit),
            partial(_fmt_player_leaderboards, sort_by=sort_by),
        )

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_team_season_stats(
        season_year: int | None = None,
        sort_by: str = "total-points",
        limit: int = 20,
    ) -> str:
        """Get NWSL team season aggregates ranked by a chosen stat.

        Sourced from the SDP/Opta data feed. Common sort_by values:
        "total-points", "goals", "goals-against", "passes-accuracy",
        "total-wins", "Xg".

        Args:
            season_year: Calendar year. Omit for the most recent season.
            sort_by: SDP stat ID to rank by. Defaults to "total-points".
            limit: Number of teams to return. Defaults to 20.
        """
        logger.info("tool=get_team_season_stats year=%r sort=%r limit=%r", season_year, sort_by, limit)
        return await _safe_call(
            service.get_team_season_stats(season_year, sort_by, limit),
            partial(_fmt_team_season_stats, sort_by=sort_by),
        )

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_historical_standings(season_year: int) -> str:
        """Get final or in-progress NWSL standings for any year from 2016 onward.

        Sourced from the SDP/Opta data feed via discovery — covers every
        season the public site advertises (currently 2016-2026, no 2020 due
        to the cancelled regular season).

        Args:
            season_year: Calendar year (e.g. 2018, 2024).
        """
        logger.info("tool=get_historical_standings year=%r", season_year)
        return await _safe_call(
            service.get_historical_standings(season_year),
            partial(_fmt_historical_standings, year=season_year),
        )

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_challenge_cup_standings(season_year: int | None = None) -> str:
        """Get NWSL Challenge Cup standings (separate competition from the Regular Season).

        Sourced from the SDP/Opta data feed. Available years: 2020 through
        the current year. Note: modern (2024+) Challenge Cups are single-match
        formats with no standings table — this tool will return an empty
        result for those years.

        Args:
            season_year: Calendar year. Omit for the most recent Challenge Cup.
        """
        logger.info("tool=get_challenge_cup_standings year=%r", season_year)
        return await _safe_call(
            service.get_challenge_cup_standings(season_year),
            partial(_fmt_challenge_cup_standings, year=season_year),
        )
