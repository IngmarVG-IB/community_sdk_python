"""Static description of one REST binding of a gRPC method (emitted by the generator)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Literal, TypeVar

from .models import KentikModel

R = TypeVar("R", bound=KentikModel)

_SAFE_PREFIXES = ("Get", "List", "Search", "Query", "Fetch", "Find")


@dataclass(frozen=True)
class Pagination:
    """Offset/limit pagination of a list RPC.

    ``location`` is ``query`` (``limit``/``offset`` are query parameters, possibly dotted such as
    ``pagination.limit``) or ``body`` (dotted paths into the JSON request body). ``items`` is the
    attribute of the response model holding the page.
    """

    location: Literal["query", "body"]
    limit: str
    offset: str
    items: str


@dataclass(frozen=True)
class Endpoint(Generic[R]):
    service: str
    """Fully qualified gRPC service, e.g. ``kentik.synthetics.v202309.SyntheticsAdminService``."""
    method: str
    """RPC name, e.g. ``ListTests``."""
    http_method: str
    path: str
    """grpc-gateway path template, e.g. ``/synthetics/v202309/agents/{agent.id}``."""
    response: type[R]
    idempotent: bool
    has_body: bool = False

    @staticmethod
    def is_idempotent(http_method: str, rpc: str) -> bool:
        if http_method.upper() in {"GET", "HEAD", "OPTIONS", "PUT", "DELETE"}:
            return True
        return rpc.startswith(_SAFE_PREFIXES)
