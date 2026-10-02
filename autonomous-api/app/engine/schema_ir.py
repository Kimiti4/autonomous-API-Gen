"""Technology-neutral schema IR for API contracts."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


_SCALARS = {"string", "integer", "number", "boolean", "null"}


@dataclass(frozen=True)
class SchemaField:
    name: str
    type: str
    required: bool = True
    nullable: bool = False
    format: str | None = None
    items_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "type": self.type, "required": self.required,
            "nullable": self.nullable, "format": self.format,
            "items_type": self.items_type,
        }


@dataclass(frozen=True)
class SchemaIR:
    name: str
    kind: str = "object"
    fields: tuple[SchemaField, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind,
                "fields": [f.to_dict() for f in self.fields]}


def validate_schema(schema: SchemaIR) -> tuple[str, ...]:
    findings: list[str] = []
    if not schema.name:
        findings.append("schema name is required")
    if schema.kind not in {"object", "array", "string", "integer", "number", "boolean", "null"}:
        findings.append(f"unsupported schema kind: {schema.kind}")
    seen: set[str] = set()
    for field in schema.fields:
        if not field.name:
            findings.append(f"empty field name in {schema.name}")
        if field.name in seen:
            findings.append(f"duplicate field {schema.name}.{field.name}")
        seen.add(field.name)
        if field.type not in _SCALARS and field.type != "array" and not field.type:
            findings.append(f"invalid field type {schema.name}.{field.name}")
        if field.type == "array" and not field.items_type:
            findings.append(f"array item type required: {schema.name}.{field.name}")
        if field.nullable and field.type == "null":
            findings.append(f"redundant nullable null field: {schema.name}.{field.name}")
    return tuple(findings)


def schema_map(schemas: tuple[SchemaIR, ...]) -> dict[str, SchemaIR]:
    return {s.name: s for s in schemas}


def compare_schemas(expected: SchemaIR, actual: SchemaIR) -> tuple[str, ...]:
    findings: list[str] = []
    if expected.kind != actual.kind:
        findings.append(f"schema kind mismatch: {expected.name}")
        return tuple(findings)
    ef = {f.name: f for f in expected.fields}
    af = {f.name: f for f in actual.fields}
    for name, field in ef.items():
        if name not in af:
            findings.append(f"missing field: {expected.name}.{name}")
            continue
        other = af[name]
        if field.type != other.type:
            findings.append(f"type mismatch: {expected.name}.{name}")
        if field.required and not other.required:
            findings.append(f"requiredness weakened: {expected.name}.{name}")
        if not field.nullable and other.nullable:
            findings.append(f"nullability widened: {expected.name}.{name}")
        if field.format != other.format:
            findings.append(f"format mismatch: {expected.name}.{name}")
        if field.type == "array" and field.items_type != other.items_type:
            findings.append(f"array item mismatch: {expected.name}.{name}")
    return tuple(findings)
