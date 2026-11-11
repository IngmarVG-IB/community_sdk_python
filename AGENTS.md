# AGENTS.md

Guide for maintainers and coding agents working on `kentik-api`, the community Python SDK for the
[Kentik APIs](https://kb.kentik.com/v0/Ab09.htm). `CLAUDE.md` imports this file.

## Purpose

Python client for Kentik:
- **v6 APIs** (gRPC services exposed as REST through grpc-gateway), defined in
  [kentik/api-schema-public](https://github.com/kentik/api-schema-public).
- **v5 REST** (`/api/v5/...`): legacy, deprecated, kept working for existing users. Do not extend it.

## Layout

| path | what |
|---|---|
| `kentik_api/kentik_api.py` | `KentikAPI`, the 1.x root client (v5 REST + synthetics v202202 + cloud_export v202101beta1 over gRPC). Deprecated. |
| `kentik_api/{api_calls,api_resources,api_connection,public,requests_payload}` | 1.x v5 REST implementation. Frozen. |
| `kentik_api/{synthetics,cloudexport,internal}` | 1.x gRPC clients for synthetics v202202 and cloud_export v202101beta1. Frozen. |
| `kentik_api/generated/` | **Generated** legacy protobuf/gRPC stubs. Do not edit. |
| `kentik_api/analytics`, `kentik_api/utils` | pandas helpers (`[analytics]` extra), credentials and device cache. |
| `schema/` | Vendored snapshot of api-schema-public; `schema/SOURCE.json` pins the commits. Do not edit by hand. |
| `scripts/generate.py` | Code generator (`make generate`). |
| `scripts/sync_schema.py` | Refreshes `schema/` from a local api-schema-public clone. |
| `scripts/check_manifest.py` | Validates `kentik-api.json`. |
| `kentik-api.json` | Machine-readable coverage manifest (services, versions, status). |
| `tests/unit`, `tests/integration` | Offline tests (stub connectors, httpretty). |
| `tests/tooling` | Tests for the scripts and the manifest. |
| `tests/e2e` | Live tests against a real tenant. Never run in CI; need `KTAPI_AUTH_EMAIL`/`KTAPI_AUTH_TOKEN`. |
| `examples/` | Example scripts. |
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
| one Python | `make test PYTHON=3.15` |

## Bumping the API schema

1. `git clone https://github.com/kentik/api-schema-public.git /tmp/api-schema-public`
2. `uv run python scripts/sync_schema.py --repo /tmp/api-schema-public --ref <commit>`
3. `make generate test lint`
4. Update `kentik-api.json` `schema_source.ref` and `CHANGELOG.md`; commit the schema, generated code and
   manifest together.

## Release process

1. Update `CHANGELOG.md` (move Unreleased to the new version).
2. Create a GitHub release with tag `vX.Y.Z` on `kentik/community_sdk_python`.
3. `.github/workflows/release.yml` builds, tests and publishes to PyPI through trusted publishing (OIDC,
   environment `pypi`). No tokens are stored. The version comes from the tag (hatch-vcs).

## Conventions

- Python `>=3.11`, ruff (line length 120), mypy strict on new code. The 1.x modules are excluded from
  strict typing (see `pyproject.toml`); do not churn them.
- Dependencies are ranges in `pyproject.toml`; exact versions live in `uv.lock` (`uv lock --upgrade-package X`).
- Every commit builds and passes `make test lint`.
- Generated code is committed and never edited by hand; change the generator instead.

## Do and don't

- **Do** keep tests offline: stub connectors, httpretty for v5. No test may need network or credentials.
- **Do** keep public names working (`kentik_api.KentikAPI`, its attributes and methods, `kentik_api.public.*`).
  Breaking changes need a major version and an entry in `docs/UPGRADING.md`.
- **Don't** commit secrets, tenant data or recorded responses containing real identifiers.
- **Don't** read `.env` files or look for credentials. E2E tests are opt-in and run by a human.
- **Don't** add features to v5 REST.
- **Don't** derive code from non-public Kentik SDKs; the only API source is api-schema-public.
