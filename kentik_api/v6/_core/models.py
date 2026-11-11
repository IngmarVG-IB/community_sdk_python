"""Base classes for generated v6 models.

Models are forward-compatible (see ADR 0003 and 0005): unknown fields are kept, every field is
optional, and enums accept values added to the API after this SDK was generated.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class KentikModel(BaseModel):
    """Base for every generated model.

    Fields are snake_case; the API's JSON (lowerCamelCase) names are aliases. Both are accepted on
    input, and models serialise with the JSON names.
    """

    model_config = ConfigDict(
        extra="allow",
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        protected_namespaces=(),
    )

    def to_api(self) -> dict[str, Any]:
        """Return the JSON-ready dict sent to the API (aliases, ``None`` omitted)."""
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class EmptyResponse(KentikModel):
    """Response of an RPC that returns no fields (``google.protobuf.Empty`` or an empty message)."""


class OpenEnum(StrEnum):
    """String enum that accepts unknown values.

    An unknown value becomes a pseudo-member whose ``name`` and ``value`` are the string received, so
    a new enum value on the server does not break response parsing.
    """

    @classmethod
    def _missing_(cls, value: object) -> Any:
        if isinstance(value, str):
            member = str.__new__(cls, value)
            member._name_ = value
            member._value_ = value
            return member
        return None
