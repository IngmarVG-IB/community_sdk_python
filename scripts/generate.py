#!/usr/bin/env python3
"""Generate code from the vendored api-schema-public snapshot in ``schema/``.

Stages:

* ``legacy``: protobuf/gRPC stubs in ``kentik_api/generated`` used by the deprecated 1.x
  clients (synthetics v202202, cloud_export v202101beta1).

Run via ``make generate`` (``uv run python scripts/generate.py``). Output is deterministic;
CI regenerates and fails on ``git diff``.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema"
LEGACY_PROTO = SCHEMA / "legacy-proto"
LEGACY_OUT = ROOT / "kentik_api" / "generated"

LEGACY_APIS = [
    "kentik/core/v202303",
    "kentik/synthetics/v202202",
    "kentik/cloud_export/v202101beta1",
]
# Generated alongside the Kentik stubs because the only PyPI package providing them
# (protoc-gen-openapiv2==0.0.1) is unmaintained and incompatible with current protobuf.
LEGACY_VENDOR = [
    ("protovendor/github.com/grpc-ecosystem/grpc-gateway", "protoc-gen-openapiv2/options"),
]
LEGACY_INCLUDES = [
    "proto",
    "protovendor/github.com/googleapis/googleapis",
    "protovendor/github.com/grpc-ecosystem/grpc-gateway",
]


def _protoc_include() -> Path:
    import grpc_tools

    return Path(grpc_tools.__file__).parent / "_proto"


def generate_legacy() -> None:
    files: list[str] = []
    for api in LEGACY_APIS:
        files += sorted(str(p) for p in (LEGACY_PROTO / "proto" / api).glob("*.proto"))
    for base, sub in LEGACY_VENDOR:
        files += sorted(str(p) for p in (LEGACY_PROTO / base / sub).glob("*.proto"))

    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"--python_out={tmp}",
            f"--grpc_python_out={tmp}",
            f"-I{_protoc_include()}",
            *[f"-I{LEGACY_PROTO / inc}" for inc in LEGACY_INCLUDES],
            *files,
        ]
        subprocess.run(cmd, check=True)
        out = Path(tmp)
        # Make every directory an importable package (kentik_api.generated.kentik.…).
        for d in [out, *[p for p in out.rglob("*") if p.is_dir()]]:
            (d / "__init__.py").touch()
        shutil.rmtree(LEGACY_OUT, ignore_errors=True)
        shutil.copytree(out, LEGACY_OUT)
    print(f"legacy: {len(files)} proto files -> {LEGACY_OUT.relative_to(ROOT)}")


STAGES = {"legacy": generate_legacy}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stages", nargs="*", help=f"stages to run (default: all of {', '.join(STAGES)})")
    args = parser.parse_args()
    unknown = set(args.stages) - set(STAGES)
    if unknown:
        parser.error(f"unknown stage(s): {', '.join(sorted(unknown))}")
    for name in args.stages or list(STAGES):
        STAGES[name]()


if __name__ == "__main__":
    main()
