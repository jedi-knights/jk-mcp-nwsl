"""Tests for the CMS adapter (dapi.nwslsoccer.com).

The CMS adapter fetches articles from the official site's content API. Used by
the awards and draft tools, which filter the article list client-side by title
patterns since the CMS's $filter param is silently ignored.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from nwsl.adapters.outbound.cms_adapter import CMSAdapter

_RAW_STORIES_RESPONSE = {
    "items": [
        {
            "slug": "best-xi-march-2026",
            "title": "NWSL Announces March Best XI of the Month",
            "summary": "The league's best players in March.",
            "contentDate": "2026-04-01T12:00:00Z",
            "tags": [{"slug": "awards"}, {"slug": "best-xi"}],
        },
        {
            "slug": "random-news-story",
            "title": "Random news story",
            "summary": "Unrelated.",
            "contentDate": "2026-04-02T12:00:00Z",
            "tags": [],
        },
    ],
}


@pytest.fixture
def mock_client() -> AsyncMock:
    client = AsyncMock()
    response = MagicMock()
    response.status_code = 200
    response.raise_for_status = MagicMock()
    client.get.return_value = response
    return client


@pytest.fixture
def adapter(mock_client: AsyncMock) -> CMSAdapter:
    return CMSAdapter(client=mock_client)


async def test_get_recent_stories_returns_parsed_articles(adapter: CMSAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = _RAW_STORIES_RESPONSE
    articles = await adapter.get_recent_stories(limit=2)
    assert len(articles) == 2
    a = articles[0]
    assert a.slug == "best-xi-march-2026"
    assert a.title.startswith("NWSL Announces")
    assert a.summary == "The league's best players in March."
    assert a.published == "2026-04-01T12:00:00Z"
    assert a.link == "https://www.nwslsoccer.com/news/best-xi-march-2026"
    assert "awards" in a.tags


async def test_get_recent_stories_passes_top_param(adapter: CMSAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"items": []}
    await adapter.get_recent_stories(limit=50)
    params = mock_client.get.call_args.kwargs.get("params", {})
    assert params.get("$top") == 50


async def test_get_recent_stories_targets_stories_endpoint(adapter: CMSAdapter, mock_client: AsyncMock) -> None:
    mock_client.get.return_value.json.return_value = {"items": []}
    await adapter.get_recent_stories(limit=10)
    requested_path = mock_client.get.call_args.args[0]
    assert "/stories" in requested_path


async def test_get_recent_stories_handles_missing_optional_fields(adapter: CMSAdapter, mock_client: AsyncMock) -> None:
    minimal = {"items": [{"slug": "x", "title": "A title"}]}
    mock_client.get.return_value.json.return_value = minimal
    articles = await adapter.get_recent_stories(limit=10)
    assert articles[0].slug == "x"
    assert articles[0].title == "A title"
    assert articles[0].summary == ""
    assert articles[0].published == ""
    assert articles[0].tags == []


async def test_get_recent_stories_raises_on_500(
    adapter: CMSAdapter, mock_client: AsyncMock, mocker: MockerFixture
) -> None:
    import httpx

    from nwsl.domain.exceptions import UpstreamAPIError

    mock_response = MagicMock()
    mock_response.status_code = 500
    http_error = httpx.HTTPStatusError("500", request=MagicMock(), response=mock_response)
    mock_client.get.return_value.raise_for_status.side_effect = http_error
    with pytest.raises(UpstreamAPIError):
        await adapter.get_recent_stories(limit=10)
