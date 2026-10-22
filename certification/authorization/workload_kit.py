"""Small builders shared by the authorization corpus workloads.

The workloads themselves are authored independently: each one has its own
source text, its own declarations, and its own mutation cases. These helpers
only remove mechanical repetition; they carry no policy meaning.
"""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

REQUIREMENT_ID_TOKEN = "$requirement_id"


def approval(
    acceptance: str,
    nodes: Sequence[Mapping[str, Any]] = (),
    edges: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """A reviewer decision carrying explicit ISR declarations."""
    return {
        "reviewer_id": "authorization-campaign-reviewer",
        "approval_ref": "decision:authorization-campaign",
        "acceptance_criteria": (acceptance,),
        "isr_nodes": [dict(node) for node in nodes],
        "isr_edges": [dict(edge) for edge in edges],
    }


def data_model_node(
    node_id: str,
    label: str,
    fields: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "data_model",
        "properties": {
            "label": label,
            "behavior": {"fields": [dict(field) for field in fields]},
            "source_requirement_ids": [REQUIREMENT_ID_TOKEN],
        },
    }


def service_node(
    node_id: str,
    label: str,
    rules: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    properties: dict[str, Any] = {"label": label}
    if rules:
        properties["behavior"] = {"rules": [dict(rule) for rule in rules]}
    properties["source_requirement_ids"] = [REQUIREMENT_ID_TOKEN]
    return {"id": node_id, "type": "service", "properties": properties}


def persists_edge(edge_id: str, service_id: str, model_id: str) -> dict[str, Any]:
    return {
        "id": edge_id,
        "type": "persists",
        "source_id": service_id,
        "target_id": model_id,
        "properties": {"source_requirement_ids": [REQUIREMENT_ID_TOKEN]},
    }


def policy_node(
    node_id: str,
    label: str,
    roles: Sequence[str],
    rules: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": "security_policy",
        "properties": {
            "label": label,
            "behavior": {
                "roles": list(roles),
                "rules": [dict(rule) for rule in rules],
            },
            "source_requirement_ids": [REQUIREMENT_ID_TOKEN],
        },
    }


def secured_by_edge(edge_id: str, service_id: str, policy_id: str) -> dict[str, Any]:
    return {
        "id": edge_id,
        "type": "secured_by",
        "source_id": service_id,
        "target_id": policy_id,
        "properties": {"source_requirement_ids": [REQUIREMENT_ID_TOKEN]},
    }


def rule(
    rule_id: str,
    effect: str,
    roles: Sequence[str],
    actions: Sequence[str],
    resource: str,
    conditions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "effect": effect,
        "roles": list(roles),
        "actions": list(actions),
        "resource": resource,
        "conditions": dict(conditions or {}),
    }


def replace_text(payload: Any, old: str, new: str) -> Any:
    """Replace every occurrence of ``old`` with ``new`` inside a payload."""
    if isinstance(payload, str):
        return payload.replace(old, new)
    if isinstance(payload, Mapping):
        return {key: replace_text(value, old, new) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [replace_text(value, old, new) for value in payload]
    return payload


def replace_node(payload: Mapping[str, Any], node_id: str, replacement: Mapping[str, Any]) -> dict:
    """Replace a declared ISR node inside an approval payload.

    A mutation is only effective if the approval carries the changed
    declaration, because the approval is what the mapper projects.
    """
    updated = copy.deepcopy(dict(payload))
    nodes = [
        replacement if node.get("id") == node_id else node
        for node in updated.get("isr_nodes", [])
    ]
    updated["isr_nodes"] = nodes
    return updated
