"""Shipment authorization workload.

Pattern: a service that owns two resources, but the policy governs only one of
them. The other resource's routes are refused, because no rule grants them.
The mutation renames the governed resource.
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
    replace_text,
    rule,
    secured_by_edge,
    service_node,
)

SOURCE = """1. FUNCTIONAL REQUIREMENTS
- The system shall manage shipment records.
- The system shall manage carrier records used to route shipments.

2. SECURITY REQUIREMENTS
- The system shall restrict shipment records to the dispatch_clerk role, which may read and create shipment records but may not delete them.
"""

SHIPMENT_MODEL = data_model_node(
    "data:shipment",
    "Shipment",
    [
        {"name": "shipment_id", "value_type": "identifier"},
        {"name": "destination", "value_type": "identifier"},
    ],
)

CARRIER_MODEL = data_model_node(
    "data:carrier",
    "Carrier",
    [
        {"name": "carrier_id", "value_type": "identifier"},
        {"name": "carrier_name", "value_type": "string"},
    ],
)

SERVICE = service_node(
    "service:shipments",
    "Shipments",
    rules=[{
        "rule_id": "shipments.destination",
        "description": "A shipment always names a destination.",
        "expression": {"op": "not_equal", "args": [
            {"op": "field", "field_ref": "Shipment.destination"},
            {"op": "literal", "value": ""},
        ]},
    }],
)

POLICY = policy_node(
    "security:dispatch-clerk",
    "DispatchClerk",
    roles=["dispatch_clerk"],
    rules=[
        rule(
            "shipments.allow",
            "allow",
            ["dispatch_clerk"],
            ["shipment.read", "shipment.create"],
            "Shipment",
        ),
        rule(
            "shipments.delete.deny",
            "deny",
            ["dispatch_clerk"],
            ["shipment.delete"],
            "Shipment",
        ),
    ],
)

POLICY_EDGE = secured_by_edge("secure:shipments", "service:shipments", "security:dispatch-clerk")

BOUND_OPERATIONS = (
    OperationBinding("shipment.read", "Shipment", "allow", ("dispatch_clerk",)),
    OperationBinding("shipment.create", "Shipment", "allow", ("dispatch_clerk",)),
    OperationBinding("shipment.delete", "Shipment", "deny", ("dispatch_clerk",)),
)


def _resource_mutation(workload: AuthorizationWorkload) -> AuthorizationWorkload:
    """Rename the governed resource from Shipment to Consignment."""
    policy = replace_text(workload.policy_node, "Shipment", "Consignment")
    policy = replace_text(policy, "shipment.", "consignment.")
    return rebuild_workload(
        workload,
        source_text=workload.source_text.replace("shipment records", "consignment records"),
        policy_requirement_needle=workload.policy_requirement_needle.replace(
            "shipment records", "consignment records"
        ),
        approval_needles=tuple(
            (
                needle.replace("shipment records", "consignment records"),
                replace_text(
                    replace_text(payload, "Shipment", "Consignment"),
                    "shipment.",
                    "consignment.",
                ),
            )
            for needle, payload in workload.approval_needles
        ),
        policy_node=policy,
        policy_edge=replace_text(workload.policy_edge, "Shipment", "Consignment"),
        bound_operations=(
            OperationBinding("consignment.read", "Consignment", "allow", ("dispatch_clerk",)),
            OperationBinding("consignment.create", "Consignment", "allow", ("dispatch_clerk",)),
            OperationBinding("consignment.delete", "Consignment", "deny", ("dispatch_clerk",)),
        ),
    )


MUTATIONS = (
    MutationCase(
        kind="resource",
        description="the governed resource is renamed from Shipment to Consignment",
        apply=_resource_mutation,
    ),
)

WORKLOAD: AuthorizationWorkload = build_workload(
    workload_id="shipments-authorization",
    source_name="shipments-authorization-tor.md",
    source_text=SOURCE,
    approval_needles=(
        (
            "manage shipment records",
            approval(
                "A shipment record can be created, queried, updated, and deleted.",
                nodes=(SHIPMENT_MODEL, SERVICE),
                edges=(persists_edge("persist:shipment", "service:shipments", "data:shipment"),),
            ),
        ),
        (
            "manage carrier records used to route shipments",
            approval(
                "A carrier record can be created, queried, updated, and deleted.",
                nodes=(CARRIER_MODEL,),
                edges=(persists_edge("persist:carrier", "service:shipments", "data:carrier"),),
            ),
        ),
        (
            "restrict shipment records",
            approval(
                "Only the dispatch_clerk role may read and create shipment records, and it "
                "may never delete them.",
                nodes=(POLICY,),
                edges=(POLICY_EDGE,),
            ),
        ),
    ),
    policy_requirement_needle="restrict shipment records",
    policy_node_id="security:dispatch-clerk",
    policy_node=POLICY,
    policy_edge=POLICY_EDGE,
    bound_operations=BOUND_OPERATIONS,
    system_id="shipments-authorization",
    revision_id="rev-shipments-authorization-1",
    created_at="2026-01-01T00:00:00Z",
    mutations=MUTATIONS,
)
