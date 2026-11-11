# v6 client examples

Runnable against a real tenant; they only read data. Credentials come from `KTAPI_AUTH_EMAIL` and
`KTAPI_AUTH_TOKEN`.

| file | shows |
|---|---|
| [synthetics_overview.py](synthetics_overview.py) | sync client, region selection, list tests and agents |
| [async_inventory.py](async_inventory.py) | `AsyncKentikClient`, concurrent calls with `asyncio.gather` |
| [alerts_pagination.py](alerts_pagination.py) | typed request models, `iter_*` pagination |
| [error_handling.py](error_handling.py) | timeouts, `RetryConfig`, typed errors, debug logging |

CI runs each `main()` against the offline fake server in `tests/v6/test_examples.py`; it never calls Kentik.
The scripts in the parent directory use the deprecated 1.x `KentikAPI` client.
