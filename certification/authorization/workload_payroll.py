"""Payroll authorization workload.

Pattern: a granting role with a read/write surface and one forbidden
operation (delete). The mutation renames the governing role.
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
- The system shall manage employee payroll records.
- The system shall calculate gross pay from base salary and allowances.

2. SECURITY REQUIREMENTS
- The system shall restrict employee payroll records to the payroll_approver role, which may read, create, and update employee payroll records but may not delete them.
"""

DATA_MODEL = data_model_node(
    "data:employee",
    "Employee",
    [
        {"name": "employee_id", "value_type": "identifier"},
        {"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2},
        {"name": "allowances", "value_type": "money", "precision": 12, "scale": 2},
    ],
)

SERVICE = service_node(
    "service:payroll",
    "Payroll",
    rules=[{
        "rule_id": "payroll.gross",
        "description": "Gross pay equals base salary plus allowances.",
        "expression": {"op": "add", "args": [
            {"op": "field", "field_ref": "Employee.base_salary"},
            {"op": "field", "field_ref": "Employee.allowances"},
        ]},
    }],
)

POLICY = policy_node(
    "security:payroll-approver",
    "PayrollApprover",
    roles=["payroll_approver"],
    rules=[
        rule(
            "payroll.employee.allow",
            "allow",
            ["payroll_approver"],
            ["employee.read", "employee.create", "employee.update"],
            "Employee",
        ),
        rule(
            "payroll.employee.deny",
            "deny",
            ["payroll_approver"],
            ["employee.delete"],
            "Employee",
        ),
    ],
)

BOUND_OPERATIONS = (
    OperationBinding("employee.read", "Employee", "allow", ("payroll_approver",)),
    OperationBinding("employee.create", "Employee", "allow", ("payroll_approver",)),
    OperationBinding("employee.update", "Employee", "allow", ("payroll_approver",)),
    OperationBinding("employee.delete", "Employee", "deny", ("payroll_approver",)),
)


def _role_mutation(workload: AuthorizationWorkload) -> AuthorizationWorkload:
    """Rename the governing role in the source and in the approval."""
    return rebuild_workload(
        workload,
        source_text=workload.source_text.replace("payroll_approver", "payroll_admin"),
        approval_needles=tuple(
            (needle, replace_text(payload, "payroll_approver", "payroll_admin"))
            for needle, payload in workload.approval_needles
        ),
        policy_node=replace_text(workload.policy_node, "payroll_approver", "payroll_admin"),
        policy_edge=replace_text(workload.policy_edge, "payroll_approver", "payroll_admin"),
        bound_operations=tuple(
            OperationBinding(
                binding.operation,
                binding.resource,
                binding.effect,
                tuple(role.replace("payroll_approver", "payroll_admin") for role in binding.roles),
            )
            for binding in workload.bound_operations
        ),
    )


MUTATIONS = (
    MutationCase(
        kind="role",
        description="the governing role is renamed from payroll_approver to payroll_admin",
        apply=_role_mutation,
    ),
)

WORKLOAD: AuthorizationWorkload = build_workload(
    workload_id="payroll-authorization",
    source_name="payroll-authorization-tor.md",
    source_text=SOURCE,
    approval_needles=(
        (
            "manage employee payroll records",
            approval(
                "An employee record can be created, queried, updated, and deleted.",
                nodes=(DATA_MODEL,),
            ),
        ),
        (
            "calculate gross pay",
            approval(
                "Gross pay is the base salary plus the allowances.",
                nodes=(SERVICE,),
                edges=(persists_edge("persist:employee", "service:payroll", "data:employee"),),
            ),
        ),
        (
            "restrict employee payroll records",
            approval(
                "Only the payroll_approver role may read, create, or update employee "
                "payroll records, and it may never delete them.",
                nodes=(POLICY,),
                edges=(secured_by_edge("secure:payroll", "service:payroll", "security:payroll-approver"),),
            ),
        ),
    ),
    policy_requirement_needle="restrict employee payroll records",
    policy_node_id="security:payroll-approver",
    policy_node=POLICY,
    policy_edge=secured_by_edge("secure:payroll", "service:payroll", "security:payroll-approver"),
    bound_operations=BOUND_OPERATIONS,
    system_id="payroll-authorization",
    revision_id="rev-payroll-authorization-1",
    created_at="2026-01-01T00:00:00Z",
    mutations=MUTATIONS,
)
