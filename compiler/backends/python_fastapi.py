"""PythonFastAPIBackend — reference Python/FastAPI backend (ADR-012 + runnability upgrade).

Emits a genuinely runnable FastAPI application: health endpoint, per-entity
CRUD routers wired through application services and an in-memory repository,
Pydantic domain models, event handlers, API-key authorization (fail-closed),
working Kubernetes/CI manifests, and a real TestClient suite exercising the
CRUD surface, the OpenAPI document, and auth.
"""
from __future__ import annotations

import json

from compiler.core.plan import CompilationPlan
from compiler.core.capabilities import BackendCapabilities, SemanticFeature, assert_plan_supported
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
        SemanticFeature.EXPRESSIONS,
        SemanticFeature.BUSINESS_RULES,
        SemanticFeature.STATE_TRANSITIONS,
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
            "infra:docs": "docs/architecture.md",
            "infra:requirements": "requirements.txt",
            "infra:test": "tests/test_app.py",
        })
        return p

    def compile(self, plan: CompilationPlan) -> GeneratedRepository:
        assert_plan_supported(plan, BackendCapabilities(backend_id=self.name, version=self.version, supported_features=self.supported_features))
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
        if path == "app/infrastructure/repositories.py":
            return self._repositories()
        if path == "app/core/security.py":
            return self._security()
        if path == "app/core/behavior.py":
            return self._behavior_runtime()
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


def _boolean(value: Any) -> bool:
    if not isinstance(value, bool):
        raise BehaviorError("boolean operand required")
    return value


def _compare(left: Any, right: Any) -> int:
    if isinstance(left, str) and isinstance(right, str):
        return (left > right) - (left < right)
    left_number, right_number = _number(left), _number(right)
    return (left_number > right_number) - (left_number < right_number)


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
    if op == "equal":
        if isinstance(args[0], str) and isinstance(args[1], str):
            return args[0] == args[1]
        try:
            return _number(args[0]) == _number(args[1])
        except BehaviorError:
            return args[0] == args[1]
    if op == "not_equal":
        return not evaluate_expression({"op": "equal", "args": raw_args}, context)
    if op == "less_than":
        return _compare(args[0], args[1]) < 0
    if op == "less_or_equal":
        return _compare(args[0], args[1]) <= 0
    if op == "greater_than":
        return _compare(args[0], args[1]) > 0
    if op == "greater_or_equal":
        return _compare(args[0], args[1]) >= 0
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
            else isinstance(value, (int, float, Decimal)) and not isinstance(value, bool) if kind in ("decimal", "money")
            else True
        )
        if not valid:
            raise BehaviorError(f"invalid type for field: {name}")
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
        title = plan.isr_id or "generated-service"

        imports = ["from fastapi import APIRouter, FastAPI, HTTPException"]
        if secured:
            imports[0] = "from fastapi import APIRouter, Depends, FastAPI, HTTPException"
            imports.append("from app.core.security import require_api_key")
        for e in entities:
            imports.append(f"from app.domain.{e['mod']} import {e['cls']}")
        for s in services:
            imports.append(
                f"from app.application.{s['mod']} import {s['cls']}Service"
            )

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
                f"@router.get('/api/{e['plural']}')",
                f"def list_{e['plural']}() -> list[dict]:",
                f"    return {svc_var}.list_{e['mod']}()",
                "",
                f"@router.post('/api/{e['plural']}', status_code=201)",
                f"def create_{e['mod']}(payload: {e['cls']}) -> dict:",
                f"    return {svc_var}.create_{e['mod']}(payload.model_dump())",
                "",
                f"@router.get('/api/{e['plural']}/{{item_id}}')",
                f"def get_{e['mod']}(item_id: str) -> dict:",
                f"    item = {svc_var}.get_{e['mod']}(item_id)",
                "    if item is None:",
                f'        raise HTTPException(status_code=404, detail="{e["plural"]} not found")',
                "    return item",
                "",
                f"@router.put('/api/{e['plural']}/{{item_id}}')",
                f"def update_{e['mod']}(item_id: str, payload: {e['cls']}) -> dict:",
                f"    item = {svc_var}.update_{e['mod']}(item_id, payload.model_dump())",
                "    if item is None:",
                f'        raise HTTPException(status_code=404, detail="{e["plural"]} not found")',
                "    return item",
                "",
                f"@router.delete('/api/{e['plural']}/{{item_id}}')",
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
            "app.include_router(router)",
            "",
        ]
        return "\n".join(lines)

    def _tests(self, plan: CompilationPlan) -> str:
        entities = self._entities(plan)
        events = self._events(plan)
        secured = self._secured(plan)
        lines = [
            "import os",
            "",
            'os.environ.setdefault("GENERATED_API_KEY", "generated-dev-key")',
            'API_KEY = os.environ["GENERATED_API_KEY"]',
            "",
            "from fastapi.testclient import TestClient",
            "",
            "from app.main import app",
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
            "def test_behavior_field_validation_fails_closed():",
            "    fields = [{'name': 'amount', 'value_type': 'money', 'required': True, 'nullable': False, 'constraints': [{'operator': 'min', 'value': 0}]}]",
            "    assert validate_fields(fields, {'amount': 10}) == {'amount': 10}",
            "    with pytest.raises(BehaviorError, match='below minimum'):",
            "        validate_fields(fields, {'amount': -1})",
            "    with pytest.raises(BehaviorError, match='unknown fields'):",
            "        validate_fields(fields, {'amount': 10, 'unexpected': 1})",
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
            lines += [
                f"def test_crud_{e['plural']}():",
                f"    created = client.post('/api/{e['plural']}', json={payload_json}, headers=HEADERS)",
                "    assert created.status_code == 201",
                "    item_id = created.json()['id']",
                f"    assert created.json()[{tested_field!r}] == {expected_created}",
                f"    listed = client.get('/api/{e['plural']}', headers=HEADERS)",
                f"    assert item_id in [i['id'] for i in listed.json()]",
                f"    fetched = client.get(f'/api/{e['plural']}/{{item_id}}', headers=HEADERS)",
                "    assert fetched.status_code == 200",
                f"    assert fetched.json()[{tested_field!r}] == {expected_created}",
                f"    updated = client.put(f'/api/{e['plural']}/{{item_id}}', json={updated_json}, headers=HEADERS)",
                "    assert updated.status_code == 200",
                f"    assert updated.json()[{tested_field!r}] == {expected_updated}",
                f"    deleted = client.delete(f'/api/{e['plural']}/{{item_id}}', headers=HEADERS)",
                "    assert deleted.status_code == 200",
                f"    gone = client.get(f'/api/{e['plural']}/{{item_id}}', headers=HEADERS)",
                "    assert gone.status_code == 404",
                "",
            ]
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
            return '"""Effect contract unavailable; this module is not executable."""\\n'
        spec = effect.behavior.model_dump(mode="json")
        spec_json = json.dumps(spec)
        return (
            '"""Generated effect adapter with explicit idempotency semantics."""\\n'
            "import json\\n"
            "from app.core.behavior import apply_effect\\n\\n"
            f"EFFECT = json.loads({spec_json!r})\\n\\n"
            "def apply(executor, idempotency_key, ledger):\\n"
            "    return apply_effect(EFFECT, idempotency_key, executor, ledger)\\n"
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
