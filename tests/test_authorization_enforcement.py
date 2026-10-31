"""Stage 2 authorization enforcement: trusted principal and per-route binding.

These tests are the compiler-side contract for the enforcement increment. The
runtime behaviour itself is proven by the generated application's own suite,
which the integration test executes.
"""
from __future__ import annotations

import ast
import subprocess
import sys

import pytest

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.authorization import (
    assert_authorization_enforceable,
    canonical_action,
    protected_services,
)
from compiler.core.capabilities import SemanticFeature, UnsupportedSemanticsError
from compiler.core.plan import (
    ApiOperation,
    CompilationPlan,
    DataModel,
    SecurityPolicy,
    Service,
)
from isr.core.behavior import (
    ApiBehavior,
    AuthorizationRule,
    ConstraintOperator,
    DataModelBehavior,
    FieldConstraint,
    FieldSpec,
    SecurityBehavior,
    ValueType,
)
from isr.core.graph import Edge, EdgeType
from compiler.core.lowering import isr_to_plan
from tests.support.tor_sources import (
    authorized_backend_plan,
    backend_plan,
    full_stack_projection,
)


def _emitted(plan) -> dict[str, str]:
    return PythonFastAPIBackend().compile(plan).files


_EMPLOYEE = (
    FieldSpec(name="employee_id", value_type=ValueType.IDENTIFIER),
    FieldSpec(name="base_salary", value_type=ValueType.MONEY, precision=12, scale=2),
    FieldSpec(name="allowances", value_type=ValueType.MONEY, precision=12, scale=2),
)


def _declared_policy() -> SecurityPolicy:
    return SecurityPolicy(
        policy_id="security:payroll-approver",
        behavior=SecurityBehavior(
            roles=("payroll_approver",),
            rules=(
                AuthorizationRule(
                    rule_id="payroll.read-create.allow",
                    effect="allow",
                    roles=("payroll_approver",),
                    actions=("employee.read", "employee.create"),
                    resource="Employee",
                ),
                AuthorizationRule(
                    rule_id="payroll.delete.deny",
                    effect="deny",
                    roles=("payroll_approver",),
                    actions=("employee.delete",),
                    resource="Employee",
                ),
            ),
        ),
    )


def _operation(
    api_id: str,
    name: str,
    method: str,
    path: str,
    action: str,
    request: tuple[FieldSpec, ...] = (),
    response: tuple[FieldSpec, ...] = (),
    *,
    service_id: str | None = "service:payroll",
    policy_ids: tuple[str, ...] = ("security:payroll-approver",),
) -> ApiOperation:
    return ApiOperation(
        id=api_id,
        name=name,
        service_id=service_id,
        behavior=ApiBehavior(
            operation_id=action,
            method=method,
            path=path,
            request_fields=request,
            response_fields=response,
            authorization_policy_ids=policy_ids,
        ),
    )


def _declared_plan() -> CompilationPlan:
    employee = _EMPLOYEE
    return CompilationPlan(
        plan_id="declared-plan",
        isr_id="declared-payroll",
        services=[
            Service(
                id="service:payroll",
                name="Payroll",
                data_models=[
                    DataModel(
                        id="dm:employee",
                        entity_name="Employee",
                        behavior=DataModelBehavior(fields=employee),
                    )
                ],
            )
        ],
        security=[_declared_policy()],
        apis=[
            _operation(
                "api:list", "listEmployees", "GET", "/payroll/employees",
                "employee.read", response=employee,
            ),
            _operation(
                "api:read", "readEmployee", "GET",
                "/payroll/employees/{employee_id}", "employee.read",
                request=employee[:1], response=employee,
            ),
            _operation(
                "api:create", "createEmployee", "POST", "/payroll/employees",
                "employee.create", request=employee, response=employee,
            ),
            _operation(
                "api:delete", "deleteEmployee", "DELETE",
                "/payroll/employees/{employee_id}", "employee.delete",
                request=employee[:1], response=employee[:1],
            ),
        ],
    )


def _with_api(plan: CompilationPlan, index: int, **updates) -> CompilationPlan:
    apis = list(plan.apis)
    api = apis[index]
    if "behavior" in updates:
        api = api.model_copy(update={
            "behavior": api.behavior.model_copy(update=updates.pop("behavior")),
        })
    apis[index] = api.model_copy(update=updates)
    return plan.model_copy(update={"apis": apis})


