"""BackendRegistry — simplified registry for the core package."""
from __future__ import annotations
from compiler.core.protocol import CompilerBackend


class BackendNotFoundError(Exception):
    pass


class BackendRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, CompilerBackend] = {}

    def register(self, backend: CompilerBackend) -> None:
        self._backends[backend.name] = backend

    def get(self, name: str) -> CompilerBackend:
        if name not in self._backends:
            raise BackendNotFoundError(f"Backend not found: {name}")
        return self._backends[name]

    def list_names(self) -> list[str]:
        return list(self._backends.keys())
