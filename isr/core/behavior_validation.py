"""Cross-node validation for opt-in behavioral ISR payloads."""
from __future__ import annotations

from isr.core.behavior import (
    ApiBehavior,
    DataModelBehavior,
    EventBehavior,
    InvariantSpec,
    Expression,
    FrontendInteractionBehavior,
    FrontendRouteBehavior,
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
        if isinstance(payload, (DataModelBehavior, EventBehavior)):
            names = [field.name for field in payload.fields]
            if len(names) != len(set(names)):
                raise BehavioralContractViolation(
                    f"Duplicate field names on data model {node_id!r}"
                )
            if isinstance(payload, DataModelBehavior):
                label = str(node.properties.get("label", node_id))
                for field in payload.fields:
                    all_field_refs.add(f"{label}.{field.name}")
                    simple_names[field.name] = simple_names.get(field.name, 0) + 1

    route_paths: dict[str, str] = {}
    for node_id, payload in parsed.items():
        if isinstance(payload, FrontendRouteBehavior):
            previous = route_paths.get(payload.path)
            if previous is not None:
                raise BehavioralContractViolation(
                    f"Duplicate frontend route path {payload.path!r} on {previous!r} and {node_id!r}"
                )
            route_paths[payload.path] = node_id
        elif isinstance(payload, FrontendInteractionBehavior):
            owner_routes = [
                edge.source_id for edge in graph.edges.values()
                if edge.type.value == "contains" and edge.target_id == node_id
                and edge.source_id in graph.nodes
                and graph.nodes[edge.source_id].type == NodeType.FRONTEND_ROUTE
            ]
            if len(owner_routes) != 1:
                raise BehavioralContractViolation(
                    f"Frontend interaction {node_id!r} must belong to exactly one frontend route"
                )
            targets = [
                edge.target_id for edge in graph.edges.values()
                if edge.type.value == "invokes" and edge.source_id == node_id
            ]
            if payload.action in {"submit", "refresh", "delete"}:
                if len(targets) != 1 or targets[0] not in graph.nodes:
                    raise BehavioralContractViolation(
                        f"Frontend interaction {node_id!r} requires exactly one API target"
                    )
                target_node = graph.nodes[targets[0]]
                if target_node.type != NodeType.API or "behavior" not in target_node.properties:
                    raise BehavioralContractViolation(
                        f"Frontend interaction {node_id!r} must invoke an API with an explicit contract"
                    )
                try:
                    api = validate_behavior_payload("api", target_node.properties["behavior"])
                except Exception as exc:
                    raise BehavioralContractViolation(
                        f"Frontend interaction {node_id!r} invokes an invalid API contract: {exc}"
                    ) from exc
                expected_methods = {
                    "submit": {"POST", "PUT", "PATCH"},
                    "refresh": {"GET"},
                    "delete": {"DELETE"},
                }[payload.action]
                if api.method not in expected_methods:
                    raise BehavioralContractViolation(
                        f"Frontend interaction {node_id!r} action {payload.action!r} "
                        f"is incompatible with API method {api.method!r}"
                    )
            elif targets:
                raise BehavioralContractViolation(
                    f"Frontend toggle interaction {node_id!r} must not invoke an API in v1"
                )

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
