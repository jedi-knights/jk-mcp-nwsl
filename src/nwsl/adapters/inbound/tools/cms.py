"""CMS-backed MCP tools — award articles scraped from the official site."""

import logging

from mcp.server.fastmcp import FastMCP

from ....application.service import NWSLService
from ..formatters import _fmt_award_articles
from ._base import _READ_ANNOTATIONS, _safe_call

logger = logging.getLogger(__name__)


def register_cms_tools(mcp: FastMCP, service: NWSLService) -> None:
    """Register the CMS-backed tools on `mcp`."""

    @mcp.tool(annotations=_READ_ANNOTATIONS)
    async def get_award_articles(limit: int = 10) -> str:
        """Get recent NWSL award-related articles (Best XI, Player of the Month, etc.).

        Awards aren't published as a structured endpoint — this tool fetches
        recent CMS articles and filters by title for awards keywords. Each
        result includes the article title, summary, and a link to the full
        story on nwslsoccer.com.

        Args:
            limit: Maximum number of award articles to return (default 10).
        """
        logger.info("tool=get_award_articles limit=%r", limit)
        return await _safe_call(service.get_award_articles(limit), _fmt_award_articles)
