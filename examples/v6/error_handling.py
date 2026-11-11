"""Timeouts, retries and typed errors.

export KTAPI_AUTH_EMAIL=... KTAPI_AUTH_TOKEN=...
python examples/v6/error_handling.py [test-id]
"""

from __future__ import annotations

import logging
import sys

from kentik_api import KentikClient
from kentik_api.v6 import APIConnectionError, APIStatusError, NotFoundError, RateLimitError, RetryConfig


def main(client: KentikClient, test_id: str) -> None:
    try:
        test = client.synthetics.get_test(test_id, timeout=10).test
        print(f"found test {test.id if test else '?'}: {test.name if test else ''}")
    except NotFoundError as err:
        print(f"no test {test_id} (gRPC {err.grpc_status}, request id {err.request_id})")
    except RateLimitError as err:
        print(f"still rate limited after retries; server asked to wait {err.retry_after}s")
    except APIStatusError as err:
        print(f"{err.service}/{err.method} failed with HTTP {err.status_code}: {err.message}")
    except APIConnectionError as err:
        print(f"could not reach the API: {err}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # shows each request and retry; credentials are never logged
    retry = RetryConfig(max_retries=5, initial_backoff=1.0, max_backoff=20.0)
    with KentikClient(retry=retry, timeout=30) as kentik:
        main(kentik, sys.argv[1] if len(sys.argv) > 1 else "0")
