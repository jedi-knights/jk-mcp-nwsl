"""Pure formatters that turn domain models into LLM-readable text.

Extracted from mcp_adapter.py so the adapter focuses on tool wiring while the
presentation layer stays a side-effect-free, easily testable concern.
"""

from ...domain.models import (
    CMSArticle,
    Match,
    MatchCompetitor,
    MatchDetails,
    MatchEvent,
    NewsArticle,
    Player,
    PlayerSeasonStat,
    SeasonStanding,
    Standing,
    Team,
    TeamSeasonStat,
)


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


def _fmt_team_schedule(matches: list[Match]) -> str:
    """Format a list of matches for the team-schedule tool."""
    if not matches:
        return "No scheduled matches found for this team."
    return "\n\n".join(_fmt_match(m) for m in matches)


def _fmt_player(i: int, player: Player) -> str:
    """Format a single roster row."""
    jersey = f"#{player.jersey}" if player.jersey else "  "
    pos = f" ({player.position_abbr})" if player.position_abbr else ""
    extras = []
    if player.position:
        extras.append(player.position)
    if player.citizenship:
        extras.append(player.citizenship)
    if player.age is not None:
        extras.append(f"age {player.age}")
    suffix = f" — {', '.join(extras)}" if extras else ""
    return f"{i}. {jersey} {player.full_name}{pos}{suffix}"


def _fmt_roster(players: list[Player]) -> str:
    """Format a roster as a numbered list."""
    if not players:
        return "No players found for this team."
    return "\n".join(_fmt_player(i, p) for i, p in enumerate(players, 1))


def _fmt_event(event: MatchEvent) -> str:
    """Format a single key event as a one-line summary."""
    marker = "⚽" if event.scoring else "•"
    parts = [f"  {marker} {event.clock}"]
    if event.team_name:
        parts.append(f"({event.team_name})")
    parts.append(event.text or event.type)
    return " ".join(parts)


def _fmt_venue_line(details: MatchDetails) -> str | None:
    """Build the venue line, or return None if no venue is set."""
    if not details.venue:
        return None
    if details.venue_city:
        return f"  Venue: {details.venue} ({details.venue_city})"
    return f"  Venue: {details.venue}"


def _fmt_match_details(details: MatchDetails) -> str:
    """Format a MatchDetails as a readable multi-line summary."""
    score = f"{details.home_score or '?'} - {details.away_score or '?'}"
    lines = [
        f"{details.home_team} {score} {details.away_team}",
        f"  Date: {details.date}",
        f"  Status: {details.status_detail}",
    ]
    venue_line = _fmt_venue_line(details)
    if venue_line:
        lines.append(venue_line)
    if details.attendance is not None:
        lines.append(f"  Attendance: {details.attendance:,}")
    if details.key_events:
        lines.append("  Key events:")
        lines.extend(_fmt_event(e) for e in details.key_events)
    return "\n".join(lines)


def _fmt_article(i: int, article: NewsArticle) -> str:
    """Format a single news article as a multi-line entry."""
    lines = [f"{i}. {article.headline}"]
    if article.published:
        lines.append(f"   Published: {article.published}")
    if article.description:
        lines.append(f"   {article.description}")
    if article.link:
        lines.append(f"   {article.link}")
    return "\n".join(lines)


def _fmt_news(articles: list[NewsArticle]) -> str:
    """Format a list of news articles."""
    if not articles:
        return "No news articles available."
    return "\n\n".join(_fmt_article(i, a) for i, a in enumerate(articles, 1))


def _fmt_stat_value(value: float) -> str:
    """Format a stat number — drop the .0 from integer-valued floats."""
    if value == int(value):
        return str(int(value))
    return f"{value:.2f}"


def _fmt_player_leaderboard_row(i: int, player: PlayerSeasonStat, sort_by: str) -> str:
    """Format one row of the player leaderboards table."""
    sort_value = player.stats.get(sort_by)
    sort_part = f" — {sort_by}: {_fmt_stat_value(sort_value)}" if sort_value is not None else ""
    role_part = f" ({player.role})" if player.role else ""
    return f"{i}. {player.name}{role_part}, {player.team}{sort_part}"


def _fmt_player_leaderboards(players: list[PlayerSeasonStat], sort_by: str) -> str:
    """Format a player-leaderboards response.

    Args:
        players: Result list, already in server-sorted order.
        sort_by: The stat ID used for sorting — surfaced in each row.
    """
    if not players:
        return f"No players found for sort '{sort_by}'."
    header = f"Top {len(players)} players by {sort_by}:"
    rows = [_fmt_player_leaderboard_row(i, p, sort_by) for i, p in enumerate(players, 1)]
    return "\n".join([header, *rows])


def _fmt_team_season_stats(teams: list[TeamSeasonStat], sort_by: str) -> str:
    """Format team season aggregates."""
    if not teams:
        return f"No team stats found for sort '{sort_by}'."
    header = f"NWSL teams ranked by {sort_by}:"
    rows = []
    for i, t in enumerate(teams, 1):
        sort_value = t.stats.get(sort_by)
        sort_part = f" — {sort_by}: {_fmt_stat_value(sort_value)}" if sort_value is not None else ""
        rows.append(f"{i}. {t.name}{sort_part}")
    return "\n".join([header, *rows])


def _fmt_season_standing(row: SeasonStanding) -> str:
    """Format one row of a historical standings table."""
    abbr = f" ({row.team_abbreviation})" if row.team_abbreviation else ""
    return (
        f"{row.rank}. {row.team_name}{abbr}"
        f" — {row.points} pts | MP:{row.matches_played} W:{row.wins} D:{row.draws} L:{row.losses}"
        f" | GF:{row.goals_for} GA:{row.goals_against} GD:{row.goal_difference:+d}"
    )


def _fmt_historical_standings(rows: list[SeasonStanding], year: int) -> str:
    """Format a historical standings table for a given year."""
    if not rows:
        return f"No standings data available for {year}."
    header = f"NWSL {year} Regular Season standings:"
    return "\n".join([header, *(_fmt_season_standing(r) for r in rows)])


def _fmt_cms_article(i: int, article: CMSArticle) -> str:
    """Format a single CMS article entry."""
    lines = [f"{i}. {article.title}"]
    if article.published:
        lines.append(f"   Published: {article.published}")
    if article.summary:
        lines.append(f"   {article.summary}")
    lines.append(f"   {article.link}")
    return "\n".join(lines)


def _fmt_award_articles(articles: list[CMSArticle]) -> str:
    """Format the awards-articles list."""
    if not articles:
        return "No recent award articles found."
    return "\n\n".join(_fmt_cms_article(i, a) for i, a in enumerate(articles, 1))


def _fmt_draft_articles(articles: list[CMSArticle]) -> str:
    """Format the draft-articles list."""
    if not articles:
        return "No recent draft articles found."
    return "\n\n".join(_fmt_cms_article(i, a) for i, a in enumerate(articles, 1))


def _fmt_challenge_cup_standings(rows: list[SeasonStanding], year: int | None) -> str:
    """Format a Challenge Cup standings table."""
    if not rows:
        return f"No Challenge Cup standings available{' for ' + str(year) if year else ''}."
    suffix = f" {year}" if year else ""
    header = f"NWSL Challenge Cup{suffix} standings:"
    return "\n".join([header, *(_fmt_season_standing(r) for r in rows)])


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
