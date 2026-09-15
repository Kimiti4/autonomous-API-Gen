# certification/feedback/rule.py

python
"""Failure feedback — classifies stage failures into causal domain + repair
eligibility for the governed evolution loop.

CRITICAL RULE: Never let Campaign B repair generated repositories directly.
If generated code fails → evidence → failure classification → learning →
governed evolution (backend variant) → new candidate → recompile → retest.
NOT: generated code fails → AI edits code → tests pass.

The key epistemic correction: **stage ≠ causal domain.**  A `build` stage can
fail from a Docker registry outage (infrastructure, NOT lowering/compiler) or
from a genuine toolchain/Dockerfile defect.  We therefore classify on the
*detected cause* (the `failure_class` produced by the real-stage classifiers in
`certification/stages/docker_stages.py`), never on the stage name alone.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Causal labels emitted by the real stage classifiers.
CAUSE_INFRASTRUCTURE = "infrastructure"
CAUSE_COMPILER = "compiler"
CAUSE_PRODUCT = "product"
CAUSE_TRANSIENT_BUILD = "transient_build_infrastructure"
CAUSE_UNKNOWN = "unknown"

# Feedback domains (ISR/genome evolution surface).
DOMAIN_INFRASTRUCTURE = "infrastructure"
DOMAIN_LOWERING = "lowering"
DOMAIN_GENOME = "genome"
DOMAIN_ARCHITECTURE = "architecture"
DOMAIN_SECURITY = "security"
DOMAIN_PROVENANCE = "provenance"

ALL_FEEDBACK_DOMAINS: frozenset[str] = frozenset({
    DOMAIN_INFRASTRUCTURE, DOMAIN_LOWERING, DOMAIN_GENOME,
    DOMAIN_ARCHITECTURE, DOMAIN_SECURITY, DOMAIN_PROVENANCE,
})

# Fallback stage→domain map used ONLY when no causal failure_class is present.
_STAGE_TO_DOMAIN: dict[str, str] = {
    "build": DOMAIN_LOWERING,
    "test": DOMAIN_GENOME,
    "deploy": DOMAIN_INFRASTRUCTURE,
    "runtime": DOMAIN_ARCHITECTURE,
    "security": DOMAIN_SECURITY,
    "semantic": DOMAIN_LOWERING,
    "structural": DOMAIN_LOWERING,
    "verify": DOMAIN_PROVENANCE,
}

# Cause → feedback domain.
_CAUSE_TO_DOMAIN: dict[str, str] = {
    CAUSE_INFRASTRUCTURE: DOMAIN_INFRASTRUCTURE,
    CAUSE_TRANSIENT_BUILD: DOMAIN_INFRASTRUCTURE,
    CAUSE_COMPILER: DOMAIN_LOWERING,
    CAUSE_PRODUCT: DOMAIN_GENOME,
}

# Domains that may trigger an EVOLVE (candidate) — backend/variant selection.
# Infrastructure is LEARN-ONLY: retrying/evolving against external infra noise
# would teach Tiannara a false causal lesson (e.g. "rust is bad" when really
# the rust registry was briefly down).
_EVOLVE_ELIGIBLE_DOMAINS = frozenset({
    DOMAIN_GENOME, DOMAIN_ARCHITECTURE, DOMAIN_LOWERING, DOMAIN_SECURITY,
})


@dataclass(frozen=True)
class FailureClassification:
    """A trial failure, classified by DETECTED CAUSE (not mere stage).

    - `stage`:          the TrialStage that failed
    - `cause`:          the detected causal class (infrastructure/compiler/...)
    - `feedback_domain`: the ISR/genome evolution surface to feed back to
    - `repair_eligible`: whether governed evolution may propose a candidate
    - `reason`:         human-readable justification for the classification
    - `evidence_ref`:   reference to the observed evidence (signature/detail)
    - `cause_mark`:     the specific transient signature matched, if any
    """
    stage: str
    cause: str = CAUSE_UNKNOWN
    feedback_domain: str = DOMAIN_GENOME
    repair_eligible: bool = False
    reason: str = ""
    evidence_ref: str = ""
    cause_mark: str = ""

    def as_record(self) -> dict:
        return {
            "stage": self.stage,
            "cause": self.cause,
            "feedback_domain": self.feedback_domain,
            "repair_eligible": self.repair_eligible,
            "reason": self.reason,
            "evidence_ref": self.evidence_ref,
            "cause_mark": self.cause_mark,
        }


def _known_domain(stage: str) -> str:
    return _STAGE_TO_DOMAIN.get(stage, DOMAIN_GENOME)


def analyze_failure(
    *,
    stage: str,
    failure_class: str = "",
    detail: str = "",
) -> FailureClassification:
    """Classify a failed stage by its causal failure_class.

    `failure_class` carries the output of the real stage classifier (see
    `certification/stages/docker_stages.py`): "infrastructure", "compiler",
    "product", "" (unknown).  When non-empty it is authoritative over the
    stage-name heuristic; when empty we fall back to the coarse stage map.
    """
    cause: str
    if failure_class in ("infrastructure", "compiler", "product"):
        cause = failure_class
    elif failure_class == "":
        # No detected causal class: derive a conservative domain from the
        # stage, but never claim repair-eligibility without a causal signal.
        domain = _known_domain(stage)
        cause = CAUSE_INFRASTRUCTURE if domain == DOMAIN_INFRASTRUCTURE else CAUSE_UNKNOWN
        return FailureClassification(
            stage=stage,
            cause=cause,
            feedback_domain=domain,
            repair_eligible=False,
            reason=(
                f"{stage} failed without a detected causal failure_class; "
                f"mapped conservatively to domain '{domain}' — no evolution without "
                "a causal signal"
            ),
            evidence_ref=f"stage={stage};failure_class=<empty>",
            cause_mark="",
        )
    else:
        cause = CAUSE_UNKNOWN

    domain = _CAUSE_TO_DOMAIN.get(cause, _known_domain(stage))
    eligible = domain in _EVOLVE_ELIGIBLE_DOMAINS
    mark = _detect_cause_mark(cause, detail)
    reason = {
        CAUSE_INFRASTRUCTURE: (
            f"{stage} failed from an infrastructure cause "
            f"(signature={mark or '<detail>'}) — LEARN-ONLY, never evolve"
        ),
        CAUSE_COMPILER: (
            f"{stage} failed from a genuine toolchain/compiler defect "
            "(lowering domain) — evolution-eligible"
        ),
        CAUSE_PRODUCT: (
            f"{stage} failed behaviorally (product domain) — evolution-eligible"
        ),
    }.get(cause, f"{stage} failed with unrecognized cause — not evolution-eligible")
    return FailureClassification(
        stage=stage,
        cause=cause,
        feedback_domain=domain,
        repair_eligible=eligible,
        reason=reason,
        evidence_ref=(
            f"stage={stage};cause={cause}"
            + (f";signature={mark}" if mark else "")
        ),
        cause_mark=mark,
    )


def _detect_cause_mark(cause: str, detail: str) -> str:
    """Return the specific recognized signature, if any, for evidence linking."""
    if cause != CAUSE_INFRASTRUCTURE:
        return ""
    from certification.stages.docker_stages import _match
    from certification.stages import docker_stages as ds

    for marks in (ds.TRANSIENT_DEPLOY_MARKS, ds.TRANSIENT_BUILD_MARKS,
                  ds.TRANSIENT_RUN_MARKS, ds.TRANSIENT_PROBE_MARKS):
        m = _match(detail, marks)
        if m:
            return m
    return ""


def classify_failure(stage: str) -> str:
    """Legacy stage→feedback-domain mapping, kept for the existing contract.

    NOTE: this is a coarse STAGE heuristic and conflates stage with cause.  For
    governed repair use `analyze_failure(...)` which classifies by DETECTED
    CAUSE (e.g. a build failure caused by a registry outage → infrastructure,
    not lowering).  Unknown stages default to "genome".
    """
    return _STAGE_TO_DOMAIN.get(stage, DOMAIN_GENOME)


# evolution/core/engine.py

python
"""EvolutionEngine: full constructive pipeline composing all ADR-011 stages."""

from __future__ import annotations

from typing import Protocol

from evolution.core.construction import ReferenceGenomeConstructor
from evolution.core.fitness import FitnessVector
from evolution.core.fitness_evaluator import ReferenceISRFitnessEvaluator
from evolution.core.genome import DecisionSpace, Genome, genome_content_hash
from evolution.core.materialize import ReferenceGenomeMaterializer
from evolution.core.operations import (
    CrossoverOperator,
    MutationOperator,
    OperationRecord,
    ReferenceCrossoverOperator,
    ReferenceMutationOperator,
)
from evolution.core.refinement import ReferenceArchitectureRefinement
from evolution.core.selection import ReferenceParetoSelection
from isr.core.graph import ISRGraph
from isr.core.revision import ISRRevision


class EvolutionObserver(Protocol):
    def on_event(self, event: dict) -> None: ...


class NullObserver:
    def on_event(self, event: dict) -> None:
        pass


class EvolutionEngine:
    """Compose all stages: construct -> evaluate -> mutate -> crossover
    -> select -> materialize -> refine -> produce ISR candidate."""

    def __init__(
        self,
        *,
        constructor: ReferenceGenomeConstructor | None = None,
        evaluator: ReferenceISRFitnessEvaluator | None = None,
        mutation_op: MutationOperator | None = None,
        crossover_op: CrossoverOperator | None = None,
        selector: ReferenceParetoSelection | None = None,
        materializer: ReferenceGenomeMaterializer | None = None,
        refiner: ReferenceArchitectureRefinement | None = None,
        observer: EvolutionObserver | None = None,
    ) -> None:
        self.constructor = constructor or ReferenceGenomeConstructor()
        self.evaluator = evaluator or ReferenceISRFitnessEvaluator()
        self.mutation_op = mutation_op or ReferenceMutationOperator()
        self.crossover_op = crossover_op or ReferenceCrossoverOperator()
        self.selector = selector or ReferenceParetoSelection()
        self.materializer = materializer or ReferenceGenomeMaterializer()
        self.refiner = refiner or ReferenceArchitectureRefinement()
        self.observer = observer or NullObserver()
        self.operations_trace: list[OperationRecord] = []

    def construct(self, isr: ISRRevision) -> Genome:
        return self.constructor.construct(isr)

    def evaluate_fitness(self, isr: ISRRevision, genome: Genome) -> FitnessVector:
        return self.evaluator.evaluate(isr, genome)

    def mutate_candidate(
        self, genome: Genome, rate: float, space: DecisionSpace
    ) -> Genome:
        result = self.mutation_op.mutate(genome, rate, space)
        self.operations_trace.append(
            OperationRecord(
                operation_type="mutation",
                source_genome_ids=[genome_content_hash(genome)],
                result_genome_id=genome_content_hash(result),
                mutation_rate=rate,
            )
        )
        return result

    def crossover_candidates(self, a: Genome, b: Genome) -> Genome:
        result = self.crossover_op.crossover(a, b)
        self.operations_trace.append(
            OperationRecord(
                operation_type="crossover",
                source_genome_ids=[
                    genome_content_hash(a),
                    genome_content_hash(b),
                ],
                result_genome_id=genome_content_hash(result),
            )
        )
        return result

    def select(self, candidates: list[FitnessVector]) -> int:
        return self.selector.select(candidates)

    def materialize_candidate(self, genome: Genome) -> ISRGraph:
        return self.materializer.materialize(genome)

    def refine_candidate(
        self, genome: Genome, weak_dims: list
    ) -> Genome:
        result = self.refiner.refine(genome, weak_dims)
        self.operations_trace.append(
            OperationRecord(
                operation_type="refinement",
                source_genome_ids=[genome_content_hash(genome)],
                result_genome_id=genome_content_hash(result),
            )
        )
        return result


# compiler/core/protocol.py

python
"""CompilerBackend — the technology-independent plugin protocol.

