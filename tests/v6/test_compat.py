"""The 1.x import surface keeps working, and the legacy client warns."""

from __future__ import annotations

import importlib

import pytest

import kentik_api


def test_kentik_api_emits_deprecation_warning() -> None:
    with pytest.warns(DeprecationWarning, match="KentikAPI is deprecated") as record:
        api = kentik_api.KentikAPI("me@example.com", "token")
    assert record[0].filename == __file__  # points at the caller
    for attr in (
        "device_labels",
        "sites",
        "users",
        "tags",
        "saved_filters",
        "custom_dimensions",
        "custom_applications",
        "query",
        "plans",
        "my_kentik_portal",
        "devices",
        "batch",
        "alerting",
        "synthetics",
        "cloud_export",
    ):
        assert hasattr(api, attr), attr
    assert callable(api.synthetics.get_all_tests)  # 1.x synthetics v202202 client
    assert kentik_api.KentikAPI.make_api_v5_url("api.kentik.eu") == "https://api.kentik.eu/api/v5"


@pytest.mark.parametrize(
    "module",
    [
        "kentik_api.auth",
        "kentik_api.api_calls",
        "kentik_api.public",
        "kentik_api.synthetics",
        "kentik_api.cloudexport",
        "kentik_api.utils",
        "kentik_api.generated.kentik.synthetics.v202202.synthetics_pb2",
        "kentik_api.generated.kentik.cloud_export.v202101beta1.cloud_export_pb2_grpc",
    ],
)
def test_legacy_modules_import(module: str) -> None:
    importlib.import_module(module)


def test_public_names_still_exported() -> None:
    for name in ("Device", "Site", "User", "Tag", "Plan", "SavedFilter", "CustomDimension", "QueryObject"):
        assert hasattr(kentik_api, name), name


def test_new_clients_exported_at_top_level() -> None:
    from kentik_api.v6 import AsyncKentikClient, KentikClient

    assert kentik_api.KentikClient is KentikClient
    assert kentik_api.AsyncKentikClient is AsyncKentikClient
