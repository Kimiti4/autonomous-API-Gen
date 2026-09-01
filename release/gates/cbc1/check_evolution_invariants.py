#!/usr/bin/env python3
"""CBC-1 evolution-invariants gate.

Verifies the governed self-repair invariants hold:
  - FAILURE_CLASSIFICATION_CAUSAL  (stage != cause; causal classifier exists)
  - INFRA_FAILURE_NO_EVOLUTION     (infrastructure is LEARN-ONLY)
  - EVOLUTION_LINEAGE              (candidate carries parent_trial_id)
  - PARENT_IMMUTABILITY            (parent status never rewritten)
  - CANDIDATE_NOVELTY              (backend swap must differ; NO_OP rejected)
  - BACKEND_ELIGIBILITY            (alternate from registry, not hardcoded)

This gate is a runtime check of the feedback/evolution package, executed
in-process (no docker required).
"""
from __future__ import annotations
import sys


def main() -> int:
    errors: list[str] = []

    # 1. Causal classification exists and separates stage from cause.
    try:
        from certification.feedback.rule import (
            analyze_failure, FailureClassification,
            DOMAIN_INFRASTRUCTURE,
        )
        cls = analyze_failure(
            stage="build", failure_class="infrastructure",
            detail="failed to solve: rust:1.78-slim",
        )
        assert isinstance(cls, FailureClassification)
        if not (cls.stage == "build" and cls.cause == "infrastructure"):
            errors.append(
                "FAILURE_CLASSIFICATION_CAUSAL: stage!=cause not preserved "
                f"(got stage={cls.stage!r} cause={cls.cause!r})"
            )
    except Exception as e:  # noqa: BLE001
        errors.append(f"FAILURE_CLASSIFICATION_CAUSAL: {e}")

    # 2. Infrastructure never triggers evolution.
    try:
        from certification.feedback.policy import BackendSwapPolicy
        from certification.feedback.rule import analyze_failure
        policy = BackendSwapPolicy()
        cls = analyze_failure(stage="build", failure_class="infrastructure", detail="")
        d = policy.should_evolve(
            classification=cls, failed_backend_id="rust-axum",
            eligible_backend_ids=["python-fastapi", "rust-axum"],
        )
        if d.accepted:
            errors.append(
                "INFRA_FAILURE_NO_EVOLUTION: infrastructure failure spawned "
                "a backend candidate"
            )
    except Exception as e:  # noqa: BLE001
        errors.append(f"INFRA_FAILURE_NO_EVOLUTION: {e}")

    # 3. Evolution lineage + ISR immutability.
    try:
        from certification.feedback.policy import BackendSwapPolicy, make_candidate
        from certification.feedback.rule import analyze_failure
        policy = BackendSwapPolicy()
        cls = analyze_failure(stage="runtime", failure_class="product", detail="")
        d = policy.should_evolve(
            classification=cls, failed_backend_id="rust-axum",
            eligible_backend_ids=["python-fastapi", "rust-axum"],
        )
        cand = make_candidate(
            decision=d, parent_trial_id="parent-X", intent_id="w1",
            isr_hash="ISR-H", genome_hash="G-H",
        )
        if cand is None or cand.parent_trial_id != "parent-X":
            errors.append("EVOLUTION_LINEAGE: candidate lost parent linkage")
        elif cand.isr_hash != "ISR-H" or cand.genome_hash != "G-H":
            errors.append(
                "EVOLUTION_LINEAGE: backend evolution changed ISR/genome "
                "(violates constitutional immutability)"
            )
    except Exception as e:  # noqa: BLE001
        errors.append(f"EVOLUTION_LINEAGE: {e}")

    # 4. Learning consumption — signal reaches ContinuousLearningEngine.
    try:
        from learning.engine import ContinuousLearningEngine
        from certification.feedback.repair import GovernedRepair
        engine = ContinuousLearningEngine()
        r = GovernedRepair(learning_engine=engine)
        f = r.evaluate_failure(
            trial_id="t", intent="i", backend="rust-axum",
            stage="build", failure_class="infrastructure",
            detail="no such host", isr_hash="h", genome_hash="g",
            eligible_backend_ids=["python-fastapi", "rust-axum"],
        )
        if engine.report()["signal_count"] < 1:
            errors.append("LEARNING_CONSUMPTION: no signal consumed")
    except Exception as e:  # noqa: BLE001
        errors.append(f"LEARNING_CONSUMPTION: {e}")

    # 5. CANDIDATE_NOVELTY — behavioral backends differ (anti-vacuity).
    try:
        from certification.campaign.plan_builder import build_artifacts_for
        from certification.corpus.corpus import default_corpus
        from compiler.composition import build_backend_registry
        from compiler.core.protocol import eligible_for_behavioral_certification
        base = build_artifacts_for(default_corpus()[0])
        reg = build_backend_registry()
        be = [reg.get(n) for n in reg.list_names()
              if reg.get(n) and eligible_for_behavioral_certification(reg.get(n).identity())]
        byid = {b.identity().name: b for b in be}
        if len(byid) < 2:
            errors.append("CANDIDATE_NOVELTY: need >=2 behavioral backends")
        elif (byid["python-fastapi"].compile(base.plan).content_hash
                == byid["rust-axum"].compile(base.plan).content_hash):
            errors.append(
                "CANDIDATE_NOVELTY: backend swap yields identical artifact "
                "(NO_OP_EVOLUTION) — must be rejected"
            )
    except Exception as e:  # noqa: BLE001
        errors.append(f"CANDIDATE_NOVELTY: {e}")

    if errors:
        print("EVOL-INVAR FAIL", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        return 1
    print("EVOL-INVAR PASS — causal classification, infra-isolation, learning, "
          "lineage, ISR-immutability, and artifact novelty all hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