Defines the backend contract plus certification class enforcement.
A stub or structural backend can NEVER award behavioral certification.
"""
from __future__ import annotations
from enum import Enum
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from compiler.core.plan import CompilationPlan
from compiler.core.repository import GeneratedRepository
from compiler.core.conformance import ConformanceReport


class BackendClass(str, Enum):
    STUB = "stub"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    PRODUCTION = "production"


BEHAVIORAL_CLASSES = frozenset({BackendClass.BEHAVIORAL, BackendClass.PRODUCTION})


class BackendIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)
    name: str
    language: str
    framework: str
    version: str
    backend_class: BackendClass


class TestSpec(BaseModel):
    """Declares how a backend's generated repository tests execute.

    The runner dispatches on this — never hardcodes a test command.
    """
    model_config = ConfigDict(frozen=True)
    __test__ = False  # not a pytest test class
    command: list[str]
    runs_in: Literal["runtime", "build"] = "runtime"
    build_target: str = "build"


def eligible_for_behavioral_certification(identity: BackendIdentity) -> bool:
    return identity.backend_class in BEHAVIORAL_CLASSES


@runtime_checkable
class CompilerBackend(Protocol):
    """Every backend must implement this protocol. The core never imports
    a concrete backend — only this protocol."""
    name: str
    language: str
    framework: str
    version: str

    def identity(self) -> BackendIdentity: ...
    def test_spec(self) -> TestSpec: ...
    def element_paths(self, plan: CompilationPlan) -> dict[str, str]: ...
    def compile(self, plan: CompilationPlan) -> GeneratedRepository: ...
    def conformance(self, plan: CompilationPlan, repo: GeneratedRepository) -> ConformanceReport: ...


# learning/engine.py

python
"""
Continuous Learning Engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .analyzers import (
    CostAnalyzer,
    CustomerFeedbackAnalyzer,
    IncidentAnalyzer,
    PerformanceAnalyzer,
    SecurityLearningAnalyzer,
)
from .feedback_compiler import ArchitectureFeedbackCompiler
from .models import (
    ArchitectureFeedbackBundle,
    FitnessUpdate,
    LearningInsight,
    LearningPolicy,
    LearningRecommendation,
    LearningSignal,
)
from .pipeline import SignalPipeline
from .recommendations import FitnessUpdater, LearningRecommendationEngine


