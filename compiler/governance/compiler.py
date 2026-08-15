"""
Governed compiler wrapper.
"""

from __future__ import annotations

from typing import Optional

from ..errors import CompilerError
from ..models import CompilationRequest, CompilationResult
from .enforcer import CompilerGovernanceEnforcer
from .models import CompilationGateDecision


class CompilationGovernanceError(CompilerError):
    """Raised when governance blocks compilation."""

    def __init__(
        self,
        message: str,
        gate: CompilationGateDecision,
    ) -> None:
        super().__init__(message)
        self.gate = gate


class GovernedCompiler:
    """Wraps a compiler kernel with production governance."""

    def __init__(
        self,
        inner,
        enforcer: CompilerGovernanceEnforcer,
    ) -> None:
        self._inner = inner
        self._enforcer = enforcer

        self.registry = inner.registry

    def compile(
        self,
        request: CompilationRequest,
    ) -> CompilationResult:
        gate = self._enforcer.evaluate_compilation(request)

        if not gate.allowed:
            raise CompilationGovernanceError(gate.reason, gate)

        return self._inner.compile(request)

    def get_job(self, job_id: str) -> Optional[CompilationResult]:
        return self._inner.get_job(job_id)
