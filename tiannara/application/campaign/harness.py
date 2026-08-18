"""R2.10.9 — the campaign harness.

Orchestrates intent → ISR → evolution → compilation → verification →
metrics across a corpus. Single responsibility: orchestrate and measure.
The harness NEVER reaches into the ISR or the verifier — it invokes the
frozen foundations (R2.10.5 evolution, R2.10.6–8 compilation/verification)
as black boxes and records every outcome's provenance chain into the
ledger. It is an evidence collector, not an authority.

Declared seams (the campaign says so, never silently approximates):

  * ``DeclaredIntentPipelineStub`` — the constitution's Problem →
    Requirements → Requirement Graph → ISR pipeline exists
    (``tiannara.application.intent.IntentCompiler``) but is LLM-driven and
    therefore not hermetic. The dry run derives ISRs deterministically
    through this DECLARED stub; the declaration is recorded on every
    campaign result. Phase 31 injects the real pipeline behind the same
    duck-typed surface.
  * ``CampaignEvolution`` — wraps the frozen R2.10.5 loop and rebuilds the
    final ISR deterministically from the recorded lineage.
  * ``CampaignCompilation`` — R2.10.6–8 as a black box: conforms the
    category's backend against each intent's ISR (evidence registered),
    compiles through the frozen gates, and assembles the R2.10.8
    provenance claim.
"""
from __future__ import annotations

