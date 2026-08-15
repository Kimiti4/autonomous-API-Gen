"""
Phase 11 — Documentation Compiler Base Contract
Compiles the ISR, Genome, and Intent into human-readable documentation, ADRs, and diagrams.

Constitutional Alignment:
- "Documentation should evolve alongside implementation... Documentation should never become stale."
- "Significant decisions should document: Context, Problem, Alternatives, Trade-offs, Benefits, Risks."
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, Optional

from constitutional_architecture.core.contracts.compiler import CompilerBackend
from constitutional_architecture.core.models.bundle import CompilationBundle
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import IntentModel
from constitutional_architecture.core.models.isr import UniversalISR


class DocumentationCompiler(CompilerBackend):
    @abstractmethod
    def compile(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        context: Dict[str, Any],
        intent: Optional[IntentModel] = None,
    ) -> CompilationBundle:
        pass
