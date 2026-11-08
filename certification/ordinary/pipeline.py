"""Ordinary workload compile pipeline (Checkpoint 054)."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Callable

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.react_frontend import ReactFrontendBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.capabilities import UnsupportedSemanticsError
from compiler.core.declared_api import declared_routes
from compiler.core.lowering import isr_to_plan
from compiler.core.plan import CompilationPlan
from compiler.core.protocol import GeneratedRepository
from isr.core.revision import ISRRevision


@dataclass(frozen=True)
class OrdinaryCompileResult:
    workload_id: str
    candidate_id: str
    revision_id: str
    plan: CompilationPlan
    revision: ISRRevision
    frontend: GeneratedRepository
    backend_python: GeneratedRepository | None
    backend_rust: GeneratedRepository | None
    python_compile_error: str | None
    rust_compile_error: str | None
    artifact_sha256: str
    artifact_manifest_digest: str
    artifact_bytes: bytes
    frontend_operations: tuple[str, ...]
    backend_operations: tuple[str, ...]
    persistence_entities: tuple[str, ...]
    shared_auth_models: bool


def _canonical_manifest(files: dict[str, str]) -> bytes:
    entries = {k: files[k] for k in sorted(files)}
    return json.dumps(entries, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def _parse_frontend_routes(app_tsx: str) -> tuple[str, ...]:
    match = re.search(r"const ROUTES: RouteSpec\[] = (\[.*?\]);\n", app_tsx, re.DOTALL)
    if not match:
        return ()
    routes = json.loads(match.group(1))
    ops: list[str] = []
    for route in routes:
        if route.get("requiresAuth"):
            ops.append(f"AUTH route:{route.get('path')}")
        for interaction in route.get("interactions") or []:
            m, p = interaction.get("method"), interaction.get("path")
            if m and p:
                ops.append(f"{str(m).upper()} {p}")
        for api_op in route.get("apiOperations") or []:
            m, p = api_op.get("method"), api_op.get("path")
            if m and p:
                sig = f"{str(m).upper()} {p}"
                if sig not in ops:
                    ops.append(sig)
    return tuple(sorted(set(ops)))


def _backend_ops(plan: CompilationPlan) -> tuple[str, ...]:
    ops: list[str] = []
    try:
        for route in declared_routes(plan):
            ops.append(f"{route.method.upper()} {route.path}")
    except UnsupportedSemanticsError:
        for api in plan.apis:
            if api.behavior:
                ops.append(f"{api.behavior.method.upper()} {api.behavior.path}")
    return tuple(sorted(set(ops)))


def compile_ordinary_candidate(
    *,
    workload_id: str,
    candidate_id: str,
    revision_fn: Callable[[], ISRRevision],
    compile_rust: bool = True,
) -> OrdinaryCompileResult:
    revision = revision_fn()
    plan = isr_to_plan(revision)
    frontend = ReactFrontendBackend().compile(plan)
    backend_py: GeneratedRepository | None = None
    backend_rs: GeneratedRepository | None = None
    py_err: str | None = None
    rs_err: str | None = None
    try:
        backend_py = PythonFastAPIBackend().compile(plan)
    except UnsupportedSemanticsError as exc:
        py_err = str(exc)
    if compile_rust:
        try:
            backend_rs = RustAxumBackend().compile(plan)
        except UnsupportedSemanticsError as exc:
            rs_err = str(exc)

    files = dict(frontend.files)
    if backend_py:
        files.update({f"backend/python/{k}": v for k, v in backend_py.files.items()})
    if backend_rs:
        files.update({f"backend/rust/{k}": v for k, v in backend_rs.files.items()})
    artifact_bytes = _canonical_manifest(files)
    digest = hashlib.sha256(artifact_bytes).hexdigest()

    entities = tuple(sorted({m.entity_name for m in plan.data_models}))
    requires_auth = any(
        r.behavior and r.behavior.requires_auth for r in plan.frontend_routes
    )
    shared = requires_auth and bool(plan.security) and backend_py is not None

    return OrdinaryCompileResult(
        workload_id=workload_id,
        candidate_id=candidate_id,
        revision_id=revision.revision_id,
        plan=plan,
        revision=revision,
        frontend=frontend,
        backend_python=backend_py,
        backend_rust=backend_rs,
        python_compile_error=py_err,
        rust_compile_error=rs_err,
        artifact_sha256=digest,
        artifact_manifest_digest=digest,
        artifact_bytes=artifact_bytes,
        frontend_operations=_parse_frontend_routes(frontend.files.get("src/App.tsx", "")),
        backend_operations=_backend_ops(plan) if backend_py else (),
        persistence_entities=entities,
        shared_auth_models=shared,
    )
