"""PythonFastAPIBackend — reference Python/FastAPI backend (ADR-012 + runnability upgrade).

Emits a genuinely runnable FastAPI application: health endpoint, per-entity
CRUD routers wired through application services and an in-memory repository,
Pydantic domain models, event handlers, API-key authorization (fail-closed),
working Kubernetes/CI manifests, and a real TestClient suite exercising the
CRUD surface, the OpenAPI document, and auth.
"""
from __future__ import annotations

import json
from decimal import Decimal

from compiler.core.plan import CompilationPlan, Service
from compiler.core.behavior_oracle import reference_evaluate, sample_context
from compiler.core.authorization import (
    ROUTE_VERBS,
    assert_authorization_enforceable,
    canonical_action,
    policy_payload,
    protected_services,
    service_policies,
)
from compiler.core.declared_api import (
    DeclaredRoute,
    declared_routes,
    normalized_path,
)
from compiler.core.capabilities import BackendCapabilities, SemanticFeature, UnsupportedSemanticsError, assert_plan_supported
from compiler.core.repository import GeneratedRepository, build_repository
from compiler.core.conformance import CHECKER, ConformanceReport
from compiler.core.protocol import BackendClass, BackendIdentity, TestSpec
from compiler.backends._naming import (
    cls_name as _cls,
    plan_entities,
    plan_events,
    plan_services,
    plural as _plural,
    slug as _slug,
)


