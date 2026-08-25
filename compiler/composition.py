"""compiler composition root — reference wiring of backend registry (ADR-012)."""
from __future__ import annotations
from compiler.core.registry import BackendRegistry
from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend


def build_backend_registry() -> BackendRegistry:
    r = BackendRegistry()
    r.register(PythonFastAPIBackend())
    r.register(RustAxumBackend())
    return r
