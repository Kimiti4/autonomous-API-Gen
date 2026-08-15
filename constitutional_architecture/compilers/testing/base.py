"""
Phase 14 — Test Compiler Base Contract
Compiles the Universal ISR and ArchitectureGenome into layered test suites
(unit, property-based, integration, security, contract, chaos).

Constitutional Alignment:
- "Prefer layered verification. Include: Unit tests, Integration tests,
  End-to-end tests, Property-based tests..."
- "Architectures should be designed to be inherently testable."
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, Optional

from constitutional_architecture.core.contracts.compiler import CompilerBackend
from constitutional_architecture.core.models.bundle import CompilationBundle
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import IntentModel
from constitutional_architecture.core.models.isr import UniversalISR


class TestCompiler(CompilerBackend):
    @abstractmethod
    def compile(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        context: Dict[str, Any],
        intent: Optional[IntentModel] = None,
    ) -> CompilationBundle:
        pass
