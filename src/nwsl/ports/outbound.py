"""Outbound ports — interfaces the application layer depends on.

These are the contracts that secondary/driven adapters must satisfy. The
application layer only imports these protocols; it never references concrete
implementations. This is what makes the hexagonal boundary testable and
swap-able (e.g. real HTTP adapter vs. an in-memory stub).
"""

from typing import Protocol

from ..domain.models import Match, Standing, Team


class NWSLAPIPort(Protocol):
    """Contract for the upstream NWSL data source (ESPN API)."""

    async def get_teams(self) -> list[Team]:
        """Return all active NWSL teams."""
        ...

    async def get_team(self, team_id: str) -> Team:
        """Return a single team by its ESPN team ID.

        Raises:
            NWSLNotFoundError: If no team with that ID exists.
        """
        ...

    async def get_scoreboard(self, date: str | None = None) -> list[Match]:
        """Return matches on the given date (YYYYMMDD) or today if date is None."""
        ...

    async def get_standings(self) -> list[Standing]:
        """Return the current NWSL league standings, ordered by points descending."""
        ...
