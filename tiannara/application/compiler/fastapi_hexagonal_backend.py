"""FastAPIHexagonalBackend — the first real compiler backend.

Consumes the typed ISR (SystemModel carried by an IntermediateSoftwareRepresentation)
and deterministically emits a complete, deployable hexagonal FastAPI service:
domain / application / infrastructure / API layers, API-key authentication,
structured JSON logging, settings, tests, Docker, compose, CI, and docs.

Design constraints honoured (see ADR adr-cap-c-fastapi-hexagonal-backend.md):
  * backends never redefine architecture — structure derives solely from the ISR;
  * dependency direction is inward (domain imports nothing outer);
  * production-first: auth, logging, health/readiness, tests, Docker, CI;
  * Kubernetes/Terraform/messaging are separate backends, not embedded here.

Conformance: implements the existing ``CompilerBackend`` port
(``tiannara.domain.ports``), so it plugs straight into the Phase 16 pipeline.
``generate`` is the pure product (``CompilationResult``); ``compile`` is the
port adapter that materializes it to ``output_dir`` and returns a bundle.
"""

from __future__ import annotations

import json
from pathlib import Path

from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.application.compiler.documentation import evidence_bound_readme
from tiannara.application.compiler.writer import write_bundle
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.capability_manifest import BundleCapability, CapabilityManifest
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.models.genome import Genome
from tiannara.domain.models.isr import (
    DataModelSpec as LegacyDataModelSpec,
    IntermediateSoftwareRepresentation,
    IntentSpecification,
    SecuritySpec as LegacySecuritySpec,
    ServiceSpec as LegacyServiceSpec,
)
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    AuthenticationPosture,
    BusinessCapability,
    DataModelSpec as TypedDataModelSpec,
    DomainSpec,
    FieldSpec,
    RequirementsReference,
    SecurityModel,
    ServiceSpec as TypedServiceSpec,
    SystemModel,
)

from .naming import pascal_case, pluralize, slugify, snake_case

#: legacy ISR field type strings -> abstract field type (best-effort).
_LEGACY_TYPE_MAP: dict[str, AbstractFieldType] = {
    "str": AbstractFieldType.TEXT,
    "string": AbstractFieldType.TEXT,
    "int": AbstractFieldType.INTEGER,
    "integer": AbstractFieldType.INTEGER,
    "float": AbstractFieldType.DECIMAL,
    "decimal": AbstractFieldType.DECIMAL,
    "bool": AbstractFieldType.BOOLEAN,
    "boolean": AbstractFieldType.BOOLEAN,
    "datetime": AbstractFieldType.TIMESTAMP,
}


def _required_first(fields: list[FieldSpec]) -> list[FieldSpec]:
    """Stable partition: required fields before optional fields.

    Python function signatures require parameters without defaults to precede
    parameters with defaults. An ISR data model's field order is semantically
    arbitrary, so every site that lowers ``DataModelSpec.fields`` into a Python
    *function signature* must emit parameters in a valid order regardless of ISR
    ordering. (Pydantic *class-body* annotations are order-tolerant and need
    no reordering -- only function parameters are constrained.)
    """
    required = [f for f in fields if f.required]
    optional = [f for f in fields if not f.required]
    return required + optional


