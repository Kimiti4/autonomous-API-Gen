"""Workload C — project and task management (ordinary)."""
from __future__ import annotations

from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision
from reqgraph.adapters.isr_projection import merge_requirement_projection
from reqgraph.core.graph import RequirementGraph

from certification.ordinary.workloads._tor import approved_requirements_from_tor

TOR_EXCERPT = """FUNCTIONAL REQUIREMENTS
- Teams shall create projects with a name and owner.
- Project leads shall create and assign tasks.
- Assignees shall transition tasks from open to in_progress to done.
- Members may not reassign tasks owned by another member.
SECURITY REQUIREMENTS
- Only project leads may assign tasks.
- Members may update tasks assigned to them.
"""

CANDIDATE_ID = "ordinary-projects-cp054"
REVISION_ID = "rev-projects-1"


def approved_projects_requirements() -> RequirementGraph:
    return approved_requirements_from_tor(TOR_EXCERPT, "projects-tor.md")


def projects_isr_revision() -> ISRRevision:
    nodes = {
        "data:project": Node(id="data:project", type=NodeType.DATA_MODEL, properties={
            "label": "Project",
            "behavior": {"fields": [
                {"name": "project_id", "value_type": "identifier"},
                {"name": "name", "value_type": "string"},
                {"name": "owner_id", "value_type": "identifier"},
            ]},
        }),
        "data:task": Node(id="data:task", type=NodeType.DATA_MODEL, properties={
            "label": "Task",
            "behavior": {"fields": [
                {"name": "task_id", "value_type": "identifier"},
                {"name": "project_id", "value_type": "identifier"},
                {"name": "title", "value_type": "string"},
                {"name": "assignee_id", "value_type": "identifier"},
                {"name": "status", "value_type": "string"},
            ]},
        }),
        "service:projects": Node(id="service:projects", type=NodeType.SERVICE, properties={
            "label": "Projects",
            "behavior": {
                "rules": [{
                    "rule_id": "task.status.assigned",
                    "description": "Assigned tasks marked assigned",
                    "expression": {"op": "literal", "value": "assigned"},
                }],
                "transitions": [{
                    "transition_id": "start",
                    "source_state": "open",
                    "target_state": "in_progress",
                    "guard": {"op": "equal", "args": [
                        {"op": "field", "field_ref": "Task.status"},
                        {"op": "literal", "value": "open"},
                    ]},
                }],
            },
        }),
        "event:task-assigned": Node(id="event:task-assigned", type=NodeType.EVENT, properties={
            "label": "TaskAssigned",
            "behavior": {"fields": [
                {"name": "task_id", "value_type": "identifier"},
                {"name": "assignee_id", "value_type": "identifier"},
            ]},
        }),
        "api:create-project": Node(id="api:create-project", type=NodeType.API, properties={
            "label": "CreateProject",
            "behavior": {
                "operation_id": "project.create",
                "method": "POST",
                "path": "/projects",
                "request_fields": [
                    {"name": "name", "value_type": "string"},
                    {"name": "owner_id", "value_type": "identifier"},
                ],
                "response_fields": [
                    {"name": "project_id", "value_type": "identifier"},
                ],
                "authorization_policy_ids": ["security:projects"],
            },
        }),
        "api:assign-task": Node(id="api:assign-task", type=NodeType.API, properties={
            "label": "AssignTask",
            "behavior": {
                "operation_id": "task.assign",
                "method": "POST",
                "path": "/tasks/assign",
                "request_fields": [
                    {"name": "task_id", "value_type": "identifier"},
                    {"name": "assignee_id", "value_type": "identifier"},
                ],
                "response_fields": [{"name": "status", "value_type": "string"}],
                "authorization_policy_ids": ["security:projects"],
            },
        }),
        "api:start-task": Node(id="api:start-task", type=NodeType.API, properties={
            "label": "StartTask",
            "behavior": {
                "operation_id": "task.start",
                "method": "POST",
                "path": "/tasks/start",
                "request_fields": [{"name": "task_id", "value_type": "identifier"}],
                "response_fields": [{"name": "status", "value_type": "string"}],
                "authorization_policy_ids": ["security:projects"],
            },
        }),
        "security:projects": Node(id="security:projects", type=NodeType.SECURITY_POLICY, properties={
            "label": "ProjectAuthorization",
            "behavior": {"roles": ["project_lead", "member"], "rules": [
                {
                    "rule_id": "create-project",
                    "effect": "allow",
                    "roles": ["project_lead"],
                    "actions": ["project.create"],
                    "resource": "Project",
                },
                {
                    "rule_id": "assign",
                    "effect": "allow",
                    "roles": ["project_lead"],
                    "actions": ["task.assign"],
                    "resource": "Task",
                },
                {
                    "rule_id": "start",
                    "effect": "allow",
                    "roles": ["member"],
                    "actions": ["task.start"],
                    "resource": "Task",
                },
            ]},
        }),
        "frontend:projects": Node(id="frontend:projects", type=NodeType.FRONTEND_ROUTE, properties={
            "label": "Projects",
            "behavior": {"path": "/projects", "title": "Projects", "requires_auth": True},
        }),
        "interaction:assign": Node(id="interaction:assign", type=NodeType.FRONTEND_INTERACTION, properties={
            "label": "Assign task",
            "behavior": {"label": "Assign", "action": "submit", "success_message": "Assigned"},
        }),
    }
    edges = {
        "persist-project": Edge(id="persist-project", type=EdgeType.PERSISTS, source_id="service:projects", target_id="data:project"),
        "persist-task": Edge(id="persist-task", type=EdgeType.PERSISTS, source_id="service:projects", target_id="data:task"),
        "publish-assigned": Edge(id="publish-assigned", type=EdgeType.PUBLISHES, source_id="service:projects", target_id="event:task-assigned"),
        "expose-create": Edge(id="expose-create", type=EdgeType.EXPOSES, source_id="service:projects", target_id="api:create-project"),
        "expose-assign": Edge(id="expose-assign", type=EdgeType.EXPOSES, source_id="service:projects", target_id="api:assign-task"),
        "expose-start": Edge(id="expose-start", type=EdgeType.EXPOSES, source_id="service:projects", target_id="api:start-task"),
        "secure-svc": Edge(id="secure-svc", type=EdgeType.SECURED_BY, source_id="service:projects", target_id="security:projects"),
        "secure-create": Edge(id="secure-create", type=EdgeType.SECURED_BY, source_id="api:create-project", target_id="security:projects"),
        "secure-assign": Edge(id="secure-assign", type=EdgeType.SECURED_BY, source_id="api:assign-task", target_id="security:projects"),
        "secure-start": Edge(id="secure-start", type=EdgeType.SECURED_BY, source_id="api:start-task", target_id="security:projects"),
        "route-ui": Edge(id="route-ui", type=EdgeType.ROUTES_TO, source_id="frontend:projects", target_id="api:create-project"),
        "contain-assign": Edge(id="contain-assign", type=EdgeType.CONTAINS, source_id="frontend:projects", target_id="interaction:assign"),
        "invoke-assign": Edge(id="invoke-assign", type=EdgeType.INVOKES, source_id="interaction:assign", target_id="api:assign-task"),
    }
    base = ISRGraph(nodes=nodes, edges=edges)
    merged = merge_requirement_projection(base, approved_projects_requirements())
    return ISRRevision.create(
        "ordinary-projects",
        REVISION_ID,
        "1.0",
        merged,
        Provenance(created_by="cp054-ordinary", created_at="2026-03-01T00:00:00Z"),
    )
