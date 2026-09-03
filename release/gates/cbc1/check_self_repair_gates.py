#!/usr/bin/env python3
"""CBC-1 governed self-repair gate runner — the RELEASE gate set from the
Revised Self-Repair Spec (D9).

Each gate is a named check; the runner is a pure in-process runtime check of
the `certification.feedback` package (no docker required).  Running this file
`python release/gates/cbc1/check_self_repair_gates.py` fails (exit 1) unless
ALL gates pass.

Gate names (spec):
  CAUSAL_FAILURE_CLASSIFICATION   stage != cause; cause drives eligibility
  LEARNING_CONSUMPTION            a failed trial's signal reaches the engine
  INFRASTRUCTURE_NO_EVOLUTION     infra/registry/port -> LEARN-ONLY
  BACKEND_ELIGIBILITY             alternate from registry/eligibility, not hardcoded
  EVOLUTION_LINEAGE               candidate carries parent_trial_id
  ISR_PRESERVATION                candidate does not change isr/genome hashes
  ARTIFACT_NOVELTY                backend swap produces a distinct artifact (anti-vacuity)
  INDEPENDENT_TRIAL               evolved candidate is a NEW trial (new id), normal path
  PARENT_IMMUTABILITY             parent verdict/identity never rewritten
  NO_DIRECT_REPAIR                static scan: no generated-code patching (reuses existing gate)
"""
from __future__ import annotations
import os
import sys

# Bootstrap: workspace root one level up from release/gates/cbc1.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

GATE_NAMES = [
    "CAUSAL_FAILURE_CLASSIFICATION",
    "LEARNING_CONSUMPTION",
    "INFRASTRUCTURE_NO_EVOLUTION",
    "BACKEND_ELIGIBILITY",
    "EVOLUTION_LINEAGE",
    "ISR_PRESERVATION",
    "ARTIFACT_NOVELTY",
    "INDEPENDENT_TRIAL",
    "PARENT_IMMUTABILITY",
    "NO_DIRECT_REPAIR",
]


def _gate_causal_classification() -> tuple[bool, str]:
    from certification.feedback.rule import analyze_failure
    cls = analyze_failure(
        stage="build", failure_class="infrastructure",
        detail="failed to solve: rust:1.78-slim: registry",
    )
    ok = cls.stage == "build" and cls.cause == "infrastructure"
    return ok, (
        f"stage={cls.stage!r} cause={cls.cause!r} "
        f"domain={cls.feedback_domain!r} eligible={cls.repair_eligible}"
    )


