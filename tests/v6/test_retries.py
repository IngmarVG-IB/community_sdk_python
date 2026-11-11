from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest
import respx

from kentik_api.v6 import (
    APIConnectionError,
    APITimeoutError,
    AsyncKentikClient,
    KentikClient,
    RateLimitError,
    RetryConfig,
    ServerError,
)
from kentik_api.v6._core.transport import parse_retry_after

from .conftest import BASE_URL, EMAIL, TOKEN

TESTS = "/synthetics/v202309/tests"


def test_get_retried_on_503_with_exponential_backoff(
    client: KentikClient, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.get(TESTS).mock(
        side_effect=[httpx.Response(503), httpx.Response(502), httpx.Response(200, json={"tests": []})]
    )
    assert client.synthetics.list_tests().tests == []
    assert route.call_count == 3
    assert sleeps == [0.5, 1.0]
    # the same request id is reused across attempts so they can be correlated
    ids = {c.request.headers["X-Request-ID"] for c in route.calls}
    assert len(ids) == 1


def test_retries_exhausted_raise_server_error(
    client: KentikClient, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.get(TESTS).respond(500, json={"code": 13, "message": "boom"})
    with pytest.raises(ServerError) as info:
        client.synthetics.list_tests()
    assert route.call_count == 4  # 1 + max_retries
    assert sleeps == [0.5, 1.0, 2.0]
    assert info.value.grpc_status == "INTERNAL"


def test_backoff_is_capped(mock: respx.MockRouter) -> None:
    sleeps: list[float] = []
    cfg = RetryConfig(max_retries=5, initial_backoff=1, multiplier=10, max_backoff=3, jitter=False)
    with KentikClient(EMAIL, TOKEN, base_url=BASE_URL, retry=cfg) as c:
        c._transport.sleep = sleeps.append
        mock.get(TESTS).respond(503)
        with pytest.raises(ServerError):
            c.synthetics.list_tests()
    assert sleeps == [1, 3, 3, 3, 3]


def test_full_jitter_stays_within_backoff(mock: respx.MockRouter) -> None:
    sleeps: list[float] = []
    cfg = RetryConfig(max_retries=3, initial_backoff=1, multiplier=2, jitter=True)
    with KentikClient(EMAIL, TOKEN, base_url=BASE_URL, retry=cfg) as c:
        c._transport.sleep = sleeps.append
        mock.get(TESTS).respond(503)
        with pytest.raises(ServerError):
            c.synthetics.list_tests()
    assert len(sleeps) == 3
    assert all(0 <= s <= cap for s, cap in zip(sleeps, [1, 2, 4], strict=True))


def test_non_idempotent_post_not_retried_on_5xx(
    client: KentikClient, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.post(TESTS).respond(503)
    with pytest.raises(ServerError):
        client.synthetics.create_test({"test": {"name": "x"}})
    assert route.call_count == 1
    assert sleeps == []


def test_read_only_post_rpc_is_retried(client: KentikClient, mock: respx.MockRouter) -> None:
    route = mock.post("/synthetics/v202309/results").mock(
        side_effect=[httpx.Response(504), httpx.Response(200, json={"results": []})]
    )
    client.synthetics.get_results_for_tests({"ids": ["1"]})
    assert route.call_count == 2


def test_429_retried_for_any_call_and_retry_after_honoured(
    client: KentikClient, mock: respx.MockRouter, sleeps: list[float]
) -> None:
    route = mock.post(TESTS).mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={"test": {"id": "9"}})]
    )
    resp = client.synthetics.create_test({"test": {"name": "x"}})
    assert resp.test and resp.test.id == "9"
    assert route.call_count == 2
    assert sleeps == [7.0]


def test_retry_after_is_capped(mock: respx.MockRouter) -> None:
    sleeps: list[float] = []
    with KentikClient(EMAIL, TOKEN, base_url=BASE_URL, retry=RetryConfig(max_retry_after=10, jitter=False)) as c:
        c._transport.sleep = sleeps.append
        mock.get(TESTS).mock(side_effect=[httpx.Response(429, headers={"Retry-After": "3600"}), httpx.Response(200)])
        c.synthetics.list_tests()
    assert sleeps == [10]


def test_rate_limit_error_carries_retry_after(mock: respx.MockRouter) -> None:
    with KentikClient(EMAIL, TOKEN, base_url=BASE_URL, retry=RetryConfig.disabled()) as c:
        mock.get(TESTS).respond(429, headers={"Retry-After": "2"}, json={"code": 8, "message": "slow down"})
        with pytest.raises(RateLimitError) as info:
            c.synthetics.list_tests()
    assert info.value.retry_after == 2.0
    assert info.value.grpc_status == "RESOURCE_EXHAUSTED"


def test_parse_retry_after_http_date() -> None:
    when = datetime.now(UTC) + timedelta(seconds=30)
    value = parse_retry_after(format_datetime(when, usegmt=True))
    assert value is not None and 25 <= value <= 31
    assert parse_retry_after("garbage") is None
    assert parse_retry_after(None) is None
    assert parse_retry_after("-5") == 0.0


def test_connect_error_retried_even_for_post(client: KentikClient, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.post(TESTS).mock(side_effect=[httpx.ConnectError("refused"), httpx.Response(200, json={})])
    client.synthetics.create_test({"test": {}})
    assert route.call_count == 2


def test_read_timeout_not_retried_for_post(client: KentikClient, mock: respx.MockRouter) -> None:
    route = mock.post(TESTS).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(APITimeoutError) as info:
        client.synthetics.create_test({"test": {}})
    assert route.call_count == 1
    assert info.value.method == "CreateTest"
    assert info.value.request_id


def test_transport_error_retried_for_get_then_raised(client: KentikClient, mock: respx.MockRouter) -> None:
    route = mock.get(TESTS).mock(side_effect=httpx.RemoteProtocolError("reset"))
    with pytest.raises(APIConnectionError) as info:
        client.synthetics.list_tests()
    assert route.call_count == 4
    assert info.value.service == "kentik.synthetics.v202309.SyntheticsAdminService"


def test_retries_disabled(mock: respx.MockRouter) -> None:
    with KentikClient(EMAIL, TOKEN, base_url=BASE_URL, retry=RetryConfig.disabled()) as c:
        route = mock.get(TESTS).respond(503)
        with pytest.raises(ServerError):
            c.synthetics.list_tests()
    assert route.call_count == 1


@pytest.mark.anyio
async def test_async_retry(aclient: AsyncKentikClient, mock: respx.MockRouter, sleeps: list[float]) -> None:
    route = mock.get(TESTS).mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "1"}), httpx.Response(200, json={"tests": []})]
    )
    assert (await aclient.synthetics.list_tests()).tests == []
    assert route.call_count == 2
    assert sleeps == [1.0]
