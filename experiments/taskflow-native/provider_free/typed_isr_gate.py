"""TaskFlow-only guarded transition from a verified graph to typed ISR.

Callers must resolve all compiler-consumed mandatory semantics first. The
resolution gate executes before the builder callback, so unresolved records
cannot trigger SystemModel construction. This is a transition guard for the
native TaskFlow path; the production compiler/backend selector must invoke the
same gate at its own entry boundary before this path is considered complete.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.domain.models.semantic_resolution import SemanticResolutionRecord
from taskflow_semantic_contract import require_taskflow_semantics
from tiannara.domain.models.system_model import SystemModel
from tiannara.domain.models.requirement_graph import RequirementGraph


T = TypeVar("T", bound=SystemModel)


def build_taskflow_typed_isr(
    *,
    graph: RequirementGraph,
    resolutions: SemanticResolutionRecord,
    build_system_model: Callable[[], T],
    system_id: str,
    lineage: list[str] | None = None,
) -> IntermediateSoftwareRepresentation:
    """Gate semantic resolution before invoking any SystemModel builder."""
    require_taskflow_semantics(graph, resolutions)
    model = build_system_model()
    if not isinstance(model, SystemModel):
        raise TypeError("build_system_model must return a validated SystemModel")
    return IntermediateSoftwareRepresentation.from_system_model(
        system_id=system_id,
        model=model,
        lineage=lineage,
    )
