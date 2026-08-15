from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from pydantic import BaseModel

from constitutional_architecture.core.models.bundle import CompilationBundle
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.isr import UniversalISR


class CompilationArtifact(BaseModel):
    backend_name: str
    target_profile: str
    files: Dict[str, str]
    metadata: Dict[str, Any]


class CompilerBackend(ABC):
    @abstractmethod
    def compile(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        context: Dict[str, Any],
    ) -> CompilationBundle:
        pass
