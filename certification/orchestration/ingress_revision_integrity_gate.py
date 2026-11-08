"""R1-W03 revision integrity at W08 ingress surfaces (scoped — not universal ISR)."""

from __future__ import annotations

from certification.orchestration.workload_registry import get_workload_spec
from isr.core.revision import ISRRevision
from isr.core.revision_integrity import assert_revision_integrity_at_boundary

W08_W03_BOUNDARY_IDS: tuple[str, ...] = (
    "orch-api-full-stack",
    "orch-dashboard-full-stack",
    "orchestration-authority",
)


def assert_w08_ingress_revision_integrity(
    revision: ISRRevision,
    *,
    boundary_id: str,
) -> None:
    if boundary_id not in W08_W03_BOUNDARY_IDS:
        raise ValueError(f"w08-w03-boundary-unknown:{boundary_id}")
    assert_revision_integrity_at_boundary(revision)


def assert_workload_revision_integrity_at_ingress(workload_id: str) -> str:
    """Pre-flight W03 check before governed HTTP orchestration ingress."""
    spec = get_workload_spec(workload_id)
    revision = spec.revision_fn()
    assert_w08_ingress_revision_integrity(
        revision,
        boundary_id="orch-api-full-stack",
    )
    return revision.content_hash
