import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("check_manifest", ROOT / "scripts" / "check_manifest.py")
assert _spec and _spec.loader
check_manifest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_manifest)


def _manifest() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((ROOT / "kentik-api.json").read_text())
    return data


def test_committed_manifest_is_valid() -> None:
    assert check_manifest.validate(_manifest()) == []


def test_manifest_rejects_bad_entries() -> None:
    bad = copy.deepcopy(_manifest())
    bad["schema_source"]["ref"] = "main"
    bad["services"].append(dict(bad["services"][0]))
    bad["services"].append(
        {"service": "x", "version": "v202501alpha1", "stability": "stable", "status": "supported", "surface": []}
    )
    errors = check_manifest.validate(bad)
    assert any("ref" in e for e in errors)
    assert any("duplicate" in e for e in errors)
    assert any("does not match version suffix" in e for e in errors)
