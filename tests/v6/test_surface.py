"""The generated client surface: versioned attributes, aliases and the experimental namespace."""

from __future__ import annotations

import inspect
import re

import pytest

from kentik_api import AsyncKentikClient, KentikClient
from kentik_api.v6 import _services as registry

from .conftest import EMAIL, TOKEN


@pytest.fixture(scope="module")
def sync() -> KentikClient:
    return KentikClient(EMAIL, TOKEN)


@pytest.fixture(scope="module")
def async_() -> AsyncKentikClient:
    return AsyncKentikClient(EMAIL, TOKEN)


def test_every_stable_version_is_a_top_level_attribute(sync: KentikClient, async_: AsyncKentikClient) -> None:
    assert registry.STABLE
    for module in registry.STABLE:
        assert not re.search(r"(alpha|beta)\d*$", module)
        assert getattr(sync, module) is getattr(sync, module)  # cached
        assert type(getattr(async_, module)).__name__.startswith("Async")


def test_pre_release_versions_only_under_experimental(sync: KentikClient) -> None:
    assert registry.EXPERIMENTAL
    for module in registry.EXPERIMENTAL:
        assert re.search(r"(alpha|beta)\d*$", module)
        assert not hasattr(sync, module)
        assert getattr(sync.experimental, module) is not None


def test_aliases_point_to_newest_stable(sync: KentikClient) -> None:
    assert sync.synthetics is sync.synthetics_v202309
    assert sync.cloud_export is sync.cloud_export_v202506
    assert sync.site is sync.site_v202509
    assert sync.user is sync.user_v202211
    for alias, target in registry.ALIASES.items():
        if isinstance(target, str):
            assert getattr(sync, alias) is getattr(sync, target)


def test_composite_alias_takes_newest_version_per_grpc_service(sync: KentikClient) -> None:
    alerting = sync.alerting_public
    assert alerting.suppression is sync.alerting_public_v202611.suppression
    assert alerting.alert is sync.alerting_public_v202505.alert
    assert alerting.policy is sync.alerting_public_v202505.policy


def test_experimental_aliases_only_for_services_without_stable(sync: KentikClient) -> None:
    assert sync.experimental.device is sync.experimental.device_v202504beta2
    for alias in registry.EXPERIMENTAL_ALIASES:
        assert alias not in registry.ALIASES


def test_flattened_methods_and_service_attributes(sync: KentikClient) -> None:
    syn = sync.synthetics
    assert syn.list_tests.__func__ is syn.synthetics_admin.list_tests.__func__  # type: ignore[attr-defined]
    assert hasattr(syn, "get_results_for_tests") and hasattr(syn.synthetics_data, "get_results_for_tests")


def test_async_methods_are_coroutines(async_: AsyncKentikClient) -> None:
    assert inspect.iscoroutinefunction(async_.synthetics.list_tests)
    assert inspect.iscoroutinefunction(async_.experimental.device.list_devices)
