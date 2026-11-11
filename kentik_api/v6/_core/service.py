"""Base classes for generated service wrappers, including offset/limit pagination."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from typing import Any

from .endpoint import Endpoint, Pagination
from .models import KentikModel
from .transport import AsyncTransport, SyncTransport, Timeout, encode_body

DEFAULT_PAGE_SIZE = 100


def _set_dotted(target: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    for part in parts[:-1]:
        nxt = target.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            target[part] = nxt
        target = nxt
    target[parts[-1]] = value


def _page_request(
    page: Pagination, query: Mapping[str, Any] | None, body: Any, offset: int, limit: int
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    q = dict(query or {})
    b = encode_body(body)
    if page.location == "query":
        q[page.limit] = limit
        q[page.offset] = offset
    else:
        b = dict(b or {})
        # uint64 pagination fields are strings in the schema; protojson accepts both.
        _set_dotted(b, page.limit, str(limit))
        _set_dotted(b, page.offset, str(offset))
    return q, b


def _int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _page_items(page: Pagination, response: KentikModel) -> list[Any]:
    items = getattr(response, page.items, None)
    return list(items or [])


def _has_more(response: KentikModel, items: list[Any], page_size: int, next_offset: int) -> bool:
    if not items or len(items) < page_size:
        return False
    info = getattr(response, "pagination", None)
    more = getattr(info, "has_more_results", None)
    if more is False:
        return False
    total = _int(getattr(info, "total_count", None)) or _int(getattr(response, "total_count", None))
    return not (total is not None and next_offset >= total)


class SyncService:
    """Base for generated synchronous service wrappers."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def _paginate(
        self,
        endpoint: Endpoint[Any],
        page: Pagination,
        *,
        path: Mapping[str, Any] | None,
        query: Mapping[str, Any] | None,
        body: Any,
        page_size: int,
        timeout: Timeout,
    ) -> Iterator[Any]:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        offset = 0
        while True:
            q, b = _page_request(page, query, body, offset, page_size)
            response = self._transport.request(endpoint, path=path, query=q, body=b, timeout=timeout)
            items = _page_items(page, response)
            yield from items
            offset += len(items)
            if not _has_more(response, items, page_size, offset):
                return


class AsyncService:
    """Base for generated asynchronous service wrappers."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def _paginate(
        self,
        endpoint: Endpoint[Any],
        page: Pagination,
        *,
        path: Mapping[str, Any] | None,
        query: Mapping[str, Any] | None,
        body: Any,
        page_size: int,
        timeout: Timeout,
    ) -> AsyncIterator[Any]:
        if page_size <= 0:
            raise ValueError("page_size must be positive")
        offset = 0
        while True:
            q, b = _page_request(page, query, body, offset, page_size)
            response = await self._transport.request(endpoint, path=path, query=q, body=b, timeout=timeout)
            items = _page_items(page, response)
            for item in items:
                yield item
            offset += len(items)
            if not _has_more(response, items, page_size, offset):
                return
