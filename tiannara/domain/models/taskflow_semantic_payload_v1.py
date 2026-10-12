"""Strict versioned envelope for reviewed TaskFlow semantic values.

This schema validates payload shape and completeness, not the truth of reviewer
decisions. Trusted-envelope verification remains a separate required gate.
Field-specific business values intentionally remain JSON values until the
canonical requirements and authorized reviewer resolve their exact semantics.
"""
from __future__ import annotations

from typing import Any, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .semantic_resolution import (
    ResolutionKind,
    SemanticResolutionRecord,
    TASKFLOW_MANDATORY_FIELDS,
    resolutions_by_field,
)
from .taskflow_semantic_contract import REQUIRED_VALUE_KEYS


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]

_PLACEHOLDERS = {"", "unknown", "unresolved", "tbd", "todo", "n/a", "not specified"}


def _validate_json_value(value: Any, path: str) -> None:
    """Reject non-JSON values and placeholder content at any nesting depth."""
    if value is None or isinstance(value, (bool, int, float)):
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            raise ValueError(f"{path}: non-finite numbers are not valid JSON values")
        return
    if isinstance(value, str):
        if value.strip().casefold() in _PLACEHOLDERS:
            raise ValueError(f"{path}: placeholder value is not an explicit semantic decision")
        return
    if isinstance(value, list):
        if not value:
            raise ValueError(f"{path}: empty list is not an explicit semantic decision")
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        if not value:
            raise ValueError(f"{path}: empty object is not an explicit semantic decision")
        for key, item in value.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError(f"{path}: object keys must be non-empty strings")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise ValueError(f"{path}: value is not JSON-compatible ({type(value).__name__})")


class TaskFlowSemanticPayloadV1(BaseModel):
    """Complete typed envelope for the exact compiler-owned TaskFlow field set."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(default="tiannara.taskflow.semantic-payload.v1", min_length=1)
    graph_id: str = Field(min_length=1)
    graph_hash: str = Field(min_length=1)
    problem_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acceptance_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    values: dict[str, dict[str, JsonValue]]

    @model_validator(mode="after")
    def validate_complete_payload(self) -> "TaskFlowSemanticPayloadV1":
        if self.schema_version != "tiannara.taskflow.semantic-payload.v1":
            raise ValueError("unsupported TaskFlow semantic payload schema_version")
        actual = set(self.values)
        expected = set(TASKFLOW_MANDATORY_FIELDS)
        if actual != expected:
            raise ValueError(
                "TaskFlow semantic payload must contain exactly the authoritative field set; "
                f"missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}"
            )
        for field_path in TASKFLOW_MANDATORY_FIELDS:
            value = self.values[field_path]
            expected_keys = set(REQUIRED_VALUE_KEYS[field_path])
            actual_keys = set(value)
            if actual_keys != expected_keys:
                raise ValueError(
                    f"{field_path}: payload keys mismatch; "
                    f"missing={sorted(expected_keys - actual_keys)}, "
                    f"unexpected={sorted(actual_keys - expected_keys)}"
                )
            for key, item in value.items():
                _validate_json_value(item, f"{field_path}.{key}")
        return self

    @classmethod
    def from_resolution_record(
        cls,
        record: SemanticResolutionRecord,
        *,
        problem_sha256: str,
        acceptance_sha256: str,
    ) -> "TaskFlowSemanticPayloadV1":
        """Build only from a complete record; does not authenticate its reviewer."""
        if record.required_fields != TASKFLOW_MANDATORY_FIELDS:
            raise ValueError("resolution record does not use the authoritative TaskFlow field set")
        unresolved = record.unresolved_fields()
        if unresolved:
            raise ValueError("cannot build payload with unresolved fields: " + ", ".join(unresolved))
        by_field = resolutions_by_field(record)
        values: dict[str, dict[str, JsonValue]] = {}
        for field_path in TASKFLOW_MANDATORY_FIELDS:
            item = by_field[field_path]
            if item.kind is ResolutionKind.UNRESOLVED or not isinstance(item.value, dict):
                raise ValueError(f"{field_path}: resolved value must be a JSON object")
            values[field_path] = item.value
        return cls(
            graph_id=record.graph_id,
            graph_hash=record.graph_hash,
            problem_sha256=problem_sha256,
            acceptance_sha256=acceptance_sha256,
            values=values,
        )
