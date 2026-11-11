"""Kentik v6 API client (REST over grpc-gateway), generated from kentik/api-schema-public.

>>> from kentik_api import KentikClient
>>> with KentikClient(email="me@example.com", token="...", region="eu") as client:  # doctest: +SKIP
...     for test in client.synthetics.list_tests().tests or []:
...         print(test.id, test.name)
"""

from ._client import AsyncKentikClient, KentikClient
from ._core.config import REGION_BASE_URLS, Region, RetryConfig
from ._core.errors import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    KentikError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    ResponseValidationError,
    ServerError,
)
from ._core.models import KentikModel, OpenEnum

__all__ = [
    "REGION_BASE_URLS",
    "APIConnectionError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncKentikClient",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "KentikClient",
    "KentikError",
    "KentikModel",
    "NotFoundError",
    "OpenEnum",
    "PermissionDeniedError",
    "RateLimitError",
    "Region",
    "ResponseValidationError",
    "RetryConfig",
    "ServerError",
]
