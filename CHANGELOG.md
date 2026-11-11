# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

## [1.0.7] - 2023-05-19

Last release from the 1.0 line. See the GitHub releases page for earlier history.