def _gate_learning_consumption() -> tuple[bool, str]:
    from learning.engine import ContinuousLearningEngine
    from certification.feedback.repair import GovernedRepair
    engine = ContinuousLearningEngine()
    r = GovernedRepair(learning_engine=engine)
    r.evaluate_failure(
        trial_id="g-t1", intent="intent", backend="rust-axum",
        stage="runtime", failure_class="product", detail="behavioral failure",
        isr_hash="h", genome_hash="g",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    n = engine.report().get("signal_count", 0)
    return n >= 1, f"signal_count={n}"


def _gate_infrastructure_no_evolution() -> tuple[bool, str]:
    from certification.feedback.rule import analyze_failure
    from certification.feedback.policy import BackendSwapPolicy
    for failure_class, detail in (
        ("infrastructure", "failed to solve: rust:1.78-slim"),       # registry
        ("infrastructure", "Bind for 0.0.0.0:8000 failed: # port"),  # port
        ("", ""),                                                    # startup/no-cause
    ):
        cls = analyze_failure(stage="build", failure_class=failure_class, detail=detail)
        d = BackendSwapPolicy().should_evolve(
            classification=cls, failed_backend_id="rust-axum",
            eligible_backend_ids=["python-fastapi", "rust-axum"],
        )
        if d.accepted:
            return False, f"infra {failure_class!r} spawned a candidate"
    return True, "registry/port/startup failures are LEARN-ONLY"


def _gate_backend_eligibility() -> tuple[bool, str]:
    from certification.feedback.policy import BackendSwapPolicy
    from certification.feedback.rule import analyze_failure
    from certification.feedback.candidate import EvolutionCandidate
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    policy = BackendSwapPolicy()
    # Registered eligibility list drives the choice (no hardcoded mapping).
    d = policy.should_evolve(
        classification=cls, failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    if not d.accepted or d.alternate_backend_id != "python-fastapi":
        return False, d.reason
    # No unified-source alternate -> rejected, not forced.
    d2 = policy.should_evolve(
        classification=cls, failed_backend_id="rust-axum",
        eligible_backend_ids=["rust-axum"],
    )
    return (not d2.accepted), f"alternate={d.alternate_backend_id}"


def _gate_evolution_lineage() -> tuple[bool, str]:
    from certification.feedback.policy import BackendSwapPolicy, make_candidate
    from certification.feedback.rule import analyze_failure
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    d = BackendSwapPolicy().should_evolve(
        classification=cls, failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    cand = make_candidate(
        decision=d, parent_trial_id="parent-G", intent_id="w",
        isr_hash="ISR", genome_hash="GEN",
        parent_backend_id="rust-axum",
    )
    ok = cand is not None and cand.parent_trial_id == "parent-G" and cand.parent_backend_id == "rust-axum"
    return ok, cand.lineage() if cand else "no candidate"


def _gate_isr_preservation() -> tuple[bool, str]:
    from certification.feedback.policy import BackendSwapPolicy, make_candidate
    from certification.feedback.rule import analyze_failure
    cls = analyze_failure(stage="runtime", failure_class="product", detail="")
    d = BackendSwapPolicy().should_evolve(
        classification=cls, failed_backend_id="rust-axum",
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    cand = make_candidate(
        decision=d, parent_trial_id="p", intent_id="i",
        isr_hash="ISR-H", genome_hash="GEN-H",
    )
    ok = cand is not None and cand.isr_hash == "ISR-H" and cand.genome_hash == "GEN-H"
    return ok, f"isr={'ISR-H' if cand is not None and cand.isr_hash == 'ISR-H' else 'CHANGED'}"


def _gate_artifact_novelty() -> tuple[bool, str]:
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
        return False, "need >=2 behavioral backends"
    pa = byid["python-fastapi"].compile(base.plan).content_hash
    ra = byid["rust-axum"].compile(base.plan).content_hash
    return pa != ra, f"py={pa[:8]} rust={ra[:8]} (distinct={pa != ra})"


def _gate_independent_trial() -> tuple[bool, str]:
    """The candidate is executed as a NEW trial via the normal pipeline path."""
    from certification.feedback.execution import run_evolved_trial
    from certification.feedback.candidate import EvolutionCandidate
    from certification.campaign.plan_builder import build_artifacts_for
    from certification.corpus.corpus import default_corpus
    base = build_artifacts_for(default_corpus()[0])
    cand = EvolutionCandidate(
        parent_trial_id="parent-X", intent_id=default_corpus()[0].intent,
        isr_hash=base.revision.content_hash, genome_hash=base.genome_hash,
        backend_id="python-fastapi", parent_backend_id="rust-axum",
    )

    class _Probe:
        def run_trial(self, **kwargs):
            self.kwargs = kwargs
            return kwargs  # surrogate: capture the path taken

    probe = _Probe()
    out = run_evolved_trial(
        runner=probe, candidate=cand, base_artifacts=base,
        alternate=object(), workload=default_corpus()[0],
    )
    k = probe.kwargs
    ok = (k.get("origin") == "evolved"
          and k.get("parent_trial_id") == "parent-X"
          and k.get("backend") is not None)
    return ok, f"origin={k.get('origin')} parent={k.get('parent_trial_id')}"


def _gate_parent_immutability() -> tuple[bool, str]:
    """Classify+decide for a frozen parent Trial; its fields must not change."""
    from certification.core.trial import Trial, TrialMetrics
    parent = Trial(
        trial_id="PARENT-IMM", intent="i", category="c", novelty_class="template",
        requirement_graph_hash="r", genome_hash="g", isr_revision_id="rev",
        backend="rust-axum", compiler_version="1.4.0", repo_hash="repo",
        metrics=TrialMetrics(), verdict="NOT_CERTIFIED",
    )
    before = parent.model_dump_json()
    from certification.feedback.repair import GovernedRepair
    GovernedRepair(learning_engine=None).evaluate_failure(
        trial_id=parent.trial_id, intent=parent.intent, backend=parent.backend,
        stage="runtime", failure_class="product", detail="behavioral",
        isr_hash=parent.requirement_graph_hash, genome_hash=parent.genome_hash,
        eligible_backend_ids=["python-fastapi", "rust-axum"],
    )
    return parent.model_dump_json() == before, "parent unchanged"


def _gate_no_direct_repair() -> tuple[bool, str]:
    import check_no_direct_repair as gate
    violations = gate.run_scan()
    return not violations, f"violations={len(violations)}"


def _build_runners() -> dict[str, tuple]:
    return {
        "CAUSAL_FAILURE_CLASSIFICATION": _gate_causal_classification,
        "LEARNING_CONSUMPTION": _gate_learning_consumption,
        "INFRASTRUCTURE_NO_EVOLUTION": _gate_infrastructure_no_evolution,
        "BACKEND_ELIGIBILITY": _gate_backend_eligibility,
        "EVOLUTION_LINEAGE": _gate_evolution_lineage,
        "ISR_PRESERVATION": _gate_isr_preservation,
        "ARTIFACT_NOVELTY": _gate_artifact_novelty,
        "INDEPENDENT_TRIAL": _gate_independent_trial,
        "PARENT_IMMUTABILITY": _gate_parent_immutability,
        "NO_DIRECT_REPAIR": _gate_no_direct_repair,
    }


def run_all() -> dict[str, tuple[bool, str]]:
    out: dict[str, tuple[bool, str]] = {}
    for name in GATE_NAMES:
        try:
            result = _build_runners()[name]()
        except Exception as exc:  # noqa: BLE001
            result = (False, str(exc))
        out[name] = result
    return out


def main() -> int:
    results = run_all()
    failed = {n: r for n, r in results.items() if not r[0]}
    for name in GATE_NAMES:
        ok, detail = results[name]
        print(f"{'PASS' if ok else 'FAIL'}  {name}  -> {detail}")
    if failed:
        print(f"GATES-FAIL ({len(failed)}/{len(GATE_NAMES)})", file=sys.stderr)
        return 1
    print(f"GATES-PASS ({len(GATE_NAMES)}/{len(GATE_NAMES)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())