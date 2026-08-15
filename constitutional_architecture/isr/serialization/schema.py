"""
ISR JSON Schema.

Defines the JSON Schema for ISR serialization format.
Used for external validation and documentation.
"""

from __future__ import annotations

from typing import Any

ISR_JSON_SCHEMA: dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Intermediate Software Representation (ISR)",
    "description": "The constitutional source of truth for software architecture",
    "type": "object",
    "required": ["system", "version"],
    "properties": {
        "system": {
            "type": "object",
            "required": ["id", "name", "modules"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "modules": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/Module"},
                },
                "deployment": {"$ref": "#/definitions/Deployment"},
                "metadata": {"type": "object"},
                "global_policies": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        },
        "version": {"type": "integer", "minimum": 1},
        "provenance": {
            "type": "object",
            "properties": {
                "created_at": {"type": "string", "format": "date-time"},
                "created_by": {"type": "string"},
                "parent_hash": {"type": ["string", "null"]},
                "mutation_description": {"type": "string"},
                "evolution_run_id": {"type": ["string", "null"]},
                "generation": {"type": "integer", "minimum": 0},
            },
        },
    },
    "definitions": {
        "Module": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "entities": {"type": "array", "items": {"$ref": "#/definitions/Entity"}},
                "services": {"type": "array", "items": {"$ref": "#/definitions/Service"}},
                "workflows": {"type": "array", "items": {"$ref": "#/definitions/Workflow"}},
                "policies": {"type": "array", "items": {"$ref": "#/definitions/Policy"}},
                "interfaces": {"type": "array", "items": {"$ref": "#/definitions/Interface"}},
                "events": {"type": "array", "items": {"$ref": "#/definitions/Event"}},
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "metadata": {"type": "object"},
            },
        },
        "Entity": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "fields": {"type": "array", "items": {"$ref": "#/definitions/Field"}},
                "relationships": {"type": "array"},
                "constraints": {"type": "array"},
                "is_aggregate_root": {"type": "boolean"},
                "is_value_object": {"type": "boolean"},
                "metadata": {"type": "object"},
            },
        },
        "Field": {
            "type": "object",
            "required": ["name", "field_type"],
            "properties": {
                "name": {"type": "string"},
                "field_type": {"type": "string"},
                "cardinality": {"type": "string", "enum": ["required", "optional", "list"]},
                "description": {"type": "string"},
                "default_value": {"type": ["string", "null"]},
                "constraints": {"type": "array"},
                "enum_values": {"type": "array", "items": {"type": "string"}},
                "reference_target": {"type": ["string", "null"]},
                "is_primary_key": {"type": "boolean"},
                "is_indexed": {"type": "boolean"},
                "metadata": {"type": "object"},
            },
        },
        "Service": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "operations": {"type": "array"},
                "dependencies": {"type": "array"},
                "emitted_events": {"type": "array", "items": {"type": "string"}},
                "consumed_events": {"type": "array", "items": {"type": "string"}},
                "is_stateless": {"type": "boolean"},
                "metadata": {"type": "object"},
            },
        },
        "Workflow": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "states": {"type": "array"},
                "transitions": {"type": "array"},
                "metadata": {"type": "object"},
            },
        },
        "Policy": {
            "type": "object",
            "required": ["id", "name", "policy_type"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "policy_type": {"type": "string"},
                "description": {"type": "string"},
                "strategy": {"type": "string"},
                "roles": {"type": "array", "items": {"type": "string"}},
                "rules": {"type": "array"},
                "permissions": {"type": "array"},
                "metadata": {"type": "object"},
            },
        },
        "Interface": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "interface_type": {"type": "string"},
                "description": {"type": "string"},
                "version": {"type": "string"},
                "endpoints": {"type": "array"},
                "secured_by_policy_id": {"type": ["string", "null"]},
                "is_internal": {"type": "boolean"},
                "metadata": {"type": "object"},
            },
        },
        "Event": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "schema": {"type": "array"},
                "pattern": {"type": "string"},
                "guarantee": {"type": "string"},
                "ordering_required": {"type": "boolean"},
                "ttl_seconds": {"type": ["integer", "null"]},
                "metadata": {"type": "object"},
            },
        },
        "Deployment": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "description": {"type": "string"},
                "environment": {"type": "string"},
                "scaling": {"type": "object"},
                "networking": {"type": "object"},
                "monitoring": {"type": "object"},
                "storage": {"type": "object"},
                "secrets": {"type": "object"},
                "metadata": {"type": "object"},
            },
        },
    },
}