class PythonFastAPIBackend:
    name = "python-fastapi"
    language = "python"
    framework = "fastapi"
    version = "1.4.0"
    supported_features = frozenset({
        SemanticFeature.TYPED_FIELDS,
        SemanticFeature.DECIMAL_SHAPE,
        SemanticFeature.EXPRESSIONS,
        SemanticFeature.BUSINESS_RULES,
        SemanticFeature.STATE_TRANSITIONS,
        SemanticFeature.API_CONTRACTS,
        SemanticFeature.AUTHORIZATION_POLICIES,
        SemanticFeature.EFFECT_POLICY_PRESERVATION,
        SemanticFeature.EFFECT_BINDING_PRESERVATION,
        SemanticFeature.CONSEQUENCE_PRESERVATION,
    })

    def identity(self) -> BackendIdentity:
        return BackendIdentity(
            name=self.name, language=self.language, framework=self.framework,
            version=self.version, backend_class=BackendClass.BEHAVIORAL,
        )

    def test_spec(self) -> TestSpec:
        return TestSpec(command=["python", "-m", "pytest", "-q"], runs_in="runtime")

    # -- plan layout -------------------------------------------------------

    def element_paths(self, plan: CompilationPlan) -> dict[str, str]:
        p: dict[str, str] = {}
        for s in plan.services:
            n = _slug(s.name)
            p[s.id] = f"app/application/{n}.py"
            for mp in s.data_models:
                p[mp.id] = f"app/domain/{_slug(mp.entity_name)}.py"
            for ev in s.published_events + s.consumed_events:
                p[ev.id] = f"app/events/{_slug(ev.name)}.py"
        for sp in plan.security:
            p[sp.policy_id] = "app/core/security.py"
        for effect in plan.effects:
            p[effect.id] = f"app/effects/{_slug(effect.name)}.py"
        p.update({
            "infra:docker": "Dockerfile",
            "infra:k8s": "k8s/deployment.yaml",
            "infra:ci": ".github/workflows/ci.yml",
            "infra:readme": "README.md",
            "infra:main": "app/main.py",
            "infra:repositories": "app/infrastructure/repositories.py",
            "infra:behavior": "app/core/behavior.py",
            "infra:authorization": "app/core/authorization.py",
            "infra:policies": "app/core/policies.py",
            "infra:docs": "docs/architecture.md",
            "infra:semantic_obligations": "docs/semantic-obligations.json",
            "infra:requirements": "requirements.txt",
            "infra:test": "tests/test_app.py",
        })
        if any(api.behavior is not None for api in plan.apis):
            p["infra:declared_apis"] = "app/api/declared.py"
        return p

    def compile(self, plan: CompilationPlan) -> GeneratedRepository:
        assert_plan_supported(plan, BackendCapabilities(backend_id=self.name, version=self.version, supported_features=self.supported_features))
        # The capability says this backend implements authorization enforcement.
        # This check says whether *this* plan's obligations have an enforcement
        # point here; an obligation without one fails closed instead of being
        # emitted as an unprotected route.
        assert_authorization_enforceable(plan)
        self._assert_no_route_collision(plan)
        f: dict[str, str] = {}
        for path in dict.fromkeys(self.element_paths(plan).values()):
            f[path] = self._emit(path, plan)
        return build_repository(f)

    def conformance(self, plan: CompilationPlan, repo: GeneratedRepository) -> ConformanceReport:
        return CHECKER.check(plan, self.element_paths(plan), repo)

    # -- plan-derived indexes ---------------------------------------------

    def _entities(self, plan: CompilationPlan) -> list[dict]:
        return plan_entities(plan)

    def _services(self, plan: CompilationPlan) -> list[dict]:
        return plan_services(plan)

    def _events(self, plan: CompilationPlan) -> list[dict]:
        return plan_events(plan)

    def _secured(self, plan: CompilationPlan) -> bool:
        return bool(plan.security)

    def _protected_service_for(self, plan: CompilationPlan, entity: dict) -> Service | None:
        """Return the service that owns the entity when it carries typed policies."""
        protected = protected_services(plan)
        for service in plan.services:
            if _slug(service.name) != entity["service_mod"]:
                continue
            policies = protected.get(service.id)
            if policies:
                return service
        return None

    def _has_protected_routes(self, plan: CompilationPlan) -> bool:
        """True when at least one emitted route carries an authorization obligation."""
        return any(
            self._protected_service_for(plan, entity) is not None
            for entity in self._entities(plan)
        )

    def _authorization_dependency(self, plan: CompilationPlan, entity: dict, verb: str) -> str:
        """Return the route dependency that authorizes this route before it runs."""
        service = self._protected_service_for(plan, entity)
        if service is None:
            return ""
        action = canonical_action(entity["entity"], verb)
        return (
            ", dependencies=[Depends(require_authorization("
            f"action=\"{action}\", resource=\"{entity['cls']}\", "
            f"policies=SERVICE_POLICIES[\"{_slug(service.name)}\"]))]"
        )

    def _authorization_rules_for(self, plan: CompilationPlan, entity: dict) -> list:
        """Return the policy rules that can match this entity's routes."""
        service = self._protected_service_for(plan, entity)
        if service is None:
            return []
        rules = []
        for policy in service_policies(service):
            rules.extend(policy.behavior.rules)
        return rules

    def _allowed_verbs(self, plan: CompilationPlan, entity: dict) -> set[str]:
        """Return the route verbs an allow rule covers for this entity."""
        allowed: set[str] = set()
        for rule in self._authorization_rules_for(plan, entity):
            if rule.effect != "allow" or rule.resource not in (entity["cls"], "*"):
                continue
            for verb in ROUTE_VERBS:
                action = canonical_action(entity["entity"], verb)
                if "*" in rule.actions or action in rule.actions:
                    allowed.add(verb)
        return allowed

    def _authorization_expectations(self, plan: CompilationPlan, entity: dict) -> dict[str, tuple[set[str], set[str]]]:
        """Return (allowed_roles, denied_roles) per route verb."""
        expectations: dict[str, tuple[set[str], set[str]]] = {}
        for verb in ROUTE_VERBS:
            action = canonical_action(entity["entity"], verb)
            allowed: set[str] = set()
            denied: set[str] = set()
            for rule in self._authorization_rules_for(plan, entity):
                if rule.resource not in (entity["cls"], "*"):
                    continue
                if not ("*" in rule.actions or action in rule.actions):
                    continue
                if rule.effect == "allow":
                    allowed.update(rule.roles)
                else:
                    denied.update(rule.roles)
            expectations[verb] = (allowed, denied)
        return expectations

    def _authorization_roles(self, plan: CompilationPlan, entity: dict) -> list[str]:
        """Return the roles granted for this entity's routes.

        Roles that a deny rule covers for every route are excluded, so the
        emitted test exercises the grant the policy actually makes.
        """
        expectations = self._authorization_expectations(plan, entity)
        granted: list[str] = []
        for allowed, denied in expectations.values():
            for role in sorted(allowed - denied):
                if role not in granted:
                    granted.append(role)
        return granted

    def _authorization_attributes(self, plan: CompilationPlan, entity: dict) -> dict[str, object]:
        """Return the subject attributes an allow rule requires for this entity."""
        attributes: dict[str, object] = {}
        for verb in ROUTE_VERBS:
            action = canonical_action(entity["entity"], verb)
            for rule in self._authorization_rules_for(plan, entity):
                if rule.effect != "allow" or rule.resource not in (entity["cls"], "*"):
                    continue
                if not ("*" in rule.actions or action in rule.actions):
                    continue
                for key, value in (rule.conditions or {}).items():
                    attributes.setdefault(str(key), value)
        return attributes

    def _authorization_tests(self, plan: CompilationPlan, entities: list[dict]) -> list[str]:
        """Emit the runtime and route level authorization tests."""
        protected = [e for e in entities if self._protected_service_for(plan, e) is not None]
        if not protected:
            return []
        target = protected[0]
        plural = target["plural"]
        expectations = self._authorization_expectations(plan, target)
        roles = self._authorization_roles(plan, target)
        granted = set(roles)
        readable = bool(granted & expectations["read"][0]) and not (granted & expectations["read"][1])
        attributes = self._authorization_attributes(plan, target)
        lines = [
            "",
            "",
            "def test_authorization_requires_a_signed_token():",
            f"    r = client.get('/api/{plural}', headers=HEADERS)",
            "    assert r.status_code == 401",
            "",
            "",
            "def test_authorization_rejects_a_tampered_token():",
            "    token = issue_token('someone', ['no_such_role'])",
            "    tampered = token[:-1] + ('a' if token[-1] != 'a' else 'b')",
            f"    r = client.get('/api/{plural}', headers={{**HEADERS, 'Authorization': f'Bearer {{tampered}}'}})",
            "    assert r.status_code == 401",
            "",
            "",
            "def test_authorization_denies_a_principal_without_a_grant():",
            "    token = issue_token('intruder', ['no_such_role'])",
            f"    r = client.get('/api/{plural}', headers={{**HEADERS, 'Authorization': f'Bearer {{token}}'}})",
            "    assert r.status_code == 403",
            "",
            "",
            "def test_authorization_rejects_an_expired_token():",
            "    token = issue_token('someone', ['no_such_role'], ttl_seconds=-1)",
            f"    r = client.get('/api/{plural}', headers={{**HEADERS, 'Authorization': f'Bearer {{token}}'}})",
            "    assert r.status_code == 401",
            "",
            "",
            "def test_authorization_ignores_spoofed_role_and_tenant_headers():",
            "    token = issue_token('intruder', ['no_such_role'])",
            f"    spoofed = {{**HEADERS, 'Authorization': f'Bearer {{token}}', 'X-Role': 'payroll_approver', 'X-Tenant': 'tenant-a'}}",
            f"    r = client.get('/api/{plural}', headers=spoofed)",
            "    assert r.status_code == 403",
            "",
            "",
            "def test_denied_request_does_not_mutate_state():",
        ]
        if readable:
            lines += [
                f"    allowed = client.get('/api/{plural}', headers=HEADERS_{plural.upper()}).json()",
                "    token = issue_token('intruder', ['no_such_role'])",
                f"    denied = client.delete('/api/{plural}/missing-item', headers={{**HEADERS, 'Authorization': f'Bearer {{token}}'}})",
                "    assert denied.status_code == 403",
                f"    after = client.get('/api/{plural}', headers=HEADERS_{plural.upper()}).json()",
                "    assert after == allowed",
            ]
        else:
            lines += [
                "    token = issue_token('intruder', ['no_such_role'])",
                f"    denied = client.post('/api/{plural}', json={{}}, headers={{**HEADERS, 'Authorization': f'Bearer {{token}}'}})",
                "    assert denied.status_code == 403",
            ]
        lines += [
            "",
            "",
        ]
        if attributes:
            lines += [
                "def test_authorization_denies_a_principal_without_the_required_attribute():",
                f"    token = issue_token('someone', {sorted(self._authorization_roles(plan, target))!r})",
                f"    r = client.get('/api/{plural}', headers={{**HEADERS, 'Authorization': f'Bearer {{token}}'}})",
                "    assert r.status_code == 403",
                "",
                "",
            ]
        lines += [
            "def test_authorization_runtime_denies_by_default():",
            "    from app.core.authorization import Principal, evaluate",
            "    principal = Principal(principal_id='p1', roles=frozenset({'reader'}))",
            "    allowed, reason = evaluate([], principal, 'employee.read', 'Employee')",
            "    assert allowed is False",
            "    assert 'default deny' in reason",
            "",
            "",
            "def test_authorization_runtime_explicit_deny_wins_over_allow():",
            "    from app.core.authorization import Principal, evaluate",
            "    policies = [{'policy_id': 'p', 'rules': [",
            "        {'rule_id': 'allow', 'effect': 'allow', 'roles': ['reader'], 'actions': ['employee.read'], 'resource': 'Employee', 'conditions': {}},",
            "        {'rule_id': 'deny', 'effect': 'deny', 'roles': ['reader'], 'actions': ['employee.read'], 'resource': 'Employee', 'conditions': {}},",
            "    ]}]",
            "    principal = Principal(principal_id='p1', roles=frozenset({'reader'}))",
            "    allowed, reason = evaluate(policies, principal, 'employee.read', 'Employee')",
            "    assert allowed is False",
            "    assert 'explicit deny' in reason",
            "",
            "",
            "def test_authorization_runtime_missing_attribute_never_grants():",
            "    from app.core.authorization import Principal, evaluate",
            "    policies = [{'policy_id': 'p', 'rules': [",
            "        {'rule_id': 'allow', 'effect': 'allow', 'roles': ['reader'], 'actions': ['employee.read'], 'resource': 'Employee', 'conditions': {'department': 'finance'}},",
            "    ]}]",
            "    principal = Principal(principal_id='p1', roles=frozenset({'reader'}))",
            "    allowed, _ = evaluate(policies, principal, 'employee.read', 'Employee')",
            "    assert allowed is False",
            "    granted = Principal(principal_id='p1', roles=frozenset({'reader'}), attributes={'department': 'finance'})",
            "    allowed, _ = evaluate(policies, granted, 'employee.read', 'Employee')",
            "    assert allowed is True",
            "",
            "",
            "def test_authorization_runtime_isolates_tenants():",
            "    from app.core.authorization import Principal, evaluate",
            "    principal = Principal(principal_id='p1', roles=frozenset({'reader'}), tenant_id='tenant-a')",
            "    allowed, reason = evaluate([], principal, 'employee.read', 'Employee', {'tenant_id': 'tenant-b'})",
            "    assert allowed is False",
            "    assert 'different tenant' in reason",
            "    anonymous = Principal(principal_id='p2', roles=frozenset({'reader'}))",
            "    allowed, reason = evaluate([], anonymous, 'employee.read', 'Employee', {'tenant_id': 'tenant-a'})",
            "    assert allowed is False",
            "    assert 'tenant identity is missing' in reason",
            "",
        ]
        return lines

    # -- declared API operation emission ----------------------------------

    _DECLARED_ANNOTATIONS = {
        "string": "str", "identifier": "str", "date": "str", "datetime": "str",
        "integer": "int", "decimal": "Decimal", "money": "Decimal", "boolean": "bool",
    }

    def _crud_route_keys(self, plan: CompilationPlan) -> set[tuple[str, str]]:
        keys = {("GET", "/health"), ("GET", "/api/services")}
        for entity in self._entities(plan):
            plural = entity["plural"]
            keys.add(("GET", f"/api/{plural}"))
            keys.add(("POST", f"/api/{plural}"))
            keys.add(("GET", f"/api/{plural}/{{}}"))
            keys.add(("PUT", f"/api/{plural}/{{}}"))
            keys.add(("DELETE", f"/api/{plural}/{{}}"))
        return keys

    def _assert_no_route_collision(self, plan: CompilationPlan) -> None:
        """A declared route must not shadow or duplicate an emitted CRUD route."""
        reserved = self._crud_route_keys(plan)
        for route in declared_routes(plan):
            key = (route.method, normalized_path(route.path))
            if key in reserved:
                raise UnsupportedSemanticsError(
                    "api_contracts: declared operation "
                    f"'{route.operation.id}' collides with the emitted "
                    f"{route.method} route {route.path!r}"
                )

    def _declared_rules(self, route: DeclaredRoute) -> list:
        rules = []
        for policy in route.policies:
            for rule in policy.behavior.rules:
                if rule.resource not in (route.resource, "*"):
                    continue
                if "*" in rule.actions or route.action in rule.actions:
                    rules.append(rule)
        return rules

    def _declared_roles(self, route: DeclaredRoute) -> list[str]:
        allowed: set[str] = set()
        denied: set[str] = set()
        for rule in self._declared_rules(route):
            if rule.effect == "allow":
                allowed.update(rule.roles)
            else:
                denied.update(rule.roles)
        return sorted(allowed - denied)

    def _declared_deny_roles(self, route: DeclaredRoute) -> list[str]:
        denied: set[str] = set()
        for rule in self._declared_rules(route):
            if rule.effect == "deny":
                denied.update(rule.roles)
        return sorted(denied)

    def _declared_attributes(self, route: DeclaredRoute) -> dict[str, object]:
        attributes: dict[str, object] = {}
        for rule in self._declared_rules(route):
            if rule.effect != "allow":
                continue
            for key, value in (rule.conditions or {}).items():
                attributes.setdefault(str(key), value)
        return attributes

    def _declared_names(self, routes: tuple[DeclaredRoute, ...]) -> list[str]:
        used: set[str] = set()
        names: list[str] = []
        for route in routes:
            base = _cls(_slug(route.operation.name))
            candidate = base
            index = 2
            while candidate in used:
                candidate = f"{base}{index}"
                index += 1
            used.add(candidate)
            names.append(candidate)
        return names

    def _declared_annotation(self, field, *, optional: bool = False) -> str:
        annotation = self._DECLARED_ANNOTATIONS[field.value_type.value]
        return f"{annotation} | None" if optional else annotation

    def _declared_constraint_args(self, field) -> list[str]:
        args: list[str] = []
        kind = field.value_type.value
        if field.precision is not None and kind in ("decimal", "money"):
            args.append(f"max_digits={field.precision}")
        if field.scale is not None and kind in ("decimal", "money"):
            args.append(f"decimal_places={field.scale}")
        for constraint in field.constraints:
            operator = constraint.operator.value
            if operator == "min":
                args.append(f"ge={constraint.value!r}")
            elif operator == "max":
                args.append(f"le={constraint.value!r}")
            elif operator == "min_length":
                args.append(f"min_length={int(constraint.value)}")
            elif operator == "max_length":
                args.append(f"max_length={int(constraint.value)}")
            elif operator == "pattern":
                args.append(f"pattern={str(constraint.value)!r}")
        return args

    def _declared_model(self, class_name: str, fields: tuple) -> list[str]:
        lines = [
            f"class {class_name}(BaseModel):",
            "    model_config = ConfigDict(extra='forbid')",
        ]
        for field in fields:
            optional = field.nullable or not field.required
            annotation = self._declared_annotation(field, optional=optional)
            default = "None" if optional else "..."
            args = [default, *self._declared_constraint_args(field)]
            lines.append(
                f"    {field.name}: {annotation} = Field({', '.join(args)})"
            )
        return lines

    def _declared_handler(self, route: DeclaredRoute, base: str, names: tuple[str, ...]) -> list[str]:
        handler = f"_declared_{_slug(route.operation.name)}"
        parameters: list[str] = []
        for field in route.path_fields:
            parameters.append(f"{field.name}: {self._declared_annotation(field)}")
        if route.body_fields:
            parameters.append(f"body: {base}Request")
        signature = ", ".join(parameters)
        module = route.resource_module
        names_literal = repr(names)
        if route.method == "GET":
            if route.path_fields:
                return [
                    f"def {handler}({signature}) -> dict:",
                    f"    return _get({module!r}, {route.path_fields[0].name!r}, "
                    f"{route.path_fields[0].name}, {names_literal})",
                ]
            return [
                f"def {handler}({signature}) -> list[dict]:",
                f"    return _list({module!r}, {names_literal})",
            ]
        if route.method == "POST":
            return [
                f"def {handler}({signature}) -> dict:",
                f"    return _create({module!r}, body.model_dump(mode='json'), "
                f"{names_literal})",
            ]
        if route.method in ("PUT", "PATCH"):
            return [
                f"def {handler}({signature}) -> dict:",
                f"    return _update({module!r}, {route.path_fields[0].name!r}, "
                f"{route.path_fields[0].name}, body.model_dump(mode='json'), "
                f"{names_literal}, merge={route.method == 'PATCH'})",
            ]
        return [
            f"def {handler}({signature}) -> dict:",
            f"    return _delete({module!r}, {route.path_fields[0].name!r}, "
            f"{route.path_fields[0].name}, {names_literal})",
        ]

    def _declared_apis(self, plan: CompilationPlan) -> str:
        routes = declared_routes(plan)
        bases = self._declared_names(routes)
        secured = any(route.policies for route in routes)
        lines = [
            '"""Declared API operations bound through explicit ISR EXPOSES relations.',
            "",
            "A route is emitted only because the plan names its owning service,",
            "resolves the resource it governs, and binds a typed policy that",
            "actually governs the declared action. Nothing is inferred from",
            "names, paths, or request fields.",
            '"""',
            "from __future__ import annotations",
            "",
            "from decimal import Decimal",
            "",
            "from fastapi import Depends, HTTPException",
            "from pydantic import BaseModel, ConfigDict, Field",
            "",
        ]
        if secured:
            lines += [
                "from app.core.authorization import require_authorization",
                "from app.core.policies import OPERATION_POLICIES",
            ]
        lines += [
            "from app.infrastructure.repositories import repository_for",
            "",
            "",
        ]
        for route, base in zip(routes, bases):
            if route.body_fields:
                lines += self._declared_model(f"{base}Request", route.body_fields)
                lines += ["", ""]
            if route.response_fields:
                lines += self._declared_model(f"{base}Response", route.response_fields)
                lines += ["", ""]
        lines += [
            "def _project(record: dict, names: tuple[str, ...]) -> dict:",
            "    return {name: record.get(name) for name in names} if names else dict(record)",
            "",
            "",
            "def _create(module: str, payload: dict, names: tuple[str, ...]) -> dict:",
            "    return _project(repository_for(module).create(payload), names)",
            "",
            "",
            "def _list(module: str, names: tuple[str, ...]) -> list[dict]:",
            "    return [_project(record, names) for record in repository_for(module).list()]",
            "",
            "",
            "def _find(module: str, field: str, value: object) -> dict:",
            "    record = repository_for(module).find(field, value)",
            "    if record is None:",
            "        raise HTTPException(status_code=404, detail=f'{module} not found')",
            "    return record",
            "",
            "",
            "def _get(module: str, field: str, value: object, names: tuple[str, ...]) -> dict:",
            "    return _project(_find(module, field, value), names)",
            "",
            "",
            "def _update(module: str, field: str, value: object, payload: dict,",
            "            names: tuple[str, ...], merge: bool) -> dict:",
            "    repository = repository_for(module)",
            "    existing = _find(module, field, value)",
            "    if merge:",
            "        payload = {**existing, **payload}",
            "    record = repository.update(existing['id'], payload)",
            "    if record is None:",
            "        raise HTTPException(status_code=404, detail=f'{module} not found')",
            "    return _project(record, names)",
            "",
            "",
            "def _delete(module: str, field: str, value: object, names: tuple[str, ...]) -> dict:",
            "    repository = repository_for(module)",
            "    existing = _find(module, field, value)",
            "    repository.delete(existing['id'])",
            "    return _project(existing, names)",
            "",
            "",
        ]
        for route, base in zip(routes, bases):
            names = tuple(field.name for field in route.response_fields)
            lines += self._declared_handler(route, base, names)
            lines += ["", ""]
        lines += [
            "def register_declared_routes(router) -> None:",
            '    """Register each declared route with its exact method, path, and guard."""',
        ]
        for route, base in zip(routes, bases):
            handler = f"_declared_{_slug(route.operation.name)}"
            name = f"declared_{_slug(route.operation.name)}"
            arguments = [
                f"        {route.path!r},",
                f"        {handler},",
                f"        methods=[{route.method!r}],",
                f"        name={name!r},",
            ]
            if route.method == "POST":
                arguments.append("        status_code=201,")
            if route.response_fields:
                model = f"{base}Response"
                if route.method == "GET" and not route.path_fields:
                    model = f"list[{model}]"
                arguments.append(f"        response_model={model},")
            if route.policies:
                arguments.append(
                    "        dependencies=[Depends(require_authorization("
                    f"action={route.action!r}, resource={route.resource!r}, "
                    f"policies=OPERATION_POLICIES[{route.operation.id!r}]))],"
                )
            lines.append("    router.add_api_route(")
            lines += arguments
            lines.append("    )")
        lines += [
            "",
            "",
            "def declared_route_metadata() -> list[dict]:",
            '    """The exact routes this module registered, for independent checks."""',
            "    return [",
        ]
        for route in routes:
            lines.append("        " + repr(route.as_dict()) + ",")
        lines += [
            "    ]",
        ]
        return "\n".join(lines) + "\n"

    def _declared_operation_tests(self, plan: CompilationPlan, routes: tuple[DeclaredRoute, ...]) -> list[str]:
        reads = [r for r in routes if r.method == "GET" and not r.path_fields]
        singles = [r for r in routes if r.method == "GET" and r.path_fields]
        creates = [r for r in routes if r.method == "POST"]
        deletes = [r for r in routes if r.method == "DELETE"]
        guarded = [r for r in routes if r.policies]

        lines = [
            "",
            "",
            "def test_declared_operation_emits_the_exact_route():",
            "    paths = client.get('/openapi.json').json()['paths']",
        ]
        for route in routes:
            lines.append(
                f"    assert {route.method.lower()!r} in paths[{route.path!r}]"
            )
        if creates:
            body = creates[0]
            payload = self._declared_payload(body)
            payload_json = json.dumps(payload, sort_keys=True)
            headers = "HEADERS_DECLARED" if guarded else "HEADERS"
            lines += [
                "",
                "",
                "def test_declared_operation_rejects_a_malformed_payload():",
                f"    r = client.post({body.path!r}, json={{'__unexpected__': 'invalid'}}, headers={headers})",
                "    assert r.status_code == 422",
            ]
        if not guarded:
            return lines

        positive = next((self._declared_roles(r) for r in guarded if self._declared_roles(r)), [])
        attributes = self._declared_attributes(guarded[0])
        lines += [
            "",
            "",
            f"TOKEN_DECLARED = issue_token('service-account', {positive!r}, attributes={attributes!r})",
            "HEADERS_DECLARED = {**HEADERS, 'Authorization': f'Bearer {TOKEN_DECLARED}'}",
            "",
            "",
            "def test_declared_operation_requires_a_signed_token():",
            f"    r = client.{guarded[0].method.lower()}({guarded[0].path!r}, headers=HEADERS)",
            "    assert r.status_code == 401",
            "",
            "",
            "def test_declared_operation_denies_a_principal_without_a_grant():",
            "    token = issue_token('intruder', ['no_such_role'])",
            f"    r = client.{guarded[0].method.lower()}({guarded[0].path!r}, headers={{**HEADERS, 'Authorization': f'Bearer {{token}}'}})",
            "    assert r.status_code == 403",
        ]
        if creates:
            body = creates[0]
            payload = self._declared_payload(body)
            payload_json = json.dumps(payload, sort_keys=True)
            if positive:
                lines += [
                    "",
                    "",
                    "def test_declared_operation_authorized_create_and_read():",
                    f"    created = client.post({body.path!r}, json={payload_json}, headers=HEADERS_DECLARED)",
                    "    assert created.status_code == 201",
                    "    item = created.json()",
                ]
                target = next(
                    (
                        single for single in singles
                        if single.service.id == body.service.id
                        and single.resource == body.resource
                        and single.path_fields[0].name in payload
                    ),
                    None,
                )
                if target is not None:
                    field = target.path_fields[0].name
                    lines += [
                        f"    {field} = item[{field!r}]",
                        f"    fetched = client.get(f'{target.path}', headers=HEADERS_DECLARED)",
                        "    assert fetched.status_code == 200",
                        f"    assert fetched.json()[{field!r}] == item[{field!r}]",
                    ]
                if reads:
                    read = reads[0]
                    lines += [
                        f"    listed = client.get({read.path!r}, headers=HEADERS_DECLARED)",
                        "    entries = listed.json()",
                        "    shared = [name for name in item if entries and name in entries[0]]",
                        "    assert shared",
                        "    assert item[shared[0]] in [entry[shared[0]] for entry in entries]",
                    ]
                if reads:
                    lines += [
                        "",
                        "",
                        "def test_declared_operation_denial_does_not_mutate_state():",
                        f"    before = client.get({reads[0].path!r}, headers=HEADERS_DECLARED).json()",
                        "    token = issue_token('intruder', ['no_such_role'])",
                        f"    denied = client.post({body.path!r}, json={payload_json}, headers={{**HEADERS, 'Authorization': f'Bearer {{token}}'}})",
                        "    assert denied.status_code == 403",
                        f"    after = client.get({reads[0].path!r}, headers=HEADERS_DECLARED).json()",
                        "    assert after == before",
                    ]
                deny = next(
                    (
                        deletion for deletion in deletes
                        if set(positive) & set(self._declared_deny_roles(deletion))
                    ),
                    None,
                )
                if deny is not None and target is not None:
                    field = target.path_fields[0].name
                    lines += [
                        "",
                        "",
                        "def test_declared_operation_explicit_deny_wins():",
                        f"    created = client.post({body.path!r}, json={payload_json}, headers=HEADERS_DECLARED)",
                        "    item = created.json()",
                        f"    {field} = item[{field!r}]",
                        f"    denied = client.delete(f'{deny.path}', headers=HEADERS_DECLARED)",
                        "    assert denied.status_code == 403",
                        f"    still_there = client.get(f'{target.path}', headers=HEADERS_DECLARED)",
                        "    assert still_there.status_code == 200",
                    ]
        return lines

    def _declared_payload(self, route: DeclaredRoute) -> dict:
        payload: dict = {}
        for field in route.body_fields:
            kind = field.value_type.value
            if kind == "integer":
                payload[field.name] = 1
            elif kind in ("decimal", "money"):
                payload[field.name] = "10.00"
            elif kind == "boolean":
                payload[field.name] = True
            elif kind == "date":
                payload[field.name] = "2026-01-01"
            elif kind == "datetime":
                payload[field.name] = "2026-01-01T00:00:00Z"
            elif kind == "identifier":
                payload[field.name] = f"{field.name}-alpha"
            else:
                payload[field.name] = "alpha"
        return payload

    # -- emitters ----------------------------------------------------------

    def _emit(self, path: str, plan: CompilationPlan) -> str:
        if path == "Dockerfile":
            return self._dockerfile()
        if path == "requirements.txt":
            return "fastapi\nuvicorn[standard]\npydantic\nhttpx\npytest\n"
        if path == "app/main.py":
            return self._main(plan)
        if path == "tests/test_app.py":
            return self._tests(plan)
        if path == "k8s/deployment.yaml":
            return self._k8s()
        if path == ".github/workflows/ci.yml":
            return self._ci()
        if path == "README.md":
            return self._readme(plan)
        if path == "docs/architecture.md":
            return self._docs(plan)
        if path == "docs/semantic-obligations.json":
            return json.dumps({
                "schema_version": "1",
                "effects": [item.model_dump(mode="json") for item in plan.effects],
                "effect_bindings": [item.model_dump(mode="json") for item in plan.effect_bindings],
                "consequences": [item.model_dump(mode="json") for item in plan.consequences],
            }, sort_keys=True, indent=2)
        if path == "app/infrastructure/repositories.py":
            return self._repositories()
        if path == "app/core/security.py":
            return self._security()
        if path == "app/core/authorization.py":
            return self._authorization()
        if path == "app/core/policies.py":
            return self._policies(plan)
        if path == "app/core/behavior.py":
            return self._behavior_runtime()
        if path == "app/api/declared.py":
            return self._declared_apis(plan)
        if path.startswith("app/domain/"):
            return self._domain(path, plan)
        if path.startswith("app/application/"):
            return self._service(path, plan)
        if path.startswith("app/events/"):
            return self._event(path, plan)
        if path.startswith("app/effects/"):
            return self._effect(path, plan)
        return f"# unrecognised element path: {path}\n"

    def _dockerfile(self) -> str:
        return (
            "FROM python:3.12-slim\n"
            "WORKDIR /app\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n"
            "EXPOSE 8000\n"
            "ENV GENERATED_API_KEY=generated-dev-key\n"
            'CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]\n'
        )

    def _repositories(self) -> str:
        return (
            '"""In-memory repository layer for the generated application."""\n'
            "from __future__ import annotations\n"
            "import threading\n\n\n"
            "class InMemoryRepository:\n"
            '    """Thread-safe key/value store with full CRUD semantics."""\n\n'
            "    def __init__(self) -> None:\n"
            "        self._items: dict[str, dict] = {}\n"
            "        self._lock = threading.Lock()\n"
            "        self._seq = 0\n\n"
            "    def create(self, payload: dict) -> dict:\n"
            "        with self._lock:\n"
            "            record = dict(payload)\n"
            '            if not record.get("id"):\n'
            "                self._seq += 1\n"
            '                record["id"] = str(self._seq)\n'
            '            self._items[record["id"]] = record\n'
            "            return record\n\n"
            "    def list(self) -> list[dict]:\n"
            "        with self._lock:\n"
            "            return [dict(v) for k, v in sorted(self._items.items())]\n\n"
            "    def find(self, field: str, value: object) -> dict | None:\n"
            "        with self._lock:\n"
            "            for record in self._items.values():\n"
            "                if record.get(field) == value:\n"
            "                    return dict(record)\n"
            "            return None\n\n"
            "    def get(self, item_id: str) -> dict | None:\n"
            "        with self._lock:\n"
            "            item = self._items.get(item_id)\n"
            "            return dict(item) if item is not None else None\n\n"
            "    def update(self, item_id: str, payload: dict) -> dict | None:\n"
            "        with self._lock:\n"
            "            if item_id not in self._items:\n"
            "                return None\n"
            "            record = dict(payload)\n"
            '            record["id"] = item_id\n'
            '            self._items[item_id] = record\n'
            "            return dict(record)\n\n"
            "    def delete(self, item_id: str) -> bool:\n"
            "        with self._lock:\n"
            "            return self._items.pop(item_id, None) is not None\n\n\n"
            "_REPOSITORIES: dict[str, InMemoryRepository] = {}\n"
            "_LOCK = threading.Lock()\n\n\n"
            "def repository_for(name: str) -> InMemoryRepository:\n"
            "    with _LOCK:\n"
            "        return _REPOSITORIES.setdefault(name, InMemoryRepository())\n"
        )

    def _security(self) -> str:
        return (
            '"""API-key authorization (fail-closed when unconfigured)."""\n'
            "from __future__ import annotations\n"
            "import os\n"
            "import secrets\n\n"
            "from fastapi import Header, HTTPException\n\n\n"
            "def require_api_key(x_api_key: str | None = Header(default=None)) -> None:\n"
            '    """Admit only requests presenting the configured API key.\n\n'
            "    An unset key is a deployment error: the dependency refuses every\n"
            "    request (503) instead of silently admitting all of them.\n"
            '    """\n'
            '    expected = os.environ.get("GENERATED_API_KEY", "")\n'
            "    if not expected:\n"
            "        raise HTTPException(\n"
            '            status_code=503, detail="GENERATED_API_KEY is not configured"\n'
            "        )\n"
            "    if not x_api_key or not secrets.compare_digest(x_api_key, expected):\n"
            '        raise HTTPException(status_code=401, detail="invalid API key")\n'
        )

    def _authorization(self) -> str:
        return '''"""Generated authorization runtime.

Identity is established by a token signed by a trusted provider. Roles and
tenant identity are read only from verified token claims; caller-supplied
headers are never trusted. Decisions are deny-by-default and an explicit deny
rule always wins over an allow rule.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from fastapi import HTTPException, Request


class AuthorizationError(Exception):
    """Raised when the authorization boundary cannot be established."""


@dataclass(frozen=True)
class Principal:
    """The authenticated identity, resolved from verified token claims."""

    principal_id: str
    roles: frozenset[str] = frozenset()
    tenant_id: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)


def _secret() -> bytes:
    raw = os.environ.get("GENERATED_AUTH_SECRET", "")
    if not raw:
        raise AuthorizationError("GENERATED_AUTH_SECRET is not configured")
    return raw.encode("utf-8")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def issue_token(principal_id: str, roles: Sequence[str] = (), tenant_id: str | None = None,
                attributes: Mapping[str, Any] | None = None, ttl_seconds: int = 3600) -> str:
    """Mint a signed token for the trusted provider that authenticated the caller."""
    claims = {
        "sub": principal_id,
        "roles": list(roles),
        "tenant_id": tenant_id,
        "attributes": dict(attributes or {}),
        "exp": int(time.time()) + int(ttl_seconds),
    }
    body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    signature = _b64(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{signature}"


def resolve_principal(authorization: str | None) -> Principal:
    """Establish identity from a signed token, or refuse the request."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="bearer token required")
    token = authorization.split(" ", 1)[1].strip()
    if token.count(".") != 1:
        raise HTTPException(status_code=401, detail="malformed token")
    body, signature = token.split(".", 1)
    expected = _b64(hmac.new(_secret(), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="invalid token signature")
    try:
        claims = json.loads(_unb64(body).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=401, detail="malformed token")
    if not isinstance(claims, dict):
        raise HTTPException(status_code=401, detail="malformed token")
    if int(claims.get("exp") or 0) < int(time.time()):
        raise HTTPException(status_code=401, detail="token expired")
    principal_id = str(claims.get("sub") or "")
    if not principal_id:
        raise HTTPException(status_code=401, detail="token carries no subject")
    return Principal(
        principal_id=principal_id,
        roles=frozenset(str(role) for role in claims.get("roles") or ()),
        tenant_id=claims.get("tenant_id"),
        attributes=dict(claims.get("attributes") or {}),
    )


def _matches(rule: Mapping[str, Any], principal: Principal, action: str,
             resource: str, attributes: Mapping[str, Any]) -> bool:
    if rule.get("resource") not in (resource, "*"):
        return False
    actions = rule.get("actions") or ()
    if "*" not in actions and action not in actions:
        return False
    if not set(rule.get("roles") or ()).intersection(principal.roles):
        return False
    subject_attributes = dict(principal.attributes or {})
    for key, expected in (rule.get("conditions") or {}).items():
        if key in attributes:
            actual = attributes[key]
        elif key in subject_attributes:
            actual = subject_attributes[key]
        else:
            # Absence of a required attribute never grants access.
            return False
        if actual != expected:
            return False
    return True


def evaluate(policies: Sequence[Mapping[str, Any]], principal: Principal, action: str,
             resource: str, resource_attributes: Mapping[str, Any] | None = None) -> tuple[bool, str]:
    """Decide an access request. Deny by default; an explicit deny always wins."""
    attributes = dict(resource_attributes or {})
    resource_tenant = attributes.get("tenant_id")
    if resource_tenant is not None:
        if not principal.tenant_id:
            return False, "tenant identity is missing"
        if principal.tenant_id != resource_tenant:
            return False, "resource belongs to a different tenant"
    for policy in policies:
        for rule in policy.get("rules", []):
            if rule.get("effect") != "deny":
                continue
            if _matches(rule, principal, action, resource, attributes):
                return False, f"explicit deny rule '{rule.get('rule_id')}' matched"
    for policy in policies:
        for rule in policy.get("rules", []):
            if rule.get("effect") != "allow":
                continue
            if _matches(rule, principal, action, resource, attributes):
                return True, f"allow rule '{rule.get('rule_id')}' matched"
    return False, "no matching allow rule; default deny"


def require_authorization(action: str, resource: str,
                          policies: Sequence[Mapping[str, Any]],
                          resource_attributes: Callable[[], Mapping[str, Any]] | None = None):
    """Build a route dependency that authorizes before the handler can mutate."""

    async def dependency(request: Request) -> Principal:
        principal = resolve_principal(request.headers.get("authorization"))
        attributes = resource_attributes() if resource_attributes is not None else {}
        allowed, reason = evaluate(policies, principal, action, resource, attributes)
        if not allowed:
            raise HTTPException(status_code=403, detail=reason)
        return principal

    return dependency
'''

    def _policies(self, plan: CompilationPlan) -> str:
        protected = protected_services(plan)
        service_payload: dict[str, list[dict]] = {}
        for service in plan.services:
            policies = protected.get(service.id)
            if not policies:
                continue
            service_payload[_slug(service.name)] = [policy_payload(policy) for policy in policies]
        operation_payload = {
            route.operation.id: [policy_payload(policy) for policy in route.policies]
            for route in declared_routes(plan)
        }
        return (
            '"""Declared authorization policies bound to the emitted routes."""\n'
            "from __future__ import annotations\n\n"
            "SERVICE_POLICIES: dict[str, list[dict]] = "
            + json.dumps(service_payload, indent=2, sort_keys=True)
            + "\n\n"
            "OPERATION_POLICIES: dict[str, list[dict]] = "
            + json.dumps(operation_payload, indent=2, sort_keys=True)
            + "\n"
        )


    def _behavior_runtime(self) -> str:
        return '''"""Generated deterministic behavioral runtime; no dynamic code execution."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


class BehaviorError(ValueError):
    pass


def _resolve(path: str, context: dict[str, Any]) -> Any:
    if path in context:
        return context[path]
    current: Any = context
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise BehaviorError(f"missing expression field: {path}")
        current = current[part]
    return current


def _number(value: Any) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        raise BehaviorError("arithmetic operand is not numeric")
    try:
        return Decimal(str(value))
    except Exception as exc:
        raise BehaviorError("arithmetic operand is not numeric") from exc


def _comparison_values(left: Any, right: Any) -> tuple[Any, Any]:
    if isinstance(left, bool) or isinstance(right, bool):
        return left, right
    try:
        return _number(left), _number(right)
    except BehaviorError:
        return left, right


def _boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise BehaviorError("boolean operand required")
    return value


def evaluate_expression(expression: dict[str, Any], context: dict[str, Any]) -> Any:
    op = expression.get("op")
    raw_args = expression.get("args", [])
    if op == "and":
        return _boolean(evaluate_expression(raw_args[0], context)) and _boolean(evaluate_expression(raw_args[1], context))
    if op == "or":
        return _boolean(evaluate_expression(raw_args[0], context)) or _boolean(evaluate_expression(raw_args[1], context))
    if op == "if_else":
        condition = _boolean(evaluate_expression(raw_args[0], context))
        return evaluate_expression(raw_args[1] if condition else raw_args[2], context)
    args = [evaluate_expression(arg, context) for arg in raw_args]
    if op == "literal":
        return expression["value"]
    if op == "field":
        return _resolve(expression["field_ref"], context)
    if op == "add":
        return _number(args[0]) + _number(args[1])
    if op == "subtract":
        return _number(args[0]) - _number(args[1])
    if op == "multiply":
        return _number(args[0]) * _number(args[1])
    if op == "divide":
        divisor = _number(args[1])
        if divisor == 0:
            raise BehaviorError("division by zero")
        return _number(args[0]) / divisor
    if op in ("equal", "not_equal", "less_than", "less_or_equal", "greater_than", "greater_or_equal"):
        left, right = _comparison_values(args[0], args[1])
        if op == "equal":
            return left == right
        if op == "not_equal":
            return left != right
        if op == "less_than":
            return left < right
        if op == "less_or_equal":
            return left <= right
        if op == "greater_than":
            return left > right
        return left >= right
    if op == "not":
        return not _boolean(args[0])
    raise BehaviorError(f"unsupported expression operator: {op!r}")


def validate_fields(fields: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise BehaviorError("record must be an object")
    declared = {field["name"]: field for field in fields}
    unknown = sorted(set(payload) - set(declared))
    if unknown:
        raise BehaviorError(f"unknown fields: {unknown}")
    for name, spec in declared.items():
        if name not in payload:
            if spec.get("required", True):
                raise BehaviorError(f"missing required field: {name}")
            continue
        value = payload[name]
        if value is None:
            if not spec.get("nullable", False):
                raise BehaviorError(f"field cannot be null: {name}")
            continue
        kind = spec["value_type"]
        valid = (
            isinstance(value, str) if kind in ("string", "identifier", "date", "datetime")
            else isinstance(value, bool) if kind == "boolean"
            else isinstance(value, int) and not isinstance(value, bool) if kind == "integer"
                else isinstance(value, (int, float, Decimal, str)) and not isinstance(value, bool) if kind in ("decimal", "money")
            else True
        )
        if not valid:
            raise BehaviorError(f"invalid type for field: {name}")
        if kind in ("decimal", "money"):
            number = _number(value)
            precision = spec.get("precision")
            scale = spec.get("scale")
            decimal_tuple = number.as_tuple()
            actual_scale = max(0, -decimal_tuple.exponent)
            if scale is not None and actual_scale > scale:
                raise BehaviorError(f"{name} exceeds declared decimal scale")
            if precision is not None and len(decimal_tuple.digits) > precision:
                raise BehaviorError(f"{name} exceeds declared decimal precision")
        for constraint in spec.get("constraints", []):
            op, bound = constraint["operator"], constraint.get("value")
            if op == "min" and value < bound:
                raise BehaviorError(f"{name} is below minimum")
            if op == "max" and value > bound:
                raise BehaviorError(f"{name} is above maximum")
            if op == "min_length" and len(value) < bound:
                raise BehaviorError(f"{name} is too short")
            if op == "max_length" and len(value) > bound:
                raise BehaviorError(f"{name} is too long")
            if op == "pattern" and re.fullmatch(str(bound), str(value)) is None:
                raise BehaviorError(f"{name} does not match pattern")
            if op == "one_of" and value not in bound:
                raise BehaviorError(f"{name} is not an allowed value")
    return dict(payload)


def authorize(policies: list[dict[str, Any]], role: str, action: str, resource: str,
              attributes: dict[str, Any] | None = None) -> bool:
    attributes = attributes or {}
    matched_allow = False
    for policy in policies:
        for rule in policy.get("rules", []):
            if role not in rule.get("roles", []) or action not in rule.get("actions", []):
                continue
            if rule.get("resource") not in (resource, "*"):
                continue
            conditions = rule.get("conditions", {})
            if any(attributes.get(key) != expected for key, expected in conditions.items()):
                continue
            if rule.get("effect") == "deny":
                return False
            if rule.get("effect") == "allow":
                matched_allow = True
    return matched_allow


def apply_effect(effect: dict[str, Any], idempotency_key: str | None, execute,
                 ledger: dict[str, Any]) -> Any:
    if not callable(execute):
        raise BehaviorError("effect executor is required")
    if effect.get("idempotency_key_required") and not idempotency_key:
        raise BehaviorError("idempotency key required")
    if effect.get("idempotent"):
        if not idempotency_key:
            raise BehaviorError("idempotent effect requires a key")
        key = f"{effect.get('effect_kind')}:{idempotency_key}"
        if key in ledger:
            return ledger[key]
        result = execute()
        ledger[key] = result
        return result
    if idempotency_key:
        raise BehaviorError("non-idempotent effect cannot claim keyed deduplication")
    return execute()

def apply_transition(transitions: list[dict[str, Any]], transition_id: str,
                    current_state: str, context: dict[str, Any]) -> str:
    transition = next((item for item in transitions if item.get("transition_id") == transition_id), None)
    if transition is None:
        raise BehaviorError("unknown transition")
    if transition.get("source_state") != current_state:
        raise BehaviorError("transition source state mismatch")
    guard = transition.get("guard")
    if guard is not None and not bool(evaluate_expression(guard, context)):
        raise BehaviorError("transition guard rejected")
    return transition["target_state"]
'''

    def _domain(self, path: str, plan: CompilationPlan) -> str:
        mod = path.rsplit("/", 1)[-1][: -len(".py")]
        entity = next((item for item in self._entities(plan) if item["mod"] == mod), None)
        model = next((item for item in plan.data_models if _slug(item.entity_name) == mod), None)
        cls = _cls(mod)
        if model is None or model.behavior is None:
            return (
                f'"""Domain model {cls} (generated)."""\n'
                "from pydantic import BaseModel\n\n\n"
                f"class {cls}(BaseModel):\n"
                "    id: str | None = None\n"
                "    name: str = ''\n"
            )
        type_names = {
            "string": "str", "identifier": "str", "date": "str", "datetime": "str",
            "integer": "int", "decimal": "Decimal", "money": "Decimal", "boolean": "bool",
        }
        lines = [
            f'"""Typed domain model {cls} (generated from ISR)."""',
            "from decimal import Decimal",
            "from pydantic import BaseModel, ConfigDict, Field",
            "",
            "",
            f"class {cls}(BaseModel):",
            "    model_config = ConfigDict(extra='forbid')",
        ]
        for field in model.behavior.fields:
            annotation = type_names[field.value_type.value]
            default = "..." if field.required else "None"
            if field.nullable and not field.required:
                annotation += " | None"
            args = [default]
            if field.precision is not None and field.value_type.value in ("decimal", "money"):
                args.append(f"max_digits={field.precision}")
            if field.scale is not None and field.value_type.value in ("decimal", "money"):
                args.append(f"decimal_places={field.scale}")
            for constraint in field.constraints:
                if constraint.operator.value == "min":
                    args.append(f"ge={constraint.value!r}")
                elif constraint.operator.value == "max":
                    args.append(f"le={constraint.value!r}")
                elif constraint.operator.value == "min_length":
                    args.append(f"min_length={int(constraint.value)}")
                elif constraint.operator.value == "max_length":
                    args.append(f"max_length={int(constraint.value)}")
                elif constraint.operator.value == "pattern":
                    args.append(f"pattern={str(constraint.value)!r}")
            lines.append(f"    {field.name}: {annotation} = Field({', '.join(args)})")
        return "\n".join(lines) + "\n"

    def _service(self, path: str, plan: CompilationPlan) -> str:
        mod = path.rsplit("/", 1)[-1][: -len(".py")]
        svc = next((s for s in self._services(plan) if s["mod"] == mod), None)
        cls = _cls(mod)
        name = svc["name"] if svc else mod
        owned = svc["owned"] if svc else []
        lines = [
            f'"""Application service for {name} (generated, wired to repositories)."""',
            "from __future__ import annotations",
            "",
            "from app.infrastructure.repositories import repository_for",
            "",
            "",
            f"class {cls}Service:",
            "    def __init__(self) -> None:",
            "        self._repos = {}",
            "",
            "    def catalog(self) -> dict:",
            f'        return {{"service": "{name}", "entities": {owned!r}}}',
            "",
        ]
        for mod_e in owned:
            lines += [
                f"    def create_{mod_e}(self, payload: dict) -> dict:",
                f'        return repository_for("{mod_e}").create(payload)',
                "",
                f"    def list_{mod_e}(self) -> list[dict]:",
                f'        return repository_for("{mod_e}").list()',
                "",
                f"    def get_{mod_e}(self, item_id: str) -> dict | None:",
                f'        return repository_for("{mod_e}").get(item_id)',
                "",
                f"    def update_{mod_e}(self, item_id: str, payload: dict) -> dict | None:",
                f'        return repository_for("{mod_e}").update(item_id, payload)',
                "",
                f"    def delete_{mod_e}(self, item_id: str) -> bool:",
                f'        return repository_for("{mod_e}").delete(item_id)',
                "",
            ]
        if svc:
            semantic_service = next((item for item in plan.services if _slug(item.name) == svc["mod"]), None)
            if semantic_service is not None and semantic_service.behavior is not None:
                rules = [item.model_dump(mode="json") for item in semantic_service.behavior.rules]
                transitions = [item.model_dump(mode="json") for item in semantic_service.behavior.transitions]
                lines[2:2] = ["import json", "from app.core.behavior import evaluate_expression, apply_transition"]
                lines += [
                    "",
                    "    def evaluate_rule(self, rule_id: str, context: dict) -> object:",
                    f"        rules = json.loads({json.dumps(rules)!r})",
                    "        rule = next((item for item in rules if item['rule_id'] == rule_id), None)",
                    "        if rule is None:",
                    "            raise ValueError('unknown business rule')",
                    "        return evaluate_expression(rule['expression'], context)",
                    "",
                    "    def apply_transition(self, transition_id: str, current_state: str, context: dict) -> str:",
                    f"        transitions = json.loads({json.dumps(transitions)!r})",
                    "        return apply_transition(transitions, transition_id, current_state, context)",
                ]
        if svc:
            semantic_service = next((item for item in plan.services if _slug(item.name) == svc["mod"]), None)
            if semantic_service is not None and semantic_service.effects:
                effect_specs = []
                for effect in semantic_service.effects:
                    if effect.behavior is None:
                        raise UnsupportedSemanticsError(
                            f"Service {semantic_service.id!r} has an effect without typed semantics"
                        )
                    effect_specs.append({"id": effect.id, **effect.behavior.model_dump(mode="json")})
                lines[2:2] = ["import json", "from app.core.behavior import apply_effect"]
                lines += [
                    "",
                    "    def execute_effect(self, effect_id: str, idempotency_key: str | None, execute, ledger: dict) -> object:",
                    f"        effects = json.loads({json.dumps(effect_specs)!r})",
                    "        effect = next((item for item in effects if item['id'] == effect_id), None)",
                    "        if effect is None:",
                    "            raise ValueError('unknown effect')",
                    "        return apply_effect(effect, idempotency_key, execute, ledger)",
                    "",
                ]
        return "\n".join(lines).rstrip("\n") + "\n"

    def _event(self, path: str, plan: CompilationPlan) -> str:
        mod = path.rsplit("/", 1)[-1][: -len(".py")]
        ev = next((e for e in self._events(plan) if e["mod"] == mod), None)
        name = ev["name"] if ev else mod
        return (
            f'"""Event handler for {name} (generated, validated)."""\n'
            "from __future__ import annotations\n"
            "\n\n"
            f"def handle_{mod}(payload: dict) -> dict:\n"
            f'    """Validate and wrap an incoming {name} event."""\n'
            "    if not isinstance(payload, dict):\n"
            '        raise TypeError("event payload must be a mapping")\n'
            f'    return {{"type": "{name}", "payload": payload}}\n'
        )

    def _main(self, plan: CompilationPlan) -> str:
        entities = self._entities(plan)
        services = self._services(plan)
        secured = self._secured(plan)
        declared = declared_routes(plan)
        title = plan.isr_id or "generated-service"

        imports = ["from fastapi import APIRouter, FastAPI, HTTPException"]
        if secured:
            imports[0] = "from fastapi import APIRouter, Depends, FastAPI, HTTPException"
            imports.append("from app.core.security import require_api_key")
        if self._has_protected_routes(plan):
            imports[0] = "from fastapi import APIRouter, Depends, FastAPI, HTTPException"
            imports.append("from app.core.authorization import require_authorization")
            imports.append("from app.core.policies import SERVICE_POLICIES")
        for e in entities:
            imports.append(f"from app.domain.{e['mod']} import {e['cls']}")
        for s in services:
            imports.append(
                f"from app.application.{s['mod']} import {s['cls']}Service"
            )
        if declared:
            imports.append("from app.api.declared import register_declared_routes")

        lines = [
            '"""Generated FastAPI application — wired CRUD, health, OpenAPI."""',
            "from __future__ import annotations",
            "",
            *imports,
            "",
            "",
            f'app = FastAPI(title="{title}")',
            "",
            "",
            "@app.get('/health')",
            "def health():",
            "    return {'status': 'ok'}",
            "",
            "",
        ]
        if secured:
            lines += [
                'router = APIRouter(dependencies=[Depends(require_api_key)])',
            ]
        else:
            lines += ["router = APIRouter()"]
        lines.append("")

        # service singletons
        for s in services:
            lines += [
                f"_{s['mod']}_service = {s['cls']}Service()",
            ]
        if services:
            svc_vars = ", ".join(f"_{s['mod']}_service" for s in services)
            lines += ["", f"SERVICES = [{svc_vars}]"]
        else:
            lines += ["", "SERVICES: list = []"]
        lines.append("")

        # business routes
        for e in entities:
            svc_var = f"_{e['service_mod']}_service"
            lines += [
                f"@router.get('/api/{e['plural']}'{self._authorization_dependency(plan, e, 'read')})",
                f"def list_{e['plural']}() -> list[dict]:",
                f"    return {svc_var}.list_{e['mod']}()",
                "",
                f"@router.post('/api/{e['plural']}', status_code=201{self._authorization_dependency(plan, e, 'create')})",
                f"def create_{e['mod']}(payload: {e['cls']}) -> dict:",
                f"    return {svc_var}.create_{e['mod']}(payload.model_dump())",
                "",
                f"@router.get('/api/{e['plural']}/{{item_id}}'{self._authorization_dependency(plan, e, 'read')})",
                f"def get_{e['mod']}(item_id: str) -> dict:",
                f"    item = {svc_var}.get_{e['mod']}(item_id)",
                "    if item is None:",
                f'        raise HTTPException(status_code=404, detail="{e["plural"]} not found")',
                "    return item",
                "",
                f"@router.put('/api/{e['plural']}/{{item_id}}'{self._authorization_dependency(plan, e, 'update')})",
                f"def update_{e['mod']}(item_id: str, payload: {e['cls']}) -> dict:",
                f"    item = {svc_var}.update_{e['mod']}(item_id, payload.model_dump())",
                "    if item is None:",
                f'        raise HTTPException(status_code=404, detail="{e["plural"]} not found")',
                "    return item",
                "",
                f"@router.delete('/api/{e['plural']}/{{item_id}}'{self._authorization_dependency(plan, e, 'delete')})",
                f"def delete_{e['mod']}(item_id: str) -> dict:",
                f"    if not {svc_var}.delete_{e['mod']}(item_id):",
                f'        raise HTTPException(status_code=404, detail="{e["plural"]} not found")',
                f'    return {{"deleted": item_id}}',
                "",
            ]
        lines += [
            "@router.get('/api/services')",
            "def list_services() -> list[dict]:",
            "    return [svc.catalog() for svc in SERVICES]",
            "",
            "",
        ]
        if declared:
            lines += [
                "register_declared_routes(router)",
                "",
                "",
            ]
        lines += [
            "app.include_router(router)",
            "",
        ]
        return "\n".join(lines)

    def _tests(self, plan: CompilationPlan) -> str:
        entities = self._entities(plan)
        events = self._events(plan)
        secured = self._secured(plan)
        declared = declared_routes(plan)
        authorized = self._has_protected_routes(plan) or any(
            route.policies for route in declared
        )
        lines = [
            "import os",
            "",
            'os.environ.setdefault("GENERATED_API_KEY", "generated-dev-key")',
            'API_KEY = os.environ["GENERATED_API_KEY"]',
        ]
        if authorized:
            lines += [
                'os.environ.setdefault("GENERATED_AUTH_SECRET", "generated-dev-secret")',
            ]
        lines += [
            "",
            "from fastapi.testclient import TestClient",
            "",
            "from app.main import app",
        ]
        if authorized:
            lines += [
                "from app.core.authorization import issue_token",
            ]
        lines += [
            "",
            "",
            "client = TestClient(app)",
            f"HEADERS = {{'X-API-Key': API_KEY}} if {secured} else {{}}",
            "",
            "",
            "def test_health():",
            "    r = client.get('/health')",
            "    assert r.status_code == 200",
            "    assert r.json() == {'status': 'ok'}",
            "",
            "",
            "def test_openapi_exposes_business_routes():",
            "    spec = client.get('/openapi.json').json()",
            "    paths = spec.get('paths', {})",
            "    business = [p for p in paths if not p.startswith('/health')]",
            "    assert business, 'openapi declares no business endpoints'",
            "",
            "",
            "def test_services_catalog():",
            "    r = client.get('/api/services', headers=HEADERS)",
            "    assert r.status_code == 200",
            "    assert isinstance(r.json(), list)",
            "",
        ]
        lines += [
            "import pytest",
            "from decimal import Decimal",
            "from app.core.behavior import BehaviorError, evaluate_expression, validate_fields, authorize, apply_effect, apply_transition",
            "",
            "",
            "def test_behavior_expression_arithmetic():",
            "    expression = {'op': 'multiply', 'args': [{'op': 'field', 'field_ref': 'hours'}, {'op': 'field', 'field_ref': 'rate'}]}",
            "    assert evaluate_expression(expression, {'hours': 7, 'rate': '12.50'}) == Decimal('87.50')",
            "    with pytest.raises(BehaviorError, match='division by zero'):",
            "        evaluate_expression({'op': 'divide', 'args': [{'op': 'literal', 'value': 1}, {'op': 'literal', 'value': 0}]}, {})",
            "",
            "",
            "def test_behavior_comparisons_use_decimal_semantics_for_money_fields():",
            "    greater = {'op': 'greater_than', 'args': [{'op': 'field', 'field_ref': 'Employee.base_salary'}, {'op': 'literal', 'value': 0}]}",
            "    equal = {'op': 'equal', 'args': [{'op': 'field', 'field_ref': 'amount'}, {'op': 'literal', 'value': 100}]}",
            "    assert evaluate_expression(greater, {'Employee.base_salary': '100.00'}) is True",
            "    assert evaluate_expression(equal, {'amount': '100.00'}) is True",
            "    lexical = {'op': 'less_than', 'args': [{'op': 'field', 'field_ref': 'name'}, {'op': 'literal', 'value': 'beta'}]}",
            "    assert evaluate_expression(lexical, {'name': 'alpha'}) is True",
            "",
            "",
            "def test_behavior_boolean_and_string_comparison_semantics():",
            "    assert evaluate_expression({'op': 'less_than', 'args': [{'op': 'literal', 'value': 'A'}, {'op': 'literal', 'value': 'B'}]}, {}) is True",
            "    with pytest.raises(BehaviorError, match='boolean operand required'):",
            "        evaluate_expression({'op': 'not', 'args': [{'op': 'literal', 'value': 1}]}, {})",
            "",
            "",
            "def test_behavior_field_validation_fails_closed():",
            "    fields = [{'name': 'amount', 'value_type': 'money', 'required': True, 'nullable': False, 'constraints': [{'operator': 'min', 'value': 0}]}]",
            "    assert validate_fields(fields, {'amount': 10}) == {'amount': 10}",
            "    with pytest.raises(BehaviorError, match='below minimum'):",
            "        validate_fields(fields, {'amount': -1})",
            "    with pytest.raises(BehaviorError, match='unknown fields'):",
            "        validate_fields(fields, {'amount': 10, 'unexpected': 1})",
            "",
            "",
            "def test_behavior_money_precision_and_scale_are_enforced():",
            "    fields = [{'name': 'amount', 'value_type': 'money', 'required': True, 'nullable': False, 'precision': 5, 'scale': 2}]",
            "    assert validate_fields(fields, {'amount': '999.99'}) == {'amount': '999.99'}",
            "    with pytest.raises(BehaviorError, match='decimal precision'):",
            "        validate_fields(fields, {'amount': '1000.00'})",
            "    with pytest.raises(BehaviorError, match='decimal scale'):",
            "        validate_fields(fields, {'amount': '1.234'})",
            "",
            "",
            "def test_behavior_authorization_defaults_to_deny_and_deny_wins():",
            "    policies = [{'rules': [{'rule_id': 'allow', 'effect': 'allow', 'roles': ['payroll_approver'], 'actions': ['payroll.approve'], 'resource': 'PayrollRun', 'conditions': {}}, {'rule_id': 'deny', 'effect': 'deny', 'roles': ['payroll_approver'], 'actions': ['payroll.approve'], 'resource': 'PayrollRun', 'conditions': {}}]}]",
            "    assert authorize([], 'payroll_approver', 'payroll.approve', 'PayrollRun') is False",
            "    assert authorize(policies, 'payroll_approver', 'payroll.approve', 'PayrollRun') is False",
            "",
            "",
            "def test_behavior_effect_idempotency_returns_prior_result():",
            "    effect = {'effect_kind': 'bank_transfer', 'idempotent': True, 'idempotency_key_required': True}",
            "    ledger = {}",
            "    calls = []",
            "    first = apply_effect(effect, 'run-1', lambda: calls.append('first') or {'status': 'queued'}, ledger)",
            "    retry = apply_effect(effect, 'run-1', lambda: calls.append('retry') or {'status': 'duplicate'}, ledger)",
            "    assert first == retry == {'status': 'queued'}",
            "    assert calls == ['first']",
            "    with pytest.raises(BehaviorError, match='idempotency key required'):",
            "        apply_effect(effect, None, lambda: {}, ledger)",
            "",
            "",
            "def test_behavior_state_transition_checks_guard_and_source():",
            "    transitions = [{'transition_id': 'submit', 'source_state': 'draft', 'target_state': 'submitted', 'guard': {'op': 'greater_than', 'args': [{'op': 'field', 'field_ref': 'gross'}, {'op': 'literal', 'value': 0}]}}]",
            "    assert apply_transition(transitions, 'submit', 'draft', {'gross': 100}) == 'submitted'",
            "    with pytest.raises(BehaviorError, match='guard rejected'):",
            "        apply_transition(transitions, 'submit', 'draft', {'gross': 0})",
            "    with pytest.raises(BehaviorError, match='source state mismatch'):",
            "        apply_transition(transitions, 'submit', 'submitted', {'gross': 100})",
            "",
            "",
        ]
        for service in plan.services:
            if service.behavior is None:
                continue
            service_module = _slug(service.name)
            service_class = _cls(service_module) + "Service"
            for rule in service.behavior.rules:
                context = sample_context(rule.expression, plan)
                expected = reference_evaluate(rule.expression, context)
                lines += [
                    f"def test_generated_rule_{_slug(rule.rule_id)}():",
                    f"    from app.application.{service_module} import {service_class}",
                    f"    context = {context!r}",
                    f"    actual = {service_class}().evaluate_rule({rule.rule_id!r}, context)",
                    f"    assert actual == {expected!r}",
                    "",
                ]
            for transition in service.behavior.transitions:
                if transition.guard is None:
                    continue
                context = sample_context(transition.guard, plan)
                accepted = bool(reference_evaluate(transition.guard, context))
                lines += [
                    f"def test_generated_transition_{_slug(transition.transition_id)}():",
                    f"    from app.application.{service_module} import {service_class}",
                    f"    context = {context!r}",
                ]
                if accepted:
                    lines.append(
                        f"    assert {service_class}().apply_transition({transition.transition_id!r}, {transition.source_state!r}, context) == {transition.target_state!r}"
                    )
                else:
                    lines += [
                        "    with pytest.raises(ValueError):",
                        f"        {service_class}().apply_transition({transition.transition_id!r}, {transition.source_state!r}, context)",
                    ]
                lines.append("")
            for effect in service.effects:
                if effect.behavior is None:
                    continue
                if effect.behavior.idempotent:
                    lines += [
                        f"def test_generated_effect_{_slug(effect.id)}_is_idempotent():",
                        f"    from app.application.{service_module} import {service_class}",
                        "    ledger = {}",
                        "    executions = []",
                        "    service = " + service_class + "()",
                        f"    first = service.execute_effect({effect.id!r}, 'key-1', lambda: executions.append('first') or {{'transfer_id': 'tx-1'}}, ledger)",
                        f"    replay = service.execute_effect({effect.id!r}, 'key-1', lambda: executions.append('replay') or {{'transfer_id': 'tx-2'}}, ledger)",
                        "    assert first == {'transfer_id': 'tx-1'}",
                        "    assert replay == first",
                        "    assert executions == ['first']",
                        "    with pytest.raises(ValueError, match='idempotency key required'):",
                        f"        service.execute_effect({effect.id!r}, None, lambda: {{'transfer_id': 'missing-key'}}, {{}})",
                        "",
                    ]
                else:
                    lines += [
                        f"def test_generated_effect_{_slug(effect.id)}_executes_without_deduplication_key():",
                        f"    from app.application.{service_module} import {service_class}",
                        "    service = " + service_class + "()",
                        f"    assert service.execute_effect({effect.id!r}, None, lambda: {{'ok': True}}, {{}}) == {{'ok': True}}",
                        "",
                    ]
        for e in entities:
            model = next((item for item in plan.data_models if _slug(item.entity_name) == e["mod"]), None)
            if model is not None and model.behavior is not None:
                payload = {}
                updated_payload = {}
                for field in model.behavior.fields:
                    kind = field.value_type.value
                    if kind == "integer":
                        value, updated = 1, 2
                    elif kind in ("decimal", "money"):
                        value, updated = "10.00", "20.00"
                    elif kind == "boolean":
                        value, updated = True, False
                    elif kind == "date":
                        value, updated = "2026-01-01", "2026-01-02"
                    elif kind == "datetime":
                        value, updated = "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
                    elif kind == "identifier":
                        value, updated = f"{field.name}-alpha", f"{field.name}-beta"
                    else:
                        value, updated = "alpha", "beta"
                    payload[field.name] = value
                    updated_payload[field.name] = updated
                tested_field = model.behavior.fields[0].name
                expected_created = repr(payload[tested_field])
                expected_updated = repr(updated_payload[tested_field])
                payload_json = json.dumps(payload, sort_keys=True)
                updated_json = json.dumps(updated_payload, sort_keys=True)
            else:
                tested_field = "name"
                expected_created = repr("alpha")
                expected_updated = repr("beta")
                payload_json = json.dumps({"name": "alpha"})
                updated_json = json.dumps({"name": "beta"})
            protected = self._protected_service_for(plan, e) is not None
            allowed = self._allowed_verbs(plan, e)
            if protected:
                header_var = f"HEADERS_{e['plural'].upper()}"
                roles = self._authorization_roles(plan, e)
                attributes = self._authorization_attributes(plan, e)
                expectations = self._authorization_expectations(plan, e)
                granted = set(roles)
                expected_verb = {
                    verb: bool(granted & allow_roles) and not (granted & deny_roles)
                    for verb, (allow_roles, deny_roles) in expectations.items()
                }
                lines += [
                    f"TOKEN_{e['plural'].upper()} = issue_token('service-account', {roles!r}, attributes={attributes!r})",
                    f"{header_var} = {{**HEADERS, 'Authorization': f'Bearer {{TOKEN_{e['plural'].upper()}}}'}}",
                    "",
                ]
            else:
                header_var = "HEADERS"
                expected_verb = {verb: True for verb in ROUTE_VERBS}
            create_allowed = expected_verb["create"]
            read_allowed = expected_verb["read"]
            update_allowed = expected_verb["update"]
            delete_allowed = expected_verb["delete"]
            body = [f"def test_crud_{e['plural']}():"]
            if create_allowed:
                body += [
                    f"    created = client.post('/api/{e['plural']}', json={payload_json}, headers={header_var})",
                    "    assert created.status_code == 201",
                    "    item_id = created.json()['id']",
                    f"    assert created.json()[{tested_field!r}] == {expected_created}",
                ]
            else:
                body += [
                    f"    denied_create = client.post('/api/{e['plural']}', json={payload_json}, headers={header_var})",
                    "    assert denied_create.status_code == 403",
                ]
            if read_allowed:
                body += [f"    listed = client.get('/api/{e['plural']}', headers={header_var})"]
                if create_allowed:
                    body += ["    assert item_id in [i['id'] for i in listed.json()]"]
                else:
                    body += ["    assert isinstance(listed.json(), list)"]
                if create_allowed:
                    body += [
                        f"    fetched = client.get(f'/api/{e['plural']}/{{item_id}}', headers={header_var})",
                        "    assert fetched.status_code == 200",
                        f"    assert fetched.json()[{tested_field!r}] == {expected_created}",
                    ]
            else:
                body += [
                    f"    denied_read = client.get('/api/{e['plural']}', headers={header_var})",
                    "    assert denied_read.status_code == 403",
                ]
            if create_allowed:
                if update_allowed:
                    body += [
                        f"    updated = client.put(f'/api/{e['plural']}/{{item_id}}', json={updated_json}, headers={header_var})",
                        "    assert updated.status_code == 200",
                        f"    assert updated.json()[{tested_field!r}] == {expected_updated}",
                    ]
                else:
                    body += [
                        f"    denied_update = client.put(f'/api/{e['plural']}/{{item_id}}', json={updated_json}, headers={header_var})",
                        "    assert denied_update.status_code == 403",
                    ]
                if delete_allowed:
                    body += [
                        f"    deleted = client.delete(f'/api/{e['plural']}/{{item_id}}', headers={header_var})",
                        "    assert deleted.status_code == 200",
                    ]
                    if read_allowed:
                        body += [
                            f"    gone = client.get(f'/api/{e['plural']}/{{item_id}}', headers={header_var})",
                            "    assert gone.status_code == 404",
                        ]
                else:
                    body += [
                        f"    denied_delete = client.delete(f'/api/{e['plural']}/{{item_id}}', headers={header_var})",
                        "    assert denied_delete.status_code == 403",
                    ]
            body += [""]
            lines += body
        lines += self._authorization_tests(plan, entities)
        if declared:
            lines += self._declared_operation_tests(plan, declared)
        if secured and entities:
            first = entities[0]["plural"]
            lines += [
                "def test_business_routes_require_api_key():",
                f"    r = client.get('/api/{first}')",
                "    assert r.status_code == 401",
                "",
            ]
        for ev in events:
            lines += [
                f"def test_event_handler_{ev['mod']}():",
                f"    from app.events.{ev['mod']} import handle_{ev['mod']}",
                f"    out = handle_{ev['mod']}({{'k': 1}})",
                f"    assert out['type'] == '{ev['name']}'",
                f"    assert out['payload'] == {{'k': 1}}",
                f"    try:",
                f"        handle_{ev['mod']}(['not', 'a', 'mapping'])",
                f"        raise AssertionError('invalid payload accepted')",
                "    except TypeError:",
                "        pass",
                "",
            ]
        for effect in plan.effects:
            if effect.behavior is None:
                continue
            effect_mod = _slug(effect.name)
            if effect.behavior.idempotent:
                lines += [
                    f"def test_effect_{effect_mod}_deduplicates_retries():",
                    f"    from app.effects.{effect_mod} import apply",
                    "    ledger = {}",
                    "    calls = []",
                    "    first = apply(lambda: calls.append('first') or {'status': 'queued'}, 'same-key', ledger)",
                    "    retry = apply(lambda: calls.append('retry') or {'status': 'duplicate'}, 'same-key', ledger)",
                    "    assert first == retry",
                    "    assert calls == ['first']",
                    "",
                ]
                if effect.behavior.idempotency_key_required:
                    lines += [
                        f"def test_effect_{effect_mod}_requires_idempotency_key():",
                        f"    from app.effects.{effect_mod} import apply",
                        "    with pytest.raises(BehaviorError, match='idempotency key required'):",
                        "        apply(lambda: {}, None, {})",
                        "",
                    ]
            else:
                lines += [
                    f"def test_effect_{effect_mod}_returns_payload():",
                    f"    from app.effects.{effect_mod} import apply",
                    "    assert apply(lambda: {'status': 'queued'}, None, {}) == {'status': 'queued'}",
                    "",
                ]

        return "\n".join(lines)

    def _effect(self, path: str, plan: CompilationPlan) -> str:
        mod = path.rsplit("/", 1)[-1][: -len(".py")]
        effect = next((item for item in plan.effects if _slug(item.name) == mod), None)
        if effect is None or effect.behavior is None:
            return '"""Effect contract unavailable; this module is not executable."""\n'
        spec = effect.behavior.model_dump(mode="json")
        spec_json = json.dumps(spec)
        return (
            '"""Generated effect adapter with explicit idempotency semantics."""\n'
            "import json\n"
            "from app.core.behavior import apply_effect\n\n"
            f"EFFECT = json.loads({spec_json!r})\n\n"
            "def apply(executor, idempotency_key, ledger):\n"
            "    return apply_effect(EFFECT, idempotency_key, executor, ledger)\n"
        )

    def _k8s(self) -> str:
        return (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: generated-app\n"
            "  labels:\n"
            "    app: generated-app\n"
            "spec:\n"
            "  replicas: 1\n"
            "  selector:\n"
            "    matchLabels:\n"
            "      app: generated-app\n"
            "  template:\n"
            "    metadata:\n"
            "      labels:\n"
            "        app: generated-app\n"
            "    spec:\n"
            "      containers:\n"
            "        - name: app\n"
            "          image: generated-app:latest\n"
            "          ports:\n"
            "            - containerPort: 8000\n"
            "          env:\n"
            "            - name: GENERATED_API_KEY\n"
            "              value: generated-dev-key\n"
            "          readinessProbe:\n"
            "            httpGet:\n"
            "              path: /health\n"
            "              port: 8000\n"
            "            initialDelaySeconds: 3\n"
            "            periodSeconds: 5\n"
            "---\n"
            "apiVersion: v1\n"
            "kind: Service\n"
            "metadata:\n"
            "  name: generated-app\n"
            "spec:\n"
            "  selector:\n"
            "    app: generated-app\n"
            "  ports:\n"
            "    - port: 80\n"
            "      targetPort: 8000\n"
        )

    def _ci(self) -> str:
        return (
            "name: ci\n"
            "on: [push, pull_request]\n"
            "jobs:\n"
            "  test:\n"
            "    runs-on: ubuntu-latest\n"
            "    steps:\n"
            "      - uses: actions/checkout@v4\n"
            "      - uses: actions/setup-python@v5\n"
            "        with:\n"
            '          python-version: "3.12"\n'
            "      - run: pip install -r requirements.txt\n"
            "      - run: python -m pytest -q\n"
        )

    def _readme(self, plan: CompilationPlan) -> str:
        entities = self._entities(plan)
        services = self._services(plan)
        events = self._events(plan)
        secured = self._secured(plan)
        lines = [f"# {plan.isr_id or 'generated-service'}", ""]
        lines.append("Generated Python/FastAPI service produced from the ISR compilation plan.")
        lines.append("")
        lines.append("## Services")
        for s in services:
            owned = ", ".join(s["owned"]) or "(no data models)"
            lines.append(f"- `{s['name']}` — entities: {owned}")
        if not services:
            lines.append("- (plan contains no services)")
        lines.append("")
        lines.append("## HTTP surface")
        lines.append("- `GET /health` — liveness")
        lines.append("- `GET /api/services` — service catalog")
        for e in entities:
            lines.append(
                f"- `/api/{e['plural']}` — CRUD for `{e['entity']}` "
                "(GET, POST, GET/PUT/DELETE by id)"
            )
        if not entities:
            lines.append("- (plan contains no data models)")
        lines.append("")
        if events:
            lines.append("## Events")
            for ev in events:
                lines.append(f"- `{ev['name']}` — handler `app.events.{ev['mod']}`")
            lines.append("")
        lines.append("## Run")
        lines.append("```bash")
        lines.append("pip install -r requirements.txt")
        lines.append("uvicorn app.main:app --host 0.0.0.0 --port 8000")
        lines.append("```")
        if secured:
            lines.append("")
            lines.append("Authorization: set `GENERATED_API_KEY` and send `X-API-Key` on every")
            lines.append("business request. Missing configuration refuses requests (fail-closed).")
        lines.append("")
        lines.append("## Test")
        lines.append("```bash")
        lines.append("python -m pytest -q")
        lines.append("```")
        lines.append("")
        return "\n".join(lines)

    def _docs(self, plan: CompilationPlan) -> str:
        entities = self._entities(plan)
        services = self._services(plan)
        events = self._events(plan)
        lines = [f"# Architecture — {plan.isr_id or 'generated-service'}", ""]
        lines.append("Derived deterministically from the ISR compilation plan.")
        lines.append("")
        lines.append("## Layering")
        lines.append("- `app/main.py` — FastAPI app, health, routers")
        lines.append("- `app/application/` — application services (use-case orchestration)")
        lines.append("- `app/domain/` — Pydantic domain models")
        lines.append("- `app/infrastructure/` — in-memory repository (thread-safe CRUD)")
        lines.append("- `app/events/` — validated event handlers")
        if self._secured(plan):
            lines.append("- `app/core/security.py` — API-key authorization (fail-closed)")
        lines.append("")
        lines.append("## Services and persisted entities")
        for s in services:
            lines.append(f"- `{s['name']}` persists {s['owned'] or 'nothing'}")
        if not services:
            lines.append("- (plan contains no services)")
        lines.append("")
        lines.append("## Request flow")
        lines.append("1. Router resolves the endpoint under `/api/...`.")
        if self._secured(plan):
            lines.append("2. `require_api_key` admits or rejects the caller (401/503).")
            start = 3
        else:
            start = 2
        lines.append(f"{start}. The application service delegates to the repository.")
        lines.append(f"{start + 1}. The repository persists the record; the model serializes the response.")
        lines.append("")
        if events:
            lines.append("## Domain events")
            for ev in events:
                lines.append(f"- `{ev['name']}` validated by `handle_{ev['mod']}`")
            lines.append("")
        return "\n".join(lines)