def test_declared_operations_emit_their_exact_method_path_and_guard():
    files = _emitted(_declared_plan())
    declared = files["app/api/declared.py"]
    for method, path in (
        ("GET", "/payroll/employees"),
        ("GET", "/payroll/employees/{employee_id}"),
        ("POST", "/payroll/employees"),
        ("DELETE", "/payroll/employees/{employee_id}"),
    ):
        assert f"methods=[{method!r}]" in declared
        assert f"        {path!r}," in declared
    assert "action='employee.read', resource='Employee'" in declared
    assert "action='employee.create', resource='Employee'" in declared
    assert "action='employee.delete', resource='Employee'" in declared
    assert "OPERATION_POLICIES['api:create']" in declared
    main = files["app/main.py"]
    assert "from app.api.declared import register_declared_routes" in main
    assert main.index("register_declared_routes(router)") < main.index(
        "app.include_router(router)"
    )


def test_declared_route_metadata_binds_each_operation_to_its_service_and_policy():
    declared = _emitted(_declared_plan())["app/api/declared.py"]
    for fragment in (
        "'operation_id': 'api:create'",
        "'declared_operation_id': 'employee.create'",
        "'service_id': 'service:payroll'",
        "'resource': 'Employee'",
        "'policy_ids': ['security:payroll-approver']",
    ):
        assert fragment in declared


def test_declared_operation_without_an_explicit_service_binding_fails_closed():
    plan = _with_api(_declared_plan(), 0, service_id=None)
    with pytest.raises(UnsupportedSemanticsError, match="explicit EXPOSES service binding"):
        _emitted(plan)


def test_declared_operation_referencing_an_unknown_policy_fails_closed():
    plan = _with_api(
        _declared_plan(), 0,
        behavior={"authorization_policy_ids": ("security:missing",)},
    )
    with pytest.raises(UnsupportedSemanticsError, match="unknown policy"):
        _emitted(plan)


def test_declared_operation_bound_to_an_untyped_policy_fails_closed():
    plan = _declared_plan()
    plan = plan.model_copy(update={
        "security": [SecurityPolicy(
            policy_id="security:payroll-approver", behavior=None,
        )],
    })
    with pytest.raises(UnsupportedSemanticsError, match="carries no typed rules"):
        _emitted(plan)


def test_declared_policy_that_does_not_govern_the_action_fails_closed():
    policy = _declared_policy()
    policy = policy.model_copy(update={
        "behavior": policy.behavior.model_copy(update={
            "rules": (policy.behavior.rules[0],),
        }),
    })
    plan = _declared_plan().model_copy(update={"security": [policy]})
    with pytest.raises(UnsupportedSemanticsError, match="do not govern action"):
        _emitted(plan)


def test_duplicate_declared_method_and_path_fails_closed():
    plan = _declared_plan()
    duplicate = _operation(
        "api:duplicate", "duplicateEmployees", "GET", "/payroll/employees",
        "employee.read", response=_EMPLOYEE,
    )
    plan = plan.model_copy(update={"apis": [*plan.apis, duplicate]})
    with pytest.raises(UnsupportedSemanticsError, match="declare the same GET route"):
        _emitted(plan)


def test_declared_route_that_collides_with_emitted_crud_fails_closed():
    plan = _declared_plan()
    colliding = _operation(
        "api:collide", "collideEmployees", "GET", "/api/employees",
        "employee.read", response=_EMPLOYEE,
    )
    plan = plan.model_copy(update={"apis": [*plan.apis, colliding]})
    with pytest.raises(UnsupportedSemanticsError, match="collides with the emitted"):
        _emitted(plan)


def test_undeclarable_response_semantics_fail_closed():
    invented = FieldSpec(name="gross_pay", value_type=ValueType.MONEY)
    plan = _with_api(
        _declared_plan(), 2,
        behavior={"response_fields": (*_EMPLOYEE, invented)},
    )
    with pytest.raises(UnsupportedSemanticsError, match="response field"):
        _emitted(plan)


def test_declared_query_and_filter_semantics_fail_closed():
    plan = _with_api(
        _declared_plan(), 0,
        behavior={"request_fields": (_EMPLOYEE[0],)},
    )
    with pytest.raises(UnsupportedSemanticsError, match="query and filter"):
        _emitted(plan)


def test_declared_delete_without_exactly_one_path_parameter_fails_closed():
    plan = _with_api(
        _declared_plan(), 3,
        behavior={"path": "/payroll/employees", "request_fields": ()},
    )
    with pytest.raises(UnsupportedSemanticsError, match="exactly one path parameter"):
        _emitted(plan)


def test_declared_constraints_the_route_cannot_enforce_fail_closed():
    constrained = FieldSpec(
        name="employee_id",
        value_type=ValueType.IDENTIFIER,
        constraints=(FieldConstraint(operator=ConstraintOperator.UNIQUE),),
    )
    plan = _with_api(
        _declared_plan(), 2,
        behavior={"request_fields": (constrained, *_EMPLOYEE[1:])},
    )
    with pytest.raises(UnsupportedSemanticsError, match="cannot enforce"):
        _emitted(plan)


