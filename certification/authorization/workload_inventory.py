"""Inventory authorization workload.

Pattern: a role that may perform every operation, but only for one warehouse.
The grant therefore depends on a subject attribute, and a principal without
that attribute is refused.
"""
from __future__ import annotations

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
    replace_text,
    rule,
    secured_by_edge,
    service_node,
)

SOURCE = """1. FUNCTIONAL REQUIREMENTS
- The system shall manage stock item records.
- The system shall record the warehouse that holds each stock item.

2. SECURITY REQUIREMENTS
- The system shall restrict stock item records to the stock_manager role, which may read, create, update, and delete stock item records, but only for the north warehouse.
"""

DATA_MODEL = data_model_node(
    "data:item",
    "Item",
    [
        {"name": "item_id", "value_type": "identifier"},
        {"name": "quantity", "value_type": "integer"},
        {"name": "warehouse", "value_type": "identifier"},
    ],
)

SERVICE = service_node(
    "service:inventory",
    "Inventory",
    rules=[{
        "rule_id": "inventory.quantity",
        "description": "A stock item quantity is never negative.",
        "expression": {"op": "greater_or_equal", "args": [
            {"op": "field", "field_ref": "Item.quantity"},
            {"op": "literal", "value": 0},
        ]},
    }],
)

POLICY = policy_node(
    "security:stock-manager",
    "StockManager",
    roles=["stock_manager"],
    rules=[
        rule(
            "inventory.item.allow",
            "allow",
            ["stock_manager"],
            ["item.read", "item.create", "item.update", "item.delete"],
            "Item",
            conditions={"warehouse": "north"},
        ),
    ],
)

POLICY_EDGE = secured_by_edge("secure:inventory", "service:inventory", "security:stock-manager")

BOUND_OPERATIONS = (
    OperationBinding("item.read", "Item", "allow", ("stock_manager",)),
    OperationBinding("item.create", "Item", "allow", ("stock_manager",)),
    OperationBinding("item.update", "Item", "allow", ("stock_manager",)),
    OperationBinding("item.delete", "Item", "allow", ("stock_manager",)),
)


def _role_mutation(workload: AuthorizationWorkload) -> AuthorizationWorkload:
    """Rename the governing role; the attribute condition is unchanged."""
    return rebuild_workload(
        workload,
        source_text=workload.source_text.replace("stock_manager", "stock_lead"),
        approval_needles=tuple(
            (needle, replace_text(payload, "stock_manager", "stock_lead"))
            for needle, payload in workload.approval_needles
        ),
        policy_node=replace_text(workload.policy_node, "stock_manager", "stock_lead"),
        policy_edge=replace_text(workload.policy_edge, "stock_manager", "stock_lead"),
        bound_operations=tuple(
            OperationBinding(
                binding.operation,
                binding.resource,
                binding.effect,
                tuple(role.replace("stock_manager", "stock_lead") for role in binding.roles),
            )
            for binding in workload.bound_operations
        ),
    )


def _attribute_mutation(workload: AuthorizationWorkload) -> AuthorizationWorkload:
    """Move the grant to another warehouse."""
    return rebuild_workload(
        workload,
        source_text=workload.source_text.replace("the north warehouse", "the south warehouse"),
        approval_needles=tuple(
            (needle, replace_text(payload, "north", "south"))
            for needle, payload in workload.approval_needles
        ),
        policy_node=replace_text(workload.policy_node, "north", "south"),
    )


MUTATIONS = (
    MutationCase(
        kind="role",
        description="the governing role is renamed from stock_manager to stock_lead",
        apply=_role_mutation,
    ),
    MutationCase(
        kind="attribute",
        description="the grant moves from the north warehouse to the south warehouse",
        apply=_attribute_mutation,
    ),
)

WORKLOAD: AuthorizationWorkload = build_workload(
    workload_id="inventory-authorization",
    source_name="inventory-authorization-tor.md",
    source_text=SOURCE,
    approval_needles=(
        (
            "manage stock item records",
            approval(
                "A stock item record can be created, queried, updated, and deleted.",
                nodes=(DATA_MODEL,),
            ),
        ),
        (
            "record the warehouse that holds each stock item",
            approval(
                "Every stock item names the warehouse that holds it.",
                nodes=(SERVICE,),
                edges=(persists_edge("persist:item", "service:inventory", "data:item"),),
            ),
        ),
        (
            "restrict stock item records",
            approval(
                "Only the stock_manager role may read, create, update, or delete stock item "
                "records, and only for the north warehouse.",
                nodes=(POLICY,),
                edges=(POLICY_EDGE,),
            ),
        ),
    ),
    policy_requirement_needle="restrict stock item records",
    policy_node_id="security:stock-manager",
    policy_node=POLICY,
    policy_edge=POLICY_EDGE,
    bound_operations=BOUND_OPERATIONS,
    system_id="inventory-authorization",
    revision_id="rev-inventory-authorization-1",
    created_at="2026-01-01T00:00:00Z",
    mutations=MUTATIONS,
)
