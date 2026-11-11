"""One offline round trip per generated operation (sync and async).

For every ``Endpoint`` the generator emitted, call the matching wrapper method with placeholder path
parameters and an empty body against the respx fake server, and check the HTTP method, the rendered
path, the auth headers and the response model. Paginated operations also exercise their ``iter_*``
helper. New services and versions are covered automatically after ``make generate``.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import json
import pkgutil
import re
import sys
from pathlib import Path
from typing import Any

import pytest
import respx

import kentik_api.v6.services as services_pkg
from kentik_api.v6 import AsyncKentikClient, KentikClient
from kentik_api.v6._core.endpoint import Endpoint, Pagination
from kentik_api.v6._core.transport import AsyncTransport, SyncTransport, render_path

from .conftest import EMAIL, TOKEN

_spec = importlib.util.spec_from_file_location("gen_v6", Path(__file__).resolve().parents[2] / "scripts" / "gen_v6.py")
assert _spec and _spec.loader
gen_v6 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("gen_v6", gen_v6)
_spec.loader.exec_module(gen_v6)


def _cases() -> list[tuple[str, str]]:
    cases = []
    for info in pkgutil.iter_modules(services_pkg.__path__):
        module = importlib.import_module(f"kentik_api.v6.services.{info.name}")
        for name, value in vars(module).items():
            if isinstance(value, Endpoint):
                cases.append((info.name, name))
    return sorted(cases)


CASES = _cases()


def _resolve(
    module_name: str, ep_name: str, flavour: str, transport: Any
) -> tuple[Endpoint[Any], Any, Pagination | None]:
    module = importlib.import_module(f"kentik_api.v6.services.{module_name}")
    ep: Endpoint[Any] = getattr(module, ep_name)
    service = ep.service.rsplit(".", 1)[1]
    cls = getattr(module, service if flavour == "sync" else f"Async{service}")
    method = getattr(cls(transport), gen_v6.snake(ep.method))
    page = getattr(module, f"{ep_name}_PAGE", None)
    return ep, method, page


def _args(method: Any, ep: Endpoint[Any]) -> tuple[list[Any], str]:
    template_names = re.findall(r"\{([^}=]+)", ep.path)
    args: list[Any] = []
    path_values: dict[str, str] = {}
    positional = [
        p
        for p in inspect.signature(method).parameters.values()
        if p.kind is p.POSITIONAL_OR_KEYWORD and p.default is p.empty
    ]
    for p in positional:
        if p.name == "body":
            args.append({})
        else:
            value = f"p-{p.name}"
            path_values[template_names[len(path_values)]] = value
            args.append(value)
    assert len(path_values) == len(template_names), f"{ep.method}: path params {template_names}"
    return args, render_path(ep.path, path_values)


def _check_request(route: respx.Route, ep: Endpoint[Any]) -> None:
    assert route.call_count == 1
    request = route.calls.last.request
    assert request.method == ep.http_method
    assert request.headers["X-CH-Auth-Email"] == EMAIL
    assert request.headers["X-CH-Auth-API-Token"] == TOKEN
    if ep.has_body:
        assert json.loads(request.content) == {}
    else:
        assert request.content == b""


def test_every_service_version_has_cases() -> None:
    modules = {m for m, _ in CASES}
    assert len(modules) == 50
    assert len(CASES) == 317


@pytest.mark.parametrize(("module_name", "ep_name"), CASES)
def test_sync_operation(module_name: str, ep_name: str, client: KentikClient, mock: respx.MockRouter) -> None:
    transport: SyncTransport = client._transport
    ep, method, page = _resolve(module_name, ep_name, "sync", transport)
    args, path = _args(method, ep)
    route = mock.route(method=ep.http_method, path=path).respond(json={"unknownFieldFromServer": 1})
    result = method(*args)
    assert isinstance(result, ep.response)
    assert result.model_extra == {"unknownFieldFromServer": 1}
    _check_request(route, ep)
    if page is not None:
        iterator = getattr(method.__self__, f"iter_{method.__name__}")
        route.calls.reset()
        assert list(iterator(*args, page_size=7)) == []
        request = route.calls.last.request
        if page.location == "query":
            assert request.url.params[page.limit] == "7"
        else:
            assert json.loads(request.content)["pagination"]["limit"] == "7"


@pytest.mark.anyio
@pytest.mark.parametrize(("module_name", "ep_name"), CASES)
async def test_async_operation(
    module_name: str, ep_name: str, aclient: AsyncKentikClient, mock: respx.MockRouter
) -> None:
    transport: AsyncTransport = aclient._transport
    ep, method, _page = _resolve(module_name, ep_name, "async", transport)
    args, path = _args(method, ep)
    route = mock.route(method=ep.http_method, path=path).respond(json={})
    result = await method(*args)
    assert isinstance(result, ep.response)
    _check_request(route, ep)
