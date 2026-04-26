"""ESPN-backed MCP tools — teams, scoreboard, roster, news, standings, etc."""

import logging

from mcp.server.fastmcp import FastMCP

from ....application.service import NWSLService
from ..formatters import (
    _fmt_match_details,
    _fmt_news,
    _fmt_roster,
    _fmt_scoreboard,
    _fmt_standings,
    _fmt_team,
    _fmt_team_schedule,
    _fmt_teams,
)
from ._base import _READ_ANNOTATIONS, _safe_call

logger = logging.getLogger(__name__)


def register_espn_tools(mcp: FastMCP, service: NWSLService) -> None:
    """Register the eight ESPN-backed read-only tools on `mcp`."""

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_teams() -> str:
        """Get all active NWSL teams.

        Returns a numbered list of teams with their ID, full name, abbreviation,
        and home city. Use the ID or abbreviation with get_team to retrieve
        detailed information about a specific team.
        """
        logger.info("tool=get_teams")
        return await _safe_call(service.get_teams(), _fmt_teams)

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_team(team_id: str) -> str:
        """Get details for a specific NWSL team.

        Returns full team information including display name, abbreviation, and
        location. Use the numeric ID returned by get_teams.

        Args:
            team_id: ESPN numeric team ID (e.g. "1899" for Portland Thorns).
        """
        logger.info("tool=get_team team_id=%r", team_id)
        return await _safe_call(service.get_team(team_id), _fmt_team)

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_scoreboard(date: str | None = None, end_date: str | None = None) -> str:
        """Get NWSL match scores and status for a date or date range.

        With no arguments, returns matches for the current matchweek. With
        `date` only, returns matches for that single day. With both `date`
        and `end_date`, returns every match in the inclusive range.

        Args:
            date: Optional start date in YYYYMMDD format (e.g. "20260418").
            end_date: Optional end date in YYYYMMDD format. Requires `date`.
        """
        logger.info("tool=get_scoreboard date=%r end_date=%r", date, end_date)
        return await _safe_call(service.get_scoreboard(date, end_date), _fmt_scoreboard)

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_roster(team_id: str) -> str:
        """Get the active roster for an NWSL team.

        Returns each player's jersey number, name, position, citizenship,
        and age. Use the team ID returned by get_teams.

        Args:
            team_id: ESPN numeric team ID (e.g. "15362" for Portland Thorns).
        """
        logger.info("tool=get_roster team_id=%r", team_id)
        return await _safe_call(service.get_roster(team_id), _fmt_roster)

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_match_details(match_id: str) -> str:
        """Get detailed information for a single NWSL match.

        Returns the score, venue, attendance, and a chronological list of key
        events (goals, substitutions, cards). Use the match ID returned by
        get_scoreboard or get_team_schedule.

        Args:
            match_id: ESPN numeric event ID (e.g. "401853883").
        """
        logger.info("tool=get_match_details match_id=%r", match_id)
        return await _safe_call(service.get_match_details(match_id), _fmt_match_details)

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_team_schedule(team_id: str) -> str:
        """Get all matches for a single NWSL team in the current season.

        Returns scheduled, in-progress, and completed matches for the team —
        with opponent, date, score (if played), and status.

        Args:
            team_id: ESPN numeric team ID (e.g. "15362" for Portland Thorns).
        """
        logger.info("tool=get_team_schedule team_id=%r", team_id)
        return await _safe_call(service.get_team_schedule(team_id), _fmt_team_schedule)

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_news(limit: int = 10) -> str:
        """Get recent NWSL news articles.

        Returns each article's headline, publication date, summary, and link
        to the full ESPN story.

        Args:
            limit: Maximum number of articles to return (default 10).
        """
        logger.info("tool=get_news limit=%r", limit)
        return await _safe_call(service.get_news(limit), _fmt_news)

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_standings() -> str:
        """Get the current NWSL league standings.

        Returns teams ordered by points (descending) with win/loss/tie record,
        goals for, goals against, and goal differential.
        """
        logger.info("tool=get_standings")
        return await _safe_call(service.get_standings(), _fmt_standings)
