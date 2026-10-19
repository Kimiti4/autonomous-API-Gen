"""Fail-closed payroll proving-case readiness assessment.

This is not a substitute for Campaign A's evidence ledger. It reports gaps
that must be closed before a payroll candidate can enter or pass certification.
"""
from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field

from compiler.core.capabilities import (
    BackendCapabilities,
    SemanticFeature,
    required_features,
    required_frontend_features,
)
from compiler.core.plan import CompilationPlan
from isr.core.graph import EdgeType, ISRGraph, NodeType
from reqgraph.core.graph import RequirementGraph


class BackendGap(BaseModel):
    model_config = ConfigDict(frozen=True)
    backend_id: str
    unsupported_features: tuple[str, ...] = ()


class PayrollReadinessReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: str = "NOT_CERTIFIED"
    requirement_count: int = Field(ge=0)
    mapped_requirement_count: int = Field(ge=0)
    unmapped_requirement_ids: tuple[str, ...] = ()
    backend_gaps: tuple[BackendGap, ...] = ()
    frontend_gaps: tuple[str, ...] = ()
    statutory_gaps: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()


def assess_payroll_readiness(
    requirements: RequirementGraph,
    isr: ISRGraph,
    plan: CompilationPlan,
    backend_capabilities: Iterable[BackendCapabilities],
    frontend_capabilities: BackendCapabilities,
    *,
    backend_runtime_evidence_ref: str | None = None,
    frontend_build_evidence_ref: str | None = None,
    statutory_authority_evidence_ref: str | None = None,
) -> PayrollReadinessReport:
    """Return a readiness report; never treat missing proof as a pass."""
    requirement_count = len(requirements.nodes)
    requirement_ref_nodes = {
        f"requirement_ref:{requirement_id}": requirement_id
        for requirement_id in requirements.nodes
    }
    satisfied_targets = {
        edge.target_id
        for edge in isr.edges.values()
        if edge.type == EdgeType.SATISFIES
        and edge.source_id in isr.nodes
        and isr.nodes[edge.source_id].type == NodeType.CAPABILITY
    }
    unmapped = tuple(sorted(
        requirement_id for node_id, requirement_id in requirement_ref_nodes.items()
        if node_id not in isr.nodes or node_id not in satisfied_targets
    ))
    mapped = requirement_count - len(unmapped)

    needed = required_features(plan)
    backend_gaps = []
    for capabilities in backend_capabilities:
        unsupported = tuple(sorted(
            feature.value for feature in needed - capabilities.supported_features
        ))
        if unsupported:
            backend_gaps.append(BackendGap(
                backend_id=capabilities.backend_id,
                unsupported_features=unsupported,
            ))

    frontend_needed = required_frontend_features(plan)
    frontend_unsupported = tuple(sorted(
        feature.value for feature in frontend_needed - frontend_capabilities.supported_features
    ))

    statutory_requirements = [
        node for node in requirements.nodes.values()
        if any(term in node.statement.lower() for term in ("statutory", "paye", "nssf", "shif", "tax deduction"))
    ]
    statutory_implemented = any(
        service.behavior is not None and any(
            any(term in (rule.rule_id + " " + rule.description).lower()
                for term in ("paye", "nssf", "shif", "statutory", "tax band", "tax table"))
            for rule in service.behavior.rules
        )
        for service in plan.services
    )
    statutory_gaps = []
    if statutory_requirements and not statutory_implemented:
        statutory_gaps.append(
            "No ISR-derived statutory tax/deduction rule is present; payroll statutory calculations are not implemented."
        )
    if statutory_requirements and not statutory_authority_evidence_ref:
        statutory_gaps.append(
            "No approved, versioned statutory authority/rate-table evidence reference was supplied."
        )

    evidence_gaps = []
    if not backend_runtime_evidence_ref:
        evidence_gaps.append("No independent generated-backend runtime evidence reference was supplied.")
    if not frontend_build_evidence_ref:
        evidence_gaps.append("No generated-frontend build and interaction evidence reference was supplied.")

    blockers = []
    if unmapped:
        blockers.append(f"{len(unmapped)} requirement(s) lack an explicit ISR capability-to-requirement SATISFIES mapping.")
    if backend_gaps:
        blockers.extend(
            f"Backend {gap.backend_id} does not support required semantics: {', '.join(gap.unsupported_features)}."
            for gap in backend_gaps
        )
    if frontend_unsupported:
        blockers.append(
            f"Frontend backend {frontend_capabilities.backend_id} does not support: {', '.join(frontend_unsupported)}."
        )
    blockers.extend(statutory_gaps)
    blockers.extend(evidence_gaps)

    return PayrollReadinessReport(
        status="NOT_CERTIFIED" if blockers else "READY_FOR_CAMPAIGN",
        requirement_count=requirement_count,
        mapped_requirement_count=mapped,
        unmapped_requirement_ids=unmapped,
        backend_gaps=tuple(backend_gaps),
        frontend_gaps=frontend_unsupported,
        statutory_gaps=tuple(statutory_gaps),
        evidence_gaps=tuple(evidence_gaps),
        blockers=tuple(blockers),
    )
