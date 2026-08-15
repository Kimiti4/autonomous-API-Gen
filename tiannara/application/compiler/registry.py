"""CompilerRegistry — capability-indexed registry of compiler backends.

Stores backends opaquely for later execution (Phase 16); Stage 2 itself
never invokes them. Declarations are passed explicitly at registration, so
existing backends need no modification. No protocol, no compile() here.
"""

from __future__ import annotations

from typing import Any

from tiannara.domain.models.backend_declaration import BackendCapabilityDeclaration


class RegistryError(ValueError):
    pass


class CompilerRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, Any] = {}
        self._declarations: dict[str, BackendCapabilityDeclaration] = {}

    def register(
        self, backend: Any, declaration: BackendCapabilityDeclaration
    ) -> BackendCapabilityDeclaration:
        backend_id = declaration.backend_id
        if backend_id in self._backends:
            raise RegistryError(f"backend already registered: {backend_id}")
        self._backends[backend_id] = backend
        self._declarations[backend_id] = declaration
        return declaration

    def backend(self, backend_id: str) -> Any:
        try:
            return self._backends[backend_id]
        except KeyError:
            raise RegistryError(f"unknown backend: {backend_id}") from None

    def declaration(self, backend_id: str) -> BackendCapabilityDeclaration:
        try:
            return self._declarations[backend_id]
        except KeyError:
            raise RegistryError(f"unknown backend: {backend_id}") from None

    def declarations(self) -> list[BackendCapabilityDeclaration]:
        return [self._declarations[k] for k in sorted(self._declarations)]

    def __contains__(self, backend_id: str) -> bool:
        return backend_id in self._backends

    def __len__(self) -> int:
        return len(self._backends)
