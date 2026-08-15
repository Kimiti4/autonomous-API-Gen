"""IntelligenceProvider port — the single boundary through which all
reasoning backends serve the platform.

Deterministic compilers, algorithmic solvers, local models, and remote
models all implement this protocol. The core never depends on one class,
one vendor, or one topology.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models.intelligence import (
    CapabilityDeclaration,
    IntelligenceResult,
    IntelligenceTask,
)


@runtime_checkable
class IntelligenceProvider(Protocol):
    @property
    def declaration(self) -> CapabilityDeclaration: ...

    def complete(self, task: IntelligenceTask) -> IntelligenceResult:
        """Serve the task or raise LanguageModelError. Never fabricate."""
        ...
