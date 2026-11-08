"""CP067 — read-only Universal ISR-family canonicality and bridge audit."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from certification.evidence_graph.isr_authority_audit import (
    IsrFamilyRow,
    audit_isr_hash,
    isr_family_inventory,
)
from certification.payroll.candidate_fixture import payroll_isr_revision
from certification.synthesis.pipeline import synthesize_for_workload
from isr.core.revision import ISRRevision


class BridgeSemantics(str, Enum):
    LOSSLESS = "LOSSLESS"
    LOSSY = "LOSSY"
    UNSUPPORTED = "UNSUPPORTED"
    BYPASS_RISK = "BYPASS_RISK"
    UNKNOWN = "UNKNOWN"


class GapSeverity(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    DOCUMENTED = "DOCUMENTED"


@dataclass(frozen=True)
class IsrBridgeRow:
    bridge_id: str
    source_family: str
    target_family: str
    entry_point: str
    semantics: BridgeSemantics
    hash_preserved: bool
    obligation_axes: tuple[str, ...]
    notes: str


@dataclass(frozen=True)
class IsrCanonicalityGap:
    gap_id: str
    severity: GapSeverity
    families: tuple[str, ...]
    finding: str
    remediation_status: str  # read-only register: OPEN | DEFERRED | VERIFIED_SLICE


def isr_bridge_inventory() -> tuple[IsrBridgeRow, ...]:
    return (
        IsrBridgeRow(
            "reqgraph-to-isr-projection",
            "reqgraph.core.graph.RequirementGraph",
            "isr.core.graph.ISRGraph (requirement_ref nodes)",
            "reqgraph.adapters.isr_projection.project_requirement_graph",
            BridgeSemantics.LOSSLESS,
            True,
            ("requirement refs", "requirement edges"),
            "Refs only; does not materialize SERVICE/API/SECURITY",
        ),
        IsrBridgeRow(
            "merge-requirement-projection",
            "isr.core.graph.ISRGraph + RequirementGraph",
            "isr.core.graph.ISRGraph",
            "reqgraph.adapters.isr_projection.merge_requirement_projection",
            BridgeSemantics.LOSSLESS,
            True,
            ("collision fail-closed",),
            "Human workload fixtures use this path",
        ),
        IsrBridgeRow(
            "synthesis-to-isr-revision",
            "reqgraph + TOR + reviewer",
            "isr.core.revision.ISRRevision",
            "reqgraph.synthesis.engineering_synthesizer",
            BridgeSemantics.LOSSY,
            True,
            ("obligations", "operation ids", "security binding", "validation"),
            "TOR-hash operation_ids; separate digest from human fixture",
        ),
        IsrBridgeRow(
            "isr-to-compilation-plan",
            "isr.core.revision.ISRRevision",
            "compiler.core.plan.CompilationPlan",
            "compiler.core.lowering.isr_to_plan",
            BridgeSemantics.LOSSY,
            False,
            ("authorization", "effects", "invariants", "frontend", "data"),
            "Lowering may narrow; backend capability gates separate",
        ),
        IsrBridgeRow(
            "plan-to-canonical-contract",
            "compiler.core.plan.CompilationPlan",
            "compiler.core.canonical_api_contract",
            "compiler.core.canonical_api_contract.build_canonical_api_contract",
            BridgeSemantics.LOSSY,
            False,
            ("operation identity", "auth policy refs"),
            "Separate contract_digest; not interchangeable with ISR hash",
        ),
        IsrBridgeRow(
            "constitutional-model-isr",
            "constitutional_architecture.isr.model.ISR",
            "constitutional_architecture.isr.model.ISR",
            "constitutional_architecture.isr.serialization.ISRSerializer",
            BridgeSemantics.LOSSLESS,
            True,
            ("structural model",),
            "Distinct serializer + ContentHasher; NOT isr.core hash",
        ),
        IsrBridgeRow(
            "implementation-ir",
            "API / frontend sketches",
            "autonomous-api.app.engine.implementation_ir",
            "autonomous-api.app.engine.source_bound_full_stack",
            BridgeSemantics.BYPASS_RISK,
            False,
            ("auth", "effects", "obligations"),
            "Not content-addressed with ISRRevision; orchestration inventory flags risk",
        ),
        IsrBridgeRow(
            "human-vs-synth-payroll",
            "payroll human fixture",
            "payroll synthesized ISR",
            "(no automated bridge)",
            BridgeSemantics.UNSUPPORTED,
            False,
            ("operation_id", "oracle binding", "requirement naming"),
            "CP066 E: must not conflate evidence",
        ),
    )


def isr_canonicality_gap_register() -> tuple[IsrCanonicalityGap, ...]:
    return (
        IsrCanonicalityGap(
            "dual-hash-algorithms",
            GapSeverity.P0,
            ("isr.core.revision.ISRRevision", "constitutional_architecture.isr.model.ISR"),
            "Two independent SHA-256 canonicalizers (compute_content_hash vs ContentHasher.hash_isr); "
            "matching digests do NOT prove cross-family equivalence.",
            "OPEN",
        ),
        IsrCanonicalityGap(
            "lowering-without-roundtrip",
            GapSeverity.P0,
            ("isr.core.revision", "compiler.core.plan"),
            "No verified plan→ISR round-trip; obligation loss detectable only via gates/tests.",
            "OPEN",
        ),
        IsrCanonicalityGap(
            "stored-hash-mutation",
            GapSeverity.P1,
            ("isr.core.revision.ISRRevision"),
            "content_hash stored on model; ISRRevision.create recomputes — but manual construct "
            "could bypass create() (Pydantic allows invalid pairing if constructed directly).",
            "OPEN",
        ),
        IsrCanonicalityGap(
            "synthesis-operation-identity",
            GapSeverity.P1,
            ("human fixture", "synthesized payroll"),
            "Same TOR requirements, different operation_id vocabulary (payroll.submit vs tor.<hash>).",
            "DOCUMENTED",
        ),
        IsrCanonicalityGap(
            "graph-evidence-slice",
            GapSeverity.P2,
            ("certification.evidence_graph"),
            "CP063 graph provenance verified for isr.core.revision.content_hash slice only.",
            "VERIFIED_SLICE",
        ),
        IsrCanonicalityGap(
            "implementation-ir-bypass",
            GapSeverity.P0,
            ("autonomous-api ImplementationIR", "isr.core.revision"),
            "Parallel compile path without governed ISRRevision digest binding.",
            "OPEN",
        ),
    )


@dataclass(frozen=True)
class Cp067AuditReport:
    families: tuple[IsrFamilyRow, ...]
    bridges: tuple[IsrBridgeRow, ...]
    gaps: tuple[IsrCanonicalityGap, ...]
    payroll_human_hash_ok: bool
    payroll_synth_hash_ok: bool
    payroll_human_synth_different: bool


def run_cp067_readonly_audit() -> Cp067AuditReport:
    human = audit_isr_hash(payroll_isr_revision())
    _, synth_rev, _ = synthesize_for_workload("payroll")
    synth = audit_isr_hash(synth_rev)
    return Cp067AuditReport(
        families=isr_family_inventory(),
        bridges=isr_bridge_inventory(),
        gaps=isr_canonicality_gap_register(),
        payroll_human_hash_ok=human.matches,
        payroll_synth_hash_ok=synth.matches,
        payroll_human_synth_different=human.stored_hash != synth.stored_hash,
    )


def recompute_payroll_hash_slice() -> tuple[IsrHashAuditPair, ...]:
    """Explicit hash recomputation evidence for payroll ISR family slice."""
    from certification.evidence_graph.isr_authority_audit import IsrHashAudit

    rows: list[tuple[str, IsrHashAudit]] = []
    for label, rev in (
        ("human-payroll", payroll_isr_revision()),
        ("synth-payroll", synthesize_for_workload("payroll")[1]),
    ):
        rows.append((label, audit_isr_hash(rev)))
    return tuple(
        IsrHashAuditPair(
            label=label,
            revision_id=a.revision_id,
            stored=a.stored_hash,
            recomputed=a.recomputed_hash,
            matches=a.matches,
        )
        for label, a in rows
    )


@dataclass(frozen=True)
class IsrHashAuditPair:
    label: str
    revision_id: str
    stored: str
    recomputed: str
    matches: bool
