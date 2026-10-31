"""Order authorization workload.

Pattern: a read-only role — one permitted operation, three forbidden ones.
The mutations change which operation the role may perform, and the effect of
the rule that grants it.
"""
from __future__ import annotations

import copy

from certification.authorization.corpus import (
    AuthorizationWorkload,
    MutationCase,
    OperationBinding,
    build_workload,
    rebuild_workload,
)
from certification.authorization.workload_kit import (
    approval,
    data_model_node,
    persists_edge,
    policy_node,
    replace_node,
    replace_text,
    rule,
    secured_by_edge,
    service_node,
)

SOURCE = """1. FUNCTIONAL REQUIREMENTS
- The system shall manage customer order records.
- The system shall calculate order totals from the line price and the discount.

2. SECURITY REQUIREMENTS
- The system shall restrict customer order records to the order_reader role, which may read customer order records but may not create, update, or delete them.
"""

DATA_MODEL = data_model_node(
    "data:order",
    "Order",
    [
        {"name": "order_id", "value_type": "identifier"},
        {"name": "customer_id", "value_type": "identifier"},
        {"name": "total", "value_type": "money", "precision": 12, "scale": 2},
    ],
)

SERVICE = service_node(
    "service:orders",
    "Orders",
    rules=[{
        "rule_id": "orders.total",
        "description": "The order total is the line price less the discount.",
        "expression": {"op": "subtract", "args": [
            {"op": "field", "field_ref": "Order.total"},
            {"op": "literal", "value": 0},
        ]},
    }],
)

POLICY = policy_node(
    "security:order-reader",
    "OrderReader",
    roles=["order_reader"],
    rules=[
        rule("orders.read.allow", "allow", ["order_reader"], ["order.read"], "Order"),
        rule("orders.create.deny", "deny", ["order_reader"], ["order.create"], "Order"),
        rule("orders.update.deny", "deny", ["order_reader"], ["order.update"], "Order"),
        rule("orders.delete.deny", "deny", ["order_reader"], ["order.delete"], "Order"),
    ],
)

POLICY_EDGE = secured_by_edge("secure:orders", "service:orders", "security:order-reader")

BOUND_OPERATIONS = (
    OperationBinding("order.read", "Order", "allow", ("order_reader",)),
    OperationBinding("order.create", "Order", "deny", ("order_reader",)),
    OperationBinding("order.update", "Order", "deny", ("order_reader",)),
    OperationBinding("order.delete", "Order", "deny", ("order_reader",)),
)


def _rules_of(policy: dict) -> list[dict]:
    return list(policy["properties"]["behavior"]["rules"])


def _with_rules(policy: dict, rules: list[dict]) -> dict:
    updated = copy.deepcopy(policy)
    updated["properties"]["behavior"]["rules"] = rules
    return updated


def _action_mutation(workload: AuthorizationWorkload) -> AuthorizationWorkload:
    """Grant the role a different operation and forbid the one it had."""
    rules = [
        rule("orders.read.allow", "deny", ["order_reader"], ["order.read"], "Order"),
        rule("orders.create.deny", "allow", ["order_reader"], ["order.create"], "Order"),
        rule("orders.update.deny", "deny", ["order_reader"], ["order.update"], "Order"),
        rule("orders.delete.deny", "deny", ["order_reader"], ["order.delete"], "Order"),
    ]
    policy = _with_rules(workload.policy_node, rules)
    return rebuild_workload(
        workload,
        source_text=workload.source_text.replace(
            "may read customer order records but may not create, update, or delete them",
            "may create customer order records but may not read, update, or delete them",
        ),
        approval_needles=tuple(
            (
                needle,
                replace_node(payload, "security:order-reader", policy)
                if needle == workload.policy_requirement_needle
                else replace_text(payload, "may read, create, or update", "may create"),
            )
            for needle, payload in workload.approval_needles
        ),
        policy_node=policy,
        bound_operations=(
            OperationBinding("order.read", "Order", "deny", ("order_reader",)),
            OperationBinding("order.create", "Order", "allow", ("order_reader",)),
            OperationBinding("order.update", "Order", "deny", ("order_reader",)),
            OperationBinding("order.delete", "Order", "deny", ("order_reader",)),
        ),
    )


def _policy_mutation(workload: AuthorizationWorkload) -> AuthorizationWorkload:
    """Flip the granting rule to a denial; the role may then do nothing."""
    rules = [
        rule("orders.read.allow", "deny", ["order_reader"], ["order.read"], "Order"),
        rule("orders.create.deny", "deny", ["order_reader"], ["order.create"], "Order"),
        rule("orders.update.deny", "deny", ["order_reader"], ["order.update"], "Order"),
        rule("orders.delete.deny", "deny", ["order_reader"], ["order.delete"], "Order"),
    ]
    policy = _with_rules(workload.policy_node, rules)
    return rebuild_workload(
        workload,
        source_text=workload.source_text.replace(
            "may read customer order records but may not create, update, or delete them",
            "may not read, create, update, or delete customer order records",
        ),
        approval_needles=tuple(
            (
                needle,
                replace_node(payload, "security:order-reader", policy)
                if needle == workload.policy_requirement_needle
                else replace_text(
                    payload,
                    "Only the order_reader role may read customer order records",
                    "The order_reader role may not read customer order records",
                ),
            )
            for needle, payload in workload.approval_needles
        ),
        policy_node=policy,
        bound_operations=(
            OperationBinding("order.read", "Order", "deny", ("order_reader",)),
            OperationBinding("order.create", "Order", "deny", ("order_reader",)),
            OperationBinding("order.update", "Order", "deny", ("order_reader",)),
            OperationBinding("order.delete", "Order", "deny", ("order_reader",)),
        ),
    )


MUTATIONS = (
    MutationCase(
        kind="action",
        description="the granted operation changes from read to create",
        apply=_action_mutation,
    ),
    MutationCase(
        kind="policy",
        description="the granting rule becomes a denial, so the role may do nothing",
        apply=_policy_mutation,
    ),
)

WORKLOAD: AuthorizationWorkload = build_workload(
    workload_id="orders-authorization",
    source_name="orders-authorization-tor.md",
    source_text=SOURCE,
    approval_needles=(
        (
            "manage customer order records",
            approval(
                "An order record can be created, queried, updated, and deleted.",
                nodes=(DATA_MODEL,),
            ),
        ),
        (
            "calculate order totals",
            approval(
                "The order total is the line price less the discount.",
                nodes=(SERVICE,),
                edges=(persists_edge("persist:order", "service:orders", "data:order"),),
            ),
        ),
        (
            "restrict customer order records",
            approval(
                "Only the order_reader role may read customer order records, and it may "
                "never create, update, or delete them.",
                nodes=(POLICY,),
                edges=(POLICY_EDGE,),
            ),
        ),
    ),
    policy_requirement_needle="restrict customer order records",
    policy_node_id="security:order-reader",
    policy_node=POLICY,
    policy_edge=POLICY_EDGE,
    bound_operations=BOUND_OPERATIONS,
    system_id="orders-authorization",
    revision_id="rev-orders-authorization-1",
    created_at="2026-01-01T00:00:00Z",
    mutations=MUTATIONS,
)
