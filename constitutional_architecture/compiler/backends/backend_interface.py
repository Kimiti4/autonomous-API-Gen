from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.compiler.quality.diagnostics import Diagnostic


@dataclass
class BackendResult:
    artifacts: list[Any] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)


class CompilerBackend(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def validate(self, bir: Any) -> list[Diagnostic]:
        ...

    @abstractmethod
    def bind_capabilities(self, capability_contracts: dict[str, Any]) -> list[Any]:
        ...

    @abstractmethod
    def compile(self, bir: Any, bindings: list[Any]) -> BackendResult:
        ...

    @abstractmethod
    def report_unsupported(self, bir: Any) -> list[str]:
        ...