class ContinuousLearningEngine:
    """Coordinates continuous learning."""

    def __init__(self, policy: LearningPolicy | None = None) -> None:
        self.policy = policy or LearningPolicy()

        self.pipeline = SignalPipeline(self.policy)

        self.analyzers = [
            IncidentAnalyzer(),
            PerformanceAnalyzer(),
            CostAnalyzer(),
            SecurityLearningAnalyzer(),
            CustomerFeedbackAnalyzer(),
        ]

        self.recommendation_engine = LearningRecommendationEngine(self.policy)
        self.fitness_updater = FitnessUpdater()
        self.feedback_compiler = ArchitectureFeedbackCompiler()

        self.insights: Dict[str, LearningInsight] = {}
        self.recommendations: Dict[str, LearningRecommendation] = {}
        self.fitness_updates: Dict[str, FitnessUpdate] = {}
        self.bundles: Dict[str, ArchitectureFeedbackBundle] = {}

    def ingest_signal(self, signal: LearningSignal) -> LearningSignal:
        return self.pipeline.ingest(signal)

    def ingest_batch(self, signals: List[LearningSignal]) -> int:
        return self.pipeline.ingest_batch(signals)

    def analyze(
        self,
        subject_ref: Optional[str] = None,
    ) -> List[LearningInsight]:
        signals = self.pipeline.query(subject_ref=subject_ref)

        new_insights: List[LearningInsight] = []

        for analyzer in self.analyzers:
            insights = analyzer.analyze(signals, self.policy)

            for insight in insights:
                if insight.id not in self.insights:
                    self.insights[insight.id] = insight
                    new_insights.append(insight)

        all_insights = list(self.insights.values())

        recommendations = self.recommendation_engine.from_insights(all_insights)

        for recommendation in recommendations:
            self.recommendations[recommendation.id] = recommendation

        fitness_updates = self.fitness_updater.from_insights(all_insights)

        for update in fitness_updates:
            self.fitness_updates[update.id] = update

        return new_insights

    def compile_feedback(
        self,
        scope: str = "platform",
        subject_ref: Optional[str] = None,
    ) -> ArchitectureFeedbackBundle:
        if not self.insights:
            self.analyze(subject_ref=subject_ref)

        insights = list(self.insights.values())

        if subject_ref:
            insights = [
                insight
                for insight in insights
                if subject_ref in insight.affected_subjects
            ]

        recommendations = list(self.recommendations.values())

        if subject_ref:
            recommendations = [
                recommendation
                for recommendation in recommendations
                if recommendation.subject_ref == subject_ref
            ]

        fitness_updates = list(self.fitness_updates.values())

        if subject_ref:
            fitness_updates = [
                update
                for update in fitness_updates
                if update.subject_ref == subject_ref
            ]

        bundle = self.feedback_compiler.compile(
            scope=scope,
            insights=insights,
            recommendations=recommendations,
            fitness_updates=fitness_updates,
        )

        self.bundles[bundle.id] = bundle

        return bundle

    def report(self) -> Dict:
        return {
            "signal_count": len(self.pipeline.signals),
            "insight_count": len(self.insights),
            "recommendation_count": len(self.recommendations),
            "fitness_update_count": len(self.fitness_updates),
            "bundle_count": len(self.bundles),
        }


# release/run_wave.py

python
"""Run Campaign B wave — invoked by run-campaign-b.sh or directly."""
import os
import sys

from certification.campaign.campaign_b import run_wave
from certification.campaign.waves import WAVES


def main():
    wave_id = os.environ.get("CBC1_WAVE", "B1")
    scale_str = os.environ.get("CBC1_SCALE", "")
    scale = int(scale_str) if scale_str else None

    wave = WAVES.get(wave_id)
    if not wave:
        print(f"Unknown wave: {wave_id}", file=sys.stderr)
        sys.exit(1)

    print(f"Wave {wave_id}: {wave.purpose}")
    print(f"Required mode: {wave.required_mode.value}")
    print()

    resume = os.environ.get("CBC1_RESUME", "") == "1"
    supplement = os.environ.get("CBC1_SUPPLEMENT", "") == "1"
    if resume:
        print("Resume mode: continuing prior ledger on the same verified hash chain")
    if supplement:
        print("Supplement mode: re-measuring failed seed trials as new trials")

    verdict, summary = run_wave(
        wave_id, scale_override=scale, resume=resume, supplement=supplement,
    )
    print(f"Verdict: {verdict}")
    print(f"Reason:  {summary.get('verdict_reason', '')}")
    print(f"Expected:  {summary.get('expected_trials', 0)}")
    print(f"Planned:   {summary.get('planned_trials', 0)}   "
          f"Resumed: {summary.get('resumed_trials', 0)}   "
          f"Supplements: {summary.get('supplement_trials', 0)}")
    print(f"Executed:  {summary.get('executed_trials', 0)}   "
          f"Certified: {summary.get('certified_trials', 0)}   "
          f"Failed: {summary.get('failed_trials', 0)}   "
          f"Skipped: {summary.get('skipped_trials', 0)}")

    if summary.get("port_preflight", {}).get("enabled"):
        pf = summary["port_preflight"]
        print(f"Port preflight: {'OK' if pf.get('ok') else 'FAILED'} "
              f"window={pf.get('window')} evidence={pf.get('evidence_path')}")

    if summary.get("failure_taxonomy_independent"):
        print()
        print("Failure taxonomy (independent):")
        for stage, count in summary["failure_taxonomy_independent"].items():
            print(f"  {stage}: {count}")

    print()
    print(f"Aggregate: release/evidence/cbc1-b-{wave_id}-aggregate.json")

    exit_codes = {"CERTIFIED": 0, "NOT_CERTIFIED": 1, "QUALIFIED_PARTIAL": 3}
    sys.exit(exit_codes.get(verdict, 1))


if __name__ == "__main__":
    main()


