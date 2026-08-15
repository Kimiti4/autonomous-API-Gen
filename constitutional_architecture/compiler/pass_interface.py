from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.compiler.compiler_context import CompilerContext


@dataclass
class PassResult:
    success: bool
    description: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)


class CompilerPass(ABC):
    @property
    @abstractmethod
    def identifier(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    def dependencies(self) -> list[str]:
        return []

    @property
    def input_requirements(self) -> set[str]:
        return set()

    @property
    def output_guarantees(self) -> set[str]:
        return set()

    @abstractmethod
    def execute(self, ctx: CompilerContext) -> PassResult:
        ...
