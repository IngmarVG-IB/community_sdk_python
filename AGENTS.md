# AGENTS.md

Guide for maintainers and coding agents working on `kentik-api`, the community Python SDK for the
[Kentik APIs](https://kb.kentik.com/v0/Ab09.htm). `CLAUDE.md` imports this file.

## Purpose

Python client for Kentik:
- **v6 APIs** (gRPC services exposed as REST through grpc-gateway), defined in
  [kentik/api-schema-public](https://github.com/kentik/api-schema-public).
- **v5 REST** (`/api/v5/...`): legacy, deprecated, kept working for existing users. Do not extend it.

Two clients live side by side: `kentik_api.KentikClient`/`AsyncKentikClient` (v6, generated, REST over
grpc-gateway, ADR 0005) and the deprecated 1.x `kentik_api.KentikAPI`.

## Layout

| path | what |
|---|---|
| `kentik_api/v6/_client.py` | `KentikClient` and `AsyncKentikClient` (hand-written, thin). |
| `kentik_api/v6/_core/` | Hand-written runtime: `config.py` (regions, `RetryConfig`), `transport.py` (httpx, retries, errors, logging), `errors.py`, `service.py` (base classes, pagination), `endpoint.py`, `models.py` (`KentikModel`, `OpenEnum`). |
| `kentik_api/v6/_services.py` | **Generated** client registry: versioned attributes, aliases, `experimental`. |
| `kentik_api/v6/services/<service>_<version>/` | **Generated** per service version: `models.py` (pydantic) and `__init__.py` (sync + async wrappers). |
| `kentik_api/kentik_api.py` | `KentikAPI`, the 1.x root client (v5 REST + synthetics v202202 + cloud_export v202101beta1 over gRPC). Deprecated. |
| `kentik_api/{api_calls,api_resources,api_connection,public,requests_payload}` | 1.x v5 REST implementation. Frozen. |
| `kentik_api/{synthetics,cloudexport,internal}` | 1.x gRPC clients for synthetics v202202 and cloud_export v202101beta1. Frozen. |
| `kentik_api/generated/` | **Generated** legacy protobuf/gRPC stubs. Do not edit. |
| `kentik_api/analytics`, `kentik_api/utils` | pandas helpers (`[analytics]` extra), credentials and device cache. |
| `schema/` | Vendored snapshot of api-schema-public; `schema/SOURCE.json` pins the commits. Do not edit by hand. |
| `scripts/generate.py` | Code generator (`make generate`): `legacy` stage (protobuf stubs) and `v6` stage. |
| `scripts/gen_v6.py` | The v6 stage: models (datamodel-code-generator), wrappers, registry, `kentik-api.json`. |
| `scripts/sync_schema.py` | Refreshes `schema/` from a local api-schema-public clone. |
| `scripts/check_manifest.py` | Validates `kentik-api.json`. |
| `kentik-api.json` | **Generated** coverage manifest (services, versions, status). |
| `tests/unit`, `tests/integration` | Offline tests (stub connectors, httpretty). |
| `tests/v6` | Offline v6 tests against respx (`conftest.py` holds the fake-server fixtures). `test_generated_services.py` makes one sync and one async call per generated operation. |
| `tests/tooling` | Tests for the scripts and the manifest. |
| `tests/e2e` | Live tests against a real tenant. Never run in CI; need `KTAPI_AUTH_EMAIL`/`KTAPI_AUTH_TOKEN`. |
| `examples/v6/` | v6 examples; `tests/v6/test_examples.py` runs them offline. |
| `examples/` | 1.x examples. |
| `docs/adr/` | Architecture decision records. |

## Commands

All commands go through uv and the committed `uv.lock`. `PYTHON=3.x` picks the interpreter (default 3.11).

| task | command |
|---|---|
| set up | `uv sync` |
| build | `make build` (sdist + wheel in `dist/`) |
| test | `make test` (offline; passes on a clean checkout) |
| lint | `make lint` (ruff check, ruff format --check, mypy) |
| format | `make fmt` |
| vuln scan | `make vuln` (pip-audit over `uv export` of the lock) |
| generate | `make generate`; `make generate-check` fails on drift (CI) |
| manifest | `python3 scripts/check_manifest.py kentik-api.json` |
| examples | `KTAPI_AUTH_EMAIL=... KTAPI_AUTH_TOKEN=... uv run python examples/v6/synthetics_overview.py` (live; never in CI) |
| one Python | `make test PYTHON=3.15` |

## Adding a new API service or version

Services and versions come from api-schema-public; nothing is hand-written per service.

1. Clone the schema with history: `git clone https://github.com/kentik/api-schema-public.git /tmp/api-schema-public`.
2. Vendor the commit you want: `uv run python scripts/sync_schema.py --repo /tmp/api-schema-public --ref <commit>`.
   This replaces `schema/openapiv3` and updates `schema/SOURCE.json`.
3. `make generate`. New versions appear as `client.<service>_<version>` (stable) or
   `client.experimental.<service>_<version>` (alpha/beta); aliases move to the newest stable version
   automatically. `kentik-api.json` is regenerated.
4. `make test lint`. `tests/v6/test_generated_services.py` covers every new operation automatically; update its
   expected counts and `tests/tooling/test_generator.py::test_discovery_matches_vendored_schema`. Add a focused
   test in `tests/v6/` if the service has unusual behaviour (new pagination shape, streaming, etc.).
5. If the generator fails, fix `scripts/gen_v6.py` (never the generated output). Typical causes: a new
   pagination pattern (`PAGINATION_PREFIXES`, `detect_pagination`), a parameter that clashes with a reserved
   name (`RESERVED_PARAMS`), or a schema naming collision (`compute_renames`).
6. Update `CHANGELOG.md` (Unreleased) and, if an alias now points to a new version, mention it under "Changed":
   that is a behaviour change for users of the alias.
7. Commit the schema, generated code and manifest together.

Removing a version from the schema removes its attribute: treat that as a breaking change (major version or
keep the old version vendored).

## Release process

1. Update `CHANGELOG.md` (move Unreleased to the new version).
2. Create a GitHub release with tag `vX.Y.Z` on `kentik/community_sdk_python`.
3. `.github/workflows/release.yml` builds, tests and publishes to PyPI through trusted publishing (OIDC,
   environment `pypi`). No tokens are stored. The version comes from the tag (hatch-vcs).

## Conventions

- v6 naming: attribute `<package path with _>_<version>`, gRPC service attribute = snake_case of the service
  name without `Service`, methods = snake_case RPC names, `iter_<method>` for offset/limit list RPCs.
  Path parameters positional, query parameters keyword-only, `body` a model or a mapping, `timeout=` on every call.
- Models are forward-compatible (ADR 0003, 0005): never make fields required or enums closed.
- Retries: only idempotent calls are retried on 5xx (`Endpoint.is_idempotent`, mirrored in `gen_v6.is_idempotent`).
- Python `>=3.11`, ruff (line length 120), mypy strict on new code. The 1.x modules are excluded from
  strict typing (see `pyproject.toml`); do not churn them.
- Dependencies are ranges in `pyproject.toml`; exact versions live in `uv.lock` (`uv lock --upgrade-package X`).
- Every commit builds and passes `make test lint`.
- Generated code is committed and never edited by hand; change the generator instead.

## Do and don't

- **Do** keep tests offline: respx for v6 (`tests/v6/conftest.py`), stub connectors and httpretty for 1.x. No test
  may need network or credentials.
- **Do** keep public names working (`kentik_api.KentikAPI`, its attributes and methods, `kentik_api.public.*`).
  Breaking changes need a major version and an entry in `docs/UPGRADING.md`.
- **Don't** commit secrets, tenant data or recorded responses containing real identifiers.
- **Don't** read `.env` files or look for credentials. E2E tests are opt-in and run by a human.
- **Don't** add features to v5 REST or to the 1.x gRPC clients; new work goes into `kentik_api.v6`.
- **Don't** edit files under `kentik_api/generated`, `kentik_api/v6/services`, `kentik_api/v6/_services.py`,
  `schema/` or `kentik-api.json` by hand.
- **Don't** derive code from non-public Kentik SDKs; the only API source is api-schema-public.