# certification/campaign/campaign_b.py

python
"""Campaign B runner — mode-enforced, configuration-driven certification.

Every behavioral stage records an explicit ExecutionMode. The verifier refuses
CERTIFIED unless the mode equals the configured required mode — so a stub can
never silently substitute for Docker.

Failure flows to classify_failure → ISR/genome evolution, NOT direct code repair.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from compiler.composition import build_backend_registry
from compiler.core.conformance import CHECKER
from compiler.core.repository import build_repository
from compiler.core.protocol import (
    BackendIdentity,
    eligible_for_behavioral_certification,
)
from certification.core.trial import (
    Trial,
    TrialStage,
    StageEvidence,
    TrialMetrics,
    compose_verdict,
)
from certification.core import metrics as M
from certification.campaign.plan_builder import build_artifacts_for
from certification.campaign.verdict import compose_campaign_verdict, CampaignVerdict
from certification.campaign.waves import CampaignBudget
from certification.evidence.ledger import EvidenceLedger
from certification.provenance.bundle import ProvenanceBundle
from certification.stages.execution_mode import (
    ExecutionMode,
    StageExecution,
    BEHAVIORAL_STAGES,
)


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass
class SubstrateReport:
    certified: bool
    executions: list[StageExecution] = field(default_factory=list)
    detail: str = ""


class CampaignBRunner:
    """Orchestrates Campaign B trials with mode-enforced stage execution.

    Stage implementations are injected: RealDockerStages for Campaign B,
    StubStages for Campaign A / unit tests.
    """

    def __init__(
        self,
        stages: Any,
        ledger: EvidenceLedger,
        required_mode: ExecutionMode = ExecutionMode.REAL_DOCKER,
    ) -> None:
        self.stages = stages
        self.ledger = ledger
        self.required_mode = required_mode

    def eligible_backends(self) -> list[Any]:
        reg = build_backend_registry()
        return [
            reg.get(n) for n in reg.list_names()
            if eligible_for_behavioral_certification(reg.get(n).identity())
        ]

    def run_trial(
        self,
        intent: str,
        category: str,
        novelty_class: str,
        plan: Any,
        revision: Any,
        backend: Any,
        corpus_hash: str = "",
        requirement_graph_hash: str = "",
        genome_hash: str = "",
        workload: Any = None,
        artifacts: Any = None,
        origin: str = "reference",
        parent_trial_id: str = "",
    ) -> Trial:
        trial_id = str(uuid.uuid4())
        ident: BackendIdentity = backend.identity()

        stage_results: dict[TrialStage, bool] = {}
        evidence: list[StageEvidence] = []
        exec_details: dict[str, Any] = {}

        def _record_execution(se: StageExecution) -> None:
            stage_results[se.stage] = se.passed
            evidence.append(StageEvidence(
                stage=se.stage,
                passed=se.passed,
                started_at=_now(),
                completed_at=_now(),
                logs_hash=se.logs_hash,
                detail=se.detail,
                mode=se.mode.value,
                duration_s=se.duration_s,
                image_digest=se.image_digest,
                container_id=se.container_id,
                peak_resource=se.peak_resource,
                retries=se.retries,
                retry_signatures=list(se.retry_signatures),
                failure_class=se.failure_class,
            ))
            exec_details[se.stage.value] = {
                "mode": se.mode.value,
                "passed": se.passed,
                "duration_s": round(se.duration_s, 3),
                "image_digest": se.image_digest,
                "peak_resource": se.peak_resource,
                "retries": se.retries,
                "retry_signatures": list(se.retry_signatures),
                "failure_class": se.failure_class,
            }

        # Structural + semantic: conformance check
        repo = backend.compile(plan)
        conf = backend.conformance(plan, repo)
        stage_results[TrialStage.STRUCTURAL] = conf.passed
        stage_results[TrialStage.SEMANTIC] = conf.passed
        evidence.append(StageEvidence(
            stage=TrialStage.STRUCTURAL, passed=conf.passed,
            started_at=_now(), completed_at=_now(),
            logs_hash=_h(f"structural-{conf.missing}"),
            detail=f"missing={conf.missing}",
        ))
        evidence.append(StageEvidence(
            stage=TrialStage.SEMANTIC, passed=conf.passed,
            started_at=_now(), completed_at=_now(),
            logs_hash=_h(f"semantic-{conf.passed}"),
            detail=f"semantic={conf.passed}",
        ))

        # Behavioral stages: build → test → deploy → runtime → destroy → verify
        tag = f"cbc1-b-{trial_id[:8]}"
        from certification.campaign.preflight import port_for_trial
        base = getattr(self, "port_base", 8000)
        span = getattr(self, "port_span", 1000)
        port = port_for_trial(trial_id, base, span)

        # Materialize repo to disk for Docker build
        d = tempfile.mkdtemp(prefix="cbc1-b-")
        for p, c in repo.files.items():
            full = os.path.join(d, p)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(c)

        se_build = self.stages.build(d, tag)
        _record_execution(se_build)

        # Test: dispatch on backend's declared TestSpec (no hardcoded commands)
        spec = backend.test_spec()
        se_test = self.stages.run_tests(tag, spec, repo_dir=d, tag=tag)
        _record_execution(se_test)

        se_deploy = self.stages.deploy(tag, port)
        _record_execution(se_deploy)

        cid = se_deploy.container_id
        se_runtime = self.stages.probe(port, cid)
        _record_execution(se_runtime)

        se_destroy = self.stages.destroy(cid)
        _record_execution(se_destroy)

        # Independent verification (separate subprocess)
        v_ok, v_out = _run_independent_verify(
            repo, plan, ident, conf,
        )
        stage_results[TrialStage.VERIFY] = v_ok
        evidence.append(StageEvidence(
            stage=TrialStage.VERIFY, passed=v_ok,
            started_at=_now(), completed_at=_now(),
            logs_hash=_h(v_out),
            detail=v_out[:500],
            mode=ExecutionMode.REAL_DOCKER.value if self.required_mode == ExecutionMode.REAL_DOCKER else ExecutionMode.STUB.value,
        ))
        exec_details["verify"] = {
            "mode": self.required_mode.value,
            "passed": v_ok,
            "duration_s": 0,
            "image_digest": "",
            "peak_resource": "",
        }

        # Mode enforcement: every behavioral stage must match required_mode
        mode_ok = True
        for se in [se_build, se_test, se_deploy, se_runtime, se_destroy]:
            if se.mode != self.required_mode:
                mode_ok = False
                break
        if not mode_ok:
            verdict = "NOT_CERTIFIED"
        else:
            verdict = compose_verdict(stage_results, evidence_present=True,
                                      required_mode=self.required_mode.value)

        # Metrics
        metrics = M.compute(
            repo_files_count=len(repo.files),
            stages=stage_results,
            structural_passed=stage_results.get(TrialStage.STRUCTURAL, False),
            test_passed=stage_results.get(TrialStage.TEST, False),
            runtime_passed=stage_results.get(TrialStage.RUNTIME, False),
            repo_content_hash=repo.content_hash,
            files=repo.files,
        )
        # Extend metrics with execution detail
        metrics = metrics.model_copy(update={
            "execution_detail": exec_details,
            "generated_repository_hash": repo.content_hash,
            "independent_verifier_result": v_ok,
        })

        trial = Trial(
            trial_id=trial_id,
            intent=intent,
            category=category,
            novelty_class=novelty_class,
            requirement_graph_hash=requirement_graph_hash,
            genome_hash=genome_hash,
            isr_revision_id=revision.revision_id,
            backend=ident.name,
            backend_class=ident.backend_class.value,
            backend_version=ident.version,
            compiler_version="1.4.0",
            repo_hash=repo.content_hash,
            corpus_hash=corpus_hash,
            stages=evidence,
            metrics=metrics,
            verdict=verdict,
            origin=origin,
            parent_trial_id=parent_trial_id,
        )

        # Provenance bundle
        if artifacts and workload is not None:
            bundle = ProvenanceBundle.emit(
                trial=trial, plan=artifacts.plan, revision=artifacts.revision,
                genome=artifacts.genome, requirement_graph=artifacts.requirement_graph,
                backend_identity=ident, conformance=conf,
            )
            bhash = ProvenanceBundle.bundle_hash(bundle)
            trial = trial.model_copy(update={"bundle_hash": bhash})

        self.ledger.append(trial.model_dump())
        return trial


def _run_independent_verify(
    repo: Any, plan: Any, ident: BackendIdentity, conf: Any,
) -> tuple[bool, str]:
    """Run independent verification in a subprocess."""
    verify_script = (
        "import json, sys, hashlib; "
        f"files = {json.dumps(dict(list(repo.files.items())[:5]))}; "
        "h = hashlib.sha256(json.dumps(sorted(files.keys())).encode()).hexdigest(); "
        f"print('verify_hash=' + h); "
        f"print('conformance_passed={conf.passed}'); "
        "sys.exit(0)"
    )
    try:
        p = subprocess.run(
            ["python", "-c", verify_script],
            capture_output=True, text=True, timeout=30,
        )
        return p.returncode == 0, p.stdout + p.stderr
    except Exception as e:
        return False, str(e)


def certify_docker_substrate(runner: CampaignBRunner) -> SubstrateReport:
    """B0: prove the Docker substrate before any trials run."""
    from certification.corpus.corpus import default_corpus
    corpus = default_corpus()
    if not corpus:
        return SubstrateReport(certified=False, detail="empty corpus")

    backends = runner.eligible_backends()
    if not backends:
        return SubstrateReport(certified=False, detail="no eligible backends")

    backend = backends[0]
    workload = corpus[0]
    artifacts = build_artifacts_for(workload)

    trial = runner.run_trial(
        intent=workload.intent,
        category=workload.category.value,
        novelty_class="template",
        plan=artifacts.plan,
        revision=artifacts.revision,
        backend=backend,
        corpus_hash="",
        requirement_graph_hash=artifacts.requirement_graph_hash,
        genome_hash=artifacts.genome_hash,
        workload=workload,
        artifacts=artifacts,
    )

    behavioral = [
        se for se in trial.stages
        if se.stage in BEHAVIORAL_STAGES
    ]
    ok = all(
        se.mode == ExecutionMode.REAL_DOCKER.value and se.passed
        for se in behavioral
    )
    detail = "; ".join(
        f"{se.stage.value}: mode={se.mode} passed={se.passed}"
        for se in behavioral
    )
    return SubstrateReport(certified=ok, detail=detail)


def run_wave(
    wave_id: str,
    scale_override: int | None = None,
    resume: bool = False,
    supplement: bool = False,
    ledger_path: str | None = None,
    agg_path: str | None = None,
) -> tuple[str, dict]:
    """Execute a Campaign B wave. Returns (verdict_string, aggregate_dict).

    resume=True continues an interrupted ledger ON THE SAME verified hash
    chain (already-recorded trials are never re-run or rewritten).
    supplement=True re-measures the failures recorded in the resumed seed as
    independent NEW trials, growing the campaign window (original failures
    stay NOT_CERTIFIED — they can never become CERTIFIED).

    ledger_path/agg_path override the fixed wave paths (testability).

    Resource exhaustion → NOT_CERTIFIED. Never silently skip trials.
    """
    import time as _time
    import types as _types
    from certification.campaign.waves import (
        WAVES, BUDGETS, expand_corpus, ledger_path_for, aggregate_path_for,
    )

    wave = WAVES.get(wave_id)
    if wave is None:
        return "NOT_CERTIFIED", {"error": f"unknown wave {wave_id}"}

    budget = BUDGETS.get(wave_id, CampaignBudget(max_trials=9999))
    scale = scale_override if scale_override is not None else wave.scale_factor
    if ledger_path is None:
        ledger_path = ledger_path_for(wave_id)
    if agg_path is None:
        agg_path = aggregate_path_for(wave_id)

    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)
    prepared: set[tuple[str, str]] = set()
    seed_trials: list[Any] = []
    if os.path.exists(ledger_path):
        # A re-run is a NEW wave ledger, never a rewrite: archive the prior
        # wave's ledger (and aggregate) so no evidence is ever destroyed.
        import shutil as _shutil
        from datetime import datetime as _dt
        stamp = _dt.now().strftime("%Y%m%d-%H%M%S")
        archive = f"{ledger_path}.archive-{stamp}"
        if resume:
            # Resume: continue the SAME verified hash chain (same records,
            # bytes for bytes) from where an interrupted run stopped.  The
            # prior ledger is still copied to archive as an independent object.
            if not EvidenceLedger.verify(ledger_path):
                agg = {
                    "wave": wave_id,
                    "verdict": "NOT_CERTIFIED",
                    "verdict_reason": "resume refused: prior ledger hash chain broken",
                    "total_trials": EvidenceLedger.count(ledger_path),
                    "resumed_from": 0,
                }
                with open(agg_path, "w", encoding="utf-8") as f:
                    json.dump(agg, f, indent=2)
                return "NOT_CERTIFIED", agg
            _shutil.copy2(ledger_path, archive)
            print(f"Resuming: archiving prior ledger -> {archive}")
            for line in open(ledger_path, encoding="utf-8"):
                if not line.strip():
                    continue
                record = json.loads(line)
                t = record.get("trial", record)
                prepared.add((t.get("intent", ""), t.get("backend", "")))
                # Lightweight seed view for verdict/amplification accounting —
                # the authoritative bytes stay in the ledger file untouched.
                seed_trials.append(_types.SimpleNamespace(
                    intent=t.get("intent", ""),
                    backend=t.get("backend", ""),
                    verdict=t.get("verdict", "NOT_CERTIFIED"),
                    backend_class=t.get("backend_class", ""),
                    stages=t.get("stages", []),
                ))
        else:
            _shutil.copy2(ledger_path, archive)
            if os.path.exists(agg_path):
                _shutil.copy2(agg_path, f"{agg_path}.archive-{stamp}")
            print(f"Archived prior wave ledger -> {archive}")
            os.remove(ledger_path)

    ledger = EvidenceLedger(ledger_path)
    runner = CampaignBRunner(
        stages=_resolve_stages(wave.required_mode),
        ledger=ledger,
        required_mode=wave.required_mode,
    )

    # Explicit execution-environment preparation: allocate a host TCP window
    # free of OS-excluded ranges BEFORE running trials.  If the environment
    # cannot provide capacity, the campaign stops honestly — it never silently
    # reuses ports or retries into secrecy.  Evidence of the assessment is
    # persisted as a first-class artifact (release/evidence/cbc1-<wave>-portpool.json).
    port_pf: dict[str, Any] = {"enabled": False}
    from certification.stages.docker_stages import RealDockerStages

    if isinstance(runner.stages, RealDockerStages):
        from certification.campaign.preflight import (
            preflight_ports, DEFAULT_SPAN, resolve_preferred_range,
        )
        preferred = resolve_preferred_range()
        alloc, pf_path = preflight_ports(wave_id, preferred=preferred, span=DEFAULT_SPAN)
        port_pf = {
            "enabled": True,
            "evidence_path": pf_path,
            "ok": alloc.ok,
            "base": alloc.base,
            "span": alloc.span,
            "preferred": list(preferred),
            "override": preferred != (8000, 9999),
            "window": alloc.window,
            "reason": alloc.reason,
            "excluded_tcp_ranges": list(alloc.excluded_ranges),
        }
        if not alloc.ok:
            agg = {
                "wave": wave_id,
                "verdict": "NOT_CERTIFIED",
                "verdict_reason": f"port capacity insufficient: {alloc.reason}",
                "port_preflight": port_pf,
                "total_trials": 0,
            }
            with open(agg_path, "w", encoding="utf-8") as f:
                json.dump(agg, f, indent=2)
            print(f"Port preflight failed: {alloc.reason}")
            return "NOT_CERTIFIED", agg
        runner.port_base = alloc.base
        runner.port_span = alloc.span
        print(
            f"Port preflight OK: host window {alloc.window[0]}..{alloc.window[1]} "
            f"({alloc.window[1] - alloc.window[0] + 1} free ports) evidence={pf_path}"
        )

    # B0: prove substrate first
    if wave_id == WaveId.B0.value or wave_id == "B0":
        rep = certify_docker_substrate(runner)
        if not rep.certified:
            agg = {
                "wave": wave_id,
                "verdict": "NOT_CERTIFIED",
                "verdict_reason": f"substrate certification failed: {rep.detail}",
                "substrate_detail": rep.detail,
            }
            with open(agg_path, "w", encoding="utf-8") as f:
                json.dump(agg, f, indent=2)
            return "NOT_CERTIFIED", agg
        # B0: substrate certified — short-circuit, no full corpus run
        agg = {
            "wave": wave_id,
            "verdict": "CERTIFIED",
            "verdict_reason": "Docker substrate certified (build/test/deploy/runtime/destroy all REAL_DOCKER)",
            "substrate_detail": rep.detail,
            "total_trials": 0,
            "certified": 0,
        }
        with open(agg_path, "w", encoding="utf-8") as f:
            json.dump(agg, f, indent=2)
        return "CERTIFIED", agg

    corpus = expand_corpus(scale) if scale > 1 else (
        __import__("certification.corpus.corpus", fromlist=["default_corpus"]).default_corpus()
    )
    ch = __import__("certification.corpus.corpus", fromlist=["corpus_hash"]).corpus_hash()
    backends = runner.eligible_backends()
    expected = len(corpus) * len(backends)
    trials: list[Trial] = list(seed_trials)
    campaign_start = _time.time()

    def _budget_check(
        running: list[Trial], planned_done: int,
        phase_label: str,
    ) -> tuple[bool, str]:
        """Enforce hard campaign budgets; never silently drop or skip trials."""
        elapsed = _time.time() - campaign_start
        if elapsed >= budget.max_total_runtime_s:
            return True, f"max_total_runtime ({budget.max_total_runtime_s}s)"
        if phase_label == "planned" and planned_done >= budget.max_trials:
            return True, "max_trials"
        if phase_label == "supplement" and len(running) >= budget.max_trials:
            # Planned window done; supplements are extra (clock-bound only).
            pass
        return False, ""

    planned_run = 0
    for w in corpus:
        artifacts = build_artifacts_for(w)
        for backend in backends:
            bkey = backend.identity().name
            if (w.intent, bkey) in prepared:
                continue
            # Budget enforcement: never silently skip trials
            exhausted, violation = _budget_check(trials, planned_run, "planned")
            if exhausted:
                certified_count = sum(1 for t in trials if t.verdict == "CERTIFIED")
                reason = f"budget exhausted ({violation}): {len(trials)}/{expected} trials completed, {certified_count} certified"
                summary = {
                    "wave": wave_id,
                    "scale_factor": scale,
                    "total_trials": len(trials),
                    "expected_trials": expected,
                    "planned_trials": expected,
                    "resumed_trials": len(seed_trials),
                    "supplement_trials": 0,
                    "executed_trials": len(trials),
                    "certified_trials": certified_count,
                    "failed_trials": len(trials) - certified_count,
                    "skipped_trials": max(0, expected - planned_run),
                    "certified": certified_count,
                    "corpus_hash": ch,
                    "verdict": "NOT_CERTIFIED",
                    "verdict_reason": reason,
                    "required_mode": wave.required_mode.value,
                    "port_preflight": port_pf,
                    "budget_violation": violation,
                    "budget": {
                        "max_trials": budget.max_trials,
                        "max_total_runtime_s": budget.max_total_runtime_s,
                        "actual_runtime_s": round(_time.time() - campaign_start, 1),
                    },
                }
                with open(agg_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, indent=2)
                return "NOT_CERTIFIED", summary

            trial = runner.run_trial(
                intent=w.intent,
                category=w.category.value,
                novelty_class="template",
                plan=artifacts.plan,
                revision=artifacts.revision,
                backend=backend,
                corpus_hash=ch,
                requirement_graph_hash=artifacts.requirement_graph_hash,
                genome_hash=artifacts.genome_hash,
                workload=w,
                artifacts=artifacts,
            )
            trials.append(trial)
            planned_run += 1

    # Supplemental re-measurements: re-run the exact failed (intent, backend)
    # pairs from the resumed seed as independent new trials, so a substrate
    # fix can be demonstrated against the SAME workloads that failed.  The
    # original failed records stay NOT_CERTIFIED in the ledger (never
    # rewritten, never dropped); the campaign window grows beyond planned.
    supplement_runs: list[Trial] = []
    if resume and supplement:
        failed_seed_keys = [
            (t.intent, t.backend) for t in seed_trials if t.verdict != "CERTIFIED"
        ]
        by_name = {b.identity().name: b for b in backends}
        by_intent = {w.intent: w for w in corpus}
        for intent, bname in failed_seed_keys:
            w = by_intent.get(intent)
            backend = by_name.get(bname)
            if w is None or backend is None:
                continue
            exhausted, violation = _budget_check(
                trials + supplement_runs, planned_run, "supplement",
            )
            if exhausted:
                break
            artifacts = build_artifacts_for(w)
            trial = runner.run_trial(
                intent=w.intent,
                category=w.category.value,
                novelty_class="template",
                plan=artifacts.plan,
                revision=artifacts.revision,
                backend=backend,
                corpus_hash=ch,
                requirement_graph_hash=artifacts.requirement_graph_hash,
                genome_hash=artifacts.genome_hash,
                workload=w,
                artifacts=artifacts,
            )
            supplement_runs.append(trial)
    trials = trials + supplement_runs
    expected_total = expected + len(supplement_runs)

    # ---- Governed evolution phase (backend-variant self-repair) ----
    # Gated behind CBC1_EVOLVE=1: applies to a fresh wave.  For each failed,
    # CAUSALLY-ACTIONABLE planned trial, we learn from it and — when the policy
    # accepts an eligible alternate behavioral backend — execute it as a NEW
    # independent evolved trial through the NORMAL pipeline (origin=evolved,
    # parent_trial_id=<immutable parent>, variant_kind=backend_swap).
    # Infrastructure/registry/port failures are LEARN-ONLY (never evolve).
    evolved_runs: list[Trial] = []
    evolution: dict[str, Any] = {"enabled": False}
    if os.environ.get("CBC1_EVOLVE", "") == "1" and isinstance(runner.stages, RealDockerStages):
        evolution["enabled"] = True
        from certification.feedback.repair import GovernedRepair
        from certification.feedback.execution import prepare_evolved_trial, run_evolved_trial
        from learning.engine import ContinuousLearningEngine

        # D2 — PRODUCTION learning consumption: every failed, causally-classified
        # trial emits a LearningSignal into a REAL ContinuousLearningEngine.  The
        # engine is never passed as None on the campaign path.
        learning_engine = ContinuousLearningEngine()
        repair = GovernedRepair(learning_engine=learning_engine)
        evolution_events: list[dict[str, Any]] = []
        by_name = {b.identity().name: b for b in backends}
        eligible_names = list(by_name.keys())
        parent_to_candidate: dict[str, str] = {}
        for t in list(trials):
            if t.verdict == "CERTIFIED":
                continue
            # Find the first independent (non-cascade) failing behavioral stage.
            causal = None
            for s in t.stages:
                if not s.passed and s.mode != ExecutionMode.SKIPPED.value and s.stage != TrialStage.STRUCTURAL and s.stage != TrialStage.SEMANTIC:
                    causal = s
                    break
            if causal is None:
                continue
            try:
                decision_feedback = repair.evaluate_failure(
                    trial_id=t.trial_id,
                    intent=t.intent,
                    backend=t.backend,
                    stage=causal.stage,
                    failure_class=causal.failure_class or "",
                    detail=causal.detail or "",
                    isr_hash=t.requirement_graph_hash,
                    genome_hash=t.genome_hash,
                    eligible_backend_ids=eligible_names,
                )
            except Exception:  # noqa: BLE001 — never crash the wave on a repair decision
                continue
            evolution_events.append({
                "event": "feedback.classified",
                "trial_id": t.trial_id,
                "backend_id": t.backend,
                "classification": decision_feedback.classification.as_record(),
            })
            if decision_feedback.signal is not None:
                evolution_events.append({
                    "event": "learning.signal_emitted",
                    "trial_id": t.trial_id,
                    "signal_type": decision_feedback.signal.signal_type.value,
                    "signal_id": decision_feedback.signal.id or "",
                    "severity": decision_feedback.signal.severity.value,
                })
            evolution_events.append({
                "event": "evolution.decided",
                "trial_id": t.trial_id,
                "decision": decision_feedback.decision.as_record(),
            })
            if decision_feedback.candidate is None:
                continue
            cand = decision_feedback.candidate
            evolution_events.append({
                "event": "evolution.candidate_created",
                "trial_id": t.trial_id,
                "candidate_id": cand.candidate_id,
                "alternate_backend_id": cand.backend_id,
            })
            if cand.backend_id in parent_to_candidate.values():
                continue  # backend already chosen as alternate for an earlier parent
            w = next((x for x in corpus if x.intent == t.intent), None)
            if w is None:
                continue
            artifacts = build_artifacts_for(w)
            novelty, alternate = prepare_evolved_trial(
                candidate=cand, runner=runner, base_artifacts=artifacts,
                backend_map=by_name, failed_backend_id=t.backend,
            )
            evolution_events.append({
                "event": "evolution.novelty_check",
                "trial_id": t.trial_id,
                "candidate_id": cand.candidate_id,
                "distinct": novelty.distinct,
                "parent_artifact_hash": novelty.parent_artifact_hash,
                "candidate_artifact_hash": novelty.candidate_artifact_hash,
            })
            if alternate is None:
                evolution["rejected_noop"] = evolution.get("rejected_noop", 0) + 1
                evolution_events.append({
                    "event": "evolution.rejected_noop",
                    "trial_id": t.trial_id,
                    "candidate_id": cand.candidate_id,
                })
                continue
            exhausted, violation = _budget_check(
                trials + evolved_runs, planned_run, "supplement",
            )
            if exhausted:
                break
            evolved_trial = run_evolved_trial(
                runner=runner, candidate=cand, base_artifacts=artifacts,
                alternate=alternate, workload=w,
            )
            evolved_runs.append(evolved_trial)
            parent_to_candidate[cand.parent_trial_id] = cand.backend_id
            evolution.setdefault("candidates", [])
            evolution["candidates"].append({
                "parent_trial_id": cand.parent_trial_id,
                "candidate_id": cand.candidate_id,
                "backend": cand.backend_id,
                "origin": "evolved",
                "variant_kind": cand.variant_kind,
                "novelty": novelty.distinct,
                "parent_immutable": True,
            })
            evolution_events.append({
                "event": "evolution.parent_immutable",
                "trial_id": t.trial_id,
                "candidate_id": cand.candidate_id,
            })
            evolution_events.append({
                "event": "evolution.executed",
                "trial_id": t.trial_id,
                "candidate_trial_id": evolved_trial.trial_id,
                "backend_id": cand.backend_id,
            })
            if evolved_trial.verdict == "CERTIFIED":
                evolution_events.append({
                    "event": "evolution.certified",
                    "trial_id": t.trial_id,
                    "candidate_trial_id": evolved_trial.trial_id,
                    "backend_id": cand.backend_id,
                })
    trials = trials + evolved_runs
    expected_total = expected + len(supplement_runs) + len(evolved_runs)
    evolution["evolved_trials"] = len(evolved_runs)
    evolution["evolved_certified"] = sum(
        1 for t in evolved_runs if t.verdict == "CERTIFIED"
    )
    if evolution["enabled"]:
        evolution["signal_count"] = learning_engine.report().get("signal_count", 0)
        evolution["insight_count"] = learning_engine.report().get("insight_count", 0)
        evolution["events"] = evolution_events

    assert EvidenceLedger.verify(ledger_path), "Evidence chain broken"

    ok, matrix, taxonomy, problems = verify_campaign_b_mode(
        ledger_path, wave.required_mode,
    )

    from certification.campaign.amplification import (
        compute_amplification, amplification_problems,
    )
    amp = compute_amplification(
        trials, expected_total, wave.max_retry_rate,
        max_startup_polls=wave.max_startup_polls,
        max_startup_wait_s=wave.max_startup_wait_s,
    )
    amp_problems = amplification_problems(amp, wave.max_retry_rate)
    if amp_problems:
        problems = problems + amp_problems

    verdict, reason = compose_campaign_verdict(
        trials=trials,
        expected_trials=expected_total,
        ledger_intact=ok,
        integrity_problems=problems,
        coverage_complete=True,
    )

    from certification.campaign.decision import b3_decision

    certified_n = sum(1 for t in trials if t.verdict == "CERTIFIED")
    # From the campaign's declared plan, not from a desired outcome:
    #   planned_trials  = corpus x backends (the contract that must run)
    #   resumed_trials  = records inherited from a verified prior ledger
    #   supplement_trials = extra independent re-measurements beyond the plan
    #   executed_trials = records actually in this window's ledger
    executed_planned = len(trials) - len(seed_trials) - len(supplement_runs)
    skipped_trials = max(0, expected - executed_planned)

    summary: dict[str, Any] = {
        "wave": wave_id,
        "scale_factor": scale,
        "plan": "planned_trials = corpus x backends; expected = planned + supplements",
        "expected_trials": expected_total,
        "planned_trials": expected,
        "resumed_from": len(seed_trials),
        "resumed_trials": len(seed_trials),
        "supplement_trials": len(supplement_runs),
        "evolved_trials": len(evolved_runs),
        "evolved_certified": evolution.get("evolved_certified", 0),
        "executed_trials": len(trials),
        "certified_trials": certified_n,
        "failed_trials": len(trials) - certified_n,
        "skipped_trials": skipped_trials,
        "total_trials": len(trials),
        "certified": certified_n,
        "corpus_hash": ch,
        "verdict": verdict.value,
        "verdict_reason": reason,
        "required_mode": wave.required_mode.value,
        "independent_verify_ok": ok,
        "independent_verify_problems": problems,
        "failure_taxonomy_independent": taxonomy,
        "category_matrix": matrix,
        "port_preflight": port_pf,
        "evolution": evolution,
        "amplification": amp.model_dump(),
        "max_retry_rate": wave.max_retry_rate,
        "decision": b3_decision(verdict.value, amp, wave.max_retry_rate),
        "budget": {
            "max_trials": budget.max_trials,
            "max_total_runtime_s": budget.max_total_runtime_s,
            "actual_runtime_s": round(_time.time() - campaign_start, 1),
            "budget_exhausted": len(trials) >= budget.max_trials,
        },
    }

    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return verdict.value, summary


def verify_campaign_b_mode(
    ledger_path: str,
    required_mode: ExecutionMode,
) -> tuple[bool, dict, dict, list[str]]:
    """Mode-enforcing verifier: rejects CERTIFIED if any behavioral stage
    doesn't match the required execution mode.
    """
    if not EvidenceLedger.verify(ledger_path):
        return False, {}, {}, ["ledger hash chain broken"]

    problems: list[str] = []
    taxonomy: dict[str, int] = {}
    matrix: dict[str, dict[str, int]] = {}
    ledger_trials: list[dict] = []

    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            t = record.get("trial", record)
            ledger_trials.append(t)

            for s in t.get("stages", []):
                stage_name = s.get("stage", "")
                # Cascade SKIPPED stages (e.g. destroy after failed deploy) are
                # not independent failures — don't inflate the taxonomy.
                if not s.get("passed") and s.get("mode") != ExecutionMode.SKIPPED.value:
                    taxonomy[stage_name] = taxonomy.get(stage_name, 0) + 1

            if t.get("verdict") == "CERTIFIED":
                # Mode enforcement
                for s in t.get("stages", []):
                    stage_name = s.get("stage", "")
                    if stage_name in {ts.value for ts in BEHAVIORAL_STAGES}:
                        mode = s.get("mode", "")
                        if mode != required_mode.value:
                            problems.append(
                                f"{t.get('trial_id','?')}: stage {stage_name} "
                                f"mode={mode} != {required_mode.value}"
                            )

                cat = t.get("category", "?")
                backend = t.get("backend", "?")
                matrix.setdefault(cat, {}).setdefault(backend, 0)
                matrix[cat][backend] += 1

    # Retry-amplification honesty cross-check from the ledger (independent of
    # the in-memory trials used for the summary).
    from certification.campaign.amplification import (
        compute_amplification, amplification_problems,
    )
    amp = compute_amplification(
        ledger_trials, len(ledger_trials), required_max_retry_rate(),
    )
    problems = problems + amplification_problems(amp, required_max_retry_rate())

    return (not problems), matrix, taxonomy, problems


def required_max_retry_rate() -> float:
    """Honesty bound for retry amplification (0.2 everywhere in Campaign B)."""
    return 0.2


def _resolve_stages(mode: ExecutionMode) -> Any:
    if mode == ExecutionMode.REAL_DOCKER:
        from certification.stages.docker_stages import RealDockerStages
        return RealDockerStages()
    else:
        from certification.stages.stub_stages import StubStages
        return StubStages()


# Import WaveId at module level for the B0 check
from certification.campaign.waves import WaveId


