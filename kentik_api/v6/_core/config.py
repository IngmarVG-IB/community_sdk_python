"""Client configuration: regions, timeouts and retry policy."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import StrEnum

import httpx

from ...version import __version__

ENV_EMAIL = "KTAPI_AUTH_EMAIL"
ENV_TOKEN = "KTAPI_AUTH_TOKEN"  # noqa: S105 - variable name, not a secret

# Auth header names as declared in the api-schema-public securitySchemes.
HEADER_EMAIL = "X-CH-Auth-Email"
HEADER_TOKEN = "X-CH-Auth-API-Token"  # noqa: S105 - header name, not a secret
HEADER_REQUEST_ID = "X-Request-ID"


class Region(StrEnum):
    """Kentik data-centre regions. Use ``base_url`` for anything else."""

    US = "us"
    EU = "eu"


REGION_BASE_URLS: dict[Region, str] = {
    Region.US: "https://grpc.api.kentik.com",
    Region.EU: "https://grpc.api.kentik.eu",
}

DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


@dataclass(frozen=True)
class RetryConfig:
    """Retry policy.

    * 429 responses are retried for every call: the request was rejected before it was processed.
    * 5xx responses in ``retry_statuses`` and transport errors after the request may have been sent are
      retried only for idempotent calls. Connection failures (nothing sent) are always retried.
    * Delay: ``Retry-After`` when the server sends it (capped at ``max_retry_after``), otherwise
      exponential backoff ``initial_backoff * multiplier**attempt`` capped at ``max_backoff``, with full
      jitter when ``jitter`` is true.
    """

    max_retries: int = 3
    initial_backoff: float = 0.5
    max_backoff: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True
    retry_statuses: frozenset[int] = field(default_factory=lambda: frozenset({429, 500, 502, 503, 504}))
    max_retry_after: float = 120.0

    @classmethod
    def disabled(cls) -> RetryConfig:
        return cls(max_retries=0)


def default_user_agent() -> str:
    py = f"{sys.version_info.major}.{sys.version_info.minor}"
    return f"kentik-api-python/{__version__} (+https://github.com/kentik/community_sdk_python) python/{py}"


@dataclass(frozen=True)
class ClientConfig:
    """Resolved settings shared by the sync and async clients."""

    email: str
    token: str = field(repr=False)
    base_url: str
    timeout: httpx.Timeout
    retry: RetryConfig
    user_agent: str
    proxy: str | None = None

    @classmethod
    def resolve(
        cls,
        email: str | None,
        token: str | None,
        *,
        region: Region | str | None,
        base_url: str | None,
        timeout: float | httpx.Timeout | None,
        retry: RetryConfig | None,
        user_agent: str | None,
        proxy: str | None,
    ) -> ClientConfig:
        email = email or os.environ.get(ENV_EMAIL)
        token = token or os.environ.get(ENV_TOKEN)
        if not email or not token:
            raise ValueError(f"Kentik credentials missing: pass email= and token=, or set {ENV_EMAIL} and {ENV_TOKEN}")
        if base_url and region:
            raise ValueError("pass either region= or base_url=, not both")
        if base_url:
            url = base_url
        else:
            try:
                url = REGION_BASE_URLS[Region(str(region or Region.US).lower())]
            except ValueError:
                raise ValueError(
                    f"unknown region {region!r}; use one of {[r.value for r in Region]} or base_url="
                ) from None
        if timeout is None:
            resolved_timeout = DEFAULT_TIMEOUT
        elif isinstance(timeout, httpx.Timeout):
            resolved_timeout = timeout
        else:
            resolved_timeout = httpx.Timeout(timeout)
        return cls(
            email=email,
            token=token,
            base_url=url.rstrip("/"),
            timeout=resolved_timeout,
            retry=retry or RetryConfig(),
            user_agent=user_agent or default_user_agent(),
            proxy=proxy,
        )

    def headers(self) -> dict[str, str]:
        return {
            HEADER_EMAIL: self.email,
            HEADER_TOKEN: self.token,
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }
