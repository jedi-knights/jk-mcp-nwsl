"""pytest fixtures for the eval harness.

Provides ``mcp_client`` — an async ``ClientSession`` connected to an
in-process FastMCP instance whose outbound HTTP adapter is a stub
returning deterministic domain objects. Scenarios run hermetically in
unit-test CI without contacting the live ESPN / CMS / SDP APIs.

The nightly drift run (see ``.github/workflows/evals.yml``) overrides
this fixture with a transport pointed at the deployed Fly instance so
the same scenarios exercise the live wire shape without any change to
the runner.

The stubs cover only the small slice of upstream calls the registered
scenarios exercise. Adding a scenario that calls a new tool means
adding the matching stub method here — there is no automatic
discovery. The trade-off is deliberate: scenarios act as both
documentation and contract tests, so explicitly listing the supported
shape keeps the test surface honest.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest_asyncio
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session

from nwsl.adapters.inbound.mcp_adapter import create_mcp_server
from nwsl.application.service import NWSLService
from nwsl.domain.models import Standing, Team


@dataclass
class _StubRepo:
    """Application-port stub returning deterministic domain objects.

    Only the methods the registered scenarios call are implemented.
    Adding a scenario that hits an unimplemented tool will surface an
    AttributeError — the explicit failure mode is the right one for
    a contract-test harness.
    """

    async def get_teams(self) -> list[Team]:
        return [_portland_thorns()]

    async def get_team(self, team_id: str) -> Team:
        _ = team_id
        return _portland_thorns()

    async def get_standings(self) -> list[Standing]:
        return [
            Standing(
                team=_portland_thorns(),
                wins=14,
                losses=3,
                ties=3,
                points=45,
                goals_for=42,
                goals_against=18,
                goal_difference=24,
            ),
        ]


def _portland_thorns() -> Team:
    return Team(
        id="1899",
        name="Portland Thorns FC",
        abbreviation="POR",
        location="Portland",
        display_name="Portland Thorns FC",
    )


class _NotWired:
    """Sentinel that raises on any attribute access.

    Used in place of out-of-scope dependencies so an accidental tool
    call against an un-stubbed surface produces an obvious error
    rather than a confusing one downstream.
    """

    def __getattr__(self, name: str):
        raise NotImplementedError(f"eval harness: dependency port not wired for {name!r}")


@pytest_asyncio.fixture
async def mcp_client() -> AsyncIterator[ClientSession]:
    """Yield a ClientSession bound to an in-process NWSL MCP server.

    The service receives the stub above; tools that are out of scope
    for the current scenario suite simply aren't wired and will surface
    NotImplementedError on call. That's deliberate — the harness
    intends to cover the scenarios it ships with explicitly.
    """
    service = NWSLService(repo=_StubRepo(), sdp=_NotWired(), discovery=_NotWired(), cms=_NotWired())
    server = create_mcp_server(service)
    async with _server_session(server) as client:
        yield client


@asynccontextmanager
async def _server_session(server) -> AsyncIterator[ClientSession]:
    """Wrap ``create_connected_server_and_client_session`` so the
    fixture stays one-line."""
    async with create_connected_server_and_client_session(server._mcp_server) as session:
        yield session
