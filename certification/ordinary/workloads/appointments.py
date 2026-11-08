"""Workload A — appointment management (ordinary, not payroll/orders)."""
from __future__ import annotations

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.adapters.isr_projection import merge_requirement_projection
from reqgraph.core.graph import RequirementGraph

from certification.ordinary.workloads._tor import approved_requirements_from_tor

TOR_EXCERPT = """FUNCTIONAL REQUIREMENTS
- Users shall register with email and role.
- Providers shall define availability slots.
- Customers shall book appointments with a provider.
- Operators shall cancel or reschedule appointments.
SECURITY REQUIREMENTS
- Only schedulers may book appointments for customers.
- Providers may read their own schedule but not other providers' calendars.
"""

CANDIDATE_ID = "ordinary-appointments-cp054"
REVISION_ID = "rev-appointments-1"


def approved_appointments_requirements() -> RequirementGraph:
    return approved_requirements_from_tor(TOR_EXCERPT, "appointments-tor.md")


def appointments_isr_revision() -> ISRRevision:
    nodes = {
        "data:appointment": Node(id="data:appointment", type=NodeType.DATA_MODEL, properties={
            "label": "Appointment",
            "behavior": {"fields": [
                {"name": "appointment_id", "value_type": "identifier"},
                {"name": "provider_id", "value_type": "identifier"},
                {"name": "customer_id", "value_type": "identifier"},
                {"name": "slot", "value_type": "datetime"},
                {"name": "status", "value_type": "string"},
            ]},
        }),
        "service:scheduling": Node(id="service:scheduling", type=NodeType.SERVICE, properties={
            "label": "Scheduling",
            "behavior": {
                "rules": [{
                    "rule_id": "appointment.status.booked",
                    "description": "New appointments start booked",
                    "expression": {"op": "literal", "value": "booked"},
                }],
                "transitions": [{
                    "transition_id": "cancel",
                    "source_state": "booked",
                    "target_state": "cancelled",
                    "guard": {"op": "equal", "args": [
                        {"op": "field", "field_ref": "Appointment.status"},
                        {"op": "literal", "value": "booked"},
                    ]},
                }],
            },
        }),
        "event:appointment-booked": Node(id="event:appointment-booked", type=NodeType.EVENT, properties={
            "label": "AppointmentBooked",
            "behavior": {"fields": [{"name": "appointment_id", "value_type": "identifier"}]},
        }),
        "api:book-appointment": Node(id="api:book-appointment", type=NodeType.API, properties={
            "label": "BookAppointment",
            "behavior": {
                "operation_id": "appointment.book",
                "method": "POST",
                "path": "/appointments",
                "request_fields": [
                    {"name": "provider_id", "value_type": "identifier"},
                    {"name": "customer_id", "value_type": "identifier"},
                    {"name": "slot", "value_type": "datetime"},
                ],
                "response_fields": [
                    {"name": "appointment_id", "value_type": "identifier"},
                    {"name": "status", "value_type": "string"},
                ],
                "authorization_policy_ids": ["security:scheduling"],
            },
        }),
        "api:cancel-appointment": Node(id="api:cancel-appointment", type=NodeType.API, properties={
            "label": "CancelAppointment",
            "behavior": {
                "operation_id": "appointment.cancel",
                "method": "POST",
                "path": "/appointments/cancel",
                "request_fields": [{"name": "appointment_id", "value_type": "identifier"}],
                "response_fields": [{"name": "status", "value_type": "string"}],
                "authorization_policy_ids": ["security:scheduling"],
            },
        }),
        "security:scheduling": Node(id="security:scheduling", type=NodeType.SECURITY_POLICY, properties={
            "label": "SchedulingAuthorization",
            "behavior": {"roles": ["scheduler", "provider"], "rules": [
                {
                    "rule_id": "book",
                    "effect": "allow",
                    "roles": ["scheduler"],
                    "actions": ["appointment.book"],
                    "resource": "Appointment",
                },
                {
                    "rule_id": "cancel",
                    "effect": "allow",
                    "roles": ["scheduler"],
                    "actions": ["appointment.cancel"],
                    "resource": "Appointment",
                },
            ]},
        }),
        "frontend:scheduling": Node(id="frontend:scheduling", type=NodeType.FRONTEND_ROUTE, properties={
            "label": "Scheduling",
            "behavior": {"path": "/scheduling", "title": "Scheduling", "requires_auth": True},
        }),
        "interaction:book": Node(id="interaction:book", type=NodeType.FRONTEND_INTERACTION, properties={
            "label": "Book appointment",
            "behavior": {"label": "Book", "action": "submit", "success_message": "Booked"},
        }),
    }
    edges = {
        "persist-appt": Edge(id="persist-appt", type=EdgeType.PERSISTS, source_id="service:scheduling", target_id="data:appointment"),
        "publish-booked": Edge(id="publish-booked", type=EdgeType.PUBLISHES, source_id="service:scheduling", target_id="event:appointment-booked"),
        "expose-book": Edge(id="expose-book", type=EdgeType.EXPOSES, source_id="service:scheduling", target_id="api:book-appointment"),
        "expose-cancel": Edge(id="expose-cancel", type=EdgeType.EXPOSES, source_id="service:scheduling", target_id="api:cancel-appointment"),
        "secure-svc": Edge(id="secure-svc", type=EdgeType.SECURED_BY, source_id="service:scheduling", target_id="security:scheduling"),
        "secure-book": Edge(id="secure-book", type=EdgeType.SECURED_BY, source_id="api:book-appointment", target_id="security:scheduling"),
        "secure-cancel": Edge(id="secure-cancel", type=EdgeType.SECURED_BY, source_id="api:cancel-appointment", target_id="security:scheduling"),
        "route-ui": Edge(id="route-ui", type=EdgeType.ROUTES_TO, source_id="frontend:scheduling", target_id="api:book-appointment"),
        "contain-book": Edge(id="contain-book", type=EdgeType.CONTAINS, source_id="frontend:scheduling", target_id="interaction:book"),
        "invoke-book": Edge(id="invoke-book", type=EdgeType.INVOKES, source_id="interaction:book", target_id="api:book-appointment"),
    }
    base = ISRGraph(nodes=nodes, edges=edges)
    merged = merge_requirement_projection(base, approved_appointments_requirements())
    return ISRRevision.create(
        "ordinary-appointments",
        REVISION_ID,
        "1.0",
        merged,
        Provenance(created_by="cp054-ordinary", created_at="2026-03-01T00:00:00Z"),
    )
