"""Independent execution (D5) + novelty/anti-vacuity (D6) for evolved
candidates.

The candidate is a NEW trial run through the NORMAL pipeline — the same
ISR-derived plan, but compiled/executed with the alternate eligible backend.
There is no "repair" execution path and no direct generated-code patching.

Anti-vacuity: a backend swap is only accepted if the two backends actually
produce a DIFFERENT compiled artifact for the workload.  If they are identical
the candidate is rejected (NO_OP_EVOLUTION) — metadata drift is not evolution.
"""
from __future__ import annotations

from dataclasses import dataclass

from certification.feedback.candidate import EvolutionCandidate

NO_OP_EVOLUTION = "NO_OP_EVOLUTION"


@dataclass(frozen=True)
class BackendArtifactCheck:
    distinct: bool
    failed_backend_id: str
    alternate_backend_id: str
    parent_artifact_hash: str
    candidate_artifact_hash: str

    @property
    def reason(self) -> str:
        if not self.distinct:
            return NO_OP_EVOLUTION
        return "artifacts differ (real compilation novelty)"


def prepare_evolved_trial(
    *,
    candidate: EvolutionCandidate,
    runner,
    base_artifacts,
    backend_map: dict,
    failed_backend_id: str,
    supports_workload: set[str] | frozenset[str] | None = None,
) -> tuple[BackendArtifactCheck, object | None]:
    """Resolve the alternate backend and validate novelty, returning the check
    and the alternate backend object (or None to reject).

    `backend_map` maps backend_id -> backend object (from the registry).
    `runner` is the CampaignBRunner with `run_trial` (normal pipeline).
    """
    alternate = backend_map.get(candidate.backend_id)
    if alternate is None:
        check = BackendArtifactCheck(
            distinct=False, failed_backend_id=failed_backend_id,
            alternate_backend_id=candidate.backend_id,
            parent_artifact_hash="", candidate_artifact_hash="",
        )
        return check, None

    # Compile the same ISR-derived plan under both backends to prove novelty.
    parent_artifact = backend_map[failed_backend_id].compile(base_artifacts.plan)
    candidate_artifact = alternate.compile(base_artifacts.plan)

    distinct = (
        parent_artifact.content_hash != candidate_artifact.content_hash
    )
    check = BackendArtifactCheck(
        distinct=distinct,
        failed_backend_id=failed_backend_id,
        alternate_backend_id=candidate.backend_id,
        parent_artifact_hash=parent_artifact.content_hash,
        candidate_artifact_hash=candidate_artifact.content_hash,
    )
    if not distinct:
        # NO_OP_EVOLUTION — do not manufacture an "evolved" trial.
        return check, None

    return check, alternate


def run_evolved_trial(
    *,
    runner,
    candidate: EvolutionCandidate,
    base_artifacts,
    alternate,
    workload,
    supports_workload: set[str] | frozenset[str] | None = None,
    failure_label: str = "",
) -> object:
    """Execute a candidate through the NORMAL pipeline as a NEW independent
    trial.  Returns the Trial (never mutates the parent)."""
    return runner.run_trial(
        intent=workload.intent,
        category=getattr(workload, "category").value,
        novelty_class="template",
        plan=base_artifacts.plan,
        revision=base_artifacts.revision,
        backend=alternate,
        corpus_hash="",
        requirement_graph_hash=base_artifacts.requirement_graph_hash,
        genome_hash=base_artifacts.genome_hash,
        workload=workload,
        artifacts=base_artifacts,
        origin="evolved",
        parent_trial_id=candidate.parent_trial_id,
    )
