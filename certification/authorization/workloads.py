"""The authorization certification corpus.

One workload: a payroll system whose source text states, in the requirement
itself, which role governs the records, which operations that role may
perform, and which operation it may not perform. The reviewer's approval binds
that statement to a typed ISR policy; nothing is inferred from prose.

The corpus is versioned and hashed. It is deliberately separate from the
general Campaign A substrate matrix, whose 78-trial expectation is unchanged.
"""
from __future__ import annotations

from typing import Any

from certification.authorization.corpus import (
    CORPUS_VERSION,
    AuthorizationWorkload,
    OperationBinding,
    build_workload,
    corpus_hash,
)

CORPUS_ID = "tiannara.authorization.corpus"

PAYROLL_AUTHORIZATION_SOURCE = """1. FUNCTIONAL REQUIREMENTS
- The system shall manage employee payroll records.
- The system shall calculate gross pay from base salary and allowances.

2. SECURITY REQUIREMENTS
- The system shall restrict employee payroll records to the payroll_approver role, which may read, create, and update employee payroll records but may not delete them.
"""

_POLICY_NODE: dict[str, Any] = {
    "id": "security:payroll-approver",
    "type": "security_policy",
    "properties": {
        "label": "PayrollApprover",
        "behavior": {
            "roles": ["payroll_approver"],
            "rules": [
                {
                    "rule_id": "payroll.employee.allow",
                    "effect": "allow",
                    "roles": ["payroll_approver"],
                    "actions": ["employee.read", "employee.create", "employee.update"],
                    "resource": "Employee",
                },
                {
                    "rule_id": "payroll.employee.deny",
                    "effect": "deny",
                    "roles": ["payroll_approver"],
                    "actions": ["employee.delete"],
                    "resource": "Employee",
                },
            ],
        },
        "source_requirement_ids": ["$requirement_id"],
    },
}

_POLICY_EDGE: dict[str, Any] = {
    "id": "secure:payroll",
    "type": "secured_by",
    "source_id": "service:payroll",
    "target_id": "security:payroll-approver",
    "properties": {"source_requirement_ids": ["$requirement_id"]},
}

_DATA_MODEL_NODE: dict[str, Any] = {
    "id": "data:employee",
    "type": "data_model",
    "properties": {
        "label": "Employee",
        "behavior": {
            "fields": [
                {"name": "employee_id", "value_type": "identifier"},
                {"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2},
                {"name": "allowances", "value_type": "money", "precision": 12, "scale": 2},
            ],
        },
        "source_requirement_ids": ["$requirement_id"],
    },
}

_SERVICE_NODE: dict[str, Any] = {
    "id": "service:payroll",
    "type": "service",
    "properties": {
        "label": "Payroll",
        "behavior": {
            "rules": [{
                "rule_id": "payroll.gross",
                "description": "Gross pay equals base salary plus allowances.",
                "expression": {"op": "add", "args": [
                    {"op": "field", "field_ref": "Employee.base_salary"},
                    {"op": "field", "field_ref": "Employee.allowances"},
                ]},
            }],
        },
        "source_requirement_ids": ["$requirement_id"],
    },
}

_PERSISTS_EDGE: dict[str, Any] = {
    "id": "persist:employee",
    "type": "persists",
    "source_id": "service:payroll",
    "target_id": "data:employee",
    "properties": {"source_requirement_ids": ["$requirement_id"]},
}


def _approval(acceptance: str, nodes: tuple[dict, ...], edges: tuple[dict, ...]) -> dict[str, Any]:
    return {
        "reviewer_id": "authorization-campaign-reviewer",
        "approval_ref": "decision:authorization-campaign",
        "acceptance_criteria": (acceptance,),
        "isr_nodes": list(nodes),
        "isr_edges": list(edges),
    }


PAYROLL_AUTHORIZATION_WORKLOAD: AuthorizationWorkload = build_workload(
    workload_id="payroll-authorization",
    source_name="payroll-authorization-tor.md",
    source_text=PAYROLL_AUTHORIZATION_SOURCE,
    approval_needles=(
        (
            "manage employee payroll records",
            _approval(
                "An employee record can be created, queried, updated, and deleted.",
                (_DATA_MODEL_NODE,),
                (),
            ),
        ),
        (
            "calculate gross pay",
            _approval(
                "Gross pay is the base salary plus the allowances.",
                (_SERVICE_NODE,),
                (_PERSISTS_EDGE,),
            ),
        ),
        (
            "restrict employee payroll records",
            _approval(
                "Only the payroll_approver role may read, create, or update employee "
                "payroll records, and it may never delete them.",
                (_POLICY_NODE,),
                (_POLICY_EDGE,),
            ),
        ),
    ),
    policy_requirement_needle="restrict employee payroll records",
    policy_node_id="security:payroll-approver",
    policy_node=_POLICY_NODE,
    policy_edge=_POLICY_EDGE,
    bound_operations=(
        OperationBinding(
            operation="employee.read",
            resource="Employee",
            effect="allow",
            roles=("payroll_approver",),
        ),
        OperationBinding(
            operation="employee.create",
            resource="Employee",
            effect="allow",
            roles=("payroll_approver",),
        ),
        OperationBinding(
            operation="employee.update",
            resource="Employee",
            effect="allow",
            roles=("payroll_approver",),
        ),
        OperationBinding(
            operation="employee.delete",
            resource="Employee",
            effect="deny",
            roles=("payroll_approver",),
        ),
    ),
    system_id="payroll-authorization",
    revision_id="rev-payroll-authorization-1",
    created_at="2026-01-01T00:00:00Z",
)

AUTHORIZATION_CORPUS: tuple[AuthorizationWorkload, ...] = (PAYROLL_AUTHORIZATION_WORKLOAD,)

AUTHORIZATION_CORPUS_HASH = corpus_hash(AUTHORIZATION_CORPUS)

CORPUS_METADATA = {
    "schema_id": CORPUS_ID,
    "corpus_version": CORPUS_VERSION,
    "corpus_hash": AUTHORIZATION_CORPUS_HASH,
    "workload_ids": [workload.workload_id for workload in AUTHORIZATION_CORPUS],
}
