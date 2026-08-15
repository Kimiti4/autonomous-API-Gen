"""
Phase 12 — Operational Intelligence Compiler Base Contract
Compiles the operational sub-graph of the Universal ISR (SLODefinition,
TelemetryRequirement, OperationalPolicy nodes) into SLOs, alerting rules,
dashboards, telemetry pipelines, and the Semantic Runbook Model.

Constitutional Alignment:
- Observability is a subset of Operability: the platform must generate systems
  that are operable, diagnosable, and resilient from generation zero.
- "The Intermediate Software Representation (ISR) is the sole architectural
  source of truth" — the operational posture is an ISR Projection, never a
  parallel model.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, Optional

from constitutional_architecture.core.contracts.compiler import CompilerBackend
from constitutional_architecture.core.models.bundle import CompilationBundle
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.intent import IntentModel
from constitutional_architecture.core.models.isr import UniversalISR


class OperationalIntelligenceCompiler(CompilerBackend):
    @abstractmethod
    def compile(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        context: Dict[str, Any],
        intent: Optional[IntentModel] = None,
    ) -> CompilationBundle:
        pass
