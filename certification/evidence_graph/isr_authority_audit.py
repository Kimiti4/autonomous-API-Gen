"""ISR canonicality audit snapshot (CP063 P0) — findings only."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from isr.core.digest_verification import verify_revision_content_integrity
from isr.core.identity import compute_content_hash
from isr.core.revision import ISRRevision


class IsrRepresentationClass(str, Enum):
    AUTHORITATIVE_REVISION = "authoritative_revision"
    PROJECTION = "projection"
    ADAPTER_IMPORT = "adapter_import"
    DERIVED_PLAN = "derived_plan"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class IsrFamilyRow:
    family_id: str
    module_path: str
    representation_class: IsrRepresentationClass
    canonical_hash: bool
    notes: str


def isr_family_inventory() -> tuple[IsrFamilyRow, ...]:
    return (
        IsrFamilyRow(
            "isr-revision-v1",
            "isr.core.revision.ISRRevision",
            IsrRepresentationClass.AUTHORITATIVE_REVISION,
            True,
            "content_hash recomputed in ISRRevision.create",
        ),
        IsrFamilyRow(
            "constitutional-isr-model",
            "constitutional_architecture.isr.model",
            IsrRepresentationClass.ADAPTER_IMPORT,
            False,
            "Separate model; not interchangeable with isr.core without bridge",
        ),
        IsrFamilyRow(
            "reqgraph-projection",
            "reqgraph.adapters.isr_projection",
            IsrRepresentationClass.PROJECTION,
            False,
            "Requirement refs only; merge via merge_requirement_projection",
        ),
        IsrFamilyRow(
            "compilation-plan",
            "compiler.core.plan.CompilationPlan",
            IsrRepresentationClass.DERIVED_PLAN,
            False,
            "Lowering from ISRRevision; obligations may narrow",
        ),
        IsrFamilyRow(
            "synthesis-candidate",
            "reqgraph.synthesis.engineering_synthesizer",
            IsrRepresentationClass.AUTHORITATIVE_REVISION,
            True,
            "Output ISRRevision with provenance; separate lineage from human",
        ),
        IsrFamilyRow(
            "autonomous-api-implementation_ir",
            "autonomous-api.app.engine.implementation_ir",
            IsrRepresentationClass.UNVERIFIED,
            False,
            "Historical surface; bypass risk — orchestration inventory tracks",
        ),
    )


@dataclass(frozen=True)
class IsrHashAudit:
    revision_id: str
    stored_hash: str
    recomputed_hash: str
    matches: bool


def audit_isr_hash(revision: ISRRevision) -> IsrHashAudit:
    recomputed = compute_content_hash(revision.schema_version, revision.graph)
    matches = recomputed == revision.content_hash
    if matches:
        verify_revision_content_integrity(revision)
    return IsrHashAudit(
        revision_id=revision.revision_id,
        stored_hash=revision.content_hash,
        recomputed_hash=recomputed,
        matches=matches,
    )
