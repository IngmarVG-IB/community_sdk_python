# Kentik API Python library

Python client for the [Kentik APIs](https://kb.kentik.com/v0/Ab09.htm), distributed on PyPI as
[`kentik-api`](https://pypi.org/project/kentik-api/) and imported as `kentik_api`.

- **`KentikClient` / `AsyncKentikClient`**: the v6 APIs, generated from
  [kentik/api-schema-public](https://github.com/kentik/api-schema-public). Every stable service version, with
  alpha and beta versions under `client.experimental`. Sync and async, typed (pydantic v2 models, `py.typed`).
- **`KentikAPI`**: the 1.x client for the legacy v5 REST API, synthetics v202202 and cloud_export
  v202101beta1. Deprecated, still working; see [docs/UPGRADING.md](docs/UPGRADING.md).

Requires Python 3.11 or newer.

## Install

```shell
pip install kentik-api            # or: uv add kentik-api
pip install "kentik-api[analytics]"  # pandas helpers for the 1.x query API
```

## Quick start

```python
from kentik_api import KentikClient

# Credentials: arguments, or KTAPI_AUTH_EMAIL / KTAPI_AUTH_TOKEN in the environment.
with KentikClient(email="me@example.com", token="...", region="us") as client:  # region="eu" for the EU cluster
    for test in client.synthetics.list_tests().tests or []:
        print(test.id, test.name, test.status)

    site = client.site.get_site("1234").site
    print(site.title if site else None)
```

Async:

```python
import asyncio
from kentik_api import AsyncKentikClient

async def main() -> None:
    async with AsyncKentikClient() as client:
        sites, labels = await asyncio.gather(client.site.list_sites(), client.label.list_labels())
        print(len(sites.sites or []), len(labels.labels or []))

asyncio.run(main())
```

## Services and versions

Each service version is an attribute named `<service>_<version>`; an alias without the version points to the
newest stable one. Nested packages use `_` (`alerting/public` is `alerting_public`).

```python
client.synthetics_v202309          # exact version (stable)
client.synthetics                  # alias: newest stable version (v202309 today)
client.cloud_export                # cloud_export v202506
client.alerting_public.alert       # alerting/public: newest stable version of each gRPC service
client.experimental.device         # no stable device API yet: newest beta (v202504beta2)
client.experimental.synthetics_v20261005alpha1
```

Within a version, every gRPC service is an attribute (`client.synthetics.synthetics_admin`,
`client.synthetics.synthetics_data`). When method names do not collide, they are also available directly
(`client.synthetics.list_tests()`). Method names are the RPC names in snake_case; path parameters are
positional, query parameters are keyword arguments, and request bodies are either a model or a plain dict:

```python
from kentik_api.v6.services.synthetics_v202309 import models

client.synthetics.update_test("123", models.SyntheticsAdminServiceUpdateTestBody(test=...))
client.synthetics.set_test_status("123", {"status": "TEST_STATUS_PAUSED"})
```

The full list, with stability and status, is in [`kentik-api.json`](kentik-api.json). Three stable services
(`deviceconf`, `diagnostic`, `kptr`) are gRPC-only and are not reachable through this REST client.

### Models

Models are generated from the OpenAPI v3 schema. Fields are snake_case; the API's camelCase names work too.
They are forward-compatible: unknown fields are kept (`model.model_extra`), unknown enum values parse instead
of failing, and every field is optional because the API omits default values. `model.to_api()` returns the JSON
that would be sent.

### Pagination

List RPCs with offset/limit pagination have an `iter_*` twin that fetches every page:

```python
for alert in client.alerting_public.alert.iter_list({"filters": {"states": ["ALERT_STATE_ACTIVE"]}}, page_size=200):
    ...
async for event in aclient.audit_public.iter_list_audit_events(start_time="2026-11-01T00:00:00Z"):
    ...
```

### Timeouts, retries and errors

```python
from kentik_api import KentikClient
from kentik_api.v6 import NotFoundError, RateLimitError, RetryConfig

client = KentikClient(timeout=30, retry=RetryConfig(max_retries=5, max_backoff=20))
try:
    client.synthetics.get_test("42", timeout=5)  # per-call timeout
except NotFoundError as err:
    print(err.status_code, err.grpc_status, err.service, err.method, err.request_id)
```

- Retries use exponential backoff with full jitter. 429 is retried for every call and `Retry-After` is honoured;
  5xx and network errors are retried only for idempotent calls (GET, PUT, DELETE, and read-only POST RPCs such
  as `GetResultsForTests`). `RetryConfig.disabled()` turns retries off.
- Errors derive from `kentik_api.v6.KentikError`: `BadRequestError`, `AuthenticationError`,
  `PermissionDeniedError`, `NotFoundError`, `ConflictError`, `RateLimitError`, `ServerError`, `APIStatusError`
  (other statuses), `APIConnectionError`/`APITimeoutError`, `ResponseValidationError`.
- Requests and retries are logged at DEBUG/WARNING on the `kentik_api.v6` logger. Credentials are never logged.
- Other options: `base_url=` (proxies, test servers), `proxy=`, `user_agent=`, `http_client=` (your own
  `httpx.Client`).

## Examples

- [examples/v6](examples/v6): the v6 client (sync, async, pagination, error handling). CI runs them against an
  offline fake server.
- [examples/](examples): the deprecated 1.x `KentikAPI` client (v5 REST resources, analytics, synthetics v202202,
  cloud export v202101beta1).

## Legacy 1.x client

`kentik_api.KentikAPI` and everything under `kentik_api.public`, `kentik_api.api_calls`, `kentik_api.synthetics`,
`kentik_api.cloudexport`, `kentik_api.utils` and `kentik_api.analytics` keep working as in 1.0.x.
Instantiating `KentikAPI` emits a `DeprecationWarning`. The v5 API is legacy on Kentik's side and gets no new
features here. The 1.x documentation for its resources (devices, sites, users, tags, saved filters, custom
dimensions and applications, plans, tenants, queries, alerting, batch) is in the source files under
[kentik_api/public](kentik_api/public) and in the [analytics readme](kentik_api/analytics/README.md).
`kentik_api.utils.get_credentials` (environment or `~/.kentik/<profile>` JSON profile) still works and its
result can be passed to `KentikClient(email, token)`.

Migration notes: [docs/UPGRADING.md](docs/UPGRADING.md).

## Development

See [AGENTS.md](AGENTS.md): `uv sync`, then `make test lint vuln generate build`. Design decisions are in
[docs/adr](docs/adr). Security reports: [SECURITY.md](SECURITY.md).

## Open-source libraries

Runtime dependencies: [httpx](https://www.python-httpx.org/) (BSD-3-Clause), [pydantic](https://docs.pydantic.dev/)
(MIT), and for the 1.x client [requests](https://pypi.org/project/requests/) (Apache-2.0),
[dacite](https://pypi.org/project/dacite/) (MIT), [protobuf](https://pypi.org/project/protobuf/) (BSD-3-Clause),
[grpcio](https://pypi.org/project/grpcio/) (Apache-2.0),
[googleapis-common-protos](https://pypi.org/project/googleapis-common-protos/) (Apache-2.0) and
[typing-extensions](https://pypi.org/project/typing-extensions/) (PSF). The `analytics` extra adds
[pandas](https://pandas.pydata.org) (BSD-3-Clause), [PyYAML](https://pyyaml.org/) (MIT) and fastparquet (Apache-2.0).
