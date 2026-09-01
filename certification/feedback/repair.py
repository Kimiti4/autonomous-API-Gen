"""Governed failure → learning → evolution orchestration (R2/D2, R4, D5 seam).

CRITICAL RULE: never repair generated code directly.  A failed trial is:
  immutable evidence
      → causal classification
        ├── LearningSignal → ContinuousLearningEngine  (ALWAYS for actionable)
        └── EvolutionPolicy → EvolutionCandidate (backend swap) ONLY when
              causally actionable AND eligible alternate backend exists.

Infrastructure/registry/port/provenance failures are LEARN-ONLY — they never
spawn an evolved workload candidate.

Execution of a candidate is a separate concern (the campaign runner submits it
through the normal compile/verify/deploy/test pipeline as a NEW trial).
"""
from __future__ import annotations

from dataclasses import dataclass

from certification.feedback.rule import (
    analyze_failure,
    FailureClassification,
)
from certification.feedback.candidate import EvolutionCandidate
from certification.feedback.policy import BackendSwapPolicy, EvolutionDecision

from learning.engine import ContinuousLearningEngine
from learning.models import LearningSignal, LearningSignalType, Severity


@dataclass(frozen=True)
class RepairFeedback:
    """The full, auditable outcome of analyzing a failed trial."""
    classification: FailureClassification
    signal: LearningSignal | None
    decision: EvolutionDecision
    candidate: EvolutionCandidate | None

    def as_record(self) -> dict:
        return {
            "classification": self.classification.as_record(),
            "decision": self.decision.as_record(),
            "candidate": self.candidate.lineage() if self.candidate else None,
        }


class GovernedRepair:
    """Consume a failed trial, learn from it, and (when justified) propose an
    evolved candidate.

    `learning_engine` may be None to run without the ContinuousLearningEngine
    store (the signal is still constructed).  `policy` defaults to the
    BackendSwapPolicy.  `eligible_backend_ids`/`attempted_backend_ids`/
    `supports_workload` supply the eligibility context for evolution.
    """

    def __init__(
        self,
        learning_engine: ContinuousLearningEngine | None = None,
        policy: BackendSwapPolicy | None = None,
    ) -> None:
        self.learning = learning_engine
        self.policy = policy or BackendSwapPolicy()

    # ------------------------------------------------------------------
    # D2 — learning consumption
    # ------------------------------------------------------------------

    def emit_learning_signal(
        self,
        *,
        trial_id: str,
        intent: str,
        backend: str,
        stage: str,
        detail: str,
        classification: FailureClassification | None = None,
    ) -> LearningSignal:
        """Construct a LearningSignal for a failed stage and route it into the
        Continuous Learning Engine when one is configured."""
        cls = classification or analyze_failure(stage=stage, failure_class="")
        signal = LearningSignal(
            source="campaign_b_evolution",
            subject_ref=f"{intent}/{backend}",
            signal_type=LearningSignalType.INCIDENT,
            severity=(
                Severity.HIGH
                if cls.feedback_domain in ("architecture", "security")
                else Severity.MEDIUM
            ),
            metric="certification_failure",
            value=1.0,
            unit="trial",
            message=(
                f"{stage} stage failed on {intent}/{backend} "
                f"(cause={cls.cause}, domain={cls.feedback_domain})"
            ),
            labels={
                "trial_id": trial_id,
                "intent_id": intent,
                "backend": backend,
                "stage": stage,
                "cause": cls.cause,
                "feedback_domain": cls.feedback_domain,
                "repair_eligible": str(cls.repair_eligible),
            },
            evidence_refs=[trial_id],
        )
        if self.learning is not None:
            emitted = self.learning.ingest_signal(signal)
            if emitted is not None:
                return emitted
        return signal

    # ------------------------------------------------------------------
    # R4 — governed evolution decision (candidate production, no execution)
    # ------------------------------------------------------------------

    def evaluate_failure(
        self,
        *,
        trial_id: str,
        intent: str,
        backend: str,
        stage: str,
        failure_class: str,
        detail: str,
        isr_hash: str,
        genome_hash: str,
        eligible_backend_ids: list[str],
        attempted_backend_ids: frozenset[str] | set[str] = frozenset(),
        supports_workload: set[str] | frozenset[str] | None = None,
    ) -> RepairFeedback:
        """Full pipeline for one failed stage: classify → learn → decide.

        Executes the causal classifier, emits the learning signal, asks the
        policy whether a backend candidate is justified, and — only when
        accepted — constructs the candidate.
        """
        cls = analyze_failure(
            stage=stage, failure_class=failure_class, detail=detail
        )

        signal = self.emit_learning_signal(
            trial_id=trial_id,
            intent=intent,
            backend=backend,
            stage=stage,
            detail=detail,
            classification=cls,
        )

        decision = self.policy.should_evolve(
            classification=cls,
            failed_backend_id=backend,
            eligible_backend_ids=eligible_backend_ids,
            attempted_backend_ids=attempted_backend_ids,
            supports_workload=supports_workload,
        )

        from certification.feedback.policy import make_candidate
        candidate = make_candidate(
            decision=decision,
            parent_trial_id=trial_id,
            intent_id=intent,
            isr_hash=isr_hash,
            genome_hash=genome_hash,
        )

        return RepairFeedback(
            classification=cls,
            signal=signal,
            decision=decision,
            candidate=candidate,
        )
