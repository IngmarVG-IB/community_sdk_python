"""The v6 clients: :class:`KentikClient` (sync) and :class:`AsyncKentikClient` (async)."""

from __future__ import annotations

from types import TracebackType

import httpx

from ._core.config import ClientConfig, Region, RetryConfig
from ._core.transport import AsyncTransport, SyncTransport
from ._services import _AsyncStableServices, _StableServices


class KentikClient(_StableServices):
    """Synchronous client for the Kentik v6 APIs (REST over grpc-gateway).

    Every stable service version is an attribute (``client.synthetics_v202309``), with an alias for the
    newest one (``client.synthetics``). Alpha and beta versions are under ``client.experimental``.

    Args:
        email: Kentik user email (``X-CH-Auth-Email``). Defaults to ``$KTAPI_AUTH_EMAIL``.
        token: API token (``X-CH-Auth-API-Token``). Defaults to ``$KTAPI_AUTH_TOKEN``.
        region: ``"us"`` (default) or ``"eu"``. Mutually exclusive with ``base_url``.
        base_url: API root, e.g. ``https://grpc.api.kentik.com`` or a proxy/mock.
        timeout: seconds or an ``httpx.Timeout`` (default: 60 s, 10 s to connect). Per-call ``timeout=``
            overrides it.
        retry: :class:`RetryConfig`; ``RetryConfig.disabled()`` turns retries off.
        proxy: proxy URL passed to httpx.
        user_agent: override the ``User-Agent`` header.
        http_client: a pre-configured ``httpx.Client`` (the client does not close it).

    Use as a context manager, or call :meth:`close`.
    """

    def __init__(
        self,
        email: str | None = None,
        token: str | None = None,
        *,
        region: Region | str | None = None,
        base_url: str | None = None,
        timeout: float | httpx.Timeout | None = None,
        retry: RetryConfig | None = None,
        proxy: str | None = None,
        user_agent: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.config = ClientConfig.resolve(
            email,
            token,
            region=region,
            base_url=base_url,
            timeout=timeout,
            retry=retry,
            user_agent=user_agent,
            proxy=proxy,
        )
        self._transport = SyncTransport(self.config, http_client)

    @property
    def base_url(self) -> str:
        return self.config.base_url

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> KentikClient:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"KentikClient(base_url={self.config.base_url!r}, email={self.config.email!r})"


class AsyncKentikClient(_AsyncStableServices):
    """Asynchronous twin of :class:`KentikClient`; every service method is a coroutine.

    Takes the same arguments, except ``http_client`` is an ``httpx.AsyncClient``. Use ``async with`` or
    ``await client.aclose()``.
    """

    def __init__(
        self,
        email: str | None = None,
        token: str | None = None,
        *,
        region: Region | str | None = None,
        base_url: str | None = None,
        timeout: float | httpx.Timeout | None = None,
        retry: RetryConfig | None = None,
        proxy: str | None = None,
        user_agent: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = ClientConfig.resolve(
            email,
            token,
            region=region,
            base_url=base_url,
            timeout=timeout,
            retry=retry,
            user_agent=user_agent,
            proxy=proxy,
        )
        self._transport = AsyncTransport(self.config, http_client)

    @property
    def base_url(self) -> str:
        return self.config.base_url

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncKentikClient:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        return f"AsyncKentikClient(base_url={self.config.base_url!r}, email={self.config.email!r})"