def test_declared_operation_without_a_policy_is_emitted_unprotected(tmp_path):
    plan = _declared_plan()
    apis = [
        api.model_copy(update={
            "behavior": api.behavior.model_copy(
                update={"authorization_policy_ids": ()}
            ),
        })
        for api in plan.apis
    ]
    plan = plan.model_copy(update={"security": [], "apis": apis})
    repo = PythonFastAPIBackend().compile(plan)
    declared = repo.files["app/api/declared.py"]
    assert "router.add_api_route(" in declared
    assert "require_authorization" not in declared
    assert "OPERATION_POLICIES" not in declared
    # Validation is still a real contract without a policy: the request model
    # rejects unknown fields and the route is emitted at its exact path.
    assert "class CreateEmployeeRequest(BaseModel):" in declared
    assert "model_config = ConfigDict(extra='forbid')" in declared
    for path, source in repo.files.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    tests = repo.files["tests/test_app.py"]
    assert "def test_declared_operation_emits_the_exact_route():" in tests
    assert "def test_declared_operation_rejects_a_malformed_payload():" in tests
    assert "def test_declared_operation_requires_a_signed_token():" not in tests


def test_rust_backend_refuses_declared_operations():
    with pytest.raises(UnsupportedSemanticsError, match="api_contracts"):
        RustAxumBackend().compile(_declared_plan())


def test_declared_operation_runtime_suite_executes_and_proves_enforcement(tmp_path):
    repo = PythonFastAPIBackend().compile(_declared_plan())
    for path, source in repo.files.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "tests"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    tests = repo.files["tests/test_app.py"]
    for name in (
        "test_declared_operation_emits_the_exact_route",
        "test_declared_operation_requires_a_signed_token",
        "test_declared_operation_denies_a_principal_without_a_grant",
        "test_declared_operation_rejects_a_malformed_payload",
        "test_declared_operation_authorized_create_and_read",
        "test_declared_operation_denial_does_not_mutate_state",
        "test_declared_operation_explicit_deny_wins",
    ):
        assert f"def {name}():" in tests


def test_source_bound_policy_reaches_the_emitted_route():
    plan = authorized_backend_plan()
    protected = protected_services(plan)
    assert "service:payroll" in protected
    main = _emitted(plan)["app/main.py"]
    assert 'action="employee.read"' in main
    assert 'resource="Employee"' in main
    assert "SERVICE_POLICIES" in main


def test_each_emitted_route_is_bound_to_its_own_action():
    main = _emitted(authorized_backend_plan())["app/main.py"]
    for verb in ("read", "create", "update", "delete"):
        assert f'action="{canonical_action("Employee", verb)}"' in main


def test_generated_runtime_resolves_identity_only_from_a_signed_token():
    source = _emitted(authorized_backend_plan())["app/core/authorization.py"]
    lowered = source.lower()
    # Roles and tenant identity come from verified claims, never from headers.
    assert "x-role" not in lowered
    assert "x-tenant" not in lowered
    assert "x-forwarded-user" not in lowered
    assert 'request.headers.get("authorization")' in source
    assert "hmac.compare_digest" in source
    assert "GENERATED_AUTH_SECRET" in source


def test_generated_runtime_denies_by_default_and_explicit_deny_wins():
    source = _emitted(authorized_backend_plan())["app/core/authorization.py"]
    assert "no matching allow rule; default deny" in source
    assert source.index("explicit deny rule") < source.index("allow rule '")
    assert "tenant identity is missing" in source
    assert "different tenant" in source
    # Absence of a required attribute must never grant access.
    assert "never grants access" in source


def test_generated_suite_proves_allow_deny_and_no_mutation_after_denial():
    source = _emitted(authorized_backend_plan())["tests/test_app.py"]
    for name in (
        "test_authorization_requires_a_signed_token",
        "test_authorization_rejects_a_tampered_token",
        "test_authorization_denies_a_principal_without_a_grant",
        "test_denied_request_does_not_mutate_state",
        "test_authorization_runtime_denies_by_default",
        "test_authorization_runtime_explicit_deny_wins_over_allow",
        "test_authorization_runtime_missing_attribute_never_grants",
        "test_authorization_runtime_isolates_tenants",
    ):
        assert f"def {name}():" in source


