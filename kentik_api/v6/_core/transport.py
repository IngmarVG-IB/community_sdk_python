"""HTTP transport for the v6 client: request building, retries, error mapping and logging."""

from __future__ import annotations

import asyncio
import email.utils
import logging
import random
import re
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TypeVar
from urllib.parse import quote

import httpx
import pydantic

from .config import HEADER_REQUEST_ID, ClientConfig
from .endpoint import Endpoint
from .errors import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
    ResponseValidationError,
    error_class_for,
)
from .models import KentikModel

log = logging.getLogger("kentik_api.v6")

R = TypeVar("R", bound=KentikModel)
Timeout = float | httpx.Timeout | None

_PATH_PARAM = re.compile(r"\{([^}=]+)(?:=[^}]*)?\}")
_RESPONSE_REQUEST_ID_HEADERS = (
    "x-request-id",
    "x-kentik-request-id",
    "request-id",
    "grpc-metadata-x-request-id",
)


def _query_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Enum):
        return str(value.value)
    if isinstance(value, datetime):
        dt: datetime = value if value.tzinfo else value.replace(tzinfo=UTC)
        return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return str(value)


QueryValue = str | int | float | bool | None


def encode_query(query: Mapping[str, Any] | None) -> list[tuple[str, QueryValue]]:
    params: list[tuple[str, QueryValue]] = []
    for name, value in (query or {}).items():
        if value is None:
            continue
        if isinstance(value, list | tuple | set | frozenset):
            params.extend((name, _query_value(v)) for v in value)
        else:
            params.append((name, _query_value(value)))
    return params


def render_path(template: str, path_params: Mapping[str, Any] | None) -> str:
    params = path_params or {}

    def sub(m: re.Match[str]) -> str:
        name = m.group(1)
        if name not in params or params[name] is None or params[name] == "":
            raise ValueError(f"missing path parameter {name!r} for {template}")
        return quote(_query_value(params[name]), safe="")

    return _PATH_PARAM.sub(sub, template)


def encode_body(body: KentikModel | Mapping[str, Any] | None) -> dict[str, Any] | None:
    if body is None:
        return None
    if isinstance(body, KentikModel):
        return body.to_api()
    if isinstance(body, pydantic.BaseModel):
        return body.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(body, Mapping):
        return dict(body)
    raise TypeError(f"request body must be a model or a mapping, not {type(body).__name__}")


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


class _Attempt:
    """Outcome of one HTTP attempt: either a response or a transport exception."""

    __slots__ = ("error", "response")

    def __init__(self, response: httpx.Response | None = None, error: httpx.TransportError | None = None) -> None:
        self.response = response
        self.error = error


class BaseTransport:
    def __init__(self, config: ClientConfig) -> None:
        self.config = config
        self._random = random.Random()  # noqa: S311 - jitter, not cryptography

    # -- request construction -------------------------------------------------------------------
    def build_request(
        self,
        client: httpx.Client | httpx.AsyncClient,
        endpoint: Endpoint[Any],
        *,
        path: Mapping[str, Any] | None,
        query: Mapping[str, Any] | None,
        body: Any,
        timeout: Timeout,
        request_id: str,
    ) -> httpx.Request:
        url = self.config.base_url + render_path(endpoint.path, path)
        json_body = encode_body(body)
        if endpoint.has_body and json_body is None:
            json_body = {}
        headers = {**self.config.headers(), HEADER_REQUEST_ID: request_id}
        if timeout is None:
            return client.build_request(
                endpoint.http_method,
                url,
                params=encode_query(query),
                json=json_body,
                headers=headers,
            )
        return client.build_request(
            endpoint.http_method,
            url,
            params=encode_query(query),
            json=json_body,
            headers=headers,
            timeout=timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout),
        )

    # -- retry policy ---------------------------------------------------------------------------
    def retry_delay(self, endpoint: Endpoint[Any], attempt: int, outcome: _Attempt) -> float | None:
        """Seconds to wait before the next attempt, or None if the call must not be retried."""
        policy = self.config.retry
        if attempt >= policy.max_retries:
            return None
        retry_after: float | None = None
        if outcome.response is not None:
            status = outcome.response.status_code
            if status not in policy.retry_statuses:
                return None
            if status != 429 and not endpoint.idempotent:
                return None
            retry_after = parse_retry_after(outcome.response.headers.get("Retry-After"))
        elif outcome.error is not None:
            nothing_sent = isinstance(outcome.error, httpx.ConnectError | httpx.ConnectTimeout)
            if not (nothing_sent or endpoint.idempotent):
                return None
        if retry_after is not None:
            return min(retry_after, policy.max_retry_after)
        backoff = min(policy.max_backoff, policy.initial_backoff * policy.multiplier**attempt)
        return self._random.uniform(0, backoff) if policy.jitter else backoff

    # -- response handling ----------------------------------------------------------------------
    @staticmethod
    def request_id_of(response: httpx.Response | None, sent: str) -> str:
        if response is not None:
            for name in _RESPONSE_REQUEST_ID_HEADERS:
                if value := response.headers.get(name):
                    return str(value)
        return sent

    def handle(self, endpoint: Endpoint[R], outcome: _Attempt, request_id: str) -> R:
        if outcome.error is not None:
            cls = APITimeoutError if isinstance(outcome.error, httpx.TimeoutException) else APIConnectionError
            raise cls(
                f"{type(outcome.error).__name__}: {outcome.error}",
                service=endpoint.service,
                method=endpoint.method,
                request_id=request_id,
            ) from outcome.error
        response = outcome.response
        assert response is not None
        rid = self.request_id_of(response, request_id)
        if not response.is_success:
            raise self.status_error(endpoint, response, rid)
        if not response.content or not response.content.strip():
            data: Any = {}
        else:
            try:
                data = response.json()
            except ValueError as exc:
                raise ResponseValidationError(
                    f"response is not JSON: {exc}", service=endpoint.service, method=endpoint.method, request_id=rid
                ) from exc
        try:
            return endpoint.response.model_validate(data)
        except pydantic.ValidationError as exc:
            raise ResponseValidationError(
                f"response does not match {endpoint.response.__name__}: {exc}",
                service=endpoint.service,
                method=endpoint.method,
                request_id=rid,
            ) from exc

    @staticmethod
    def status_error(endpoint: Endpoint[Any], response: httpx.Response, request_id: str) -> APIStatusError:
        message = response.reason_phrase or "error"
        grpc_code: int | None = None
        details: list[Any] = []
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            message = str(payload.get("message") or payload.get("error") or message)
            code = payload.get("code")
            grpc_code = code if isinstance(code, int) else None
            raw_details = payload.get("details")
            details = raw_details if isinstance(raw_details, list) else []
        elif response.text:
            message = response.text[:500]
        kwargs: dict[str, Any] = {
            "status_code": response.status_code,
            "response": response,
            "grpc_code": grpc_code,
            "details": details,
            "service": endpoint.service,
            "method": endpoint.method,
            "request_id": request_id,
        }
        cls = error_class_for(response.status_code)
        if cls is RateLimitError:
            return RateLimitError(message, retry_after=parse_retry_after(response.headers.get("Retry-After")), **kwargs)
        return cls(message, **kwargs)

    @staticmethod
    def _log_attempt(
        endpoint: Endpoint[Any], request: httpx.Request, outcome: _Attempt, elapsed: float, rid: str
    ) -> None:
        if not log.isEnabledFor(logging.DEBUG):
            return
        result = str(outcome.response.status_code) if outcome.response is not None else type(outcome.error).__name__
        log.debug(
            "%s %s -> %s in %.3fs (%s/%s request_id=%s)",
            request.method,
            request.url.path,
            result,
            elapsed,
            endpoint.service,
            endpoint.method,
            rid,
        )

    @staticmethod
    def _log_retry(endpoint: Endpoint[Any], outcome: _Attempt, attempt: int, delay: float, rid: str) -> None:
        reason = (
            f"HTTP {outcome.response.status_code}" if outcome.response is not None else type(outcome.error).__name__
        )
        log.warning(
            "retrying %s/%s after %s (attempt %d, sleeping %.2fs, request_id=%s)",
            endpoint.service,
            endpoint.method,
            reason,
            attempt + 1,
            delay,
            rid,
        )


