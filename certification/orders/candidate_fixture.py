"""Orders full-stack proving-case ISR (Checkpoint 049)."""
from __future__ import annotations

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.adapters.isr_projection import merge_requirement_projection
from reqgraph.core.graph import RequirementGraph, RequirementKind
from reqgraph.ingestion.tor_extractor import HumanApproval, extract_tor_text

TOR_EXCERPT = """FUNCTIONAL REQUIREMENTS
- The system shall manage customer order records.
- The system shall calculate order totals from line price and discount.
- The system shall allow an operator to submit a draft order.

2. SECURITY REQUIREMENTS
- The order_operator role may create and submit orders but may not delete them.
"""

CANDIDATE_ID = "orders-proving-cp049"
REVISION_ID = "rev-orders-full-stack-1"


def approved_orders_requirements() -> RequirementGraph:
    draft = extract_tor_text(TOR_EXCERPT, "orders-proving-tor.md")
    approvals = {
        item.requirement_id: HumanApproval(
            reviewer_id="orders-requirements-review",
            approval_ref=f"review:{item.requirement_id}",
            acceptance_criteria=(
                "The generated application passes an independently authored test for this requirement.",
            ),
            selected_kind=RequirementKind.FUNCTIONAL,
            resolution_ref=f"resolved:{item.requirement_id}" if item.ambiguity_score >= 0.5 else None,
        )
        for item in draft.candidates
    }
    return draft.approve(approvals)


