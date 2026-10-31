"""Explicit declared API operation emission contract.

A declared ``ApiBehavior`` is only emittable when the plan states every binding
the route needs. Nothing is inferred from names, paths, or request fields:

* the operation names exactly one owning service through an explicit ISR
  ``EXPOSES`` relation;
* the resource the operation governs comes from the typed policy rule that
  names the operation, or from the service's single persisted data model;
* every referenced policy exists, carries typed rules, and governs the
  operation; and
* the declared response fields are produced by the operation itself.

Anything else fails closed with ``UnsupportedSemanticsError`` instead of
emitting a route whose semantics were invented by the emitter.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from compiler.core.capabilities import UnsupportedSemanticsError
from compiler.core.plan import ApiOperation, CompilationPlan, SecurityPolicy, Service
from isr.core.behavior import FieldSpec

_PATH_PARAMETER = re.compile(r"\{([^{}]+)\}")

#: Methods whose declared payload is sent in the request body. Everything else
#: turns the non-path request fields into query parameters.
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


@dataclass(frozen=True)
class DeclaredRoute:
    """One declared operation with every binding resolved for an emitter."""

    operation: ApiOperation
    service: Service
    resource: str
    action: str
    policies: tuple[SecurityPolicy, ...]
    path_fields: tuple[FieldSpec, ...]
    body_fields: tuple[FieldSpec, ...]
    response_fields: tuple[FieldSpec, ...]

    @property
    def path(self) -> str:
        return self.operation.behavior.path

    @property
    def method(self) -> str:
        return self.operation.behavior.method

    @property
    def resource_module(self) -> str:
        return re.sub(r"\W", "_", self.resource.strip()).lower()

    def as_dict(self) -> dict[str, object]:
        return {
            "operation_id": self.operation.id,
            "declared_operation_id": self.action,
            "service_id": self.service.id,
            "method": self.method,
            "path": self.path,
            "resource": self.resource,
            "policy_ids": [policy.policy_id for policy in self.policies],
            "request_fields": [
                field.name for field in self.path_fields + self.body_fields
            ],
            "response_fields": [field.name for field in self.response_fields],
        }


def normalized_path(path: str) -> str:
    """Collapse path parameter names so conflicting templates compare equal."""
    return _PATH_PARAMETER.sub("{}", path)


def _placeholders(path: str) -> tuple[str, ...]:
    return tuple(_PATH_PARAMETER.findall(path))


def _bound_policies(plan: CompilationPlan, api: ApiOperation) -> tuple[SecurityPolicy, ...]:
    """Resolve the policies bound to an operation, without silently dropping one."""
    by_id = {policy.policy_id: policy for policy in plan.security}
    attached: list[SecurityPolicy] = list(api.security_policies)
    behavior = api.behavior
    if behavior is not None:
        for policy_id in behavior.authorization_policy_ids:
            policy = by_id.get(policy_id)
            if policy is None:
                raise UnsupportedSemanticsError(
                    "authorization_policies: operation "
                    f"'{api.id}' references unknown policy '{policy_id}'"
                )
            attached.append(policy)
    resolved: list[SecurityPolicy] = []
    seen: set[str] = set()
    for policy in attached:
        if policy.policy_id in seen:
            continue
        seen.add(policy.policy_id)
        if policy.behavior is None:
            raise UnsupportedSemanticsError(
                "authorization_policies: policy "
                f"'{policy.policy_id}' is bound to operation '{api.id}' but "
                "carries no typed rules, so no enforcement can be proven"
            )
        resolved.append(policy)
    return tuple(resolved)


def _resource_for(service: Service, api: ApiOperation, policies: tuple[SecurityPolicy, ...]) -> str:
    """Resolve the resource the operation governs, or fail closed."""
    assert api.behavior is not None
    action = api.behavior.operation_id
    matching_rules = []
    for policy in policies:
        policy_rules = [
            rule for rule in policy.behavior.rules
            if "*" in rule.actions or action in rule.actions
        ]
        if not policy_rules:
            raise UnsupportedSemanticsError(
                "authorization_policies: policy "
                f"'{policy.policy_id}' is bound to operation '{api.id}' but "
                f"its rules do not govern action '{action}'"
            )
        matching_rules.extend(policy_rules)

    resources = {
        rule.resource for rule in matching_rules if rule.resource != "*"
    }
    if len(resources) > 1:
        raise UnsupportedSemanticsError(
            "authorization_policies: operation "
            f"'{api.id}' is governed by rules naming multiple resources: "
            f"{sorted(resources)}"
        )
    if resources:
        resource = resources.pop()
    else:
        owned = [model.entity_name for model in service.data_models]
        if len(owned) != 1:
            raise UnsupportedSemanticsError(
                "api_contracts: operation "
                f"'{api.id}' has no resource binding and service "
                f"'{service.id}' persists {len(owned)} resources, so the "
                "emitted route would have no unambiguous target"
            )
        resource = owned[0]

    if not any(model.entity_name == resource for model in service.data_models):
        raise UnsupportedSemanticsError(
            "api_contracts: operation "
            f"'{api.id}' names resource '{resource}', which service "
            f"'{service.id}' does not persist"
        )
    return resource


def _route_shape(api: ApiOperation) -> tuple[tuple[FieldSpec, ...], tuple[FieldSpec, ...]]:
    """Split declared request fields into path and body parameters."""
    assert api.behavior is not None
    behavior = api.behavior
    if "?" in behavior.path or "#" in behavior.path:
        raise UnsupportedSemanticsError(
            f"api_contracts: operation '{api.id}' declares a path with a query "
            f"or fragment component: {behavior.path!r}"
        )
    placeholders = _placeholders(behavior.path)
    if len(placeholders) != len(set(placeholders)):
        raise UnsupportedSemanticsError(
            f"api_contracts: operation '{api.id}' declares duplicate path parameters"
        )
    by_name = {field.name: field for field in behavior.request_fields}
    missing = [name for name in placeholders if name not in by_name]
    if missing:
        raise UnsupportedSemanticsError(
            f"api_contracts: operation '{api.id}' declares path parameters "
            f"{missing} that are not request fields"
        )
    path_fields = tuple(by_name[name] for name in placeholders)
    if any(not field.required for field in path_fields):
        raise UnsupportedSemanticsError(
            f"api_contracts: operation '{api.id}' declares a path parameter "
            "that is not required"
        )
    remaining = tuple(
        field for field in behavior.request_fields if field.name not in set(placeholders)
    )

    if behavior.method == "GET":
        if len(path_fields) > 1:
            raise UnsupportedSemanticsError(
                f"api_contracts: GET operation '{api.id}' declares "
                f"{len(path_fields)} path parameters; at most one is supported"
            )
        if remaining:
            raise UnsupportedSemanticsError(
                f"api_contracts: GET operation '{api.id}' declares request "
                f"fields {[field.name for field in remaining]} that are not "
                "path parameters; query and filter semantics are not supported"
            )
        return path_fields, ()
    if behavior.method == "DELETE":
        if len(path_fields) != 1:
            raise UnsupportedSemanticsError(
                f"api_contracts: DELETE operation '{api.id}' must declare "
                "exactly one path parameter"
            )
        if remaining:
            raise UnsupportedSemanticsError(
                f"api_contracts: DELETE operation '{api.id}' declares request "
                "fields beyond the path parameter, whose semantics are not defined"
            )
        return path_fields, ()
    if behavior.method in ("PUT", "PATCH"):
        if len(path_fields) != 1:
            raise UnsupportedSemanticsError(
                f"api_contracts: {behavior.method} operation '{api.id}' must "
                "declare exactly one path parameter"
            )
        return path_fields, remaining
    if behavior.method == "POST":
        if path_fields:
            raise UnsupportedSemanticsError(
                f"api_contracts: POST operation '{api.id}' declares path "
                "parameters, whose effect on the target record is not defined, "
                "so it fails closed"
            )
        return (), remaining
    raise UnsupportedSemanticsError(
        f"api_contracts: operation '{api.id}' declares unsupported method "
        f"{behavior.method!r}"
    )


def _response_fields(
    api: ApiOperation,
    service: Service,
    resource: str,
) -> tuple[FieldSpec, ...]:
    """Reject response contracts the operation itself cannot produce."""
    assert api.behavior is not None
    behavior = api.behavior
    names = [field.name for field in behavior.response_fields]
    if len(names) != len(set(names)):
        raise UnsupportedSemanticsError(
            f"api_contracts: operation '{api.id}' declares duplicate response fields"
        )
    produced = {"id"} | {field.name for field in behavior.request_fields}
    # Reads and merges return a stored record, whose fields come from the
    # resource's typed data model as well as from the operation's own writes.
    if behavior.method in ("GET", "DELETE", "PATCH"):
        model = next(
            (item for item in service.data_models if item.entity_name == resource),
            None,
        )
        if model is not None and model.behavior is not None:
            produced |= {field.name for field in model.behavior.fields}
    unsupported = sorted(set(names) - produced)
    if unsupported:
        raise UnsupportedSemanticsError(
            "api_contracts: operation "
            f"'{api.id}' declares response field(s) {unsupported} that the "
            "operation does not accept or generate; unsupported response "
            "semantics fail closed instead of returning invented values"
        )
    return tuple(behavior.response_fields)


def _validate_field_constraints(api: ApiOperation, fields: tuple[FieldSpec, ...]) -> None:
    """Reject constraints the emitted route cannot enforce."""
    for field in fields:
        for constraint in field.constraints:
            operator = constraint.operator.value
            if operator in {"one_of", "unique", "immutable", "references"}:
                raise UnsupportedSemanticsError(
                    f"api_contracts: operation '{api.id}' declares constraint "
                    f"{operator!r} on field '{field.name}', which the emitted "
                    "route cannot enforce"
                )


def declared_routes(plan: CompilationPlan) -> tuple[DeclaredRoute, ...]:
    """Return every declared operation with its bindings resolved, or fail closed."""
    services = {service.id: service for service in plan.services}
    routes: list[DeclaredRoute] = []
    seen: dict[tuple[str, str], str] = {}

    for api in plan.apis:
        if api.behavior is None:
            if api.security_policies:
                raise UnsupportedSemanticsError(
                    "authorization_policies: operation "
                    f"'{api.id}' is bound to a policy but declares no API "
                    "behavior, so no route can be emitted to enforce it"
                )
            continue

        policies = _bound_policies(plan, api)
        if api.service_id is None:
            raise UnsupportedSemanticsError(
                "api_contracts: operation "
                f"'{api.id}' has no explicit EXPOSES service binding, so its "
                "side effect target is ambiguous"
            )
        service = services.get(api.service_id)
        if service is None:
            raise UnsupportedSemanticsError(
                "api_contracts: operation "
                f"'{api.id}' binds unknown service '{api.service_id}'"
            )

        key = (api.behavior.method, normalized_path(api.behavior.path))
        previous = seen.get(key)
        if previous is not None:
            raise UnsupportedSemanticsError(
                "api_contracts: operations "
                f"'{previous}' and '{api.id}' declare the same "
                f"{api.behavior.method} route {api.behavior.path!r}"
            )
        seen[key] = api.id

        resource = _resource_for(service, api, policies)
        path_fields, body_fields = _route_shape(api)
        response_fields = _response_fields(api, service, resource)
        _validate_field_constraints(api, path_fields + body_fields + response_fields)
        routes.append(DeclaredRoute(
            operation=api,
            service=service,
            resource=resource,
            action=api.behavior.operation_id,
            policies=policies,
            path_fields=path_fields,
            body_fields=body_fields,
            response_fields=response_fields,
        ))

    return tuple(routes)