class SyncTransport(BaseTransport):
    def __init__(self, config: ClientConfig, http_client: httpx.Client | None = None) -> None:
        super().__init__(config)
        self._owns_client = http_client is None
        self.http = http_client or httpx.Client(timeout=config.timeout, proxy=config.proxy)
        self.sleep: Callable[[float], None] = time.sleep

    def close(self) -> None:
        if self._owns_client:
            self.http.close()

    def request(
        self,
        endpoint: Endpoint[R],
        *,
        path: Mapping[str, Any] | None = None,
        query: Mapping[str, Any] | None = None,
        body: Any = None,
        timeout: Timeout = None,
    ) -> R:
        request_id = uuid.uuid4().hex
        attempt = 0
        while True:
            request = self.build_request(
                self.http, endpoint, path=path, query=query, body=body, timeout=timeout, request_id=request_id
            )
            started = time.monotonic()
            try:
                response = self.http.send(request)
                response.read()
                outcome = _Attempt(response=response)
            except httpx.TransportError as exc:
                outcome = _Attempt(error=exc)
            rid = self.request_id_of(outcome.response, request_id)
            self._log_attempt(endpoint, request, outcome, time.monotonic() - started, rid)
            delay = self.retry_delay(endpoint, attempt, outcome)
            if delay is None:
                return self.handle(endpoint, outcome, request_id)
            self._log_retry(endpoint, outcome, attempt, delay, rid)
            self.sleep(delay)
            attempt += 1


class AsyncTransport(BaseTransport):
    def __init__(self, config: ClientConfig, http_client: httpx.AsyncClient | None = None) -> None:
        super().__init__(config)
        self._owns_client = http_client is None
        self.http = http_client or httpx.AsyncClient(timeout=config.timeout, proxy=config.proxy)
        self.sleep: Callable[[float], Awaitable[None]] = asyncio.sleep

    async def aclose(self) -> None:
        if self._owns_client:
            await self.http.aclose()

    async def request(
        self,
        endpoint: Endpoint[R],
        *,
        path: Mapping[str, Any] | None = None,
        query: Mapping[str, Any] | None = None,
        body: Any = None,
        timeout: Timeout = None,
    ) -> R:
        request_id = uuid.uuid4().hex
        attempt = 0
        while True:
            request = self.build_request(
                self.http, endpoint, path=path, query=query, body=body, timeout=timeout, request_id=request_id
            )
            started = time.monotonic()
            try:
                response = await self.http.send(request)
                await response.aread()
                outcome = _Attempt(response=response)
            except httpx.TransportError as exc:
                outcome = _Attempt(error=exc)
            rid = self.request_id_of(outcome.response, request_id)
            self._log_attempt(endpoint, request, outcome, time.monotonic() - started, rid)
            delay = self.retry_delay(endpoint, attempt, outcome)
            if delay is None:
                return self.handle(endpoint, outcome, request_id)
            self._log_retry(endpoint, outcome, attempt, delay, rid)
            await self.sleep(delay)
            attempt += 1
