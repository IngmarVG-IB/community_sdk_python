from __future__ import annotations

import httpx
import pytest
import respx

from kentik_api import AsyncKentikClient, KentikClient
from kentik_api.v6 import REGION_BASE_URLS, Region

from .conftest import BASE_URL, EMAIL, TOKEN


def test_region_presets() -> None:
    assert KentikClient(EMAIL, TOKEN).base_url == "https://grpc.api.kentik.com"
    assert KentikClient(EMAIL, TOKEN, region="eu").base_url == "https://grpc.api.kentik.eu"
    assert KentikClient(EMAIL, TOKEN, region=Region.US).base_url == REGION_BASE_URLS[Region.US]
    assert KentikClient(EMAIL, TOKEN, region="EU").base_url == REGION_BASE_URLS[Region.EU]


def test_custom_base_url_strips_trailing_slash() -> None:
    assert KentikClient(EMAIL, TOKEN, base_url="http://localhost:8080/").base_url == "http://localhost:8080"


def test_region_and_base_url_are_exclusive() -> None:
    with pytest.raises(ValueError, match="either region"):
        KentikClient(EMAIL, TOKEN, region="eu", base_url=BASE_URL)


def test_unknown_region() -> None:
    with pytest.raises(ValueError, match="unknown region"):
        KentikClient(EMAIL, TOKEN, region="mars")


def test_credentials_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KTAPI_AUTH_EMAIL", "env@example.com")
    monkeypatch.setenv("KTAPI_AUTH_TOKEN", "env-token")
    assert KentikClient().config.email == "env@example.com"


def test_missing_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KTAPI_AUTH_EMAIL", raising=False)
    monkeypatch.delenv("KTAPI_AUTH_TOKEN", raising=False)
    with pytest.raises(ValueError, match="credentials missing"):
        KentikClient()


def test_repr_does_not_leak_token() -> None:
    c = KentikClient(EMAIL, TOKEN)
    assert TOKEN not in repr(c)
    assert TOKEN not in repr(c.config)


def test_timeout_configuration() -> None:
    assert KentikClient(EMAIL, TOKEN, timeout=5).config.timeout == httpx.Timeout(5)
    custom = httpx.Timeout(3, connect=1)
    assert KentikClient(EMAIL, TOKEN, timeout=custom).config.timeout is custom


def test_auth_and_identity_headers(client: KentikClient, mock: respx.MockRouter) -> None:
    route = mock.get("/synthetics/v202309/tests").respond(json={"tests": []})
    client.synthetics.list_tests()
    req = route.calls.last.request
    assert req.headers["X-CH-Auth-Email"] == EMAIL
    assert req.headers["X-CH-Auth-API-Token"] == TOKEN
    assert req.headers["Accept"] == "application/json"
    assert req.headers["User-Agent"].startswith("kentik-api-python/")
    assert len(req.headers["X-Request-ID"]) == 32


def test_per_call_timeout_is_applied(client: KentikClient, mock: respx.MockRouter) -> None:
    route = mock.get("/synthetics/v202309/tests").respond(json={})
    client.synthetics.list_tests(timeout=1.5)
    assert route.calls.last.request.extensions["timeout"]["read"] == 1.5


def test_injected_http_client_is_not_closed(mock: respx.MockRouter) -> None:
    http = httpx.Client()
    with KentikClient(EMAIL, TOKEN, base_url=BASE_URL, http_client=http) as c:
        mock.get("/synthetics/v202309/agents").respond(json={"agents": []})
        assert c.synthetics.list_agents().agents == []
    assert not http.is_closed
    http.close()


@pytest.mark.anyio
async def test_async_client_headers(aclient: AsyncKentikClient, mock: respx.MockRouter) -> None:
    route = mock.get("/synthetics/v202309/tests").respond(json={"tests": [{"id": "1", "name": "t"}]})
    resp = await aclient.synthetics.list_tests()
    assert resp.tests and resp.tests[0].name == "t"
    assert route.calls.last.request.headers["X-CH-Auth-API-Token"] == TOKEN
