#!/usr/bin/env python3
"""Validate ``kentik-api.json`` (the machine-readable coverage manifest).

Standard library only, so CI can run it without installing the project::

    python3 scripts/check_manifest.py kentik-api.json

Checks the shape required by the kentikcommunity indexer and, when the vendored schema is
present, that every service version in ``schema/openapiv3`` with REST bindings is listed.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
STABILITY = {"stable", "beta", "alpha"}
STATUS = {"supported", "partial", "experimental", "deprecated", "unsupported"}
VERSION_RE = re.compile(r"^v\d{6}(\d{2})?((alpha|beta)\d*)?$|^v\d+$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def stability_of(version: str) -> str:
    m = re.search(r"(alpha|beta)\d*$", version)
    return m.group(1) if m else "stable"


def schema_versions(root: Path) -> set[tuple[str, str]]:
    """(service, version) pairs in the vendored OpenAPI v3 schema that expose REST paths."""
    base = root / "schema" / "openapiv3" / "kentik"
    found: set[tuple[str, str]] = set()
    if not base.is_dir():
        return found
    for spec in base.rglob("*.json"):
        if json.loads(spec.read_text()).get("paths"):
            rel = spec.parent.relative_to(base)
            found.add(("/".join(rel.parts[:-1]), rel.parts[-1]))
    return found


def validate(manifest: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    src = manifest.get("schema_source")
    if not isinstance(src, dict):
        errors.append("schema_source: missing or not an object")
    else:
        if src.get("repo") != "github.com/kentik/api-schema-public":
            errors.append("schema_source.repo must be github.com/kentik/api-schema-public")
        if not SHA_RE.match(str(src.get("ref", ""))):
            errors.append("schema_source.ref must be a full 40-character commit SHA")

    services = manifest.get("services")
    if not isinstance(services, list) or not services:
        errors.append("services: missing or empty")
        services = []
    seen: set[tuple[str, str]] = set()
    for i, svc in enumerate(services):
        where = f"services[{i}]"
        if not isinstance(svc, dict):
            errors.append(f"{where}: not an object")
            continue
        name, version = svc.get("service"), svc.get("version")
        if not isinstance(name, str) or not name:
            errors.append(f"{where}.service: missing")
            continue
        if not isinstance(version, str) or not VERSION_RE.match(version):
            errors.append(f"{where}.version: invalid {version!r}")
            continue
        where = f"{name}/{version}"
        if (name, version) in seen:
            errors.append(f"{where}: duplicate entry")
        seen.add((name, version))
        if svc.get("stability") not in STABILITY:
            errors.append(f"{where}.stability: must be one of {sorted(STABILITY)}")
        elif svc["stability"] != stability_of(version):
            errors.append(f"{where}.stability: {svc['stability']!r} does not match version suffix")
        if svc.get("status") not in STATUS:
            errors.append(f"{where}.status: must be one of {sorted(STATUS)}")
        if svc.get("stability") in {"alpha", "beta"} and svc.get("status") == "supported":
            errors.append(f"{where}.status: pre-release versions cannot be 'supported' (use 'experimental')")
        surface = svc.get("surface")
        if not isinstance(surface, list) or not all(isinstance(s, str) for s in surface):
            errors.append(f"{where}.surface: must be a list of strings")

    legacy = manifest.get("legacy", [])
    if not isinstance(legacy, list) or not all(
        isinstance(x, dict) and x.get("api") and x.get("status") for x in legacy
    ):
        errors.append("legacy: must be a list of {api, status} objects")

    missing = sorted(schema_versions(root) - seen)
    for name, version in missing:
        errors.append(f"{name}/{version}: in schema/openapiv3 but not listed in services")
    return errors


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else ROOT / "kentik-api.json"
    try:
        manifest = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"{path}: {exc}", file=sys.stderr)
        return 1
    errors = validate(manifest)
    for err in errors:
        print(f"{path}: {err}", file=sys.stderr)
    if not errors:
        print(f"{path}: OK ({len(manifest['services'])} service versions)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
