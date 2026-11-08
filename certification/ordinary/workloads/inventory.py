"""Workload B — inventory and purchasing (ordinary)."""
from __future__ import annotations

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.adapters.isr_projection import merge_requirement_projection
from reqgraph.core.graph import RequirementGraph

from certification.ordinary.workloads._tor import approved_requirements_from_tor

TOR_EXCERPT = """FUNCTIONAL REQUIREMENTS
- The system shall maintain a product catalogue with SKU and price.
- The system shall track stock on hand per product.
- Purchasers shall create purchase orders.
- Stock clerks shall post stock adjustments with audit events.
SECURITY REQUIREMENTS
- Only purchasers may create purchase orders.
- Only stock clerks may adjust inventory quantities.
"""

CANDIDATE_ID = "ordinary-inventory-cp054"
REVISION_ID = "rev-inventory-1"


def approved_inventory_requirements() -> RequirementGraph:
    return approved_requirements_from_tor(TOR_EXCERPT, "inventory-tor.md")


def inventory_isr_revision() -> ISRRevision:
    nodes = {
        "data:product": Node(id="data:product", type=NodeType.DATA_MODEL, properties={
            "label": "Product",
            "behavior": {"fields": [
                {"name": "sku", "value_type": "identifier"},
                {"name": "name", "value_type": "string"},
                {"name": "unit_price", "value_type": "money", "precision": 12, "scale": 2},
            ]},
        }),
        "data:stock-level": Node(id="data:stock-level", type=NodeType.DATA_MODEL, properties={
            "label": "StockLevel",
            "behavior": {"fields": [
                {"name": "sku", "value_type": "identifier"},
                {"name": "on_hand", "value_type": "integer"},
            ]},
        }),
        "data:purchase-order": Node(id="data:purchase-order", type=NodeType.DATA_MODEL, properties={
            "label": "PurchaseOrder",
            "behavior": {"fields": [
                {"name": "po_id", "value_type": "identifier"},
                {"name": "sku", "value_type": "identifier"},
                {"name": "quantity", "value_type": "integer"},
                {"name": "status", "value_type": "string"},
            ]},
        }),
        "service:inventory": Node(id="service:inventory", type=NodeType.SERVICE, properties={
            "label": "Inventory",
            "behavior": {
                "rules": [
                    {
                        "rule_id": "purchase.status.draft",
                        "description": "Purchase orders start draft",
                        "expression": {"op": "literal", "value": "draft"},
                    },
                    {
                        "rule_id": "inventory.available",
                        "description": "Available units equal on_hand for SKU",
                        "expression": {"op": "field", "field_ref": "StockLevel.on_hand"},
                    },
                ],
            },
        }),
        "event:stock-adjusted": Node(id="event:stock-adjusted", type=NodeType.EVENT, properties={
            "label": "StockAdjusted",
            "behavior": {"fields": [
                {"name": "sku", "value_type": "identifier"},
                {"name": "delta", "value_type": "integer"},
            ]},
        }),
        "api:create-po": Node(id="api:create-po", type=NodeType.API, properties={
            "label": "CreatePurchaseOrder",
            "behavior": {
                "operation_id": "purchase.create",
                "method": "POST",
                "path": "/purchase-orders",
                "request_fields": [
                    {"name": "sku", "value_type": "identifier"},
                    {"name": "quantity", "value_type": "integer", "constraints": [{"operator": "min", "value": 1}]},
                ],
                "response_fields": [
                    {"name": "po_id", "value_type": "identifier"},
                    {"name": "status", "value_type": "string"},
                ],
                "authorization_policy_ids": ["security:inventory"],
            },
        }),
        "api:adjust-stock": Node(id="api:adjust-stock", type=NodeType.API, properties={
            "label": "AdjustStock",
            "behavior": {
                "operation_id": "stock.adjust",
                "method": "POST",
                "path": "/stock/adjust",
                "request_fields": [
                    {"name": "sku", "value_type": "identifier"},
                    {"name": "delta", "value_type": "integer"},
                ],
                "response_fields": [{"name": "on_hand", "value_type": "integer"}],
                "authorization_policy_ids": ["security:inventory"],
            },
        }),
        "security:inventory": Node(id="security:inventory", type=NodeType.SECURITY_POLICY, properties={
            "label": "InventoryAuthorization",
            "behavior": {"roles": ["purchaser", "stock_clerk"], "rules": [
                {
                    "rule_id": "create-po",
                    "effect": "allow",
                    "roles": ["purchaser"],
                    "actions": ["purchase.create"],
                    "resource": "PurchaseOrder",
                },
                {
                    "rule_id": "adjust",
                    "effect": "allow",
                    "roles": ["stock_clerk"],
                    "actions": ["stock.adjust"],
                    "resource": "StockLevel",
                },
            ]},
        }),
        "frontend:inventory": Node(id="frontend:inventory", type=NodeType.FRONTEND_ROUTE, properties={
            "label": "Inventory",
            "behavior": {"path": "/inventory", "title": "Inventory", "requires_auth": True},
        }),
        "interaction:create-po": Node(id="interaction:create-po", type=NodeType.FRONTEND_INTERACTION, properties={
            "label": "Create PO",
            "behavior": {"label": "Create PO", "action": "submit", "success_message": "PO created"},
        }),
    }
    edges = {
        "persist-product": Edge(id="persist-product", type=EdgeType.PERSISTS, source_id="service:inventory", target_id="data:product"),
        "persist-stock": Edge(id="persist-stock", type=EdgeType.PERSISTS, source_id="service:inventory", target_id="data:stock-level"),
        "persist-po": Edge(id="persist-po", type=EdgeType.PERSISTS, source_id="service:inventory", target_id="data:purchase-order"),
        "publish-adjusted": Edge(id="publish-adjusted", type=EdgeType.PUBLISHES, source_id="service:inventory", target_id="event:stock-adjusted"),
        "expose-po": Edge(id="expose-po", type=EdgeType.EXPOSES, source_id="service:inventory", target_id="api:create-po"),
        "expose-adjust": Edge(id="expose-adjust", type=EdgeType.EXPOSES, source_id="service:inventory", target_id="api:adjust-stock"),
        "secure-svc": Edge(id="secure-svc", type=EdgeType.SECURED_BY, source_id="service:inventory", target_id="security:inventory"),
        "secure-po": Edge(id="secure-po", type=EdgeType.SECURED_BY, source_id="api:create-po", target_id="security:inventory"),
        "secure-adj": Edge(id="secure-adj", type=EdgeType.SECURED_BY, source_id="api:adjust-stock", target_id="security:inventory"),
        "route-ui": Edge(id="route-ui", type=EdgeType.ROUTES_TO, source_id="frontend:inventory", target_id="api:create-po"),
        "contain-po": Edge(id="contain-po", type=EdgeType.CONTAINS, source_id="frontend:inventory", target_id="interaction:create-po"),
        "invoke-po": Edge(id="invoke-po", type=EdgeType.INVOKES, source_id="interaction:create-po", target_id="api:create-po"),
    }
    base = ISRGraph(nodes=nodes, edges=edges)
    merged = merge_requirement_projection(base, approved_inventory_requirements())
    return ISRRevision.create(
        "ordinary-inventory",
        REVISION_ID,
        "1.0",
        merged,
        Provenance(created_by="cp054-ordinary", created_at="2026-03-01T00:00:00Z"),
    )
