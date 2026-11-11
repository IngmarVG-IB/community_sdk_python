# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **v6 client** `kentik_api.KentikClient` and its async twin `kentik_api.AsyncKentikClient` (REST over
  grpc-gateway, httpx + pydantic v2), generated from api-schema-public `gen/openapiv3` at `5d1d2fa`:
  - every stable service version as `client.<service>_<version>` (22 versions, e.g. `client.synthetics_v202309`,
    `client.cloud_export_v202506`, `client.site_v202509`), with `client.<service>` aliases to the newest stable
    version; 28 alpha/beta versions under `client.experimental`; 317 operations in total;
  - auth via `X-CH-Auth-Email`/`X-CH-Auth-API-Token` (arguments or `KTAPI_AUTH_EMAIL`/`KTAPI_AUTH_TOKEN`),
    US/EU region presets or a custom `base_url`, timeouts (client-wide and per call), proxy support;
  - retries with exponential backoff and full jitter: 429 for every call (honouring `Retry-After`), 5xx and
    transport errors for idempotent calls only;
  - typed errors (`BadRequestError`, `AuthenticationError`, `PermissionDeniedError`, `NotFoundError`,
    `ConflictError`, `RateLimitError`, `ServerError`, `APIConnectionError`, `APITimeoutError`,
    `ResponseValidationError`) carrying HTTP status, gRPC code, service, method and request id;
  - `iter_*` pagination helpers for offset/limit list RPCs; debug logging on the `kentik_api.v6` logger;
  - forward-compatible models: unknown fields kept, open enums, all fields optional;
  - `py.typed`.
- Offline test suite for the v6 client (respx): configuration, auth headers, retries, errors, pagination,
  models, client surface, examples, and one sync plus one async round trip for each of the 317 generated
  operations.
- `examples/v6/`: sync, async, pagination and error-handling examples.
- `docs/UPGRADING.md` (1.0.x to 2.0); README rewritten around the v6 client.
- `scripts/generate.py` v6 stage (`scripts/gen_v6.py`) generates models, service wrappers, the client registry
  and `kentik-api.json`; vendored schema in `schema/openapiv3`.

### Deprecated
- `kentik_api.KentikAPI` (v5 REST, synthetics v202202, cloud_export v202101beta1) now emits a
  `DeprecationWarning` when instantiated. It keeps working.

### Changed
- Packaging moved to `pyproject.toml` with the hatchling backend and hatch-vcs versioning; `setup.py`,
  `requirements.txt` and `requirements-dev.txt` are removed. Development uses uv with a committed `uv.lock`.
- `requires-python` is now `>=3.11` (3.8–3.10 are dropped). CI tests 3.11 to 3.15.
- Runtime dependencies are unpinned ranges instead of exact pins: `protobuf>=7.35.1,<8`, `grpcio>=1.85.1`,
  `googleapis-common-protos>=1.70`, `requests[socks]>=2.32.4`, `dacite>=1.8`.
- The legacy gRPC stubs in `kentik_api/generated` are now committed and generated from a vendored, pinned
  copy of the protos (`schema/legacy-proto`) instead of cloning api-schema-public at build time.
- Linting and formatting use ruff (replacing black, isort, flake8 and pylint); mypy runs in strict mode on new code.

### Fixed
- Permissive enums (`PermissiveEnumMeta`) returned raw strings for known values on Python 3.15.
- `test_get_user_fails_when_server_is_down` no longer performs a DNS lookup.

### Removed
- Dependency on `protoc-gen-openapiv2==0.0.1` (its stubs are generated in-tree).
- Exact pins of vulnerable packages: certifi 2022.9.14, urllib3 1.26.12, GitPython 3.1.27, Pillow 9.2.0,
  and the unused setuptools_scm, pylint, black, isort and flake8 dev pins.

### Security
- `pip-audit` against `uv.lock` reports no known vulnerabilities (previously 14 vulnerable packages).
- Release workflow: artifact actions v4+ (the v3 actions are retired), PyPI trusted publishing via OIDC
  instead of a stored token, least-privilege `permissions`, every action pinned by commit SHA.
- New `ci.yml`: lint, tests on 3.11–3.15, pip-audit, generate drift check, `kentik-api.json` validation,
  wheel install test. Dependabot for uv and GitHub Actions.

### Added
- `AGENTS.md`, `CLAUDE.md`, `SECURITY.md`, this changelog, `kentik-api.json` coverage manifest and
  `scripts/check_manifest.py`, ADR 0004.
- ADR 0005: the v6 client uses REST over grpc-gateway, generated from api-schema-public OpenAPI v3.

## [1.0.7] - 2023-05-19

Last release from the 1.0 line. See the GitHub releases page for earlier history.
