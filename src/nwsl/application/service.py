"""Application service — the core of the hexagonal architecture.

This layer orchestrates work by delegating to outbound ports. It knows nothing
about MCP, HTTP, or JSON — those are adapter concerns.
"""

from ..domain.models import Match, Standing, Team
from ..ports.outbound import NWSLAPIPort

_DATE_PATTERN_LENGTH = 8


class NWSLService:
    """Coordinates NWSL data lookups through the outbound port."""

    def __init__(self, repo: NWSLAPIPort) -> None:
        self._repo = repo

    async def get_teams(self) -> list[Team]:
        """Return all active NWSL teams."""
        return await self._repo.get_teams()

    async def get_team(self, team_id: str) -> Team:
        """Return a single team by its ESPN team ID.

        Args:
            team_id: ESPN numeric team ID or team abbreviation.

        Raises:
            ValueError: If team_id is empty.
            NWSLNotFoundError: If no team with that ID exists.
        """
        if not team_id or not team_id.strip():
            raise ValueError("team_id must not be empty")
        return await self._repo.get_team(team_id.strip())

    async def get_scoreboard(self, date: str | None = None) -> list[Match]:
        """Return matches for a given date or today if date is None.

        Args:
            date: Optional date string in YYYYMMDD format (e.g. "20250601").

        Raises:
            ValueError: If date is provided but not exactly 8 digits.
        """
        if date is not None:
            date = date.strip()
            if not date.isdigit() or len(date) != _DATE_PATTERN_LENGTH:
                raise ValueError(f"date must be in YYYYMMDD format, got {date!r}")
        return await self._repo.get_scoreboard(date)

    async def get_standings(self) -> list[Standing]:
        """Return the current NWSL league standings ordered by points descending."""
        return await self._repo.get_standings()
