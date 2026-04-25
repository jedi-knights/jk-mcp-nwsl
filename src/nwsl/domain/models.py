"""Domain models for the NWSL MCP server.

Pure Python dataclasses with zero framework dependencies. Adapters are
responsible for translating to/from these types from the ESPN API wire format.
"""

from dataclasses import dataclass, field


@dataclass
class Team:
    """An NWSL franchise.

    id and abbreviation are the stable identifiers used by the ESPN API.
    """

    id: str
    name: str
    abbreviation: str
    location: str
    display_name: str
    logo_url: str | None = None


@dataclass
class MatchCompetitor:
    """One side of a match — home or away team with its score."""

    team: Team
    home_away: str
    score: str | None = None
    winner: bool | None = None


@dataclass
class Match:
    """A single NWSL match (scheduled, in-progress, or completed).

    status_type values from the ESPN API:
      "pre"  — scheduled, not yet started
      "in"   — in progress
      "post" — final
    """

    id: str
    date: str
    name: str
    short_name: str
    status_type: str
    status_detail: str
    competitors: list[MatchCompetitor] = field(default_factory=list)


@dataclass
class Standing:
    """A team's position in the NWSL league table."""

    team: Team
    wins: int
    losses: int
    ties: int
    points: int
    goals_for: int
    goals_against: int
    goal_difference: int