def orders_isr_revision() -> ISRRevision:
    nodes = {
        "data:order": Node(id="data:order", type=NodeType.DATA_MODEL, properties={
            "label": "Order",
            "behavior": {"fields": [
                {"name": "order_id", "value_type": "identifier"},
                {"name": "customer_id", "value_type": "identifier"},
                {"name": "line_price", "value_type": "money", "precision": 12, "scale": 2},
                {"name": "discount", "value_type": "money", "precision": 12, "scale": 2},
                {"name": "total", "value_type": "money", "precision": 12, "scale": 2},
                {"name": "status", "value_type": "string"},
            ]},
        }),
        "service:orders": Node(id="service:orders", type=NodeType.SERVICE, properties={
            "label": "Orders",
            "behavior": {
                "rules": [{
                    "rule_id": "orders.total",
                    "description": "Order total is line price minus discount.",
                    "expression": {"op": "subtract", "args": [
                        {"op": "field", "field_ref": "Order.line_price"},
                        {"op": "field", "field_ref": "Order.discount"},
                    ]},
                }],
                "transitions": [{
                    "transition_id": "submit",
                    "source_state": "draft",
                    "target_state": "submitted",
                    "guard": {"op": "equal", "args": [
                        {"op": "field", "field_ref": "Order.status"},
                        {"op": "literal", "value": "draft"},
                    ]},
                }],
            },
        }),
        "event:order-submitted": Node(id="event:order-submitted", type=NodeType.EVENT, properties={
            "label": "OrderSubmitted",
            "behavior": {"fields": [{"name": "order_id", "value_type": "identifier"}]},
        }),
        "api:create-order": Node(id="api:create-order", type=NodeType.API, properties={
            "label": "CreateOrder",
            "behavior": {
                "operation_id": "order.create",
                "method": "POST",
                "path": "/orders",
                "request_fields": [
                    {"name": "customer_id", "value_type": "identifier"},
                    {"name": "line_price", "value_type": "money", "precision": 12, "scale": 2},
                    {"name": "discount", "value_type": "money", "precision": 12, "scale": 2},
                    {"name": "status", "value_type": "string"},
                ],
                "response_fields": [
                    {"name": "id", "value_type": "identifier"},
                    {"name": "total", "value_type": "money", "precision": 12, "scale": 2},
                ],
                "authorization_policy_ids": ["security:orders"],
            },
        }),
        "api:submit-order": Node(id="api:submit-order", type=NodeType.API, properties={
            "label": "SubmitOrder",
            "behavior": {
                "operation_id": "order.submit",
                "method": "POST",
                "path": "/orders/submit",
                "request_fields": [{"name": "id", "value_type": "identifier"}],
                "response_fields": [{"name": "status", "value_type": "string"}],
                "authorization_policy_ids": ["security:orders"],
            },
        }),
        "security:orders": Node(id="security:orders", type=NodeType.SECURITY_POLICY, properties={
            "label": "OrdersAuthorization",
            "behavior": {
                "roles": ["order_operator", "order_reader"],
                "rules": [
                    {
                        "rule_id": "orders-create",
                        "effect": "allow",
                        "roles": ["order_operator"],
                        "actions": ["order.create"],
                        "resource": "Order",
                    },
                    {
                        "rule_id": "orders-submit",
                        "effect": "allow",
                        "roles": ["order_operator"],
                        "actions": ["order.submit"],
                        "resource": "Order",
                    },
                    {
                        "rule_id": "orders-read",
                        "effect": "allow",
                        "roles": ["order_reader", "order_operator"],
                        "actions": ["order.read"],
                        "resource": "Order",
                    },
                ],
            },
        }),
        "effect:reserve-inventory": Node(id="effect:reserve-inventory", type=NodeType.EFFECT, properties={
            "label": "ReserveInventory",
            "behavior": {
                "effect_kind": "inventory_reserve",
                "idempotent": True,
                "idempotency_key_required": True,
            },
        }),
        "invariant:nonnegative-total": Node(id="invariant:nonnegative-total", type=NodeType.INVARIANT, properties={
            "label": "NonnegativeOrderTotal",
            "behavior": {
                "invariant_id": "orders.total.nonnegative",
                "description": "Order total must be nonnegative.",
                "expression": {"op": "greater_or_equal", "args": [
                    {"op": "field", "field_ref": "Order.line_price"},
                    {"op": "field", "field_ref": "Order.discount"},
                ]},
            },
        }),
        "frontend:orders": Node(id="frontend:orders", type=NodeType.FRONTEND_ROUTE, properties={
            "label": "OrdersPage",
            "behavior": {"path": "/orders", "title": "Orders", "requires_auth": False},
        }),
        "interaction:create": Node(id="interaction:create", type=NodeType.FRONTEND_INTERACTION, properties={
            "label": "Create order",
            "behavior": {"label": "Create order", "action": "submit", "success_message": "Order created"},
        }),
        "interaction:submit": Node(id="interaction:submit", type=NodeType.FRONTEND_INTERACTION, properties={
            "label": "Submit order",
            "behavior": {"label": "Submit order", "action": "submit", "success_message": "Order submitted"},
        }),
    }
    edges = {
        "persist-order": Edge(id="persist-order", type=EdgeType.PERSISTS, source_id="service:orders", target_id="data:order"),
        "expose-create": Edge(id="expose-create", type=EdgeType.EXPOSES, source_id="service:orders", target_id="api:create-order"),
        "expose-submit": Edge(id="expose-submit", type=EdgeType.EXPOSES, source_id="service:orders", target_id="api:submit-order"),
        "secure-service": Edge(id="secure-service", type=EdgeType.SECURED_BY, source_id="service:orders", target_id="security:orders"),
        "secure-create": Edge(id="secure-create", type=EdgeType.SECURED_BY, source_id="api:create-order", target_id="security:orders"),
        "secure-submit": Edge(id="secure-submit", type=EdgeType.SECURED_BY, source_id="api:submit-order", target_id="security:orders"),
        "cause-effect": Edge(id="cause-effect", type=EdgeType.CAUSES_EFFECT, source_id="service:orders", target_id="effect:reserve-inventory"),
        "publish-event": Edge(id="publish-event", type=EdgeType.PUBLISHES, source_id="service:orders", target_id="event:order-submitted"),
        "require-invariant": Edge(id="require-invariant", type=EdgeType.REQUIRES_INVARIANT, source_id="service:orders", target_id="invariant:nonnegative-total"),
        "route-create": Edge(id="route-create", type=EdgeType.ROUTES_TO, source_id="frontend:orders", target_id="api:create-order"),
        "route-submit": Edge(id="route-submit", type=EdgeType.ROUTES_TO, source_id="frontend:orders", target_id="api:submit-order"),
        "contains-create": Edge(id="contains-create", type=EdgeType.CONTAINS, source_id="frontend:orders", target_id="interaction:create"),
        "contains-submit": Edge(id="contains-submit", type=EdgeType.CONTAINS, source_id="frontend:orders", target_id="interaction:submit"),
        "invoke-create": Edge(id="invoke-create", type=EdgeType.INVOKES, source_id="interaction:create", target_id="api:create-order"),
        "invoke-submit": Edge(id="invoke-submit", type=EdgeType.INVOKES, source_id="interaction:submit", target_id="api:submit-order"),
    }
    base = ISRGraph(nodes=nodes, edges=edges)
    merged = merge_requirement_projection(base, approved_orders_requirements())
    return ISRRevision.create(
        "orders-proving",
        REVISION_ID,
        "1.0",
        merged,
        Provenance(created_by="orders-proving-case", created_at="2026-01-01T00:00:00Z"),
    )
