"""Plan-to-ISR immutable binding record (ADR-R1-04, R1-W04)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from compiler.core.plan import CompilationPlan
from compiler.core.plan_canonicalization import canonical_bytes_f04
from isr.core.canonicalization_registry import F01_ISR_REVISION, F04_COMPILATION_PLAN
from isr.core.revision import ISRRevision

_SHA256_HEX_RE = re.compile(r"^[a-f0-9]{64}$")

COMPILER_ID = "compiler.core.lowering"
COMPILER_VERSION = "1.0.0"
DEFAULT_BACKEND_ID = "python-fastapi"
DEFAULT_BACKEND_CAPABILITY_REF = "compiler.backends.capability_manifest.v1"


class PlanBindingError(ValueError):
    """Fail-closed plan binding violation."""


@dataclass(frozen=True, slots=True)
class PlanBindingRecord:
    """Immutable binding between one ISR revision and one lowered plan."""

    isr_family_id: str
    isr_revision_id: str
    isr_content_digest: str
    isr_schema_version: str
    canonicalization_id: str
    canonicalization_version: str
    plan_digest: str
    plan_revision: str
    plan_id: str
    compiler_id: str
    compiler_version: str
    backend_id: str
    backend_capability_ref: str
    transformation_lineage_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not _SHA256_HEX_RE.match(self.isr_content_digest):
            raise PlanBindingError("isr_content_digest must be 64-char sha256 hex")
        if not _SHA256_HEX_RE.match(self.plan_digest):
            raise PlanBindingError("plan_digest must be 64-char sha256 hex")


def compute_plan_digest(plan: CompilationPlan) -> str:
    """F-04 plan digest for execution-time binding."""
    return hashlib.sha256(canonical_bytes_f04(plan)).hexdigest()


def build_plan_binding_record(
    revision: ISRRevision,
    plan: CompilationPlan,
    *,
    backend_id: str = DEFAULT_BACKEND_ID,
    backend_capability_ref: str = DEFAULT_BACKEND_CAPABILITY_REF,
    transformation_lineage_refs: tuple[str, ...] = (),
) -> PlanBindingRecord:
    """Materialize binding from a verified revision and freshly lowered plan."""
    return PlanBindingRecord(
        isr_family_id=F01_ISR_REVISION.isr_family_id,
        isr_revision_id=revision.revision_id,
        isr_content_digest=revision.content_hash,
        isr_schema_version=revision.schema_version,
        canonicalization_id=F04_COMPILATION_PLAN.canonicalization_id,
        canonicalization_version=F04_COMPILATION_PLAN.canonicalization_version,
        plan_digest=compute_plan_digest(plan),
        plan_revision=plan.plan_id,
        plan_id=plan.plan_id,
        compiler_id=COMPILER_ID,
        compiler_version=COMPILER_VERSION,
        backend_id=backend_id,
        backend_capability_ref=backend_capability_ref,
        transformation_lineage_refs=transformation_lineage_refs,
    )


def verify_plan_binding_record_matches(
    revision: ISRRevision,
    plan: CompilationPlan,
    record: PlanBindingRecord,
) -> None:
    """Reject stale, superseded, or tampered bindings."""
    fresh = build_plan_binding_record(revision, plan)
    mismatches: list[str] = []
    if record.isr_revision_id != revision.revision_id:
        mismatches.append("isr_revision_id")
    if record.isr_content_digest != revision.content_hash:
        mismatches.append("isr_content_digest")
    if record.plan_digest != fresh.plan_digest:
        mismatches.append("plan_digest")
    if record.plan_id != plan.plan_id:
        mismatches.append("plan_id")
    if record.isr_schema_version != revision.schema_version:
        mismatches.append("isr_schema_version")
    if mismatches:
        raise PlanBindingError(
            f"plan-binding-stale-or-tampered:{','.join(mismatches)}"
        )