class FastAPIHexagonalBackend:
    """Deterministic, model-free compiler backend for a hexagonal FastAPI service."""

    backend_id = "fastapi_hexagonal"

    # -- public: pure product ---------------------------------------------

    def generate(self, system_model: SystemModel) -> CompilationResult:
        slug = slugify(system_model.system_name)
        models = system_model.data_models
        files: dict[str, str] = {
            f"{slug}/__init__.py": "",
            f"{slug}/config.py": self._config_py(system_model),
            f"{slug}/logging_config.py": self._logging_py(),
            f"{slug}/observability.py": self._observability_py(),
            f"{slug}/domain/__init__.py": "",
            f"{slug}/domain/models.py": self._models_py(models),
            f"{slug}/domain/repositories.py": self._repositories_py(slug, models),
            f"{slug}/application/__init__.py": "",
            f"{slug}/application/services.py": self._services_py(slug, models),
            f"{slug}/infrastructure/__init__.py": "",
            f"{slug}/infrastructure/memory_repositories.py": self._memory_repositories_py(
                slug, models
            ),
            f"{slug}/api/__init__.py": "",
            f"{slug}/api/schemas.py": self._schemas_py(models),
            f"{slug}/api/deps.py": self._deps_py(slug),
            f"{slug}/api/routes.py": self._routes_py(slug, models),
            f"{slug}/main.py": self._main_py(slug, models),
            f"{slug}/observability-map.json": self._observability_map(system_model),
            f"{slug}/tests/__init__.py": "",
            f"{slug}/tests/test_api.py": self._tests_py(slug, models),
            "requirements.txt": self._requirements(),
            "requirements-dev.txt": self._requirements_dev(),
            "Dockerfile": self._dockerfile(slug),
            "docker-compose.yml": self._compose(),
            ".github/workflows/ci.yml": self._ci(slug),
            "README.md": self._readme(slug, system_model),
            ".gitignore": self._gitignore(),
        }
        return CompilationResult(
            backend_id=self.backend_id,
            system_name=slug,
            files=files,
            capability_manifest=self._manifest(),
        )

    def build_profile(self, system_name: str) -> BackendBuildProfile:
        """Backend-supplied verification contract (Phase 19 generalization).

        The Python profile reproduces the requirements ``ProjectCompiler._verify``
        previously hardcoded: the bundle must contain ``<slug>/main.py``. Reading
        this from the backend (instead of the meta-compiler) is what lets a second,
        differently-laid-out backend (e.g. Go) declare its own shape.
        """
        from .naming import slugify

        slug = slugify(system_name)
        return BackendBuildProfile(
            language="python",
            required_files=(f"{slug}/main.py",),
            verifier_kind="python",
            # R2.4.0a: the FastAPI backend's runtime now mirrors Go's -- it
            # declares how its output is executed (runtime_image) AND how its
            # deps are provisioned (build_command) so the calibration harness
            # can run its tests inside a stock Python image without a host
            # toolchain. Requires the build phase (pip install) before pytest.
            test_command=["python", "-m", "pytest", "-q", f"{slug}/tests"],
            build_command=[
                "python", "-m", "pip", "install", "-q",
                "-r", "requirements.txt", "-r", "requirements-dev.txt",
            ],
            runtime_image="python:3.12-slim",
            requires_build_phase=True,
        )

    def async_resolution_module(self, workflows) -> str:
        """R2.4.0b Step 1 -- async-resolution codegen + naming contract.

        For every ``WorkflowState`` declaring ``metadata['awaits'] = <coroutine>``:

        * emit ``async def <coroutine>(): ...`` -- the coroutine name is EXACTLY
          the ``awaits`` value. This is the naming contract the
          ``TransitionRestoration`` operator reads out of stderr
          (``coroutine '<name>' was never awaited``); real backends must
          establish it before grounding.
        * emit its call site as ``await <coroutine>()`` when a resolving
          ``WorkflowTransition`` (``trigger == coroutine``) exists in the same
          workflow; otherwise fire-and-forget ``<coroutine>()`` -- which, under
          ``-W error::RuntimeWarning``, surfaces
          ``RuntimeWarning: coroutine '<name>' was never awaited``.

        The compiler always reflects the ISR faithfully (await iff the resolving
        edge exists). It never emits "broken" code for a well-formed ISR: the
        defect is in the *design* (a dropped transition edge), which is exactly
        what the Evolution Engine repairs -- not a backend "broken mode" flag.
        """
        lines: list[str] = [
            "# Auto-generated async-resolution surface (R2.4.0b).",
            "# Coroutine names mirror WorkflowState.metadata['awaits']; the call site awaits iff the resolving transition exists.",
            "",
        ]
        calls: list[str] = []
        emitted: set[str] = set()
        for wf in workflows:
            triggers = {t.trigger for t in wf.transitions}
            for state in wf.states:
                coroutine = state.metadata.get("awaits")
                if not coroutine:
                    continue
                if coroutine not in emitted:
                    lines.append(f"async def {coroutine}():")
                    lines.append(
                        f'    """Async operation awaited by ISR workflow state {state.id!r}."""'
                    )
                    lines.append("    return None")
                    lines.append("")
                    emitted.add(coroutine)
                if coroutine in triggers:
                    calls.append(f"    await {coroutine}()")
                else:
                    calls.append(
                        f"    {coroutine}()  # fire-and-forget: resolving transition absent"
                    )
        lines.append("async def orchestrate():")
        if calls:
            lines.extend(calls)
        else:
            lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    # -- public: CompilerBackend port adapter ------------------------------

    @property
    def name(self) -> str:
        return self.backend_id

    def compile(
        self,
        isr: IntermediateSoftwareRepresentation,
        genome: Genome,
        output_dir: str,
    ) -> SystemDeploymentBundle:
        model = self._system_model(isr)
        result = self.generate(model)
        root = write_bundle(result, output_dir)
        return SystemDeploymentBundle(
            project_id=isr.system_id,
            backend_name=self.name,
            isr_hash=isr.content_hash(),
            path=Path(output_dir),
            artifacts=result.file_paths(),
            capability_manifest=result.capability_manifest,
        )

    # -- ISR extraction / legacy synthesis ---------------------------------

    def _system_model(self, isr: IntermediateSoftwareRepresentation) -> SystemModel:
        typed = isr.system_model()
        if typed is not None:
            return typed
        # Legacy envelope: synthesize a typed SystemModel from legacy fields.
        return self._legacy_to_system_model(isr)

    @staticmethod
    def _legacy_authentication(spec) -> AuthenticationPosture:
        raw = getattr(spec, "authentication", "anonymous") or "anonymous"
        try:
            return AuthenticationPosture(raw)
        except ValueError:
            return AuthenticationPosture.TOKEN_BASED

    def _legacy_to_system_model(
        self, isr: IntermediateSoftwareRepresentation
    ) -> SystemModel:
        data_models: list[TypedDataModelSpec] = []
        for legacy in isr.data_models:
            assert isinstance(legacy, LegacyDataModelSpec)
            fields: list[FieldSpec] = []
            for field_name, type_str in legacy.fields.items():
                if field_name == "id":
                    kind = AbstractFieldType.IDENTIFIER
                else:
                    kind = _LEGACY_TYPE_MAP.get(type_str, AbstractFieldType.TEXT)
                fields.append(FieldSpec(name=field_name, type=kind))
            data_models.append(
                TypedDataModelSpec(
                    id=f"dm-{legacy.name}",
                    name=legacy.name,
                    owning_service_id="primary",
                    fields=fields,
                )
            )

        services: list[TypedServiceSpec] = []
        for legacy in isr.services:
            assert isinstance(legacy, LegacyServiceSpec)
            services.append(
                TypedServiceSpec(
                    id=f"svc-{legacy.name}",
                    name=legacy.name,
                    domain_id="general",
                    responsibilities=list(legacy.responsibilities),
                )
            )

        capabilities = [
            BusinessCapability(id=f"svc-{s.name}", name=s.name) for s in isr.services
        ]

        return SystemModel(
            system_name=isr.system_name,
            problem_statement=getattr(isr.intent, "statement", "") or isr.system_name,
            requirements_ref=RequirementsReference(
                graph_id="legacy", graph_hash=isr.content_hash()
            ),
            capabilities=capabilities,
            services=services,
            data_models=data_models,
            security=SecurityModel(
                authentication=self._legacy_authentication(isr.security)
            ),
            domains=[DomainSpec(id="general", name="general")],
        )

    # -- type mapping ------------------------------------------------------

    def _py_type(self, field: FieldSpec) -> str:
        kind = field.type
        if kind is AbstractFieldType.IDENTIFIER:
            return "str"
        if kind is AbstractFieldType.TEXT:
            return "str"
        if kind is AbstractFieldType.INTEGER:
            return "int"
        if kind is AbstractFieldType.DECIMAL:
            return "float"
        if kind is AbstractFieldType.BOOLEAN:
            return "bool"
        if kind is AbstractFieldType.TIMESTAMP:
            return "datetime"
        if kind is AbstractFieldType.ENUMERATION:
            if field.enumeration_values:
                return "Literal[" + ", ".join(repr(v) for v in field.enumeration_values) + "]"
            return "str"
        if kind is AbstractFieldType.REFERENCE:
            return "str"
        if kind is AbstractFieldType.BINARY:
            return "bytes"
        if kind is AbstractFieldType.DOCUMENT:
            return "dict"
        return "str"

    @staticmethod
    def _id_field_name(fields: list[FieldSpec]) -> str | None:
        for field in fields:
            if field.name == "id":
                return field.name
        for field in fields:
            if field.type is AbstractFieldType.IDENTIFIER:
                return field.name
        return None

    def _non_id_fields(self, model: TypedDataModelSpec) -> list[FieldSpec]:
        id_name = self._id_field_name(model.fields)
        return [f for f in model.fields if f.name != id_name]

    # -- file generators ---------------------------------------------------

    def _config_py(self, sm: SystemModel) -> str:
        auth_required = sm.security.authentication is not AuthenticationPosture.ANONYMOUS
        default_name = sm.system_name.replace('"', "'")
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import os",
                "",
                "from pydantic import BaseModel",
                "",
                f"AUTH_REQUIRED: bool = {auth_required}",
                "",
                "",
                "class Settings(BaseModel):",
                f'    app_name: str = "{default_name}"',
                '    api_key: str = ""',
                '    log_level: str = "INFO"',
                '    app_version: str = "unknown"',
                '    deployment_id: str = "local"',
                "",
                "",
                "def load_settings() -> Settings:",
                "    return Settings(",
                f'        app_name=os.getenv("APP_NAME", "{default_name}"),',
                '        api_key=os.getenv("API_KEY", ""),',
                '        log_level=os.getenv("LOG_LEVEL", "INFO"),',
                '        app_version=os.getenv("APP_VERSION", "unknown"),',
                '        deployment_id=os.getenv("DEPLOYMENT_ID", "local"),',
                "    )",
                "",
            ]
        )

    def _logging_py(self) -> str:
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import json",
                "import logging",
                "import sys",
                "",
                "",
                "class JsonFormatter(logging.Formatter):",
                "    def format(self, record: logging.LogRecord) -> str:",
                "        payload = {",
                '            "level": record.levelname,',
                '            "message": record.getMessage(),',
                '            "logger": record.name,',
                '            "timestamp": self.formatTime(record),',
                "        }",
                "        for name in (",
                '            "request_id", "correlation_id", "trace_id", "span_id",',
                '            "parent_span_id", "method", "route", "status_code",',
                '            "duration_seconds", "error_id", "app_version", "deployment_id",',
                "        ):",
                "            if hasattr(record, name):",
                "                payload[name] = getattr(record, name)",
                "        return json.dumps(payload)",
                "",
                "",
                'def configure_logging(level: str = "INFO") -> None:',
                "    handler = logging.StreamHandler(sys.stdout)",
                "    handler.setFormatter(JsonFormatter())",
                "    root = logging.getLogger()",
                "    root.handlers.clear()",
                "    root.addHandler(handler)",
                "    root.setLevel(level.upper())",
                "",
            ]
        )

    def _observability_py(self) -> str:
        return '''from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from collections import Counter

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("generated.observability")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def _header_id(value: str | None) -> str:
    if value and _SAFE_ID.fullmatch(value):
        return value
    return uuid.uuid4().hex


def _trace(value: str | None) -> tuple[str, str, str | None, str]:
    match = _TRACEPARENT.fullmatch(value or "")
    if match and set(match.group(1)) != {"0"} and set(match.group(2)) != {"0"}:
        trace_id, parent_span_id, flags = match.groups()
        return trace_id, uuid.uuid4().hex[:16], parent_span_id, flags
    return uuid.uuid4().hex, uuid.uuid4().hex[:16], None, "01"


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: Counter[tuple[str, str, int]] = Counter()
        self._durations: Counter[tuple[str, str, int]] = Counter()

    def observe(self, method: str, route: str, status_code: int, elapsed: float) -> None:
        key = (method, route, status_code)
        with self._lock:
            self._counts[key] += 1
            self._durations[key] += elapsed

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\\\", "\\\\\\\\").replace('"', '\\\\"').replace("\\n", "\\\\n")

    def render(self, app_name: str, app_version: str, deployment_id: str) -> str:
        with self._lock:
            counts = sorted(self._counts.items())
            durations = dict(self._durations)
        lines = [
            "# HELP generated_http_requests_total Completed HTTP requests.",
            "# TYPE generated_http_requests_total counter",
        ]
        for (method, route, status), count in counts:
            labels = f'method="{self._escape(method)}",route="{self._escape(route)}",status_code="{status}"'
            lines.append(f"generated_http_requests_total{{{labels}}} {count}")
        lines.extend([
            "# HELP generated_http_request_duration_seconds_sum Total request duration.",
            "# TYPE generated_http_request_duration_seconds_sum counter",
        ])
        for (method, route, status), _count in counts:
            labels = f'method="{self._escape(method)}",route="{self._escape(route)}",status_code="{status}"'
            lines.append(f"generated_http_request_duration_seconds_sum{{{labels}}} {durations[(method, route, status)]:.9f}")
        identity = ",".join(
            f'{key}="{self._escape(value)}"'
            for key, value in (
                ("app_name", app_name),
                ("app_version", app_version),
                ("deployment_id", deployment_id),
            )
        )
        lines.extend([
            "# HELP generated_app_info Generated application identity.",
            "# TYPE generated_app_info gauge",
            f"generated_app_info{{{identity}}} 1",
        ])
        return "\\n".join(lines) + "\\n"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, metrics: RequestMetrics, app_version: str, deployment_id: str):
        super().__init__(app)
        self.metrics = metrics
        self.app_version = app_version
        self.deployment_id = deployment_id

    async def dispatch(self, request: Request, call_next):
        request_id = _header_id(request.headers.get("x-request-id"))
        correlation_id = _header_id(request.headers.get("x-correlation-id"))
        trace_id, span_id, parent_span_id, flags = _trace(request.headers.get("traceparent"))
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.trace_id = trace_id
        request.state.error_id = None
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started
        route = getattr(request.scope.get("route"), "path", "unmatched")
        status = response.status_code
        self.metrics.observe(request.method, route, status, elapsed)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["traceparent"] = f"00-{trace_id}-{span_id}-{flags}"
        if request.state.error_id:
            response.headers["X-Error-ID"] = request.state.error_id
        logger.info(
            "http.request.completed",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "parent_span_id": parent_span_id,
                "method": request.method,
                "route": route,
                "status_code": status,
                "duration_seconds": round(elapsed, 9),
                "error_id": request.state.error_id,
                "app_version": self.app_version,
                "deployment_id": self.deployment_id,
            },
        )
        return response


async def internal_error(request: Request, exc: Exception) -> JSONResponse:
    error_id = uuid.uuid4().hex
    request.state.error_id = error_id
    settings = getattr(request.app.state, "settings", None)
    logger.exception(
        "http.request.failed",
        exc_info=(type(exc), exc, exc.__traceback__),
        extra={
            "request_id": getattr(request.state, "request_id", ""),
            "correlation_id": getattr(request.state, "correlation_id", ""),
            "trace_id": getattr(request.state, "trace_id", ""),
            "error_id": error_id,
            "app_version": getattr(settings, "app_version", "unknown"),
            "deployment_id": getattr(settings, "deployment_id", "local"),
        },
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_id": error_id},
        headers={"X-Error-ID": error_id},
    )
'''

    def _observability_map(self, sm: SystemModel) -> str:
        components = [
            {"id": service.id, "name": service.name}
            for service in sorted(sm.services, key=lambda item: item.id)
        ]
        if not components:
            components = [
                {"id": capability.id, "name": capability.name}
                for capability in sorted(sm.capabilities, key=lambda item: item.id)
            ]
        component_ids = [component["id"] for component in components]
        bindings = {
            "structured_logging": {
                "status": "SUPPORTED",
                "runtime_events": ["http.request.completed", "http.request.failed"],
                "signals": ["structured_log"],
                "evidence": ["logs"],
            },
            "metrics": {
                "status": "SUPPORTED",
                "runtime_events": ["http.request.completed"],
                "signals": ["request_counter", "duration_total"],
                "evidence": ["/metrics"],
            },
            "distributed_tracing": {
                "status": "PARTIAL",
                "runtime_events": ["http.request.completed"],
                "signals": ["trace_context"],
                "evidence": ["logs", "response_headers"],
                "limitations": ["Trace context is propagated locally; no external exporter is configured."],
            },
            "health_checks": {
                "status": "SUPPORTED",
                "runtime_events": ["service.health"],
                "signals": ["liveness"],
                "evidence": ["/health/live"],
            },
            "readiness_checks": {
                "status": "SUPPORTED",
                "runtime_events": ["service.health"],
                "signals": ["readiness"],
                "evidence": ["/health/ready"],
            },
            "audit_events": {
                "status": "NOT_IMPLEMENTED",
                "runtime_events": [],
                "signals": [],
                "evidence": [],
                "limitations": ["Business audit-event generation is not implemented by this backend."],
            },
        }
        requirement_bindings = [
            {
                "requirement": requirement.value,
                "component_ids": component_ids,
                **bindings.get(
                    requirement.value,
                    {
                        "status": "NOT_IMPLEMENTED",
                        "runtime_events": [],
                        "signals": [],
                        "evidence": [],
                        "limitations": ["No backend mapping is defined for this requirement."],
                    },
                ),
            }
            for requirement in sm.operational_policies.observability_requirements
        ]
        payload = {
            "schema_version": "1.0",
            "requirements_source": {
                "graph_id": sm.requirements_ref.graph_id,
                "graph_hash": sm.requirements_ref.graph_hash,
                "observability_requirements": [
                    requirement.value
                    for requirement in sm.operational_policies.observability_requirements
                ],
            },
            "components": components,
            "requirement_bindings": requirement_bindings,
            "runtime_events": [
                {
                    "name": "http.request.completed",
                    "signals": [
                        "structured_log",
                        "request_counter",
                        "duration_total",
                        "trace_context",
                    ],
                    "component_ids": component_ids,
                    "evidence": ["logs", "/metrics", "response_headers"],
                },
                {
                    "name": "http.request.failed",
                    "signals": ["structured_error_log", "error_id"],
                    "component_ids": component_ids,
                    "evidence": ["logs", "X-Error-ID"],
                },
                {
                    "name": "service.health",
                    "signals": ["liveness", "readiness"],
                    "component_ids": component_ids,
                    "evidence": ["/health/live", "/health/ready"],
                },
            ],
            "limitations": [
                "Metrics are process-local and reset on restart.",
                "Trace context is propagated and logged locally; no external trace exporter is configured.",
            ],
        }
        return json.dumps(payload, sort_keys=True, indent=2) + "\n"

    def _models_py(self, models: list[TypedDataModelSpec]) -> str:
        needs_datetime = any(
            f.type is AbstractFieldType.TIMESTAMP for m in models for f in m.fields
        )
        needs_literal = any(
            f.type is AbstractFieldType.ENUMERATION and f.enumeration_values
            for m in models
            for f in m.fields
        )
        needs_optional = any(not f.required for m in models for f in m.fields)

        lines = ["from __future__ import annotations", ""]
        if needs_datetime:
            lines.append("from datetime import datetime")
        typing_names = []
        if needs_literal:
            typing_names.append("Literal")
        if needs_optional:
            typing_names.append("Optional")
        if typing_names:
            lines.append("from typing import " + ", ".join(sorted(typing_names)))
        lines.append("")
        lines.append("from pydantic import BaseModel")
        lines.append("")

        for model in models:
            name = pascal_case(model.name)
            lines.append("")
            lines.append(f"class {name}(BaseModel):")
            lines.append("    id: str")
            emitted_body = False
            for field in model.fields:
                if field.name == self._id_field_name(model.fields):
                    continue
                py = self._py_type(field)
                if field.required:
                    lines.append(f"    {field.name}: {py}")
                else:
                    lines.append(f"    {field.name}: Optional[{py}] = None")
                emitted_body = True
            if not emitted_body:
                lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    def _repositories_py(self, slug: str, models: list[TypedDataModelSpec]) -> str:
        names = [pascal_case(m.name) for m in models]
        lines = [
            "from __future__ import annotations",
            "",
            "from abc import ABC, abstractmethod",
            "from typing import List, Optional",
            "",
        ]
        if names:
            lines.append(f"from {slug}.domain.models import " + ", ".join(names))
            lines.append("")
        for model in models:
            name = pascal_case(model.name)
            lines += [
                "",
                f"class {name}Repository(ABC):",
                "    @abstractmethod",
                f"    def get(self, entity_id: str) -> Optional[{name}]:",
                "        ...",
                "",
                "    @abstractmethod",
                f"    def list(self) -> List[{name}]:",
                "        ...",
                "",
                "    @abstractmethod",
                f"    def add(self, entity: {name}) -> {name}:",
                "        ...",
                "",
                "    @abstractmethod",
                "    def remove(self, entity_id: str) -> bool:",
                "        ...",
            ]
        lines.append("")
        return "\n".join(lines)

    def _memory_repositories_py(
        self, slug: str, models: list[TypedDataModelSpec]
    ) -> str:
        names = [pascal_case(m.name) for m in models]
        repo_names = [f"{n}Repository" for n in names]
        lines = [
            "from __future__ import annotations",
            "",
            "from typing import Dict, List, Optional",
            "",
        ]
        if names:
            lines.append(f"from {slug}.domain.models import " + ", ".join(names))
        if repo_names:
            lines.append(
                f"from {slug}.domain.repositories import " + ", ".join(repo_names)
            )
        lines.append("")
        for model in models:
            name = pascal_case(model.name)
            lines += [
                "",
                f"class InMemory{name}Repository({name}Repository):",
                "    def __init__(self) -> None:",
                f"        self._store: Dict[str, {name}] = {{}}",
                "",
                f"    def get(self, entity_id: str) -> Optional[{name}]:",
                "        return self._store.get(entity_id)",
                "",
                f"    def list(self) -> List[{name}]:",
                "        return list(self._store.values())",
                "",
                f"    def add(self, entity: {name}) -> {name}:",
                "        self._store[entity.id] = entity",
                "        return entity",
                "",
                "    def remove(self, entity_id: str) -> bool:",
                "        return self._store.pop(entity_id, None) is not None",
            ]
        lines.append("")
        return "\n".join(lines)

    def _services_py(self, slug: str, models: list[TypedDataModelSpec]) -> str:
        names = [pascal_case(m.name) for m in models]
        repo_names = [f"{n}Repository" for n in names]
        lines = [
            "from __future__ import annotations",
            "",
            "import uuid",
            "from typing import List, Optional",
            "",
        ]
        if names:
            lines.append(f"from {slug}.domain.models import " + ", ".join(names))
        if repo_names:
            lines.append(f"from {slug}.domain.repositories import " + ", ".join(repo_names))
        lines.append("")
        for model in models:
            name = pascal_case(model.name)
            # DEFECT-TRACKED: previously emitted fields in ISR order, producing
            # `SyntaxError: parameter without a default follows parameter with a
            # default` whenever an optional field preceded a required one.
            # Reordered at emission (see _required_first); regression-guarded by
            # tests/test_backend_field_order_regression.py (fails without this).
            fields = _required_first(self._non_id_fields(model))
            params = ", ".join(
                f"{f.name}: "
                + (("Optional[" + self._py_type(f) + "]") if not f.required else self._py_type(f))
                + (" = None" if not f.required else "")
                for f in fields
            )
            assignments = ", ".join(f"{f.name}={f.name}" for f in fields)
            args = "id=str(uuid.uuid4())" + (", " + assignments if assignments else "")
            lines += [
                "",
                f"class {name}Service:",
                f"    def __init__(self, repository: {name}Repository) -> None:",
                "        self._repository = repository",
                "",
                f"    def create(self, {params}) -> {name}:",
                f"        entity = {name}({args})",
                "        return self._repository.add(entity)",
                "",
                f"    def get(self, entity_id: str) -> Optional[{name}]:",
                "        return self._repository.get(entity_id)",
                "",
                f"    def list(self) -> List[{name}]:",
                "        return self._repository.list()",
                "",
                "    def delete(self, entity_id: str) -> bool:",
                "        return self._repository.remove(entity_id)",
            ]
        lines.append("")
        return "\n".join(lines)

    def _schemas_py(self, models: list[TypedDataModelSpec]) -> str:
        needs_datetime = any(
            f.type is AbstractFieldType.TIMESTAMP
            for m in models
            for f in self._non_id_fields(m)
        )
        needs_literal = any(
            f.type is AbstractFieldType.ENUMERATION and f.enumeration_values
            for m in models
            for f in self._non_id_fields(m)
        )
        needs_optional = any(
            not f.required for m in models for f in self._non_id_fields(m)
        )

        lines = ["from __future__ import annotations", ""]
        if needs_datetime:
            lines.append("from datetime import datetime")
        typing_names = []
        if needs_literal:
            typing_names.append("Literal")
        if needs_optional:
            typing_names.append("Optional")
        if typing_names:
            lines.append("from typing import " + ", ".join(sorted(typing_names)))
        lines.append("")
        lines.append("from pydantic import BaseModel")
        lines.append("")
        for model in models:
            name = pascal_case(model.name)
            lines.append("")
            lines.append(f"class {name}Create(BaseModel):")
            emitted = False
            for field in self._non_id_fields(model):
                py = self._py_type(field)
                if field.required:
                    lines.append(f"    {field.name}: {py}")
                else:
                    lines.append(f"    {field.name}: Optional[{py}] = None")
                emitted = True
            if not emitted:
                lines.append("    pass")
        lines.append("")
        return "\n".join(lines)

    def _deps_py(self, slug: str) -> str:
        return "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from fastapi import HTTPException, Request",
                "",
                f"from {slug}.config import AUTH_REQUIRED, Settings",
                "",
                "",
                "def make_auth_dependency(settings: Settings):",
                "    async def verify_api_key(request: Request) -> None:",
                "        if not AUTH_REQUIRED:",
                "            return None",
                "        if not settings.api_key:",
                "            return None",
                '        provided = request.headers.get("X-API-Key")',
                "        if provided != settings.api_key:",
                "            raise HTTPException(",
                '                status_code=401, detail="Invalid or missing API key"',
                "            )",
                "        return None",
                "",
                "    return verify_api_key",
                "",
            ]
        )

    def _routes_py(self, slug: str, models: list[TypedDataModelSpec]) -> str:
        names = [pascal_case(m.name) for m in models]
        service_names = [f"{n}Service" for n in names]
        schema_names = [f"{n}Create" for n in names]
        lines = [
            "from __future__ import annotations",
            "",
            "from typing import List",
            "",
            "from fastapi import APIRouter, Depends, HTTPException, Response",
            "",
        ]
        if schema_names:
            lines.append(f"from {slug}.api.schemas import " + ", ".join(schema_names))
        if service_names:
            lines.append(
                f"from {slug}.application.services import " + ", ".join(service_names)
            )
        if names:
            lines.append(f"from {slug}.domain.models import " + ", ".join(names))
        lines.append("")
        template = "\n".join(
            [
                "",
                "def build_<<SNAKE>>_router(service: <<NAME>>Service, auth_dependency) -> APIRouter:",
                "    router = APIRouter(",
                '        prefix="/<<PLURAL>>",',
                '        tags=["<<PLURAL>>"],',
                "        dependencies=[Depends(auth_dependency)],",
                "    )",
                "",
                "    @router.get(\"\", response_model=List[<<NAME>>])",
                "    def list_<<SNAKE>>() -> List[<<NAME>>]:",
                "        return service.list()",
                "",
                "    @router.post(\"\", response_model=<<NAME>>, status_code=201)",
                "    def create_<<SNAKE>>(payload: <<NAME>>Create) -> <<NAME>>:",
                "        return service.create(**payload.model_dump())",
                "",
                '    @router.get("/{<<SNAKE>>_id}", response_model=<<NAME>>)',
                "    def get_<<SNAKE>>(<<SNAKE>>_id: str) -> <<NAME>>:",
                "        entity = service.get(<<SNAKE>>_id)",
                "        if entity is None:",
                '            raise HTTPException(status_code=404, detail="<<NAME>> not found")',
                "        return entity",
                "",
                '    @router.delete("/{<<SNAKE>>_id}", status_code=204)',
                "    def delete_<<SNAKE>>(<<SNAKE>>_id: str) -> Response:",
                "        deleted = service.delete(<<SNAKE>>_id)",
                "        if not deleted:",
                '            raise HTTPException(status_code=404, detail="<<NAME>> not found")',
                "        return Response(status_code=204)",
                "",
                "    return router",
            ]
        )
        for model in models:
            name = pascal_case(model.name)
            snake = snake_case(model.name)
            plural = pluralize(snake)
            block = (
                template.replace("<<SNAKE>>", snake)
                .replace("<<NAME>>", name)
                .replace("<<PLURAL>>", plural)
            )
            lines.append(block)
        lines.append("")
        return "\n".join(lines)

    def _main_py(self, slug: str, models: list[TypedDataModelSpec]) -> str:
        names = [pascal_case(m.name) for m in models]
        repo_imports = ", ".join(f"InMemory{n}Repository" for n in names)
        service_imports = ", ".join(f"{n}Service" for n in names)
        router_imports = ", ".join(
            f"build_{snake_case(m.name)}_router" for m in models
        )
        lines = [
            "from __future__ import annotations",
            "",
            "from typing import Optional",
            "",
            "from fastapi import FastAPI",
            "from fastapi.responses import PlainTextResponse",
            "",
            f"from {slug}.api.deps import make_auth_dependency",
        ]
        if router_imports:
            lines.append(f"from {slug}.api.routes import " + router_imports)
        if service_imports:
            lines.append(f"from {slug}.application.services import " + service_imports)
        lines.append(f"from {slug}.config import Settings, load_settings")
        if repo_imports:
            lines.append(
                f"from {slug}.infrastructure.memory_repositories import " + repo_imports
            )
        lines.append(f"from {slug}.logging_config import configure_logging")
        lines.append(
            f"from {slug}.observability import ObservabilityMiddleware, RequestMetrics, internal_error"
        )
        lines += [
            "",
            "",
            "def create_app(settings: Optional[Settings] = None) -> FastAPI:",
            "    settings = settings or load_settings()",
            "    configure_logging(settings.log_level)",
            "    app = FastAPI(title=settings.app_name)",
            "    app.state.settings = settings",
            "    app.state.request_metrics = RequestMetrics()",
            "    app.add_middleware(",
            "        ObservabilityMiddleware,",
            "        metrics=app.state.request_metrics,",
            "        app_version=settings.app_version,",
            "        deployment_id=settings.deployment_id,",
            "    )",
            "    app.add_exception_handler(Exception, internal_error)",
            "    auth_dependency = make_auth_dependency(settings)",
            "",
            '    @app.get("/health/live")',
            '    @app.get("/health")',
            "    def health() -> dict:",
            '        return {"status": "alive"}',
            "",
            '    @app.get("/health/ready")',
            '    @app.get("/readiness")',
            "    def readiness() -> dict:",
            '        return {"status": "ready"}',
            "",
            '    @app.get("/metrics", response_class=PlainTextResponse)',
            "    def metrics() -> str:",
            "        return app.state.request_metrics.render(",
            "            settings.app_name, settings.app_version, settings.deployment_id",
            "        )",
            "",
        ]
        for model in models:
            name = pascal_case(model.name)
            snake = snake_case(model.name)
            lines += [
                f"    {snake}_repository = InMemory{name}Repository()",
                f"    {snake}_service = {name}Service({snake}_repository)",
                f"    app.include_router(build_{snake}_router({snake}_service, auth_dependency))",
                "",
            ]
        lines.append("    return app")
        lines.append("")
        return "\n".join(lines)

    def _tests_py(self, slug: str, models: list[TypedDataModelSpec]) -> str:
        lines = [
            "from __future__ import annotations",
            "",
            "from fastapi.testclient import TestClient",
            "",
            f"from {slug}.config import Settings",
            f"from {slug}.main import create_app",
            "",
            "",
            "def _client() -> TestClient:",
            '    app = create_app(Settings(api_key="test-key"))',
            "    return TestClient(app)",
            "",
            "",
            "def test_health_and_readiness_are_open() -> None:",
            "    client = _client()",
            '    assert client.get("/health").status_code == 200',
            '    assert client.get("/readiness").status_code == 200',
            "",
        ]
        if models:
            plural = pluralize(snake_case(models[0].name))
            lines += [
                "",
                "def test_resources_require_auth() -> None:",
                "    client = _client()",
                f'    assert client.get("/{plural}").status_code == 401',
                "",
                "",
                "def test_list_with_api_key() -> None:",
                "    client = _client()",
                '    headers = {"X-API-Key": "test-key"}',
                f'    assert client.get("/{plural}", headers=headers).status_code == 200',
                "",
            ]
        return "\n".join(lines)

    # -- project scaffolding ----------------------------------------------

    def _requirements(self) -> str:
        return "\n".join(
            ["fastapi>=0.110", "uvicorn[standard]>=0.29", "pydantic>=2.6", ""]
        )

    def _requirements_dev(self) -> str:
        return "\n".join(["pytest>=8.0", "httpx>=0.27", ""])

    def _dockerfile(self, slug: str) -> str:
        return "\n".join(
            [
                "FROM python:3.12-slim",
                "WORKDIR /srv",
                "COPY requirements.txt .",
                "RUN pip install --no-cache-dir -r requirements.txt",
                f"COPY {slug} ./{slug}",
                "RUN useradd -m appuser && chown -R appuser:appuser /srv",
                "USER appuser",
                "EXPOSE 8000",
                f'CMD ["uvicorn", "{slug}.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]',
                "",
            ]
        )

    def _compose(self) -> str:
        return "\n".join(
            [
                "services:",
                "  api:",
                "    build: .",
                "    ports:",
                '      - "8000:8000"',
                "    environment:",
                "      - API_KEY=${API_KEY:-}",
                "      - LOG_LEVEL=INFO",
                "",
            ]
        )

    def _ci(self, slug: str) -> str:
        return "\n".join(
            [
                "name: ci",
                "on:",
                "  push:",
                "  pull_request:",
                "jobs:",
                "  test:",
                "    runs-on: ubuntu-latest",
                "    steps:",
                "      - uses: actions/checkout@v4",
                "      - uses: actions/setup-python@v5",
                "        with:",
                '          python-version: "3.12"',
                "      - name: Install dependencies",
                "        run: |",
                "          pip install -r requirements.txt -r requirements-dev.txt",
                "      - name: Run tests",
                f"        run: pytest {slug}/tests -q",
                "",
            ]
        )

    def _readme(self, slug: str, sm: SystemModel) -> str:
        return evidence_bound_readme(
            slug=slug,
            system_name=sm.system_name,
            backend_id=self.backend_id,
            capabilities=[c.value for c in self._manifest().capabilities],
            architecture_lines=[
                "Hexagonal (ports & adapters):",
                "",
                "- `domain/` — entities and repository ports (depends on nothing outer)",
                "- `application/` — services / use cases (depends on domain)",
                "- `infrastructure/` — adapters (in-memory repositories)",
                "- `api/` — FastAPI routers, schemas, dependencies",
                "- `observability-map.json` — requirement/component/runtime-signal/evidence traceability",
                "- `/health/live`, `/health/ready`, and `/metrics` — generated operational surfaces",
                "- Request and correlation IDs plus W3C trace context are logged and returned in headers.",
                "- Metrics are process-local; trace context is not exported to an external collector.",
                "- Business audit events are not generated; see `observability-map.json` for requirement status.",
                "",
                "Evolution notes:",
                "",
                "- Persistence is in-memory (stage 1); SQL/persistence backends evolve the",
                "  repository adapters behind the existing domain ports.",
                "- Authentication is API-key gating; OAuth2/OIDC/JWT arrive as security",
                "  backends.",
                "- Kubernetes/Terraform/messaging are separate compiler backends.",
            ],
            verify_commands=[
                "pip install -r requirements-dev.txt",
                f"pytest {slug}/tests",
            ],
            run_commands=[
                "pip install -r requirements.txt",
                f'uvicorn "{slug}.main:create_app" --factory --reload',
            ],
        )

    def _gitignore(self) -> str:
        return "\n".join(
            ["__pycache__/", "*.pyc", ".venv/", ".pytest_cache/", ".env", ""]
        )

    def _manifest(self) -> CapabilityManifest:
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[
                BundleCapability.BUILD,
                BundleCapability.LINT,
                BundleCapability.STATIC_ANALYSIS,
                BundleCapability.TEST,
                BundleCapability.SECURITY_SCAN,
                BundleCapability.CONTAINERIZE,
                BundleCapability.DEPLOY,
                BundleCapability.HEALTH_CHECK,
                BundleCapability.OBSERVABILITY,
                BundleCapability.DOCUMENTATION,
                BundleCapability.RELEASE,
            ],
            metadata={
                "language": "python",
                "framework": "fastapi",
                "style": "hexagonal",
                "observability": {
                    "structured_request_logs": True,
                    "request_correlation": True,
                    "process_local_metrics": True,
                    "trace_context_propagation": True,
                    "external_trace_export": False,
                    "health_endpoints": ["/health/live", "/health/ready"],
                    "error_identity": True,
                    "audit_events": False,
                },
            },
        )
