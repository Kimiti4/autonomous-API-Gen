"""Capability-driven meta-compilation seam (Cap-D, D2).

Meta-compilers import from a single, stable location; they never branch on
backend identifiers. The backend-coupling guard
(tiannara.domain.governance.backend_coupling_*) forbids backend-id selection
logic beneath META_COMPILER_ROOTS.
"""

from .capability_stages import StageRequirement, plan_stages

__all__ = ["StageRequirement", "plan_stages"]
