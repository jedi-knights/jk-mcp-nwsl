"""Tests for the season discovery adapter.

Discovery scrapes nwslsoccer.com for the embedded `seasonIdJson` widget config
and returns a list of Season domain objects. The HTML format is fragile (it's
public site markup, not a documented API), so unit tests pin the parser to a
small fixture rather than hitting the network.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from nwsl.adapters.outbound.season_discovery import SeasonDiscoveryAdapter, _parse_seasons_from_html
from nwsl.domain.models import Season

# Minimal HTML fragment matching the real page's seasonIdJson encoding.
# The real page double-escapes JSON inside an HTML attribute, so we mirror
# that exactly: outer `&quot;` for HTML entity escaping, inner `\&quot;` for
# the JSON string-within-a-string.
_SAMPLE_HTML = """
<html><body>
<div data-widget-config="seasonIdJson&quot;:&quot;{\\&quot;nwsl::Football_Season::aaaa\\&quot;:\\&quot;Regular Season 2026\\&quot;,\\&quot;nwsl::Football_Season::bbbb\\&quot;:\\&quot;Regular Season 2025\\&quot;}&quot;,foo">
</div>
</body></html>
"""


def test_parse_seasons_extracts_year_and_id() -> None:
    seasons = _parse_seasons_from_html(_SAMPLE_HTML)
    assert len(seasons) == 2
    by_year = {s.year: s for s in seasons}
    assert by_year[2026].id == "nwsl::Football_Season::aaaa"
    assert by_year[2026].name == "Regular Season 2026"
    assert by_year[2026].competition == "Regular Season"
    assert by_year[2025].id == "nwsl::Football_Season::bbbb"


def test_parse_seasons_returns_empty_when_config_absent() -> None:
    seasons = _parse_seasons_from_html("<html><body><p>no widget here</p></body></html>")
    assert seasons == []


async def test_adapter_raises_when_markup_lacks_season_config() -> None:
    """If a configured page returns 200 but the seasonIdJson regex finds nothing,
    the adapter must raise UpstreamAPIError so callers see that discovery
    itself broke (rather than the misleading 'No Regular Season available')."""
    from nwsl.domain.exceptions import UpstreamAPIError

    response = MagicMock(text="<html><body>no config</body></html>", raise_for_status=MagicMock())
    client = AsyncMock()
    client.get.return_value = response

    adapter = SeasonDiscoveryAdapter(page_urls=["https://example/standings"], client=client)
    with pytest.raises(UpstreamAPIError, match="seasonIdJson"):
        await adapter.get_seasons()


async def test_adapter_get_seasons_fetches_and_parses() -> None:
    response = MagicMock()
    response.status_code = 200
    response.text = _SAMPLE_HTML
    response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.get.return_value = response

    adapter = SeasonDiscoveryAdapter(client=client)
    seasons = await adapter.get_seasons()

    assert len(seasons) == 2
    assert any(s.year == 2026 and s.id == "nwsl::Football_Season::aaaa" for s in seasons)


async def test_adapter_scans_both_regular_season_and_challenge_cup_pages() -> None:
    """Discovery should fetch every URL in `page_urls` and merge the results."""
    rs_response = MagicMock(text=_SAMPLE_HTML, raise_for_status=MagicMock())
    cc_html = _SAMPLE_HTML.replace("Regular Season", "Challenge Cup").replace("aaaa", "ccc1")
    cc_response = MagicMock(text=cc_html, raise_for_status=MagicMock())
    client = AsyncMock()
    client.get.side_effect = [rs_response, cc_response]

    adapter = SeasonDiscoveryAdapter(page_urls=["https://example/regular", "https://example/challenge"], client=client)
    seasons = await adapter.get_seasons()

    assert client.get.call_count == 2
    competitions = {s.competition for s in seasons}
    assert competitions == {"Regular Season", "Challenge Cup"}


def _stub_clock(state: list[float]):
    def _now() -> float:
        return state[0]

    return _now


async def test_adapter_caches_subsequent_calls_within_ttl() -> None:
    """Discovery should hit each page once, then serve subsequent calls from cache.

    SDP season IDs change yearly so the cache TTL is intentionally long.
    Without this, every SDP-backed tool call would re-fetch the standings page.
    """
    response = MagicMock(text=_SAMPLE_HTML, raise_for_status=MagicMock())
    client = AsyncMock()
    client.get.return_value = response
    clock = [0.0]

    adapter = SeasonDiscoveryAdapter(
        page_urls=["https://example/standings"],
        client=client,
        ttl_seconds=3600.0,
        now=_stub_clock(clock),
    )

    await adapter.get_seasons()
    await adapter.get_seasons()
    await adapter.get_seasons()

    client.get.assert_called_once()


async def test_adapter_refetches_after_ttl_expiry() -> None:
    response = MagicMock(text=_SAMPLE_HTML, raise_for_status=MagicMock())
    client = AsyncMock()
    client.get.return_value = response
    clock = [0.0]

    adapter = SeasonDiscoveryAdapter(
        page_urls=["https://example/standings"],
        client=client,
        ttl_seconds=60.0,
        now=_stub_clock(clock),
    )

    await adapter.get_seasons()
    clock[0] = 61.0
    await adapter.get_seasons()

    assert client.get.call_count == 2


def test_season_dataclass_holds_fields() -> None:
    s = Season(id="abc", year=2026, name="Regular Season 2026", competition="Regular Season")
    assert s.id == "abc"
    assert s.year == 2026
    assert s.competition == "Regular Season"
