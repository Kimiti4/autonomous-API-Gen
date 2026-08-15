from __future__ import annotations

from typing import Optional

from constitutional_architecture.compiler.backends.backend_interface import CompilerBackend


class BackendRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, CompilerBackend] = {}

    def register(self, backend: CompilerBackend) -> None:
        self._backends[backend.name.lower()] = backend

    def get(self, name: str) -> Optional[CompilerBackend]:
        return self._backends.get(name.lower())

    @property
    def all_names(self) -> list[str]:
        return list(self._backends.keys())

    @property
    def count(self) -> int:
        return len(self._backends)

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._backends
