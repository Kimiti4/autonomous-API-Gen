"""One ISR-derived HTTP contract for backend parity.

The contract is the plan's declared operations. A backend either executes that
contract over HTTP or refuses to generate. A fixed ``/api/records`` smoke test
is not this contract, and a refusal is not production readiness.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
import time
from decimal import Decimal

from compiler.core.capabilities import (
    BackendCapabilities,
    SemanticFeature,
    UnsupportedSemanticsError,
    assert_plan_supported,
)
from compiler.core.declared_api import DeclaredRoute, declared_routes
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
    DataModelBehavior,
    FieldSpec,
    SecurityBehavior,
    ValueType,
)


PAYROLL_EMPLOYEE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec(name="employee_id", value_type=ValueType.IDENTIFIER),
    FieldSpec(name="base_salary", value_type=ValueType.MONEY, precision=12, scale=2),
    FieldSpec(name="allowances", value_type=ValueType.MONEY, precision=12, scale=2),
)


def payroll_security_policy() -> SecurityPolicy:
    return SecurityPolicy(
        policy_id="security:payroll-approver",
        behavior=SecurityBehavior(
            roles=("payroll_approver", "payroll_admin"),
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
                AuthorizationRule(
                    rule_id="payroll.delete.allow",
                    effect="allow",
                    roles=("payroll_admin",),
                    actions=("employee.delete",),
                    resource="Employee",
                ),
            ),
        ),
    )


def payroll_parity_operation(
    api_id: str,
    name: str,
    method: str,
    path: str,
    action: str,
    request: tuple[FieldSpec, ...] = (),
    response: tuple[FieldSpec, ...] = (),
) -> ApiOperation:
    return ApiOperation(
        id=api_id,
        name=name,
        service_id="service:payroll",
        behavior=ApiBehavior(
            operation_id=action,
            method=method,
            path=path,
            request_fields=request,
            response_fields=response,
            authorization_policy_ids=("security:payroll-approver",),
        ),
    )


def canonical_payroll_parity_plan() -> CompilationPlan:
    """The frozen ISR compilation plan for cross-backend HTTP parity."""
    fields = PAYROLL_EMPLOYEE_FIELDS
    return CompilationPlan(
        plan_id="isr-parity",
        isr_id="isr-parity",
        services=[Service(
            id="service:payroll",
            name="Payroll",
            data_models=[DataModel(
                id="dm:employee",
                entity_name="Employee",
                behavior=DataModelBehavior(fields=fields),
            )],
        )],
        security=[payroll_security_policy()],
        apis=[
            payroll_parity_operation(
                "api:create", "createEmployee", "POST", "/payroll/employees",
                "employee.create", request=fields, response=fields,
            ),
            payroll_parity_operation(
                "api:read", "readEmployee", "GET",
                "/payroll/employees/{employee_id}", "employee.read",
                request=fields[:1], response=fields,
            ),
            payroll_parity_operation(
                "api:delete", "deleteEmployee", "DELETE",
                "/payroll/employees/{employee_id}", "employee.delete",
                request=fields[:1], response=fields[:1],
            ),
        ],
    )


def canonical_payroll_http_contract() -> dict[str, object]:
    """The projected HTTP contract for the frozen canonical payroll plan."""
    return copy.deepcopy(http_contract(canonical_payroll_parity_plan()))


_DATABASE_MARKERS = (
    "psycopg",
    "sqlalchemy",
    "asyncpg",
    "Npgsql",
    "postgres://",
    "sqlite3",
)


class RefusingParityBackend:
    """A named target with no implementation of the ISR HTTP contract."""

    def __init__(self, name: str, reason: str) -> None:
        self.name = name
        self.version = "0"
        self.reason = reason
        self.supported_features = frozenset[SemanticFeature]()

    def compile(self, plan: CompilationPlan) -> None:
        assert_plan_supported(plan, BackendCapabilities(
            backend_id=self.name,
            version=self.version,
            supported_features=self.supported_features,
        ))
        raise UnsupportedSemanticsError(
            f"{self.name} has no ISR-derived HTTP implementation; {self.reason}"
        )


def ruby_rails_parity_backend() -> RefusingParityBackend:
    return RefusingParityBackend(
        "ruby-rails",
        "Rails boot remains unverified and is not implied by the stdlib server",
    )


def aspnet_parity_backend() -> RefusingParityBackend:
    return RefusingParityBackend(
        "aspnet-core",
        "the generated host smoke test is not an ISR-derived API",
    )


def sample_value(field: FieldSpec) -> object:
    """A value inside the declared type. This is not a backend fixture."""
    kind = field.value_type.value
    if kind == "integer":
        return 1
    if kind in ("decimal", "money"):
        return "10.00"
    if kind == "boolean":
        return True
    if kind == "date":
        return "2026-01-01"
    if kind == "datetime":
        return "2026-01-01T00:00:00Z"
    return f"{field.name}-alpha"


def _roles(route: DeclaredRoute, effect: str) -> list[str]:
    found: list[str] = []
    for policy in route.policies:
        assert policy.behavior is not None
        for rule in policy.behavior.rules:
            if rule.effect != effect or rule.resource not in (route.resource, "*"):
                continue
            if "*" in rule.actions or route.action in rule.actions:
                found.extend(rule.roles)
    return list(dict.fromkeys(found))


def _route_binding(route: DeclaredRoute) -> dict[str, object]:
    allow_roles = _roles(route, "allow")
    deny_roles = _roles(route, "deny")
    return {
        "operation_id": route.operation.id,
        "method": route.method,
        "path": route.path,
        "action": route.action,
        "resource": route.resource,
        "path_fields": [field.name for field in route.path_fields],
        "body_fields": [field.name for field in route.body_fields],
        "response_fields": [field.name for field in route.response_fields],
        "sample_body": {field.name: sample_value(field) for field in route.body_fields},
        "authorized": bool(route.policies),
        "allow_roles": allow_roles,
        "deny_roles": deny_roles,
    }


def assert_contract_slice(routes: tuple[DeclaredRoute, ...]) -> None:
    """Refuse declared operations outside the passing payroll slice.

    The slice is one resource, one create, item read and delete, no query
    collection, no attribute conditions, and the field types the HTTP gate
    validates. PUT and other methods stay unsupported.
    """
    if not routes:
        return
    key_fields = {route.path_fields[0].name for route in routes if route.path_fields}
    if len(key_fields) != 1:
        raise UnsupportedSemanticsError(
            "api_contracts: the contract slice requires one shared path key, "
            f"not {sorted(key_fields)}"
        )
    key = next(iter(key_fields))
    posts = [route for route in routes if route.method == "POST"]
    if len(posts) != 1 or key not in {field.name for field in posts[0].body_fields}:
        raise UnsupportedSemanticsError(
            "api_contracts: the contract slice requires the create body to "
            f"carry the path key '{key}'"
        )
    if len({route.resource for route in routes}) != 1:
        raise UnsupportedSemanticsError(
            "api_contracts: the contract slice serves one declared resource"
        )
    for route in routes:
        if route.method not in {"GET", "POST", "DELETE"}:
            raise UnsupportedSemanticsError(
                "api_contracts: the contract slice does not implement "
                f"{route.method} for operation '{route.operation.id}'"
            )
        if route.method == "GET" and not route.path_fields:
            raise UnsupportedSemanticsError(
                "api_contracts: the contract slice does not implement "
                f"collection read '{route.operation.id}'"
            )
        for policy in route.policies:
            assert policy.behavior is not None
            for rule in policy.behavior.rules:
                if rule.conditions:
                    raise UnsupportedSemanticsError(
                        "authorization_policies: the contract slice does not "
                        f"evaluate conditions on '{rule.rule_id}'"
                    )
        if not route.policies:
            raise UnsupportedSemanticsError(
                "api_contracts: the contract slice does not emit an "
                f"unauthenticated declared operation '{route.operation.id}'"
            )
        for field in route.path_fields + route.body_fields + route.response_fields:
            if field.value_type.value not in {"string", "identifier", "integer", "decimal", "money", "boolean"}:
                raise UnsupportedSemanticsError(
                    "api_contracts: the contract slice cannot validate "
                    f"{field.value_type.value} on '{field.name}'"
                )
            if field.constraints:
                raise UnsupportedSemanticsError(
                    "api_contracts: the contract slice cannot enforce "
                    f"constraints on '{field.name}'"
                )


def http_contract(plan: CompilationPlan) -> dict[str, object]:
    """Project the HTTP obligations of one plan. Paths come from the ISR."""
    routes = declared_routes(plan)
    if not routes:
        raise UnsupportedSemanticsError(
            "api_contracts: the parity plan declares no executable operations"
        )
    creates = [route for route in routes if route.method == "POST"]
    reads = [route for route in routes if route.method == "GET" and route.path_fields]
    deletes = [route for route in routes if route.method == "DELETE"]
    if len(creates) != 1 or len(reads) != 1 or len(deletes) != 1:
        raise UnsupportedSemanticsError(
            "api_contracts: the parity contract requires one create, one item "
            "read, and one delete so the HTTP checks have one target"
        )
    create = creates[0]
    read = reads[0]
    delete = deletes[0]
    if create.resource != read.resource or create.service.id != read.service.id:
        raise UnsupportedSemanticsError(
            "api_contracts: create and read must address the same declared resource"
        )
    invalid_body = dict(_route_binding(create)["sample_body"])  # type: ignore[arg-type]
    money = next(
        (field for field in create.body_fields if field.value_type.value in ("decimal", "money")),
        None,
    )
    if money is None:
        raise UnsupportedSemanticsError(
            "api_contracts: the parity contract requires one decimal field so "
            "invalid input is a type failure"
        )
    invalid_body[money.name] = "not-a-decimal"
    omitted = next(iter(create.body_fields)).name
    missing_field = {
        key: value for key, value in invalid_body.items() if key != omitted
    }
    missing_field[money.name] = "10.00"
    delete_binding = _route_binding(delete)
    denied = set(delete_binding["deny_roles"])  # type: ignore[arg-type]
    positive_delete = [
        role for role in delete_binding["allow_roles"]  # type: ignore[union-attr]
        if role not in denied
    ]
    if not positive_delete:
        raise UnsupportedSemanticsError(
            "api_contracts: the declared delete has no role that is allowed "
            "to succeed, so the positive delete path cannot be tested"
        )
    return {
        "create": _route_binding(create),
        "read": _route_binding(read),
        "delete": delete_binding,
        "delete_role": positive_delete[0],
        "invalid_type_body": invalid_body,
        "missing_field_body": missing_field,
        "missing_field": omitted,
        "paths": [route.path for route in routes],
    }


def issue_contract_token(principal_id: str, roles: list[str], *,
                         secret: str = "generated-dev-secret", ttl_seconds: int = 3600) -> str:
    """Mint the bearer token both HTTP verifiers accept.

    The payload is HMAC-SHA256 over the unpadded URL-safe body. Callers use
    this instead of a backend's own issuer so each verifier is checked
    against the same bytes.
    """
    claims = {
        "sub": principal_id,
        "roles": list(roles),
        "tenant_id": None,
        "attributes": {},
        "exp": int(time.time()) + int(ttl_seconds),
    }
    body = _token_b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    signature = _token_b64(hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def _token_b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def assess_contract(send, contract: dict) -> dict[str, object]:
    """Apply the shared HTTP assertions through ``send``.

    ``send(method, path, body, headers)`` returns ``(status, payload)``.
    ``/health`` is the only path allowed beside the declared operations.
    """
    failures: list[str] = []

    def check(name: str, condition: bool, detail: object) -> None:
        if not condition:
            failures.append(f"{name}: {detail}")

    def same(expected: object, actual: object) -> bool:
        if isinstance(expected, str):
            try:
                return Decimal(expected) == Decimal(str(actual))
            except Exception:
                return actual == expected
        return actual == expected

    key = {"X-API-Key": "generated-dev-key"}

    def bearer(roles: list[str]) -> dict[str, str]:
        return {**key, "Authorization": f"Bearer {issue_contract_token('service-account', roles)}"}

    create = contract["create"]
    read = contract["read"]
    delete = contract["delete"]
    auth = bearer(list(create["allow_roles"]))
    deleter = bearer([contract["delete_role"]])
    status, spec = send("GET", "/openapi.json", None, {})
    paths = spec.get("paths", {}) if isinstance(spec, dict) else {}
    check("openapi", status == 200 and isinstance(paths, dict), status)
    declared_paths = set(contract["paths"])
    actual_paths = set(paths)
    check("missing-routes", declared_paths <= actual_paths, sorted(declared_paths - actual_paths))
    check(
        "undeclared-routes",
        actual_paths <= declared_paths | {"/health"},
        sorted(actual_paths - declared_paths - {"/health"}),
    )
    for binding in (create, read, delete):
        methods = paths.get(binding["path"], {})
        check(
            binding["operation_id"],
            isinstance(methods, dict) and binding["method"].lower() in methods,
            f"missing {binding['method']} {binding['path']}",
        )
    unauthenticated, _ = send("POST", create["path"], create["sample_body"], key)
    check("unauthenticated", unauthenticated == 401, unauthenticated)
    forbidden, _ = send("POST", create["path"], create["sample_body"], bearer(["no_such_role"]))
    check("forbidden", forbidden == 403, forbidden)
    invalid_type, _ = send("POST", create["path"], contract["invalid_type_body"], auth)
    check("invalid-type", invalid_type == 422, invalid_type)
    missing_field, _ = send("POST", create["path"], contract["missing_field_body"], auth)
    check("missing-field", missing_field == 422, missing_field)
    created_status, body = send("POST", create["path"], create["sample_body"], auth)
    body = body if isinstance(body, dict) else {}
    check("create-status", created_status == 201, created_status)
    check("response-fields", set(body) == set(create["response_fields"]), sorted(body))
    for name, expected in create["sample_body"].items():
        check(f"projected-{name}", same(expected, body.get(name)), body.get(name))
    identifier = read["path_fields"][0]

    def item_path(value: object) -> str:
        return read["path"].replace("{" + identifier + "}", str(value))

    loaded_status, loaded = send("GET", item_path(body.get(identifier)), None, auth)
    loaded = loaded if isinstance(loaded, dict) else {}
    check("read-status", loaded_status == 200, loaded_status)
    if loaded_status == 200:
        check("read-fields", set(loaded) == set(read["response_fields"]), sorted(loaded))
        check("read-same-id", loaded.get(identifier) == body.get(identifier), loaded)
    missing_status, _ = send("GET", item_path("missing-employee"), None, auth)
    check("missing", missing_status == 404, missing_status)
    rejected = dict(create["sample_body"])
    rejected[identifier] = "employee_id-rejected"
    before_status, before = send("GET", item_path(body.get(identifier)), None, auth)
    denied_create, _ = send("POST", create["path"], rejected, bearer(["no_such_role"]))
    after_status, after = send("GET", item_path(body.get(identifier)), None, auth)
    absent_status, _ = send("GET", item_path("employee_id-rejected"), None, auth)
    check("denied-create", denied_create == 403, denied_create)
    check(
        "denied-create-keeps-state",
        before_status == 200 and after_status == 200 and after == before and absent_status == 404,
        after_status,
    )
    target = delete["path"].replace("{" + identifier + "}", str(body.get(identifier)))
    denied_delete, _ = send("DELETE", target, None, auth)
    still_status, still = send("GET", item_path(body.get(identifier)), None, auth)
    check("delete-denied", denied_delete == 403, denied_delete)
    check(
        "delete-denied-keeps-state",
        still_status == 200 and still == before,
        still_status,
    )
    removed_status, removed = send("DELETE", target, None, deleter)
    removed = removed if isinstance(removed, dict) else {}
    check("delete-authorized", removed_status == 200, removed_status)
    if removed_status == 200:
        check("delete-projection", set(removed) == set(delete["response_fields"]), sorted(removed))
        check("delete-id", removed.get(identifier) == body.get(identifier), removed)
    gone_status, _ = send("GET", item_path(body.get(identifier)), None, auth)
    check("read-after-delete", gone_status == 404, gone_status)
    repeated_status, _ = send("DELETE", target, None, deleter)
    check("delete-repeated", repeated_status == 404, repeated_status)
    return {"ok": not failures, "failures": failures}


def durable_database_claims(files: dict[str, str]) -> list[str]:
    """Return emitted files that claim a database driver or connection."""
    hits: list[str] = []
    for path, content in files.items():
        for marker in _DATABASE_MARKERS:
            if marker in content:
                hits.append(f"{path}: {marker}")
    return hits
