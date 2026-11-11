import importlib.util
import sys
from pathlib import Path

import pytest

from kentik_api.v6._core.endpoint import Endpoint

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("gen_v6", ROOT / "scripts" / "gen_v6.py")
assert _spec and _spec.loader
gen_v6 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("gen_v6", gen_v6)
_spec.loader.exec_module(gen_v6)


@pytest.mark.parametrize(
    ("http_method", "rpc"),
    [
        ("GET", "ListTests"),
        ("POST", "CreateTest"),
        ("POST", "GetResultsForTests"),
        ("PUT", "UpdateTest"),
        ("DELETE", "DeleteTest"),
        ("PATCH", "UpdateAgent"),
        ("POST", "SearchFlowTag"),
        ("POST", "Act"),
    ],
)
def test_idempotency_rule_matches_runtime(http_method: str, rpc: str) -> None:
    assert gen_v6.is_idempotent(http_method, rpc) == Endpoint.is_idempotent(http_method, rpc)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("ListTests", "list_tests"),
        ("GetASNInsights", "get_asn_insights"),
        ("agent.id", "agent_id"),
        ("agentIds", "agent_ids"),
        ("GetResultsForTestsCsv", "get_results_for_tests_csv"),
        ("ASGroup", "as_group"),
    ],
)
def test_snake(name: str, expected: str) -> None:
    assert gen_v6.snake(name) == expected


def test_safe_param_avoids_keywords_and_reserved_names() -> None:
    assert gen_v6.safe_param("from") == "from_"
    assert gen_v6.safe_param("body") == "body_"
    assert gen_v6.safe_param("timeout") == "timeout_"


def test_version_ordering_and_stability() -> None:
    versions = ["v202611", "v202505", "v20261020alpha1", "v202407alpha1", "v202504beta2", "v202308beta1"]
    assert sorted(versions, key=gen_v6.version_key) == [
        "v202308beta1",
        "v202407alpha1",
        "v202504beta2",
        "v202505",
        "v20261020alpha1",
        "v202611",
    ]
    assert gen_v6.stability("v202309") == "stable"
    assert gen_v6.stability("v202504beta2") == "beta"


def test_schema_renames_strip_version_prefix_and_keep_collisions_unique() -> None:
    pv = gen_v6.PackageVersion(
        "x",
        "v202505",
        {
            "v202505Alert": {},
            "typesv202506PaginationInfo": {},
            "AlertAcknowledgement": {},
            "v202505AlertAcknowledgement": {},
            "rpcStatus": {},
            "Svc_DoThingBody": {},
        },
        [],
        [],
    )
    r = gen_v6.compute_renames(pv)
    assert r["v202505Alert"] == "Alert"
    assert r["typesv202506PaginationInfo"] == "PaginationInfo"
    assert r["rpcStatus"] == "RpcStatus"
    assert r["Svc_DoThingBody"] == "SvcDoThingBody"
    assert {r["AlertAcknowledgement"], r["v202505AlertAcknowledgement"]} == {
        "AlertAcknowledgement",
        "V202505AlertAcknowledgement",
    }


def test_discovery_matches_vendored_schema() -> None:
    pvs = gen_v6.discover()
    rest = [pv for pv in pvs if pv.operations]
    assert len(rest) == 50
    grpc_only = sorted(pv.module for pv in pvs if not pv.operations and pv.grpc_services)
    assert grpc_only == ["deviceconf_v202511", "diagnostic_v202501", "kptr_v202602"]
    audit = next(pv for pv in pvs if pv.module == "audit_public_v202601")
    get_event = next(op for op in audit.operations if op.rpc == "GetAuditEvent")
    assert get_event.path == "/audit/v202601/events/{id}/{ctime}"  # primary binding wins
