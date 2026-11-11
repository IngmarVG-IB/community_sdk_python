"""Run every examples/v6 script's main() against the offline fake server."""

from __future__ import annotations

import httpx
import pytest
import respx

from examples.v6 import alerts_pagination, async_inventory, error_handling, synthetics_overview
from kentik_api import AsyncKentikClient, KentikClient


def test_synthetics_overview(client: KentikClient, mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]) -> None:
    mock.get("/synthetics/v202309/tests").respond(
        json={"tests": [{"id": "1", "name": "web", "type": "url", "status": "TEST_STATUS_ACTIVE"}]}
    )
    mock.get("/synthetics/v202309/agents").respond(
        json={"agents": [{"id": "a", "status": "AGENT_STATUS_OK"}, {"id": "b", "status": "AGENT_STATUS_OK"}]}
    )
    synthetics_overview.main(client)
    out = capsys.readouterr().out
    assert "1 synthetic tests" in out and "web" in out
    assert "2 agents: AGENT_STATUS_OK=2" in out


@pytest.mark.anyio
async def test_async_inventory(
    aclient: AsyncKentikClient, mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]
) -> None:
    mock.get("/site/v202509/sites").respond(json={"sites": [{"id": "1", "title": "Ashburn"}]})
    mock.get("/label/v202210/labels").respond(json={"labels": [{"name": "prod"}, {"name": "edge"}]})
    mock.get("/user/v202211/users").respond(json={"users": [{"id": "1"}]})
    await async_inventory.main(aclient)
    out = capsys.readouterr().out
    assert "Ashburn" in out and "edge, prod" in out and "users:  1" in out


def test_alerts_pagination(client: KentikClient, mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]) -> None:
    route = mock.post("/v202505/alerts").mock(
        side_effect=[
            httpx.Response(
                200, json={"alerts": [{"id": str(i)} for i in range(200)], "pagination": {"hasMoreResults": True}}
            ),
            httpx.Response(200, json={"alerts": [{"id": "last"}]}),
        ]
    )
    alerts_pagination.main(client)
    assert "201 active alerts" in capsys.readouterr().out
    assert route.call_count == 2


def test_error_handling(client: KentikClient, mock: respx.MockRouter, capsys: pytest.CaptureFixture[str]) -> None:
    mock.get("/synthetics/v202309/tests/42").respond(404, json={"code": 5, "message": "not found"})
    error_handling.main(client, "42")
    assert "no test 42 (gRPC NOT_FOUND" in capsys.readouterr().out
