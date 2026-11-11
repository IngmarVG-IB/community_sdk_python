from __future__ import annotations

import json

import httpx
import pytest
import respx

from kentik_api.v6 import AsyncKentikClient, KentikClient
from kentik_api.v6.services.alerting_public_v202505 import models as alerting

EVENTS = "/audit/v202601/events"
ALERTS = "/v202505/alerts"


def _events(start: int, n: int) -> dict:  # type: ignore[type-arg]
    return {"events": [{"id": str(i)} for i in range(start, start + n)]}


def test_query_pagination_follows_offset_until_short_page(client: KentikClient, mock: respx.MockRouter) -> None:
    pages = [_events(0, 2), _events(2, 2), _events(4, 1)]
    route = mock.get(EVENTS).mock(side_effect=[httpx.Response(200, json=p) for p in pages])
    ids = [e.id for e in client.audit_public.iter_list_audit_events(start_time="2026-01-01T00:00:00Z", page_size=2)]
    assert ids == ["0", "1", "2", "3", "4"]
    params = [dict(c.request.url.params) for c in route.calls]
    assert [(p["offset"], p["limit"]) for p in params] == [("0", "2"), ("2", "2"), ("4", "2")]
    assert all(p["startTime"] == "2026-01-01T00:00:00Z" for p in params)


def test_query_pagination_stops_on_empty_page(client: KentikClient, mock: respx.MockRouter) -> None:
    route = mock.get(EVENTS).mock(side_effect=[httpx.Response(200, json=_events(0, 2)), httpx.Response(200, json={})])
    assert len(list(client.audit_public.iter_list_audit_events(page_size=2))) == 2
    assert route.call_count == 2


def test_body_pagination_uses_has_more_results(client: KentikClient, mock: respx.MockRouter) -> None:
    pages = [
        {"alerts": [{"id": "a"}, {"id": "b"}], "pagination": {"hasMoreResults": True}},
        {"alerts": [{"id": "c"}, {"id": "d"}], "pagination": {"hasMoreResults": False}},
    ]
    route = mock.post(ALERTS).mock(side_effect=[httpx.Response(200, json=p) for p in pages])
    body = alerting.AlertServiceListRequest(pagination=alerting.PaginationConfig(include_total_count=True))
    alerts = list(client.alerting_public.alert.iter_list(body, page_size=2))
    assert [a.id for a in alerts] == ["a", "b", "c", "d"]
    assert all(isinstance(a, alerting.Alert) for a in alerts)
    sent = [json.loads(c.request.content) for c in route.calls]
    assert sent[0]["pagination"] == {"includeTotalCount": True, "limit": "2", "offset": "0"}
    assert sent[1]["pagination"]["offset"] == "2"
    assert route.call_count == 2


def test_body_pagination_uses_total_count(client: KentikClient, mock: respx.MockRouter) -> None:
    route = mock.post(ALERTS).mock(
        return_value=httpx.Response(200, json={"alerts": [{"id": "x"}, {"id": "y"}], "pagination": {"totalCount": "2"}})
    )
    assert len(list(client.alerting_public.alert.iter_list(page_size=2))) == 2
    assert route.call_count == 1


def test_page_size_must_be_positive(client: KentikClient) -> None:
    with pytest.raises(ValueError, match="page_size"):
        list(client.audit_public.iter_list_audit_events(page_size=0))


@pytest.mark.anyio
async def test_async_pagination(aclient: AsyncKentikClient, mock: respx.MockRouter) -> None:
    mock.get(EVENTS).mock(
        side_effect=[httpx.Response(200, json=_events(0, 3)), httpx.Response(200, json=_events(3, 1))]
    )
    ids = [e.id async for e in aclient.audit_public.iter_list_audit_events(page_size=3)]
    assert ids == ["0", "1", "2", "3"]
