"""Tests for domain model construction and field access."""

from nwsl.domain.models import Match, Standing, Team


def test_team_fields(portland_thorns: Team) -> None:
    assert portland_thorns.id == "1899"
    assert portland_thorns.abbreviation == "POR"
    assert portland_thorns.display_name == "Portland Thorns FC"


def test_match_competitor_fields(sample_match: Match) -> None:
    home = next(c for c in sample_match.competitors if c.home_away == "home")
    assert home.score == "2"
    assert home.winner is True


def test_standing_goal_difference(sample_standing: Standing) -> None:
    assert sample_standing.goal_difference == 22
    assert sample_standing.points == 38
