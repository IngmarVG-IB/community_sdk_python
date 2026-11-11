# Development tasks. Everything runs through uv against the committed uv.lock.
# PYTHON selects the interpreter for the dev venv (e.g. `make test PYTHON=3.15`).
PYTHON ?= 3.11
UV ?= uv
UV_RUN = $(UV) run --frozen --python $(PYTHON)
AUDIT_REQS = build/requirements-audit.txt

.PHONY: all sync build test lint fmt typecheck vuln generate generate-check docs manifest-check clean

all: lint test build vuln

sync:
	$(UV) sync --frozen --python $(PYTHON)

## build: sdist and wheel into dist/
build:
	rm -rf dist
	$(UV) build --python $(PYTHON)

## test: offline unit and integration tests (no network, no credentials)
test:
	$(UV_RUN) pytest

## lint: ruff lint, ruff format check, mypy
lint:
	$(UV_RUN) ruff check .
	$(UV_RUN) ruff format --check .
	$(UV_RUN) mypy kentik_api tests examples scripts

## fmt: apply ruff fixes and formatting
fmt:
	$(UV_RUN) ruff check --fix .
	$(UV_RUN) ruff format .

## vuln: pip-audit every locked dependency (all extras and groups)
vuln:
	@mkdir -p build
	$(UV) export --frozen --all-extras --all-groups --no-emit-project --format requirements-txt -o $(AUDIT_REQS) >/dev/null
	$(UV) tool run pip-audit@2.10.1 --strict --disable-pip --require-hashes -r $(AUDIT_REQS)

## generate: regenerate code from the vendored schema in schema/
generate:
	$(UV_RUN) python scripts/generate.py

## generate-check: regenerate and fail if anything changed (used by CI)
generate-check: generate
	git diff --exit-code -- kentik_api schema kentik-api.json
	@test -z "$$(git status --porcelain --untracked-files=all -- kentik_api schema kentik-api.json)" || (git status --short -- kentik_api schema kentik-api.json; echo "untracked generated files"; exit 1)

docs:
	@echo "Docs are Markdown: README.md, docs/, AGENTS.md. Nothing to build."

clean:
	rm -rf build dist .mypy_cache .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
