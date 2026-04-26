"""Inbound adapter — exposes the application service as MCP tools.

This file is the composition root for the MCP layer:
- Creates the FastMCP server instance
- Registers liveness/readiness/health endpoints
- Delegates per-data-source tool registration to the modules in `tools/`

FastMCP generates tool schemas from Python type hints and docstrings, so the
docstrings on each registered tool are the LLM's primary guide.

Logging note (STDIO transport): NEVER use print() here. It writes to stdout
and corrupts the JSON-RPC stream.
"""

import logging

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...application.service import NWSLService
from .tools._base import _safe_call as _safe_call_internal
from .tools.analytics import register_analytics_tools
from .tools.cms import register_cms_tools
from .tools.espn import register_espn_tools
from .tools.sdp import register_sdp_tools

logger = logging.getLogger(__name__)

# Re-exported so existing test imports (`from nwsl.adapters.inbound.mcp_adapter
# import _safe_call`) keep working.
_safe_call = _safe_call_internal


# ---------------------------------------------------------------------------
# Health probe handlers
# ---------------------------------------------------------------------------


async def _handle_livez(request: Request) -> JSONResponse:
    """Liveness probe — returns 200 OK if the HTTP server is up."""
    return JSONResponse({"status": "ok"})


async def _handle_readyz(request: Request) -> JSONResponse:
    """Readiness probe — returns 200 when the server is ready to serve traffic."""
    return JSONResponse({"status": "ok"})


async def _handle_health(request: Request) -> JSONResponse:
    """Aggregate health endpoint for monitoring systems."""
    return JSONResponse({"status": "ok", "checks": {"liveness": "ok", "readiness": "ok"}})


# ---------------------------------------------------------------------------
# MCP server factory
# ---------------------------------------------------------------------------


def create_mcp_server(service: NWSLService, host: str = "0.0.0.0", port: int = 8000) -> FastMCP:
    """Wire the application service into a FastMCP instance and register tools.

    Args:
        service: The NWSLService to expose as MCP tools.
        host: Bind address for HTTP transport (ignored for stdio). Defaults to 0.0.0.0.
        port: TCP port for HTTP transport (ignored for stdio). Defaults to 8000.
    """
    mcp = FastMCP("nwsl", host=host, port=port, stateless_http=True)

    mcp.custom_route("/livez", methods=["GET"])(_handle_livez)
    mcp.custom_route("/readyz", methods=["GET"])(_handle_readyz)
    mcp.custom_route("/health", methods=["GET"])(_handle_health)

    register_espn_tools(mcp, service)
    register_sdp_tools(mcp, service)
    register_cms_tools(mcp, service)
    register_analytics_tools(mcp, service)

    return mcp
