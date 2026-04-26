"""Pure functions that map SDP/Opta JSON wire format into domain models.

The api-sdp.nwslsoccer.com responses use a different shape from ESPN — most
notably the per-player `stats` array carries 100+ Opta metrics, each as a
{statsId, statsLabel, statsValue} triple.
"""

from typing import Any

from ...domain.models import PlayerSeasonStat, SeasonStanding, TeamSeasonStat


def _player_display_name(raw: dict[str, Any]) -> str:
    """Pick the most informative name available for a player.

    Prefers `mediaFirstName + mediaLastName`, falls back to `shortName`.
    """
    first = raw.get("mediaFirstName")
    last = raw.get("mediaLastName")
    if first and last:
        return f"{first} {last}"
    return raw.get("shortName") or ""


def _stats_dict(raw_stats: list[dict[str, Any]]) -> dict[str, float]:
    """Flatten the [{statsId, statsValue}, ...] list into a {id: value} map.

    Drops entries with non-numeric values silently — the SDP feed sometimes
    returns null for stats a player has no data for.
    """
    return {s["statsId"]: s["statsValue"] for s in raw_stats if isinstance(s.get("statsValue"), (int, float))}


def _parse_season_standing(raw: dict[str, Any]) -> SeasonStanding:
    """Map a single team row from an SDP standings table to a SeasonStanding.

    Args:
        raw: An entry from `standings[i].teams[j]` on the standings response.
    """
    stats = _stats_dict(raw.get("stats") or [])
    goals_for = int(stats.get("goals-for", 0))
    goals_against = int(stats.get("goals-against", 0))
    return SeasonStanding(
        rank=int(stats.get("rank", 0)),
        team_id=str(raw.get("teamId", "")),
        team_name=raw.get("officialName") or raw.get("shortName") or "",
        team_abbreviation=raw.get("acronymName"),
        points=int(stats.get("points", 0)),
        matches_played=int(stats.get("matches-played", 0)),
        wins=int(stats.get("win", 0)),
        draws=int(stats.get("draw", 0)),
        losses=int(stats.get("lose", 0)),
        goals_for=goals_for,
        goals_against=goals_against,
        goal_difference=goals_for - goals_against,
    )


def _parse_team_season_stat(raw: dict[str, Any]) -> TeamSeasonStat:
    """Map a raw SDP teams[] entry to a domain TeamSeasonStat.

    Args:
        raw: An entry from the .teams array on /stats/teams.
    """
    return TeamSeasonStat(
        team_id=str(raw.get("teamId", "")),
        name=raw.get("officialName") or raw.get("shortName") or "",
        stats=_stats_dict(raw.get("stats") or []),
    )


def _parse_player_season_stat(raw: dict[str, Any]) -> PlayerSeasonStat:
    """Map a raw SDP players[] entry to a domain PlayerSeasonStat.

    Args:
        raw: An entry from the .players array on /stats/players.
    """
    team = raw.get("team") or {}
    return PlayerSeasonStat(
        player_id=str(raw.get("playerId", "")),
        name=_player_display_name(raw),
        team=team.get("officialName") or team.get("shortName") or "",
        role=raw.get("roleLabel"),
        nationality=raw.get("nationality"),
        stats=_stats_dict(raw.get("stats") or []),
    )
