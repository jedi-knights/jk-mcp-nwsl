"""Entry point for the NWSL MCP server.

Wires together the outbound adapter (ESPN HTTP), the application service, and
the inbound MCP adapter. The dependency graph flows inward — adapters depend on
ports, ports depend on domain models. Nothing here is circular.

Transport: controlled by the MCP_TRANSPORT environment variable.
- "stdio" (default): JSON-RPC over stdin/stdout — client spawns the server as
  a subprocess. Never write to stdout in this mode; it corrupts the message stream.
- "streamable-http": HTTP server on HOST:PORT. The MCP client connects over HTTP.
  Use this for deployed / networked deployments. HOST defaults to "0.0.0.0" and
  PORT defaults to 8000.

ESPN API host: controlled by the API_HOST environment variable.
- Default: https://site.api.espn.com

Structured logging: all log records are emitted as JSON objects to stderr.
Docker captures stderr as container logs, so JSON output is parseable by
log aggregators without additional parsing rules. The log level can be
overridden at runtime with the LOG_LEVEL environment variable (default: INFO).
"""

import json
import logging
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from .adapters.inbound.mcp_adapter import create_mcp_server
from .adapters.outbound.caching_adapter import CachingAdapter
from .adapters.outbound.cms_adapter import CMSAdapter
from .adapters.outbound.espn_adapter import ESPNAdapter
from .adapters.outbound.retry_adapter import RetryingAdapter
from .adapters.outbound.sdp_adapter import SDPAdapter
from .adapters.outbound.sdp_caching_adapter import SDPCachingAdapter
from .adapters.outbound.sdp_retry_adapter import SDPRetryingAdapter
from .adapters.outbound.season_discovery import SeasonDiscoveryAdapter
from .application.service import NWSLService


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Using a custom formatter rather than a third-party library keeps the
    dependency surface minimal. Each record becomes one JSON line, which is
    the format expected by most container log drivers and aggregators.
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def _configure_logging() -> None:
    """Configure the root logger to emit JSON records to stderr.

    Reads the LOG_LEVEL environment variable (default: INFO). Invalid values
    fall back to INFO.
    """
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter())
    logging.root.setLevel(level)
    logging.root.addHandler(handler)


load_dotenv()
_configure_logging()

logger = logging.getLogger(__name__)

_VALID_TRANSPORTS = ("stdio", "streamable-http")


def build_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    api_host: str = "https://site.api.espn.com",
) -> FastMCP:
    """Wire ESPNAdapter → NWSLService → FastMCP and return the server.

    Extracted from main() so the composition graph can be constructed and
    tested without starting any transport.

    Args:
        host: Bind address for HTTP transport (ignored for stdio). Defaults to 0.0.0.0.
        port: TCP port for HTTP transport (ignored for stdio). Defaults to 8000.
        api_host: Base URL of the upstream ESPN API.
    """
    adapter = ESPNAdapter(base_url=api_host)
    # Compose cross-cutting adapters: HTTP → retry on transient errors → cache results.
    retrying = RetryingAdapter(adapter)
    caching = CachingAdapter(retrying)

    sdp_adapter = SDPAdapter()
    sdp_retrying = SDPRetryingAdapter(sdp_adapter)
    sdp_caching = SDPCachingAdapter(sdp_retrying)

    discovery = SeasonDiscoveryAdapter()
    cms = CMSAdapter()

    service = NWSLService(repo=caching, sdp=sdp_caching, discovery=discovery, cms=cms)
    return create_mcp_server(service, host=host, port=port)


def main() -> None:
    """Start the NWSL MCP server.

    Reads configuration from the environment:
      API_HOST       — base URL of the upstream ESPN API (default: https://site.api.espn.com)
      MCP_TRANSPORT  — "stdio" (default) or "streamable-http"
      HOST           — bind address for HTTP transport (default: 0.0.0.0)
      PORT           — TCP port for HTTP transport (default: 8000)
    """
    api_host = os.environ.get("API_HOST", "https://site.api.espn.com")
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))

    if transport not in _VALID_TRANSPORTS:
        raise ValueError(f"Invalid MCP_TRANSPORT={transport!r}. Must be one of: {', '.join(_VALID_TRANSPORTS)}")

    if transport == "streamable-http":
        logger.info("Starting NWSL MCP server (streamable-http transport, %s:%s)", host, port)
        build_server(host=host, port=port, api_host=api_host).run(transport="streamable-http")
    else:
        logger.info("Starting NWSL MCP server (stdio transport)")
        build_server(api_host=api_host).run(transport="stdio")


if __name__ == "__main__":
    main()
