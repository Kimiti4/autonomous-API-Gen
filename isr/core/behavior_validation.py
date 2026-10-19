"""Cross-node validation for opt-in behavioral ISR payloads."""
from __future__ import annotations

from isr.core.behavior import (
    ApiBehavior,
    DataModelBehavior,
    InvariantSpec,
    Expression,
    ServiceBehavior,
    expression_field_refs,
    validate_behavior_payload,
)
from isr.core.graph import ISRGraph, NodeType


class BehavioralContractViolation(ValueError):
    """Raised when typed behavioral semantics are inconsistent across ISR nodes."""


def validate_behavioral_graph(graph: ISRGraph) -> None:
    """Validate opt-in payloads and references before revision hashing.

    Structural-only legacy graphs remain accepted. Once behavior is declared,
    malformed schemas and unresolved field/policy references fail closed.
    """
    parsed: dict[str, object] = {}
    all_field_refs: set[str] = set()
    simple_names: dict[str, int] = {}
    policy_ids = {
        node_id for node_id, node in graph.nodes.items()
        if node.type == NodeType.SECURITY_POLICY
    }

    for node_id, node in graph.nodes.items():
        if "behavior" not in node.properties:
            continue
        try:
            payload = validate_behavior_payload(node.type.value, node.properties["behavior"])
        except Exception as exc:
            raise BehavioralContractViolation(
                f"Invalid behavioral payload on node {node_id!r}: {exc}"
            ) from exc
        parsed[node_id] = payload
        if isinstance(payload, DataModelBehavior):
            names = [field.name for field in payload.fields]
            if len(names) != len(set(names)):
                raise BehavioralContractViolation(
                    f"Duplicate field names on data model {node_id!r}"
                )
            label = str(node.properties.get("label", node_id))
            for field in payload.fields:
                all_field_refs.add(f"{label}.{field.name}")
                simple_names[field.name] = simple_names.get(field.name, 0) + 1

    valid_refs = all_field_refs | {
        name for name, count in simple_names.items() if count == 1
    }
    for node_id, payload in parsed.items():
        expressions: list[Expression] = []
        if isinstance(payload, DataModelBehavior):
            expressions.extend(item.expression for item in payload.invariants)
        elif isinstance(payload, ServiceBehavior):
            expressions.extend(item.expression for item in payload.rules)
            expressions.extend(item.guard for item in payload.transitions if item.guard is not None)
        elif isinstance(payload, InvariantSpec):
            expressions.append(payload.expression)
        elif isinstance(payload, ApiBehavior):
            missing = sorted(set(payload.authorization_policy_ids) - policy_ids)
            if missing:
                raise BehavioralContractViolation(
                    f"API {node_id!r} references missing authorization policies: {missing}"
                )
        for expression in expressions:
            unknown = sorted(expression_field_refs(expression) - valid_refs)
            if unknown:
                raise BehavioralContractViolation(
                    f"Behavior on node {node_id!r} references unknown or ambiguous fields: {unknown}"
                )
