from __future__ import annotations

from datetime import UTC, datetime

from kentik_api.v6.services.synthetics_v202309 import models as syn


def test_unknown_enum_values_do_not_break_parsing() -> None:
    agent = syn.Agent.model_validate({"status": "AGENT_STATUS_FROM_THE_FUTURE"})
    assert agent.status == "AGENT_STATUS_FROM_THE_FUTURE"
    assert isinstance(agent.status, syn.AgentStatus)
    assert agent.status.name == "AGENT_STATUS_FROM_THE_FUTURE"
    known = syn.Agent.model_validate({"status": "AGENT_STATUS_OK"})
    assert known.status is syn.AgentStatus.AGENT_STATUS_OK


def test_unknown_fields_are_kept_and_round_trip() -> None:
    agent = syn.Agent.model_validate({"alias": "a", "newField": {"x": 1}})
    assert agent.model_extra == {"newField": {"x": 1}}
    assert agent.to_api() == {"alias": "a", "newField": {"x": 1}}


def test_snake_case_and_json_names_both_accepted() -> None:
    a = syn.Agent(site_name="s", last_authed=datetime(2026, 1, 1, tzinfo=UTC))
    b = syn.Agent.model_validate({"siteName": "s", "lastAuthed": "2026-01-01T00:00:00Z"})
    assert a == b
    assert a.to_api() == {"siteName": "s", "lastAuthed": "2026-01-01T00:00:00Z"}


def test_protojson_int64_strings_are_coerced() -> None:
    assert syn.Agent.model_validate({"asn": "64512"}).asn == 64512


def test_all_fields_optional() -> None:
    assert syn.Test().to_api() == {}
