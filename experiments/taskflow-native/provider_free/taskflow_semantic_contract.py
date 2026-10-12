"""Compatibility exports for the compiler-owned TaskFlow semantic contract.

The domain module is the single source of truth. This experiment-level module
exists for older imports only; it must not duplicate or weaken the field set.
"""
from tiannara.domain.models.semantic_resolution import (
    TASKFLOW_MANDATORY_FIELDS,
    ResolutionKind,
    SemanticResolution,
    SemanticResolutionRecord,
    build_initial_resolution_record,
    require_taskflow_semantics,
)

__all__ = [
    "TASKFLOW_MANDATORY_FIELDS",
    "ResolutionKind",
    "SemanticResolution",
    "SemanticResolutionRecord",
    "build_initial_resolution_record",
    "require_taskflow_semantics",
]
