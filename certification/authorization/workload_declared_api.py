"""Declared API operation authorization workload.

Pattern: a service exposes four reviewed API operations on one resource, each
bound to one typed policy. The role may read and create but may never delete.
The candidate must emit those exact routes, guard each with its bound policy,
and execute the declared-operation proof before any side effect.

Unlike the other corpus entries, this workload is only certifiable by a backend
that emits declared operations. A backend that accepts the plan but drops the
routes is caught by the runtime suite, not inferred.
"""
from __future__ import annotations

from certification.authorization.corpus import (
    AuthorizationWorkload,
    DeclaredOperation,
    MutationCase,
    OperationBinding,
    build_workload,
    rebuild_workload,
)
from certification.authorization.workload_kit import (
    api_node,
    approval,
    data_model_node,
    exposes_edge,
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

2. API REQUIREMENTS
- The system shall expose employee payroll records through declared API operations.

3. SECURITY REQUIREMENTS
- The system shall restrict the payroll employee API to the payroll_api_approver role, which may read, create, and update employee payroll records but may never delete them.
"""

EMPLOYEE_FIELDS = [
    {"name": "employee_id", "value_type": "identifier"},
    {"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2},
    {"name": "allowances", "value_type": "money", "precision": 12, "scale": 2},
]

IDENTIFIER_FIELD = [EMPLOYEE_FIELDS[0]]

DATA_MODEL = data_model_node("data:employee", "Employee", EMPLOYEE_FIELDS)

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
    "security:payroll-api-approver",
    "PayrollApiApprover",
    roles=["payroll_api_approver"],
    rules=[
        rule(
            "payroll.api.employee.allow",
            "allow",
            ["payroll_api_approver"],
            ["employee.read", "employee.create", "employee.update"],
            "Employee",
        ),
        rule(
            "payroll.api.employee.deny",
            "deny",
            ["payroll_api_approver"],
            ["employee.delete"],
            "Employee",
        ),
    ],
)

BOUND_OPERATIONS = (
    OperationBinding("employee.read", "Employee", "allow", ("payroll_api_approver",)),
    OperationBinding("employee.create", "Employee", "allow", ("payroll_api_approver",)),
    OperationBinding("employee.update", "Employee", "allow", ("payroll_api_approver",)),
    OperationBinding("employee.delete", "Employee", "deny", ("payroll_api_approver",)),
)

POLICY_ID = "security:payroll-api-approver"

API_DECLARATIONS = (
    api_node(
        "api:payroll-employees-list",
        "ListPayrollEmployees",
        "employee.read",
        "GET",
        "/payroll/employees",
        response_fields=EMPLOYEE_FIELDS,
    ),
    api_node(
        "api:payroll-employees-read",
        "ReadPayrollEmployee",
        "employee.read",
        "GET",
        "/payroll/employees/{employee_id}",
        request_fields=IDENTIFIER_FIELD,
        response_fields=EMPLOYEE_FIELDS,
    ),
    api_node(
        "api:payroll-employees-create",
        "CreatePayrollEmployee",
        "employee.create",
        "POST",
        "/payroll/employees",
        request_fields=EMPLOYEE_FIELDS,
        response_fields=EMPLOYEE_FIELDS,
    ),
    api_node(
        "api:payroll-employees-delete",
        "DeletePayrollEmployee",
        "employee.delete",
        "DELETE",
        "/payroll/employees/{employee_id}",
        request_fields=IDENTIFIER_FIELD,
        response_fields=IDENTIFIER_FIELD,
    ),
)

API_EDGES = tuple(
    edge
    for declaration in API_DECLARATIONS
    for edge in (
        exposes_edge(
            f"exposes:{declaration['id'].split(':', 1)[1]}",
            "service:payroll",
            declaration["id"],
        ),
        secured_by_edge(
            f"secure:{declaration['id'].split(':', 1)[1]}",
            declaration["id"],
            POLICY_ID,
        ),
    )
)

DECLARED_OPERATIONS = (
    DeclaredOperation(
        api_id="api:payroll-employees-list",
        operation="employee.read",
        method="GET",
        path="/payroll/employees",
        resource="Employee",
        policy_ids=(POLICY_ID,),
        response_fields=("employee_id", "base_salary", "allowances"),
    ),
    DeclaredOperation(
        api_id="api:payroll-employees-read",
        operation="employee.read",
        method="GET",
        path="/payroll/employees/{employee_id}",
        resource="Employee",
        policy_ids=(POLICY_ID,),
        request_fields=("employee_id",),
        response_fields=("employee_id", "base_salary", "allowances"),
    ),
    DeclaredOperation(
        api_id="api:payroll-employees-create",
        operation="employee.create",
        method="POST",
        path="/payroll/employees",
        resource="Employee",
        policy_ids=(POLICY_ID,),
        request_fields=("employee_id", "base_salary", "allowances"),
        response_fields=("employee_id", "base_salary", "allowances"),
    ),
    DeclaredOperation(
        api_id="api:payroll-employees-delete",
        operation="employee.delete",
        method="DELETE",
        path="/payroll/employees/{employee_id}",
        resource="Employee",
        policy_ids=(POLICY_ID,),
        request_fields=("employee_id",),
        response_fields=("employee_id",),
    ),
)


def _role_mutation(workload: AuthorizationWorkload) -> AuthorizationWorkload:
    """Rename the governing role everywhere the source and approval name it."""
    return rebuild_workload(
        workload,
        source_text=workload.source_text.replace(
            "payroll_api_approver", "payroll_api_admin"
        ),
        approval_needles=tuple(
            (needle, replace_text(payload, "payroll_api_approver", "payroll_api_admin"))
            for needle, payload in workload.approval_needles
        ),
        policy_node=replace_text(
            workload.policy_node, "payroll_api_approver", "payroll_api_admin"
        ),
        policy_edge=replace_text(
            workload.policy_edge, "payroll_api_approver", "payroll_api_admin"
        ),
        bound_operations=tuple(
            OperationBinding(
                binding.operation,
                binding.resource,
                binding.effect,
                tuple(
                    role.replace("payroll_api_approver", "payroll_api_admin")
                    for role in binding.roles
                ),
            )
            for binding in workload.bound_operations
        ),
    )


MUTATIONS = (
    MutationCase(
        kind="role",
        description=(
            "the declared-API governing role is renamed from "
            "payroll_api_approver to payroll_api_admin"
        ),
        apply=_role_mutation,
    ),
)

WORKLOAD: AuthorizationWorkload = build_workload(
    workload_id="payroll-declared-api-authorization",
    source_name="payroll-declared-api-authorization-tor.md",
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
            "expose employee payroll records",
            approval(
                "Four declared operations list, read, create, and delete employee "
                "payroll records; each is exposed by the payroll service and bound "
                "to the reviewed policy.",
                nodes=API_DECLARATIONS,
                edges=API_EDGES,
            ),
        ),
        (
            "restrict the payroll employee API",
            approval(
                "Only the payroll_api_approver role may read, create, or update "
                "employee payroll records, and it may never delete them.",
                nodes=(POLICY,),
                edges=(
                    secured_by_edge(
                        "secure:payroll-api", "service:payroll", POLICY_ID
                    ),
                ),
            ),
        ),
    ),
    policy_requirement_needle="restrict the payroll employee API",
    policy_node_id=POLICY_ID,
    policy_node=POLICY,
    policy_edge=secured_by_edge("secure:payroll-api", "service:payroll", POLICY_ID),
    bound_operations=BOUND_OPERATIONS,
    declared_operations=DECLARED_OPERATIONS,
    system_id="payroll-declared-api-authorization",
    revision_id="rev-payroll-declared-api-authorization-1",
    created_at="2026-01-01T00:00:00Z",
    mutations=MUTATIONS,
)
