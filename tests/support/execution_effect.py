"""ISR fixture for the W12 executable-effect contract lane.

The fixture is deliberately small and canonical: one service that persists one
resource (``Payment``), one typed policy that grants ``payment.create`` on
that resource, and one complete executable effect contract. Every binding is
explicit so the plan can be checked for an enforcement point.
"""
from __future__ import annotations

from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision

SYSTEM_ID = "w12-executable-effect"
REVISION_ID = "w12-executable-effect-1"

SERVICE_ID = "service:payments"
DATA_MODEL_ID = "data:payment"
POLICY_ID = "security:clerk"
EFFECT_ID = "effect:record-payment"
EFFECT_NAME = "RecordPayment"

AUTHORIZED_OPERATION = "payment.create"
PERMITTED_SIDE_EFFECT = "Payment"


def _precondition() -> dict[str, object]:
    return {
        "op": "greater_than",
        "args": [
            {"op": "field", "field_ref": "amount"},
            {"op": "literal", "value": 0},
        ],
    }


def _postcondition() -> dict[str, object]:
    return {
        "op": "equal",
        "args": [
            {"op": "field", "field_ref": "approved"},
            {"op": "literal", "value": True},
        ],
    }


def executable_effect_properties() -> dict[str, object]:
    """The complete effect contract, as declared on the EFFECT ISR node."""
    return {
        "effect_kind": "record_payment",
        "idempotent": True,
        "idempotency_key_required": True,
        "precondition": _precondition(),
        "authorized_operation": AUTHORIZED_OPERATION,
        "permitted_side_effect": PERMITTED_SIDE_EFFECT,
        "failure_behavior": "reject_without_commit",
        "postcondition": _postcondition(),
    }


def executable_revision() -> ISRRevision:
    nodes = {
        DATA_MODEL_ID: Node(id=DATA_MODEL_ID, type=NodeType.DATA_MODEL, properties={
            "label": PERMITTED_SIDE_EFFECT,
            "behavior": {"fields": [
                {
                    "name": "amount", "value_type": "money",
                    "required": True, "nullable": False,
                    "precision": 12, "scale": 2,
                },
                {
                    "name": "approved", "value_type": "boolean",
                    "required": False, "nullable": False,
                },
            ]},
        }),
        SERVICE_ID: Node(id=SERVICE_ID, type=NodeType.SERVICE, properties={
            "label": "Payments",
        }),
        POLICY_ID: Node(id=POLICY_ID, type=NodeType.SECURITY_POLICY, properties={
            "label": "ClerkPaymentPolicy",
            "behavior": {
                "roles": ["clerk"],
                "rules": [{
                    "rule_id": "clerk-records-payment",
                    "effect": "allow",
                    "roles": ["clerk"],
                    "actions": [AUTHORIZED_OPERATION],
                    "resource": PERMITTED_SIDE_EFFECT,
                }],
            },
        }),
        EFFECT_ID: Node(id=EFFECT_ID, type=NodeType.EFFECT, properties={
            "label": EFFECT_NAME,
            "behavior": executable_effect_properties(),
        }),
    }
    edges = {
        "persists-payment": Edge(
            id="persists-payment", type=EdgeType.PERSISTS,
            source_id=SERVICE_ID, target_id=DATA_MODEL_ID,
        ),
        "secures-payments": Edge(
            id="secures-payments", type=EdgeType.SECURED_BY,
            source_id=SERVICE_ID, target_id=POLICY_ID,
        ),
        "causes-effect": Edge(
            id="causes-effect", type=EdgeType.CAUSES_EFFECT,
            source_id=SERVICE_ID, target_id=EFFECT_ID,
        ),
    }
    return ISRRevision.create(
        system_id=SYSTEM_ID,
        revision_id=REVISION_ID,
        schema_version="1.0",
        graph=ISRGraph(nodes=nodes, edges=edges),
        provenance=Provenance(
            created_by="w12-executable-effect-fixture",
            created_at="2026-01-01T00:00:00Z",
        ),
    )


def executable_plan() -> CompilationPlan:
    return isr_to_plan(executable_revision())
