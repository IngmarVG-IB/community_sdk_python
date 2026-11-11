# 4. Packaging with hatchling and uv; vendored schema; committed generated code

Date: 2026-11-10

## Status

Accepted

## Context

1.x used setuptools with a custom `setup.py` that cloned `api-schema-public` at build time and ran
`grpc_tools.protoc` (CI and every packager needed network access and git). Dependencies were pinned in
`requirements*.txt` files with known vulnerabilities (certifi 2022.9, urllib3 1.26.12, gitpython, pillow),
and there was no lockfile for scanners to check. `synthetics/v202202`, used by the 1.x synthetics client,
has since been removed from `api-schema-public` HEAD, so the old build no longer works at all.

## Decision

- `pyproject.toml` with the `hatchling` backend and `hatch-vcs` (version from the release tag);
  `requires-python >=3.11`. Dev tooling (ruff, mypy, pytest, grpcio-tools) is a uv dependency group,
  resolved into a committed `uv.lock`. `requirements*.txt` and `setup.py` are removed.
- The schema inputs are vendored under `schema/` at pinned commits recorded in `schema/SOURCE.json`
  and `kentik-api.json`; `scripts/sync_schema.py` refreshes them from a local clone.
- Generated code is committed (`kentik_api/generated` for the legacy gRPC stubs). `make generate`
  rebuilds it deterministically and CI fails on drift. Builds need no network or git.
- The legacy stubs include `protoc_gen_openapiv2.options` so the unmaintained
  `protoc-gen-openapiv2==0.0.1` PyPI package is no longer required.
- `pip-audit` runs against `uv export` of the lock (all extras and groups) in CI.

## Consequences

Reproducible, offline builds; scanners see every pinned version; Dependabot updates `uv.lock`.
Generated files appear in diffs when the schema is bumped; that is intended (reviewable API changes).
