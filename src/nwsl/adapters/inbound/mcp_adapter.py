"""Inbound adapter — exposes the application service as MCP tools.

FastMCP generates tool schemas from Python type hints and docstrings. The LLM
sees the docstring as the tool description and uses the type hints to know what
arguments to pass. Keep docstrings precise: they are the LLM's primary guide.

Logging note (STDIO transport): NEVER use print() here. It writes to stdout and
corrupts the JSON-RPC stream. Use the standard logging module instead — it
writes to stderr when configured via server.py.
"""

import logging
from collections.abc import Awaitable, Callable

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...application.service import NWSLService
from ...domain.exceptions import NWSLNotFoundError, UpstreamAPIError
from ...domain.models import Match, MatchCompetitor, Standing, Team

logger = logging.getLogger(__name__)

_READ_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
"""Annotation for tools that make read-only, idempotent calls to the upstream ESPN API."""


async def _safe_call[T](coro: Awaitable[T], fmt: Callable[[T], str]) -> str:
    """Await coro, apply fmt to the result, and convert domain exceptions to error strings.

    Prevents NWSLNotFoundError, UpstreamAPIError, and ValueError from propagating
    to the MCP layer as unhandled exceptions. The LLM receives a readable error message.

    Args:
        coro: An awaitable that returns the raw domain result.
        fmt: A callable that converts the domain result to a formatted string.

    Returns:
        The formatted string, or an error message if a domain exception was raised.
    """
    try:
        return fmt(await coro)
    except NWSLNotFoundError as exc:
        logger.warning("Not found: %s", exc)
        return f"Not found: {exc}"
    except UpstreamAPIError as exc:
        logger.error("Upstream API error: %s", exc)
        return f"Upstream error: {exc}"
    except ValueError as exc:
        logger.warning("Invalid request: %s", exc)
        return f"Invalid request: {exc}"


# ---------------------------------------------------------------------------
# Formatters — turn domain models into readable text for the LLM
# ---------------------------------------------------------------------------


def _fmt_team(team: Team) -> str:
    """Format a single Team as a labeled key-value block."""
    lines = [
        f"ID: {team.id}",
        f"Name: {team.display_name}",
        f"Abbreviation: {team.abbreviation}",
        f"Location: {team.location}",
    ]
    if team.logo_url:
        lines.append(f"Logo: {team.logo_url}")
    return "\n".join(lines)


def _fmt_teams(teams: list[Team]) -> str:
    """Format a list of teams as a numbered list."""
    if not teams:
        return "No teams found."
    entries = [f"{i}. {t.display_name} ({t.abbreviation}) — ID: {t.id}" for i, t in enumerate(teams, 1)]
    return "\n".join(entries)


def _fmt_competitor(comp: MatchCompetitor) -> str:
    """Format one side of a match: team name, score, and home/away label."""
    score_str = f" {comp.score}" if comp.score is not None else ""
    winner_str = " ✓" if comp.winner else ""
    return f"{comp.team.display_name}{score_str}{winner_str} ({comp.home_away})"


def _fmt_match(match: Match) -> str:
    """Format a single Match as a readable summary."""
    competitor_lines = "\n  ".join(_fmt_competitor(c) for c in match.competitors)
    return (
        f"Match: {match.name}\n"
        f"  Date: {match.date}\n"
        f"  Status: {match.status_detail}\n"
        f"  Competitors:\n  {competitor_lines}"
    )


def _fmt_scoreboard(matches: list[Match]) -> str:
    """Format a list of matches for the scoreboard tool."""
    if not matches:
        return "No matches found for the requested date."
    return "\n\n".join(_fmt_match(m) for m in matches)


def _fmt_standing(i: int, standing: Standing) -> str:
    """Format a single standings row."""
    return (
        f"{i}. {standing.team.display_name} ({standing.team.abbreviation})"
        f" — {standing.points} pts"
        f" | W:{standing.wins} L:{standing.losses} T:{standing.ties}"
        f" | GF:{standing.goals_for} GA:{standing.goals_against} GD:{standing.goal_difference:+d}"
    )


def _fmt_standings(standings: list[Standing]) -> str:
    """Format the full standings table."""
    if not standings:
        return "No standings data available."
    return "\n".join(_fmt_standing(i, s) for i, s in enumerate(standings, 1))


# ---------------------------------------------------------------------------
# Health probe handlers
# ---------------------------------------------------------------------------


async def _handle_livez(request: Request) -> JSONResponse:
    """Liveness probe — returns 200 OK if the HTTP server is up."""
    return JSONResponse({"status": "ok"})


async def _handle_readyz(request: Request) -> JSONResponse:
    """Readiness probe — returns 200 when the server is ready to serve traffic."""
    return JSONResponse({"status": "ok"})


async def _handle_health(request: Request) -> JSONResponse:
    """Aggregate health endpoint for monitoring systems."""
    return JSONResponse({"status": "ok", "checks": {"liveness": "ok", "readiness": "ok"}})


# ---------------------------------------------------------------------------
# MCP server factory
# ---------------------------------------------------------------------------


def create_mcp_server(service: NWSLService, host: str = "0.0.0.0", port: int = 8000) -> FastMCP:
    """Wire the application service into a FastMCP instance and register tools.

    Args:
        service: The NWSLService to expose as MCP tools.
        host: Bind address for HTTP transport (ignored for stdio). Defaults to 0.0.0.0.
        port: TCP port for HTTP transport (ignored for stdio). Defaults to 8000.
    """
    mcp = FastMCP("nwsl", host=host, port=port, stateless_http=True)

    mcp.custom_route("/livez", methods=["GET"])(_handle_livez)
    mcp.custom_route("/readyz", methods=["GET"])(_handle_readyz)
    mcp.custom_route("/health", methods=["GET"])(_handle_health)

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
    async def get_scoreboard(date: str | None = None) -> str:
        """Get NWSL match scores and status.

        Returns scores, match status, and team results for the given date.
        If no date is provided, returns matches for the current matchweek.

        Args:
            date: Optional date in YYYYMMDD format (e.g. "20250601").
                  Omit to get the current matchweek's scores.
        """
        logger.info("tool=get_scoreboard date=%r", date)
        return await _safe_call(service.get_scoreboard(date), _fmt_scoreboard)

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_standings() -> str:
        """Get the current NWSL league standings.

        Returns teams ordered by points (descending) with win/loss/tie record,
        goals for, goals against, and goal differential.
        """
        logger.info("tool=get_standings")
        return await _safe_call(service.get_standings(), _fmt_standings)

    return mcp
