"""Fixtures for offline v6 client tests.

The fake server is respx: every test mocks ``BASE_URL`` routes, so no request leaves the process.
Retries are fast and deterministic: jitter is off and ``sleep`` only records the delays.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import respx

from kentik_api.v6 import AsyncKentikClient, KentikClient, RetryConfig

BASE_URL = "https://kentik.test"
EMAIL = "tester@example.com"
TOKEN = "test-token"  # not a secret


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=BASE_URL, assert_all_called=False, assert_all_mocked=True) as router:
        yield router


@pytest.fixture
def sleeps() -> list[float]:
    return []


@pytest.fixture
def retry() -> RetryConfig:
    return RetryConfig(max_retries=3, initial_backoff=0.5, multiplier=2.0, max_backoff=4.0, jitter=False)


@pytest.fixture
def client(mock: respx.MockRouter, sleeps: list[float], retry: RetryConfig) -> Iterator[KentikClient]:
    with KentikClient(EMAIL, TOKEN, base_url=BASE_URL, retry=retry) as c:
        c._transport.sleep = sleeps.append
        yield c


@pytest.fixture
async def aclient(mock: respx.MockRouter, sleeps: list[float], retry: RetryConfig) -> AsyncIterator[AsyncKentikClient]:
    async def record(delay: float) -> None:
        sleeps.append(delay)

    async with AsyncKentikClient(EMAIL, TOKEN, base_url=BASE_URL, retry=retry) as c:
        c._transport.sleep = record
        yield c
