from __future__ import annotations

import logging

import pytest
import respx

from kentik_api.v6 import (
    APIStatusError,
    AsyncKentikClient,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    KentikClient,
    KentikError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ResponseValidationError,
    RetryConfig,
    ServerError,
)

from .conftest import BASE_URL, EMAIL, TOKEN

AGENT = "/synthetics/v202309/agents/a-1"


@pytest.fixture
def noretry(mock: respx.MockRouter) -> KentikClient:
    return KentikClient(EMAIL, TOKEN, base_url=BASE_URL, retry=RetryConfig.disabled())


@pytest.mark.parametrize(
    ("status", "cls"),
    [
        (400, BadRequestError),
        (401, AuthenticationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (409, ConflictError),
        (429, RateLimitError),
        (500, ServerError),
        (503, ServerError),
        (418, APIStatusError),
    ],
)
def test_status_maps_to_error_class(noretry: KentikClient, mock: respx.MockRouter, status: int, cls: type) -> None:
    mock.get(AGENT).respond(status, json={"code": 5, "message": "agent not found", "details": [{"@type": "x"}]})
    with pytest.raises(cls) as info:
        noretry.synthetics.get_agent("a-1")
    err = info.value
    assert isinstance(err, APIStatusError) and isinstance(err, KentikError)
    assert err.status_code == status
    assert err.grpc_code == 5 and err.grpc_status == "NOT_FOUND"
    assert err.message == "agent not found"
    assert err.details == [{"@type": "x"}]
    assert err.service == "kentik.synthetics.v202309.SyntheticsAdminService"
    assert err.method == "GetAgent"
    assert err.request_id and len(err.request_id) == 32  # client-generated
    assert f"HTTP {status} NOT_FOUND: agent not found" in str(err)
    assert "SyntheticsAdminService/GetAgent" in str(err)


def test_server_request_id_preferred(noretry: KentikClient, mock: respx.MockRouter) -> None:
    mock.get(AGENT).respond(404, headers={"X-Request-Id": "srv-123"}, json={"code": 5, "message": "nope"})
    with pytest.raises(NotFoundError) as info:
        noretry.synthetics.get_agent("a-1")
    assert info.value.request_id == "srv-123"


def test_non_json_error_body(noretry: KentikClient, mock: respx.MockRouter) -> None:
    mock.get(AGENT).respond(502, text="<html>bad gateway</html>")
    with pytest.raises(ServerError) as info:
        noretry.synthetics.get_agent("a-1")
    assert "bad gateway" in info.value.message
    assert info.value.grpc_code is None


def test_invalid_json_success_body(noretry: KentikClient, mock: respx.MockRouter) -> None:
    mock.get(AGENT).respond(200, text="not json")
    with pytest.raises(ResponseValidationError, match="not JSON"):
        noretry.synthetics.get_agent("a-1")


def test_type_mismatch_in_response(noretry: KentikClient, mock: respx.MockRouter) -> None:
    mock.get(AGENT).respond(200, json={"agent": {"lat": "not-a-number"}})
    with pytest.raises(ResponseValidationError) as info:
        noretry.synthetics.get_agent("a-1")
    assert info.value.method == "GetAgent"


def test_empty_success_body(noretry: KentikClient, mock: respx.MockRouter) -> None:
    mock.delete(AGENT).respond(200, content=b"")
    assert noretry.synthetics.delete_agent("a-1").model_dump() == {}


def test_path_parameters_are_escaped(noretry: KentikClient, mock: respx.MockRouter) -> None:
    route = mock.get(url__regex=r"/synthetics/v202309/agents/.*").respond(json={})
    noretry.synthetics.get_agent("a/b c")
    assert route.calls.last.request.url.raw_path == b"/synthetics/v202309/agents/a%2Fb%20c"


def test_missing_path_parameter(noretry: KentikClient) -> None:
    with pytest.raises(ValueError, match="missing path parameter"):
        noretry.synthetics.get_agent("")


def test_logging_never_contains_token(
    noretry: KentikClient, mock: respx.MockRouter, caplog: pytest.LogCaptureFixture
) -> None:
    mock.get(AGENT).respond(200, json={})
    with caplog.at_level(logging.DEBUG, logger="kentik_api.v6"):
        noretry.synthetics.get_agent("a-1")
    assert "GET /synthetics/v202309/agents/a-1 -> 200" in caplog.text
    assert TOKEN not in caplog.text


@pytest.mark.anyio
async def test_async_error(aclient: AsyncKentikClient, mock: respx.MockRouter) -> None:
    mock.get(AGENT).respond(403, json={"code": 7, "message": "denied"})
    with pytest.raises(PermissionDeniedError) as info:
        await aclient.synthetics.get_agent("a-1")
    assert info.value.grpc_status == "PERMISSION_DENIED"
