from __future__ import annotations

from typing import Optional

from constitutional_architecture.compiler.backends.backend_interface import CompilerBackend
from constitutional_architecture.compiler.backends.backend_registry import BackendRegistry
from constitutional_architecture.compiler.compilation_config import CompilationConfig


class BackendSelector:
    def __init__(self, registry: BackendRegistry) -> None:
        self._registry = registry

    def select(self, config: CompilationConfig) -> list[CompilerBackend]:
        backends: list[CompilerBackend] = []
        for name in config.target_backends:
            backend = self._registry.get(name)
            if backend is not None:
                backends.append(backend)
        return backends

    def validate_selection(self, config: CompilationConfig) -> list[str]:
        missing: list[str] = []
        for name in config.target_backends:
            if name.lower() not in self._registry:
                missing.append(name)
        return missing
