"""Extract operation lists and digests from real compiler outputs (Checkpoint 045)."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.react_frontend import ReactFrontendBackend
from compiler.core.capabilities import UnsupportedSemanticsError
from compiler.core.declared_api import declared_routes
from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from compiler.core.protocol import GeneratedRepository
from isr.core.revision import ISRRevision

from .candidate_fixture import CANDIDATE_ID, payroll_isr_revision


@dataclass(frozen=True)
class PayrollCompileResult:
    candidate_id: str
    revision_id: str
    plan: CompilationPlan
    revision: ISRRevision
    frontend: GeneratedRepository
    backend: GeneratedRepository | None
    backend_compile_error: str | None
    artifact_sha256: str
    artifact_manifest_digest: str
    artifact_bytes: bytes
    frontend_operations: tuple[str, ...]
    declared_backend_operations: tuple[str, ...]
    backend_operations: tuple[str, ...]
    persistence_entities: tuple[str, ...]
    frontend_requires_auth: bool
    shared_auth_models: bool


def _canonical_manifest(files: dict[str, str]) -> bytes:
    entries = {k: files[k] for k in sorted(files)}
    return json.dumps(entries, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def manifest_digest(files: dict[str, str]) -> str:
    return hashlib.sha256(_canonical_manifest(files)).hexdigest()


def artifact_sha256_from_files(files: dict[str, str]) -> str:
    return manifest_digest(files)


def artifact_bytes_from_files(files: dict[str, str]) -> bytes:
    return _canonical_manifest(files)


def _parse_frontend_routes_from_app(app_tsx: str) -> tuple[str, ...]:
    match = re.search(r"const ROUTES: RouteSpec\[] = (\[.*?\]);\n", app_tsx, re.DOTALL)
    if not match:
        return ()
    routes = json.loads(match.group(1))
    ops: list[str] = []
    for route in routes:
        requires_auth = bool(route.get("requiresAuth"))
        if requires_auth:
            ops.append(f"AUTH route:{route.get('path')}")
        for interaction in route.get("interactions") or []:
            method = interaction.get("method")
            path = interaction.get("path")
            if method and path:
                ops.append(f"{str(method).upper()} {path}")
        for api_op in route.get("apiOperations") or []:
            method = api_op.get("method")
            path = api_op.get("path")
            if method and path:
                sig = f"{str(method).upper()} {path}"
                if sig not in ops:
                    ops.append(sig)
    return tuple(sorted(set(ops)))


def _backend_operations_from_plan(plan: CompilationPlan) -> tuple[str, ...]:
    ops: list[str] = []
    try:
        for route in declared_routes(plan):
            ops.append(f"{route.method.upper()} {route.path}")
    except UnsupportedSemanticsError:
        for api in plan.apis:
            if api.behavior is None:
                continue
            ops.append(f"{api.behavior.method.upper()} {api.behavior.path}")
    return tuple(sorted(set(ops)))


def _persistence_entities(plan: CompilationPlan) -> tuple[str, ...]:
    names = {m.entity_name for m in plan.data_models}
    for svc in plan.services:
        for dm in svc.data_models:
            names.add(dm.entity_name)
    return tuple(sorted(names))


def compile_payroll_from_revision(revision: ISRRevision) -> PayrollCompileResult:
    """Compile payroll artifacts from an explicit ISR revision (governed route)."""
    plan = isr_to_plan(revision)
    frontend = ReactFrontendBackend().compile(plan)
    backend: GeneratedRepository | None = None
    backend_error: str | None = None
    try:
        backend = PythonFastAPIBackend().compile(plan)
    except UnsupportedSemanticsError as exc:
        backend_error = str(exc)

    merged_files = dict(frontend.files)
    if backend is not None:
        merged_files.update({f"backend/{k}": v for k, v in backend.files.items()})
    artifact_bytes = artifact_bytes_from_files(merged_files)

    fe_ops = _parse_frontend_routes_from_app(frontend.files.get("src/App.tsx", ""))
    declared_be_ops = _backend_operations_from_plan(plan)
    # Without a compiled backend, coherence uses an empty operation set so declarations
    # cannot satisfy frontend calls (audit §4 — no acceptance-by-declaration).
    be_ops_for_coherence = declared_be_ops if backend is not None else ()

    requires_auth = any(
        bool(r.behavior.requires_auth)
        for r in plan.frontend_routes
        if r.behavior is not None
    )
    has_policy = bool(plan.security)
    shared_auth = requires_auth and has_policy

    digest = hashlib.sha256(artifact_bytes).hexdigest()
    manifest = digest

    return PayrollCompileResult(
        candidate_id=CANDIDATE_ID,
        revision_id=revision.revision_id,
        plan=plan,
        revision=revision,
        frontend=frontend,
        backend=backend,
        backend_compile_error=backend_error,
        artifact_sha256=digest,
        artifact_manifest_digest=manifest,
        artifact_bytes=artifact_bytes,
        frontend_operations=fe_ops,
        declared_backend_operations=declared_be_ops,
        backend_operations=be_ops_for_coherence,
        persistence_entities=_persistence_entities(plan),
        frontend_requires_auth=requires_auth,
        shared_auth_models=shared_auth,
    )


def compile_payroll_candidate() -> PayrollCompileResult:
    """Governed compiler route for the payroll proving candidate (fail-closed backend)."""
    return compile_payroll_from_revision(payroll_isr_revision())
