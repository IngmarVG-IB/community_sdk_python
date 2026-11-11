#!/usr/bin/env python3
"""Refresh the vendored copy of kentik/api-schema-public under ``schema/``.

The SDK is generated from a pinned, vendored snapshot of the public API schema so that
``make generate`` is deterministic and works offline (CI checks for drift).

Usage::

    git clone https://github.com/kentik/api-schema-public.git /tmp/api-schema-public
    python scripts/sync_schema.py --repo /tmp/api-schema-public --ref <commit>

Only plain ``git`` read commands are run against the schema checkout; nothing from that
repository is executed.
"""

from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schema"
SOURCE_FILE = SCHEMA / "SOURCE.json"
REPO_URL = "github.com/kentik/api-schema-public"

# Legacy gRPC stubs (kentik_api.generated) back the deprecated 1.x clients. Their protos were
# removed from api-schema-public HEAD (synthetics/v202202), so they come from a separate,
# older pinned commit.
LEGACY_PATHS = [
    "proto/kentik/synthetics/v202202",
    "proto/kentik/cloud_export/v202101beta1",
    "proto/kentik/core/v202303",
    "protovendor/github.com/googleapis/googleapis/google/api/annotations.proto",
    "protovendor/github.com/googleapis/googleapis/google/api/client.proto",
    "protovendor/github.com/googleapis/googleapis/google/api/field_behavior.proto",
    "protovendor/github.com/googleapis/googleapis/google/api/http.proto",
    "protovendor/github.com/googleapis/googleapis/google/api/launch_stage.proto",
    "protovendor/github.com/grpc-ecosystem/grpc-gateway/protoc-gen-openapiv2/options",
]


def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def _extract(repo: Path, ref: str, paths: list[str], dest: Path, strip: str = "") -> None:
    data = _git(repo, "archive", "--format=tar", ref, *paths)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = member.name
            if strip and name.startswith(strip):
                name = name[len(strip) :]
            target = dest / name
            if not target.resolve().is_relative_to(dest.resolve()):
                raise SystemExit(f"refusing to write outside {dest}: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            fh = tar.extractfile(member)
            assert fh is not None
            target.write_bytes(fh.read())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, required=True, help="local clone of api-schema-public (full history)")
    parser.add_argument("--ref", help="commit for gen/openapiv3 (v6 client); default: keep current")
    parser.add_argument("--legacy-ref", help="commit for legacy protos; default: keep current")
    args = parser.parse_args()

    source = json.loads(SOURCE_FILE.read_text()) if SOURCE_FILE.exists() else {"repo": REPO_URL}
    if args.ref:
        sha = _git(args.repo, "rev-parse", f"{args.ref}^{{commit}}").decode().strip()
        date = _git(args.repo, "show", "-s", "--format=%cI", sha).decode().strip()
        dest = SCHEMA / "openapiv3"
        shutil.rmtree(dest, ignore_errors=True)
        _extract(args.repo, sha, ["gen/openapiv3"], dest, strip="gen/openapiv3/")
        source["ref"] = sha
        source["ref_date"] = date
    if args.legacy_ref:
        sha = _git(args.repo, "rev-parse", f"{args.legacy_ref}^{{commit}}").decode().strip()
        dest = SCHEMA / "legacy-proto"
        shutil.rmtree(dest, ignore_errors=True)
        _extract(args.repo, sha, LEGACY_PATHS, dest)
        source["legacy_ref"] = sha
    source["repo"] = REPO_URL
    SCHEMA.mkdir(exist_ok=True)
    SOURCE_FILE.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n")
    print(json.dumps(source, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
