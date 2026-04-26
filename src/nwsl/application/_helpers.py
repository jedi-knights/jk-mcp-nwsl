"""Internal helpers for NWSLService — validation, season selection, keyword filtering.

Extracted from service.py to keep that file focused on use-case orchestration.
Schedule-strength analytics helpers live in `_analytics_helpers.py`.
"""

from ..domain.exceptions import NWSLNotFoundError
from ..domain.models import Season

_DATE_PATTERN_LENGTH = 8

# Title patterns the awards tool surfaces. Conservative — false positives are
# preferred over missing legitimate award stories.
_AWARD_TITLE_KEYWORDS: tuple[str, ...] = (
    "best xi",
    "player of the month",
    "player of the match",
    "rookie of the",
    "save of the",
    "goal of the",
    "coach of the",
    "mvp",
)

# Cap on stories pulled before client-side filtering. The CMS returns ~25 per
# page; we sweep up to ~100 recent stories which is enough for current-season
# award coverage without hammering the API.
_MAX_CMS_FETCH = 100


def _matches_keywords(title: str, keywords: tuple[str, ...]) -> bool:
    """Case-insensitive check that any of `keywords` appears in `title`."""
    lower = title.lower()
    return any(k in lower for k in keywords)


def _select_season(candidates: list[Season], year: int | None, competition: str) -> Season:
    """Pick a season from `candidates` by year, defaulting to the most recent.

    Raises:
        NWSLNotFoundError: If candidates is empty or no entry matches `year`.
    """
    if not candidates:
        raise NWSLNotFoundError(f"No {competition} seasons available")
    if year is None:
        return max(candidates, key=lambda s: s.year)
    match = next((s for s in candidates if s.year == year), None)
    if match is None:
        raise NWSLNotFoundError(f"{competition} {year} not found")
    return match


def _validate_yyyymmdd(value: str, label: str) -> str:
    """Return value if it is exactly 8 digits, else raise ValueError citing the label."""
    if not value.isdigit() or len(value) != _DATE_PATTERN_LENGTH:
        raise ValueError(f"{label} must be in YYYYMMDD format, got {value!r}")
    return value
