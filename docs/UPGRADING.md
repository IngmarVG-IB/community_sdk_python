# Upgrading from 1.0.x to 2.0

2.0 adds a generated client for the current Kentik v6 APIs and modernises packaging. Code written against
1.0.x keeps working, with the exceptions listed under "Breaking changes".

## Breaking changes

| change | what to do |
|---|---|
| Python 3.8, 3.9 and 3.10 are no longer supported (`requires-python >=3.11`). | Upgrade Python, or pin `kentik-api<2`. |
| protobuf runtime moved from 4.x to `>=7.35.1,<8`, grpcio to `>=1.85.1`. The legacy stubs in `kentik_api.generated` are regenerated for this runtime. | If another package pins protobuf 4–6, resolve the conflict or stay on 1.0.x. |
| `protoc-gen-openapiv2` (0.0.1) is no longer a dependency; its modules are generated inside `kentik_api.generated`. | Nothing, unless your own code imported `protoc_gen_openapiv2` from that package: depend on it directly. |
| Exact dependency pins (`requests==`, `dacite==1.6.0`, `typing-extensions==4.3.0`, `urllib3==1.26.12`, …) are now ranges. urllib3 2.x is used. | Nothing for most users. Code passing a `urllib3.Retry` with removed 1.x arguments (e.g. `method_whitelist`) must use the 2.x names (`allowed_methods`). |
| `setup.py` and its commands (`python setup.py grpc_stubs/pytest/format/mypy`), `requirements*.txt` are removed. | Development: `uv sync`, `make test lint generate` (see AGENTS.md). |

## Deprecations

`kentik_api.KentikAPI` emits a `DeprecationWarning` when instantiated. It covers:

- the v5 REST API (`api.kentik.com/api/v5`), which Kentik treats as legacy;
- `KentikAPI.synthetics`: synthetics **v202202**, removed from api-schema-public;
- `KentikAPI.cloud_export`: cloud_export **v202101beta1**, superseded by v202506.

To silence it while you migrate:

```python
import warnings
warnings.filterwarnings("ignore", message="kentik_api.KentikAPI is deprecated", category=DeprecationWarning)
```

## Moving to the v6 client

```python
# 1.0.x
from kentik_api import KentikAPI
api = KentikAPI(email, token, api_host=KentikAPI.API_HOST_EU)
tests = api.synthetics.get_all_tests()

# 2.0
from kentik_api import KentikClient
client = KentikClient(email, token, region="eu")
tests = client.synthetics.list_tests().tests or []
```

| 1.0.x | 2.0 v6 client |
|---|---|
| `KentikAPI(email, token, api_host=...)` | `KentikClient(email, token, region="us" \| "eu")` or `base_url=` |
| `kentik_api.utils.get_credentials()` | still works: `KentikClient(*get_credentials())`; or set `KTAPI_AUTH_EMAIL`/`KTAPI_AUTH_TOKEN` |
| `timeout=(10.0, 60.0)` | `timeout=httpx.Timeout(60, connect=10)` (the default), or seconds; per call `timeout=` |
| `retry_strategy=urllib3.Retry(...)` | `retry=RetryConfig(max_retries=..., initial_backoff=..., max_backoff=...)` |
| `proxy="socks5://..."` | `proxy="http://..."` (httpx; SOCKS needs `httpx[socks]`) |
| `api.synthetics.get_all_tests()` | `client.synthetics.list_tests().tests` |
| `api.synthetics.get_test(id)` | `client.synthetics.get_test(id).test` |
| `api.synthetics.create_test(test)` | `client.synthetics.create_test({"test": {...}})` or `models.CreateTestRequest(test=models.Test(...))` |
| `api.synthetics.set_test_status(id, status)` | `client.synthetics.set_test_status(id, {"status": "TEST_STATUS_PAUSED"})` |
| `api.synthetics.results_for_tests(...)` | `client.synthetics.get_results_for_tests({...})` |
| `api.synthetics.get_all_agents()` | `client.synthetics.list_agents().agents` |
| `api.cloud_export.get_all()` | `client.cloud_export.list_cloud_exports().exports` (v202506) |
| `api.sites.get_all()` (v5) | `client.site.list_sites().sites` (site v202509) |
| `api.users.get_all()` (v5) | `client.user.list_users().users` (user v202211) |
| `api.device_labels.get_all()` (v5) | `client.label.list_labels().labels` (label v202210) |
| `api.devices.get_all()` (v5) | `client.experimental.device.list_devices()` (device v202504beta2; beta) |
| `api.custom_dimensions`, `api.custom_applications`, `api.saved_filters`, `api.plans` (v5) | `client.experimental.custom_dimension`, `.custom_application`, `.saved_filter`, `.plan` (alpha) |
| `api.my_kentik_portal` (v5) | `client.mkp` (mkp v202407) |
| `api.query`, `api.tags`, `api.batch`, `api.alerting` (v5) | no v6 equivalent with the same scope; keep using `KentikAPI` (alerting policies and alerts: `client.alerting_public`) |
| `kentik_api.public.errors.*` | `kentik_api.v6.KentikError` and subclasses (`NotFoundError`, `RateLimitError`, …) |
| dataclass models in `kentik_api.public` / protobuf messages | pydantic models in `kentik_api.v6.services.<service>_<version>.models` |

Differences worth knowing:

- Responses are the RPC response messages: `list_tests()` returns `ListTestsResponse` with a `tests` list, not
  a bare list. Fields are optional; use `or []` / `or ""` where you need a value.
- IDs are strings in v6 (they were `int`-like `ID` values in v5).
- Enum fields are open `StrEnum`s; compare with the enum member or the string.
- `client.experimental.*` versions are alpha or beta: Kentik may change them without notice.

## Recommended version

Release this as **2.0.0**. Dropping Python 3.8–3.10 and moving the protobuf runtime from 4.x to 7.x can break
existing installs, which under semantic versioning needs a major version, even though the 1.x API is kept.
The v6 client is additive and would otherwise fit a minor release.