import dataclasses
import hashlib
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from constitutional_architecture.isr.model import (
    AcceptanceCriterion,
    AnchorAuthority,
    ArchitecturalBoundary,
    BusinessCapability,
    CompatibilityPolicy,
    DataMigrationIntent,
    DegradationPolicy,
    DeploymentIntent,
    DocumentationAudience,
    DocumentationIntent,
    DocumentationPurpose,
    Entity,
    EvolutionObjective,
    EvolutionPolicy,
    FailureMode,
    ISR,
    ISRProvenance,
    Interface,
    InterfaceType,
    Module,
    ObjectiveDimension,
    ObjectiveDirection,
    ObjectiveTier,
    ObligationKind,
    ProtectedRegion,
    ProtectionKind,
    ProtectionPolicy,
    RecoveryBehavior,
    RecoveryObjective,
    ReliabilityRequirement,
    Requirement,
    RolloutStrategy,
    StateType,
    System,
    TemporalConstraint,
    TemporalConstraintKind,
    TestingAnchor,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from tiannara.application.compilation.artifact_verification import (
    ArtifactProvenance,
    compilation_event_ref_for,
    conformance_event_ref_for,
    provenance_claim,
)
from tiannara.application.compilation.consumption_contract import (
    CompilationTarget,
)
from tiannara.application.evolution.identity_index import IdentityIndex
from tiannara.application.evolution.ledger import (
    EvolutionLedger,
    stable_isr_hash,
)
from tiannara.application.evolution.protection import (
    EvolutionProtectionEvaluator,
)
from tiannara.application.evolution.semantic_evolution_gate import (
    SemanticEvolutionGate,
    apply_multi_gene_delta,
)
from tiannara.application.evolution.universal_evolution import (
    UniversalEvolutionLoop,
    UniversalSelector,
    UniversalVariationOperator,
)

from .corpus import CorpusIntent, ProjectCategory
from .failure_taxonomy import FailureClassification, classify_failure

DEFAULT_POPULATION = 4


# -- the realization selection (per category, declaration-backed) --------------

#: category -> backend, drawn from the R2.10.7 declarations: every category's
#: target is one the backend actually supports (fastapi SUPPORTED
#: behavior_transitions + business_capabilities; postgres SUPPORTED
#: data_migrations — ERP/LOGISTICS carry migration semantics).
_CATEGORY_BACKENDS: dict[ProjectCategory, str] = {
    ProjectCategory.CRUD_SAAS: "fastapi",
    ProjectCategory.ERP: "postgres",
    ProjectCategory.BANKING: "fastapi",
    ProjectCategory.HEALTHCARE: "fastapi",
    ProjectCategory.LOGISTICS: "postgres",
    ProjectCategory.AI_PLATFORM: "fastapi",
    ProjectCategory.GAMING: "fastapi",
    ProjectCategory.IOT: "fastapi",
    ProjectCategory.ROBOTICS: "fastapi",
    ProjectCategory.DISTRIBUTED: "fastapi",
    ProjectCategory.EMBEDDED: "fastapi",
    ProjectCategory.API: "fastapi",
    ProjectCategory.STREAMING: "fastapi",
}


def backend_for(category: ProjectCategory) -> str:
    return _CATEGORY_BACKENDS[category]


def target_for(category: ProjectCategory, registry: Any = None) -> CompilationTarget:
    """The realization selection for a project category: a registry target
    the category's backend actually supports, with a category-scoped
    target_id (the realization selection is never embedded in the ISR)."""
    backend_id = _CATEGORY_BACKENDS[category]
    if registry is None:
        from tiannara.application.compilation.backend_capability_registry import (
            BackendRegistry,
        )

        registry = BackendRegistry()
    base = registry.target(backend_id)
    return dataclasses.replace(
        base, target_id=f"{category.value.lower()}-{base.target_id}"
    )


# -- the declared intent pipeline stub -----------------------------------------

def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


class DeclaredIntentPipelineStub:
    """DECLARED deterministic stand-in for the intent → ISR pipeline.

    The constitution's top half (Problem → Requirements → Requirement Graph
    → ISR) exists as ``tiannara.application.intent.IntentCompiler`` but is
    LLM-driven and therefore not hermetic: a campaign through it cannot be
    deterministic. This stub derives a deterministic constitutional ISR
    from a ``CorpusIntent`` — the same shape R2.10.4/5/6/7/8 proved — and
    is DECLARED, never silent: every campaign result carries
    ``declared_assumptions`` naming the stand-in. Phase 31 injects the real
    pipeline behind the same duck-typed ``derive`` surface.
    """

    is_declared_stub = True

    declared_assumptions: tuple[str, ...] = (
        "intent_derivation: DECLARED deterministic stub (the constitution's "
        "Problem -> Requirements -> Requirement Graph -> ISR pipeline exists "
        "as tiannara.application.intent.IntentCompiler but is LLM-driven and "
        "not hermetic; the dry run derives ISRs deterministically through "
        "this declared stub — never a silent approximation of the real "
        "pipeline)",
    )

    def derive(self, intent: CorpusIntent) -> ISR:
        """A deterministic constitutional ISR for one corpus intent.

        The intent's problem statement becomes the capability intent and
        the requirement statement; identifiers derive from the intent's
        category + id, so every intent yields a distinct, stable ISR. The
        ISR carries the full semantic surface (behavior, capabilities,
        migrations, requirements, reliability, deployment, documentation,
        evolution policy) so the R2.10.5 search genuinely has material to
        evolve.
        """
        tag = _slug(f"{intent.category.value}-{intent.intent_id}")
        system_id = f"{tag}-sys"
        e1, e2 = f"{tag}-e1", f"{tag}-e2"
        w1 = f"{tag}-w1"
        capability = f"{tag}-cap"
        problem = intent.problem_statement.strip()
        acceptance = (
            intent.acceptance_semantics[0] if intent.acceptance_semantics else problem
        )
        return ISR(
            system=System(
                id=system_id,
                name=f"{intent.category.value} {intent.intent_id}",
                modules=(
                    Module(
                        id=f"{tag}-m",
                        name=f"{tag}-m",
                        entities=(
                            Entity(id=e1, name=e1),
                            Entity(id=e2, name=e2),
                        ),
                        workflows=(
                            Workflow(
                                id=w1,
                                name=f"workflow {w1}",
                                states=(
                                    WorkflowState(
                                        id=f"{w1}-start",
                                        name="started",
                                        state_type=StateType.INTERMEDIATE,
                                        metadata={"awaits": f"op_{tag}"},
                                    ),
                                    WorkflowState(
                                        id=f"{w1}-done",
                                        name="done",
                                        state_type=StateType.FINAL,
                                    ),
                                ),
                                transitions=(
                                    WorkflowTransition(
                                        id=f"{w1}-t1",
                                        name="resolve",
                                        from_state_id=f"{w1}-start",
                                        to_state_id=f"{w1}-done",
                                        trigger=f"op_{tag}",
                                    ),
                                ),
                            ),
                        ),
                        interfaces=(
                            Interface(
                                id=f"{tag}-i1",
                                name=f"{tag}-i1",
                                interface_type=InterfaceType.REST,
                            ),
                        ),
                        temporal_constraints=(
                            TemporalConstraint(
                                constraint_id=f"{tag}-t1.deadline",
                                kind=TemporalConstraintKind.TRANSITION_DEADLINE,
                                target_ref=f"{w1}-t1",
                                duration_ms=250,
                            ),
                        ),
                        data_migrations=(
                            DataMigrationIntent(
                                migration_id=f"{tag}-m1",
                                source_schema_ref=e1,
                                target_schema_ref=e2,
                                compatibility_policy=CompatibilityPolicy.BACKWARD,
                                preservation_refs=(e1,),
                                rollback_required=True,
                                rollback_target_ref=e1,
                                rollback_invariants=(f"{e1} intact",),
                                postconditions=(f"{e2} valid",),
                            ),
                        ),
                    ),
                ),
                business_capabilities=(
                    BusinessCapability(
                        capability_id=capability,
                        intent=problem,
                        behavior_refs=(w1,),
                        interface_refs=(f"{tag}-i1",),
                    ),
                ),
                reliability_requirements=(
                    ReliabilityRequirement(
                        requirement_id=f"{tag}-rr1",
                        target_refs=(capability,),
                        failure_modes=(
                            FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                        ),
                        recovery_objectives=(
                            RecoveryObjective(
                                failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                                required_behavior=RecoveryBehavior.EVENTUAL_RECOVERY,
                                max_recovery_duration_ms=5000,
                            ),
                        ),
                        degradation_policy=DegradationPolicy.NO_DEGRADATION,
                        preservation_invariants=(f"{capability} coherent",),
                    ),
                ),
                architectural_boundaries=(
                    ArchitecturalBoundary(
                        boundary_id=f"{tag}-b1",
                        member_refs=(f"{tag}-m",),
                        forbidden_dependency_refs=(),
                        protected=False,
                        crossing_invariants=(
                            "no cross without declared intent",
                        ),
                    ),
                ),
                requirements=(
                    Requirement(
                        requirement_id=f"{tag}-req",
                        statement=acceptance,
                        target_refs=(capability,),
                        acceptance_refs=(f"{tag}-crit",),
                        constraint_refs=(w1,),
                    ),
                ),
                acceptance_criteria=(
                    AcceptanceCriterion(
                        criterion_id=f"{tag}-crit",
                        obligation=acceptance,
                        kind=ObligationKind.PRESENCE,
                        subject_refs=(capability,),
                    ),
                ),
                deployment_intents=(
                    DeploymentIntent(
                        deployment_id=f"{tag}-dep1",
                        target_refs=(capability,),
                        rollout_strategy=RolloutStrategy.CANARY,
                        rollback_required=True,
                        rollback_target_ref=capability,
                        rollback_invariants=(
                            "the capability's state is preserved",
                        ),
                    ),
                ),
                testing_anchors=(
                    TestingAnchor(
                        anchor_id=f"{tag}-anchor1",
                        subject_refs=(w1,),
                        obligation_refs=(f"{tag}-crit",),
                        evidence_requirements=(
                            "the declared obligation must be demonstrable",
                        ),
                        protection_policy=ProtectionPolicy.EVOLVABLE,
                        authority=AnchorAuthority.DERIVED,
                    ),
                ),
                documentation_intents=(
                    DocumentationIntent(
                        documentation_id=f"{tag}-doc1",
                        subject_refs=(capability,),
                        purpose=DocumentationPurpose.OPERATIONAL_REFERENCE,
                        audience=DocumentationAudience.DEVELOPER,
                        obligations=(
                            "the capability's declared behavior must be "
                            "documented",
                        ),
                    ),
                ),
                evolution_objectives=(
                    EvolutionObjective(
                        objective_id=f"{tag}-opt1",
                        dimension=ObjectiveDimension.RELIABILITY,
                        direction=ObjectiveDirection.MAXIMIZE,
                        tier=ObjectiveTier.OPTIMIZATION,
                        priority=0,
                        weight=1.0,
                        subject_refs=(f"{tag}-rr1",),
                    ),
                ),
                protected_regions=(
                    ProtectedRegion(
                        region_id=f"{tag}-region_1",
                        subject_refs=(f"{tag}-anchor1", f"{tag}-b1"),
                        protection_kind=ProtectionKind.IMMUTABLE,
                    ),
                ),
                evolution_policies=(
                    EvolutionPolicy(
                        policy_id=f"{tag}-policy1",
                        objective_refs=(f"{tag}-opt1",),
                    ),
                ),
            ),
            provenance=ISRProvenance(
                parent_hash=f"intent:{intent.intent_id}",
                mutation_description=f"intent:{intent.intent_id}",
            ),
        )


# -- R2.10.5 as a black box ----------------------------------------------------

@dataclass(frozen=True)
class CampaignEvolutionResult:
    final_isr: Any
    final_isr_semantic_hash: str
    generations_run: int
    reconstructable: bool


class CampaignEvolution:
    """R2.10.5 as a black box for the campaign: one fresh loop, gate, and
    ledger per intent run.

    The frozen loop scopes its byte-exact reconstruction by ledger-length
    slices and keeps per-run state (``_run_evolution_id``) on the instance,
    so the R2.10.5 design assumes one loop per run. Parallel campaign
    threads sharing a loop would leak deltas and evolution ids across
    intents, so the campaign isolates every run behind fresh instances —
    the campaign ledger remains the durable evidence ledger (outcomes,
    compilations, verifications) while per-run evolution internals live in
    the run's own ledger. The final ISR is rebuilt deterministically from
    the recorded lineage (``apply_multi_gene_delta`` through the public
    surface — the same application seam the gate itself uses).
    """

    def __init__(
        self,
        domain_mutators_factory: Any,
        identity_index: Any = None,
        protection: Any = None,
        authorization: Any = None,
    ) -> None:
        self._domain_mutators_factory = domain_mutators_factory
        self._identity_index = identity_index
        self._protection = protection
        self._authorization = authorization

    def run(
        self,
        initial_isr: Any,
        generations: int,
        population_size: int,
        seed: int,
    ) -> CampaignEvolutionResult:
        identity_index = self._identity_index or IdentityIndex
        run_ledger = EvolutionLedger()
        gate = SemanticEvolutionGate(
            identity_index=identity_index,
            protection=self._protection
            or EvolutionProtectionEvaluator(authority=None),
            ledger=run_ledger,
        )
        loop = UniversalEvolutionLoop(
            variation=UniversalVariationOperator(
                identity_index=identity_index,
                domain_mutators=self._domain_mutators_factory(),
            ),
            semantic_gate=gate,
            selector=UniversalSelector(),
            ledger=run_ledger,
            identity_index=identity_index,
            authorization=self._authorization,
        )
        result = loop.run(initial_isr, generations, population_size, seed)
        final = initial_isr
        for record in result.lineage:
            final = apply_multi_gene_delta(final, record.selected_delta, 0)
        assert stable_isr_hash(final) == result.final_isr_semantic_hash
        return CampaignEvolutionResult(
            final_isr=final,
            final_isr_semantic_hash=result.final_isr_semantic_hash,
            generations_run=result.generations_run,
            reconstructable=result.reconstructable,
        )


# -- R2.10.6-8 as a black box --------------------------------------------------

@dataclass(frozen=True)
class CompiledDerivation:
    """One compilation plus its R2.10.8 provenance claim, as the verifier
    and the ledger see it."""

    artifact: dict[str, Any]
    provenance: ArtifactProvenance
    artifact_hash: str
    isr_hash: str
    target_id: str
    backend_id: str


class CampaignCompilation:
    """R2.10.6–8 as a black box for the campaign.

    Per intent: conform the category's backend against that intent's ISR
    (the frozen gates run; the COMPILATION event is chain-recorded; the
    conformance evidence is registered — the verifier judges that it
    EXISTS, never re-runs it), then compile and assemble the R2.10.8 claim.
    """

    def __init__(
        self,
        registry: Any,
        gate: Any,
        evaluator: Any,
        conformance_registry: Any,
    ) -> None:
        self._registry = registry
        self._gate = gate
        self._evaluator = evaluator
        self._conformance_registry = conformance_registry
        self._by_target_id: dict[str, str] = {
            target_for(category, registry).target_id: _CATEGORY_BACKENDS[category]
            for category in ProjectCategory
        }

    def compile(self, isr: Any, target: CompilationTarget) -> CompiledDerivation:
        backend_id = self._by_target_id.get(target.target_id)
        if backend_id is None:
            raise ValueError(
                f"no declared backend for target {target.target_id!r} — "
                "targets must come from campaign target_for()"
            )
        adapter = self._registry.adapter(backend_id)
        report = self._evaluator.conform(adapter, isr, target)
        self._evaluator.record_report(report)
        result = adapter.compile(isr, target)
        claim = provenance_claim(
            result,
            compilation_event_ref_for(result),
            conformance_event_ref_for(report),
        )
        return CompiledDerivation(
            artifact=result.artifact,
            provenance=claim,
            artifact_hash=result.artifact_hash,
            isr_hash=result.isr_hash,
            target_id=result.target_id,
            backend_id=result.backend_id,
        )


# -- the harness ---------------------------------------------------------------

@dataclass(frozen=True)
class ResourceBudget:
    max_parallel: int
    max_duration_per_intent_ms: int
    max_memory_per_intent_mb: int


@dataclass(frozen=True)
class CampaignConfig:
    campaign_id: str
    corpus_id: str
    resource_budget: ResourceBudget
    generations_per_intent: int
    seed: int


@dataclass(frozen=True)
class GenerationMetrics:
    compilation_succeeded: bool
    verification_verified: bool
    deployment_attempted: bool
    artifact_hash: str | None
    provenance_chain_ref: str | None
    duration_ms: int


@dataclass(frozen=True)
class GenerationOutcome:
    intent_id: str
    category: ProjectCategory
    succeeded: bool
    failure: FailureClassification | None
    metrics: GenerationMetrics | None


@dataclass(frozen=True)
class CampaignResult:
    campaign_id: str
    outcomes: tuple[GenerationOutcome, ...]
    success_count: int
    failure_count: int
    ledger_intact: bool
    declared_assumptions: tuple[str, ...] = ()


class CampaignHarness:
    """Orchestrates intent → ISR → evolution → compilation → verification →
    metrics across a corpus.

    Single responsibility: orchestrate and measure. The harness NEVER
    reaches into the ISR or the verifier — it invokes the frozen foundations
    (R2.10.5 evolution, R2.10.6–8 compilation/verification) as black boxes
    and records every outcome's provenance chain into the ledger. It is an
    evidence collector, not an authority: there is no ISR-mutation surface
    and no verifier-override surface. Parallel execution (``max_parallel``)
    preserves determinism via per-intent seeds and serialized ledger
    appends.
    """

    def __init__(
        self,
        intent_pipeline: Any,
        evolution_loop: Any,
        compilation: Any,
        verifier: Any,
        ledger: Any,
    ) -> None:
        self._intent_pipeline = intent_pipeline  # intent -> ISR (constitution's top half)
        self._evolution_loop = evolution_loop  # R2.10.5
        self._compilation = compilation  # R2.10.6-8
        self._verifier = verifier  # R2.10.8
        self._ledger = ledger

    def run(
        self, config: CampaignConfig, corpus: Any
    ) -> CampaignResult:
        intents = tuple(corpus.intents)
        max_workers = max(
            1, min(config.resource_budget.max_parallel, len(intents))
        )
        if max_workers > 1:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                outcomes = list(
                    pool.map(
                        lambda intent: self._run_one(intent, config), intents
                    )
                )
        else:
            outcomes = [self._run_one(intent, config) for intent in intents]
        return CampaignResult(
            campaign_id=config.campaign_id,
            outcomes=tuple(outcomes),
            success_count=sum(1 for o in outcomes if o.succeeded),
            failure_count=sum(1 for o in outcomes if not o.succeeded),
            ledger_intact=self._ledger.verify_event_chain(),
            declared_assumptions=self._declared_assumptions(),
        )

    def _declared_assumptions(self) -> tuple[str, ...]:
        assumptions = tuple(
            getattr(self._intent_pipeline, "declared_assumptions", ())
        )
        return assumptions

    def _seed_for(self, intent: CorpusIntent, config: CampaignConfig) -> int:
        """Per-intent deterministic seed: the campaign's determinism never
        depends on thread scheduling or on other intents."""
        digest = hashlib.sha256(
            f"{config.seed}:{intent.intent_id}".encode("utf-8")
        ).hexdigest()
        return int(digest[:8], 16)

    def _run_one(
        self, intent: CorpusIntent, config: CampaignConfig
    ) -> GenerationOutcome:
        started = time.perf_counter()
        try:
            try:
                isr = self._intent_pipeline.derive(intent)
            except Exception as error:  # noqa: BLE001 — campaign boundary
                return self._failed(
                    intent, classify_failure(error, "intent_derivation")
                )
            try:
                evolved = self._evolution_loop.run(
                    isr,
                    config.generations_per_intent,
                    population_size=DEFAULT_POPULATION,
                    seed=self._seed_for(intent, config),
                )
            except Exception as error:  # noqa: BLE001 — campaign boundary
                return self._failed(
                    intent, classify_failure(error, "evolution")
                )
            try:
                compiled = self._compilation.compile(
                    evolved.final_isr, target_for(intent.category)
                )
            except Exception as error:  # noqa: BLE001 — campaign boundary
                return self._failed(
                    intent, classify_failure(error, "compilation")
                )
            try:
                verified = self._verifier.verify(
                    compiled.artifact, compiled.provenance, evolved.final_isr
                )
            except Exception as error:  # noqa: BLE001 — campaign boundary
                return self._failed(
                    intent, classify_failure(error, "verification")
                )
            metrics = GenerationMetrics(
                compilation_succeeded=True,
                verification_verified=verified.verified,
                deployment_attempted=False,
                artifact_hash=compiled.artifact_hash,
                provenance_chain_ref=self._ledger.record_generation_outcome(
                    intent.intent_id,
                    compiled,
                    verified,
                    campaign_id=config.campaign_id,
                ),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            return GenerationOutcome(
                intent.intent_id,
                intent.category,
                verified.verified,
                None,
                metrics,
            )
        except Exception as error:  # noqa: BLE001 — campaign boundary
            return self._failed(intent, classify_failure(error, "unknown"))

    def _failed(
        self, intent: CorpusIntent, failure: FailureClassification
    ) -> GenerationOutcome:
        return GenerationOutcome(
            intent.intent_id, intent.category, False, failure, None
        )