def test_changing_the_policy_changes_the_emitted_enforcement():
    plan = authorized_backend_plan()
    policies = _emitted(plan)["app/core/policies.py"]
    assert "payroll_approver" in policies

    policy = next(p for p in plan.security if p.policy_id == "security:payroll-approver")
    changed = policy.model_copy(update={
        "behavior": policy.behavior.model_copy(update={
            "roles": ("payroll_admin",),
            "rules": tuple(
                rule.model_copy(update={"roles": ("payroll_admin",)})
                for rule in policy.behavior.rules
            ),
        }),
    })
    revised = plan.model_copy(update={
        "security": [changed],
        "services": [
            service.model_copy(update={
                "security_policies": [
                    changed if item.policy_id == changed.policy_id else item
                    for item in service.security_policies
                ],
            })
            for service in plan.services
        ],
    })
    revised_policies = _emitted(revised)["app/core/policies.py"]
    assert "payroll_admin" in revised_policies
    assert "payroll_approver" not in revised_policies


def test_operation_bound_obligation_fails_closed():
    policy = SecurityPolicy(policy_id="security:payroll", behavior=None)
    plan = CompilationPlan(
        plan_id="operation-plan", isr_id="system",
        apis=[ApiOperation(
            id="api:submit", name="submit",
            behavior=ApiBehavior(
                operation_id="submit", method="POST", path="/submit",
                authorization_policy_ids=("security:payroll",),
            ),
        )],
        security=[policy],
    )
    with pytest.raises(UnsupportedSemanticsError, match="authorization_policies"):
        assert_authorization_enforceable(plan)
    for backend in (PythonFastAPIBackend(), RustAxumBackend()):
        with pytest.raises(UnsupportedSemanticsError):
            backend.compile(plan)


def test_rule_naming_an_action_that_is_not_a_route_fails_closed():
    plan = authorized_backend_plan()
    policy = next(p for p in plan.security if p.policy_id == "security:payroll-approver")
    rule = policy.behavior.rules[0]
    broken = policy.model_copy(update={
        "behavior": policy.behavior.model_copy(update={
            "rules": (rule.model_copy(update={"actions": ("payroll.submit",)}),),
        }),
    })
    broken_plan = plan.model_copy(update={
        "security": [broken],
        "services": [
            service.model_copy(update={
                "security_policies": [
                    broken if item.policy_id == broken.policy_id else item
                    for item in service.security_policies
                ],
            })
            for service in plan.services
        ],
    })
    with pytest.raises(UnsupportedSemanticsError, match="payroll.submit"):
        assert_authorization_enforceable(broken_plan)


def test_only_the_python_backend_claims_authorization_support():
    assert SemanticFeature.AUTHORIZATION_POLICIES in PythonFastAPIBackend().supported_features
    assert SemanticFeature.AUTHORIZATION_POLICIES not in RustAxumBackend().supported_features


def test_declaration_only_policy_leaves_routes_unprotected():
    plan = backend_plan()
    main = _emitted(plan)["app/main.py"]
    assert "require_authorization" not in main
    assert "SERVICE_POLICIES" not in main


def test_emitted_sources_are_valid_python():
    for path, source in _emitted(authorized_backend_plan()).items():
        if path.endswith(".py"):
            ast.parse(source, filename=path)



def test_lowering_preserves_explicit_service_exposes_api_binding():
    revision = full_stack_projection().revision
    graph = revision.graph
    edges = dict(graph.edges)
    edges["exposes:payroll"] = Edge(
        id="exposes:payroll",
        type=EdgeType.EXPOSES,
        source_id="service:payroll",
        target_id="api:payroll",
    )
    bound_revision = revision.model_copy(
        update={"graph": graph.model_copy(update={"edges": edges})}
    )

    plan = isr_to_plan(bound_revision)
    operation = next(api for api in plan.apis if api.id == "api:payroll")
    assert operation.service_id == "service:payroll"


def test_lowering_does_not_infer_api_service_from_names_or_fields():
    plan = isr_to_plan(full_stack_projection().revision)
    operation = next(api for api in plan.apis if api.id == "api:payroll")
    assert operation.service_id is None


def test_lowering_rejects_ambiguous_service_exposes_api_bindings():
    revision = full_stack_projection().revision
    graph = revision.graph
    edges = dict(graph.edges)
    edges["exposes:payroll"] = Edge(
        id="exposes:payroll",
        type=EdgeType.EXPOSES,
        source_id="service:payroll",
        target_id="api:payroll",
    )
    edges["exposes:payroll-duplicate"] = Edge(
        id="exposes:payroll-duplicate",
        type=EdgeType.EXPOSES,
        source_id="service:other",
        target_id="api:payroll",
    )
    bound_revision = revision.model_copy(
        update={"graph": graph.model_copy(update={"edges": edges})}
    )

    with pytest.raises(ValueError, match="exactly one explicit EXPOSES service binding"):
        isr_to_plan(bound_revision)
