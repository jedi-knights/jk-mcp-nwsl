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
class SeasonStanding:
    """A single team's row in a historical standings table from SDP/Opta.

    Distinct from `Standing` (which is sourced from ESPN and uses ESPN team IDs).
    Carries SDP team IDs and richer fields like rank.
    """

    rank: int
    team_id: str
    team_name: str
    points: int
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    team_abbreviation: str | None = None


@dataclass
class TeamSeasonStat:
    """A team's per-season aggregates from the SDP/Opta data feed.

    `stats` carries 100+ Opta metrics — possession, pass accuracy, xG, shots,
    set pieces, etc. — keyed by stat ID like "total-points", "goals",
    "passes-accuracy".
    """

    team_id: str
    name: str
    stats: dict[str, float] = field(default_factory=dict)


@dataclass
class PlayerSeasonStat:
    """A player's per-season stat row from the SDP/Opta data feed.

    `stats` is a free-form mapping of stat ID (e.g. "goals", "assists",
    "minutes-played", "Xg") to numeric value. Different player roles surface
    different stats — goalkeepers carry "saves" while outfield players don't.
    """

    player_id: str
    name: str
    team: str
    role: str | None = None
    nationality: str | None = None
    stats: dict[str, float] = field(default_factory=dict)


@dataclass
class CMSArticle:
    """A story article from the official site's CMS (dapi.nwslsoccer.com).

    Distinct from `NewsArticle` (sourced from ESPN) — the two CMS systems
    use different IDs, slugs, and lifecycles. CMSArticle carries the
    public-site URL and the editorial tag list, which is how the awards/draft
    tools filter to relevant stories.
    """

    slug: str
    title: str
    summary: str
    published: str
    link: str
    tags: list[str] = field(default_factory=list)


@dataclass
class Season:
    """A single NWSL season as exposed by the official site's widget config.

    `id` is the SDP entity ID (e.g. `nwsl::Football_Season::0b6761e4...`),
    used as a path segment when calling api-sdp.nwslsoccer.com. `competition`
    distinguishes Regular Season from Challenge Cup etc.
    """

    id: str
    year: int
    name: str
    competition: str


@dataclass
class NewsArticle:
    """A single NWSL news article from the ESPN news feed."""

    id: str
    headline: str
    description: str
    published: str
    link: str | None = None


@dataclass
class Player:
    """An NWSL player on a team's roster.

    Optional fields (jersey, position, citizenship, age) may be missing for
    unsigned, recently traded, or international players whose data ESPN has
    not fully populated.
    """

    id: str
    full_name: str
    jersey: str | None = None
    position: str | None = None
    position_abbr: str | None = None
    citizenship: str | None = None
    age: int | None = None


@dataclass
class MatchEvent:
    """A single key event within a match (goal, substitution, card, etc.).

    Mirrors ESPN's keyEvents entries: type is the raw event tag
    (e.g. "goal", "goal---header", "yellow-card", "substitution"); scoring
    is a convenience flag for goal events.
    """

    clock: str
    period: int
    type: str
    scoring: bool
    text: str | None = None
    team_name: str | None = None


@dataclass
class MatchDetails:
    """Detailed information about a single NWSL match.

    Combines header data (teams, score, status) with venue, attendance, and
    a chronological list of key in-game events.
    """

    id: str
    date: str
    status_detail: str
    home_team: str
    away_team: str
    home_score: str | None = None
    away_score: str | None = None
    venue: str | None = None
    venue_city: str | None = None
    attendance: int | None = None
    key_events: list[MatchEvent] = field(default_factory=list)


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
