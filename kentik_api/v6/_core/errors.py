"""Typed errors raised by the v6 client.

Every error carries the gRPC ``service`` and ``method`` it relates to and the ``request_id`` (the id
returned by the server when present, otherwise the ``X-Request-ID`` the client sent).
"""

from __future__ import annotations

from typing import Any

import httpx

# google.rpc.Code
GRPC_CODES: dict[int, str] = {
    0: "OK",
    1: "CANCELLED",
    2: "UNKNOWN",
    3: "INVALID_ARGUMENT",
    4: "DEADLINE_EXCEEDED",
    5: "NOT_FOUND",
    6: "ALREADY_EXISTS",
    7: "PERMISSION_DENIED",
    8: "RESOURCE_EXHAUSTED",
    9: "FAILED_PRECONDITION",
    10: "ABORTED",
    11: "OUT_OF_RANGE",
    12: "UNIMPLEMENTED",
    13: "INTERNAL",
    14: "UNAVAILABLE",
    15: "DATA_LOSS",
    16: "UNAUTHENTICATED",
}


class KentikError(Exception):
    """Base class for all v6 client errors."""

    def __init__(self, message: str, *, service: str = "", method: str = "", request_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.service = service
        self.method = method
        self.request_id = request_id

    def _where(self) -> str:
        parts = []
        if self.service or self.method:
            parts.append(f"{self.service}/{self.method}")
        if self.request_id:
            parts.append(f"request_id={self.request_id}")
        return f" [{', '.join(parts)}]" if parts else ""

    def __str__(self) -> str:
        return f"{self.message}{self._where()}"


class APIConnectionError(KentikError):
    """The request could not be sent or no response was received."""


class APITimeoutError(APIConnectionError):
    """The request timed out."""


class ResponseValidationError(KentikError):
    """The response body could not be decoded or did not match the expected model."""


class APIStatusError(KentikError):
    """The API returned a non-2xx status. The body is the grpc-gateway ``google.rpc.Status`` JSON."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        response: httpx.Response | None = None,
        grpc_code: int | None = None,
        details: list[Any] | None = None,
        service: str = "",
        method: str = "",
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, service=service, method=method, request_id=request_id)
        self.status_code = status_code
        self.response = response
        self.grpc_code = grpc_code
        self.details = details or []

    @property
    def grpc_status(self) -> str | None:
        """Name of the gRPC status code (e.g. ``NOT_FOUND``), if the body carried one."""
        return GRPC_CODES.get(self.grpc_code) if self.grpc_code is not None else None

    def __str__(self) -> str:
        status = f"HTTP {self.status_code}"
        if self.grpc_status:
            status += f" {self.grpc_status}"
        return f"{status}: {self.message}{self._where()}"


class BadRequestError(APIStatusError):
    """400: invalid argument, failed precondition or out of range."""


class AuthenticationError(APIStatusError):
    """401: missing or invalid credentials."""


class PermissionDeniedError(APIStatusError):
    """403: the credentials are valid but not allowed to perform the call."""


class NotFoundError(APIStatusError):
    """404: the resource does not exist."""


class ConflictError(APIStatusError):
    """409: already exists or aborted."""


class RateLimitError(APIStatusError):
    """429: rate limited or resource exhausted."""

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ServerError(APIStatusError):
    """5xx: server-side failure."""


_STATUS_ERRORS: dict[int, type[APIStatusError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    429: RateLimitError,
}


def error_class_for(status_code: int) -> type[APIStatusError]:
    if status_code in _STATUS_ERRORS:
        return _STATUS_ERRORS[status_code]
    if status_code >= 500:
        return ServerError
    return APIStatusError
