# community_sdk_python - developer notes

The canonical maintainer and agent guide is [AGENTS.md](../AGENTS.md). In short:

```shell
git clone https://github.com/kentik/community_sdk_python.git
cd community_sdk_python
uv sync            # creates .venv from uv.lock (Python 3.11+)
make test lint     # offline tests, ruff, mypy
make generate      # regenerate code from the vendored schema in schema/
make vuln          # pip-audit against uv.lock
make build         # sdist + wheel in dist/
```

Design decisions are recorded in [adr/](adr). Diagrams in [diagrams/](diagrams) describe the 1.x (v5) client.
