from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from constitutional_architecture.core.models.bundle import CompilationBundle
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.isr import UniversalISR


class CompilerBackend(ABC):
    @abstractmethod
    def compile(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        context: Dict[str, Any],
    ) -> CompilationBundle:
        pass
