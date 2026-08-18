"""R2.10.9 — campaign readiness: the dry run that justifies scaling.

The gate that applies the campaign's own discipline to itself: do not scale
an unverified boundary. R2.10.6–8 verified the compilation boundary; Phase
31 will stress it at thousands-project scale. This suite proves the campaign
harness itself is trustworthy at small scale — deterministic, budget-
respecting, failure-classifying, ledger-faithful under parallel load — and
that every outcome records its full provenance chain. The acceptance
evidence:

  1.  the corpus covers all thirteen Phase-31 categories, and its entries
      are INTENTS (problems to solve), never representations to compile;
  2.  the harness is structurally an orchestrator, not an authority — no
      ISR-mutation or verifier-override surface in its source;
  3.  the dry run is deterministic under the same seed;
  4.  the dry run respects the declared resource budget;
  5.  every dry-run failure is classified — no silent UNKNOWNs;
  6.  the ledger stays intact under the harness's parallel load;
  7.  every successful outcome carries a chain-addressable provenance
      chain (intent -> ISR -> compilation -> verification);
  8.  the failure taxonomy distinguishes a non-recoverable contract
      violation from a recoverable timeout;
  9.  the intent->ISR dependency is confirmed: the real pipeline exists
      (IntentCompiler) but is LLM-driven, so the dry run uses a DECLARED
      deterministic stub and says so explicitly on every result;
  10. Option A (seventeenth use) — no new carriers, no matrix movement.
"""
from __future__ import annotations

import ast
import inspect
import tempfile

import pytest

from constitutional_architecture.isr.model import ISR
from tiannara.application.campaign.corpus import (
    CorpusIntent,
    GenerationCorpus,
    ProjectCategory,
)
from tiannara.application.campaign.dry_run import (
    CampaignDryRun,
    DryRunVerdict,
    budget_respected,
)
from tiannara.application.campaign.failure_taxonomy import (
    CompilationContractViolation,
    FailureCategory,
    FailureClassification,
    classify_failure,
)
from tiannara.application.campaign.harness import (
    CampaignCompilation,
    CampaignConfig,
    CampaignEvolution,
    CampaignHarness,
    CampaignResult,
    DeclaredIntentPipelineStub,
    DEFAULT_POPULATION,
    ResourceBudget,
    backend_for,
    target_for,
)
from tiannara.application.compilation.artifact_verification import (
    ArtifactVerifier,
    ConformanceEvidenceRegistry,
)
from tiannara.application.compilation.backend_capability_registry import (
    BackendRegistry,
)
from tiannara.application.compilation.backend_conformance import (
    BackendConformanceEvaluator,
)
from tiannara.application.compilation.consumption_contract import (
    ContaminationGuard,
)
from tiannara.application.compilation.integrity_gate import (
    CompilationIntegrityGate,
)
from tiannara.application.evolution.ledger import (
    EventType,
    EvolutionLedger,
)
from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_5_universal_evolution import domain_mutators

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def _intent(intent_id: str, category: ProjectCategory, problem: str) -> CorpusIntent:
    return CorpusIntent(
        intent_id=intent_id,
        category=category,
        problem_statement=problem,
        complexity_tier=2,
        acceptance_semantics=(
            "the system must demonstrably satisfy the declared problem",
        ),
        semantic_shape_hints=(),
    )


def dry_run_corpus() -> GenerationCorpus:
    """Two intents per category — the shape of Phase 31's space at tens of
    intents. Problem statements are technology-free by construction."""
    entries = [
        # CRUD_SAAS
        _intent("billing-01", ProjectCategory.CRUD_SAAS,
                "Operate a multi-tenant subscription billing service where "
                "tenants manage plans, invoices, and usage records."),
        _intent("workspace-02", ProjectCategory.CRUD_SAAS,
                "Run a shared project workspace where members organize "
                "tasks, milestones, and file attachments per workspace."),
        # ERP
        _intent("procurement-01", ProjectCategory.ERP,
                "Manage enterprise procurement across vendors, purchase "
                "orders, and goods receipts with audit trails."),
        _intent("accounting-02", ProjectCategory.ERP,
                "Operate an accounting cycle covering journals, ledgers, "
                "reconciliations, and period close tasks."),
        # BANKING
        _intent("retail-bank-01", ProjectCategory.BANKING,
                "Provide retail banking operations: accounts, transfers, "
                "settlements, and statement generation."),
        _intent("credit-02", ProjectCategory.BANKING,
                "Run a credit decisioning workflow: applications, "
                "underwriting reviews, approvals, and disbursements."),
        # HEALTHCARE
        _intent("clinic-01", ProjectCategory.HEALTHCARE,
                "Operate a clinic scheduling system: appointments, "
                "practitioners, reminders, and cancellation handling."),
        _intent("records-02", ProjectCategory.HEALTHCARE,
                "Manage patient records with consent tracking, treatment "
                "plans, and clinical audit trails."),
        # LOGISTICS
        _intent("freight-01", ProjectCategory.LOGISTICS,
                "Run a freight network: shipments, carriers, routing "
                "plans, and delivery proof capture."),
        _intent("warehouse-02", ProjectCategory.LOGISTICS,
                "Operate warehouse operations: receiving, putaway, "
                "picking, packing, and dispatch."),
        # AI_PLATFORM
        _intent("eval-01", ProjectCategory.AI_PLATFORM,
                "Provide a model evaluation platform: datasets, "
                "experiments, trials, and result comparisons."),
        _intent("recommend-02", ProjectCategory.AI_PLATFORM,
                "Run a recommendation service: item catalogs, interaction "
                "events, scoring jobs, and feedback loops."),
        # GAMING
        _intent("matchmaking-01", ProjectCategory.GAMING,
                "Operate a matchmaking service: lobbies, player ratings, "
                "match assignments, and result recording."),
        _intent("economy-02", ProjectCategory.GAMING,
                "Run a game economy: virtual goods, purchases, "
                "inventories, and market listings."),
        # IOT
        _intent("fleet-01", ProjectCategory.IOT,
                "Operate a device fleet: registrations, telemetry "
                "ingestion, alerts, and firmware update scheduling."),
        _intent("building-02", ProjectCategory.IOT,
                "Run a smart building service: sensors, zone settings, "
                "occupancy events, and comfort reports."),
        # ROBOTICS
        _intent("cell-01", ProjectCategory.ROBOTICS,
                "Operate a robot cell: task queues, motion plans, safety "
                "interlocks, and execution logs."),
        _intent("fleet-02", ProjectCategory.ROBOTICS,
                "Run a warehouse robot fleet: pick assignments, battery "
                "states, docking plans, and mission logs."),
        # DISTRIBUTED
        _intent("kv-01", ProjectCategory.DISTRIBUTED,
                "Operate a replicated key-value store: partitions, replica "
                "assignments, quorum reads, and consistency checks."),
        _intent("scheduler-02", ProjectCategory.DISTRIBUTED,
                "Run a distributed job scheduler: job definitions, "
                "workers, retries, and completion records."),
        # EMBEDDED
        _intent("controller-01", ProjectCategory.EMBEDDED,
                "Operate an embedded controller: sensor loops, actuator "
                "commands, watchdog events, and diagnostics."),
        _intent("telematics-02", ProjectCategory.EMBEDDED,
                "Run a telematics unit: trip recording, geofence events, "
                "upload queues, and configuration updates."),
        # API
        _intent("catalog-01", ProjectCategory.API,
                "Provide a public catalog service: product listings, "
                "availability checks, rate limits, and usage reports."),
        _intent("identity-02", ProjectCategory.API,
                "Run an identity verification service: verification "
                "requests, document checks, results, and review queues."),
        # STREAMING
        _intent("video-01", ProjectCategory.STREAMING,
                "Operate a live video pipeline: sources, transcoding "
                "jobs, playback sessions, and quality reports."),
        _intent("events-02", ProjectCategory.STREAMING,
                "Run an event streaming service: topics, producers, "
                "consumers, partitions, and delivery confirmations."),
    ]
    return GenerationCorpus(corpus_id="corpus-13", intents=tuple(entries))


class CampaignReadinessHarness:
    """The R2.10.5-8 foundations wired behind the campaign's black boxes."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger = EvolutionLedger(root=self._tmp.name)
        self.gate = CompilationIntegrityGate(ledger=self.ledger)
        self.guard = ContaminationGuard()
        self.conformance_registry = ConformanceEvidenceRegistry()
        self.evaluator = BackendConformanceEvaluator(
            integrity_gate=self.gate,
            contamination_guard=self.guard,
            ledger=self.ledger,
            conformance_registry=self.conformance_registry,
        )
        self.registry = BackendRegistry()
        self.verifier = ArtifactVerifier(
            ledger=self.ledger,
            conformance_registry=self.conformance_registry,
        )
        self.compilation = CampaignCompilation(
            self.registry, self.gate, self.evaluator,
            self.conformance_registry,
        )
        self.evolution = CampaignEvolution(domain_mutators_factory=domain_mutators)
        self.intent_pipeline = DeclaredIntentPipelineStub()
        self.harness = CampaignHarness(
            intent_pipeline=self.intent_pipeline,
            evolution_loop=self.evolution,
            compilation=self.compilation,
            verifier=self.verifier,
            ledger=self.ledger,
        )
        self.dry_runner = CampaignDryRun(self.harness)
        self.config = CampaignConfig(
            campaign_id="dry-run-1",
            corpus_id="corpus-13",
            resource_budget=ResourceBudget(
                max_parallel=4,
                max_duration_per_intent_ms=120_000,
                max_memory_per_intent_mb=1024,
            ),
            generations_per_intent=2,
            seed=7,
        )
        self.corpus = dry_run_corpus()
        self._verdict: DryRunVerdict | None = None

    def dry_run(self) -> DryRunVerdict:
        if self._verdict is None:
            self._verdict = self.dry_runner.run(self.corpus, self.config)
        return self._verdict

    def run_dry(self) -> CampaignResult:
        return self.harness.run(self.config, self.corpus)

    def corpus_categories(self) -> frozenset[ProjectCategory]:
        return self.corpus.categories_covered()

    def matrix_summary(self):
        from tiannara.application.evolution.isr_capability_audit import (
            ISRCapabilityAudit,
        )

        result = ISRCapabilityAudit().run(RECIPE)
        summary = result.summary()
        return (
            summary["expressed"],
            summary["partial"],
            summary["projected"],
            summary["missing"],
        )

    def recipe_isr_hash(self):
        return RECIPE.content_hash


@pytest.fixture
def campaign_harness() -> CampaignReadinessHarness:
    return CampaignReadinessHarness()


def test_corpus_covers_all_thirteen_categories(campaign_harness):
    assert campaign_harness.corpus_categories() == frozenset(ProjectCategory)
    assert len(campaign_harness.corpus.intents) >= 13


def test_corpus_entries_are_intents_not_representations(campaign_harness):
    """Corpus entries are problems to solve, never ISRs to compile."""
    for intent in campaign_harness.corpus.intents:
        assert intent.problem_statement
        assert intent.acceptance_semantics
        assert not hasattr(intent, "isr")


def test_harness_is_an_orchestrator_not_an_authority(campaign_harness):
    """Structural: the harness has no ISR-mutation or verifier-override
    surface."""
    tree = ast.parse(inspect.getsource(CampaignHarness))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert not any(
                m in fn for m in ("replace_gene", "mutate", "set_", "override_verdict")
            ), fn


def test_intent_pipeline_is_declared_not_silent(campaign_harness):
    """The intent->ISR pipeline exists (IntentCompiler) but is LLM-driven;
    the dry run derives ISRs through a DECLARED deterministic stub and says
    so explicitly on every campaign result."""
    assert campaign_harness.intent_pipeline.is_declared_stub is True
    assert campaign_harness.intent_pipeline.declared_assumptions
    result = campaign_harness.run_dry()
    assert result.declared_assumptions
    assert "DECLARED deterministic stub" in result.declared_assumptions[0]


def test_intent_pipeline_derives_a_constitutional_isr(campaign_harness):
    intent = campaign_harness.corpus.intents[0]
    isr = campaign_harness.intent_pipeline.derive(intent)
    assert isinstance(isr, ISR)
    assert isr.system.id == (
        f"{intent.category.value.lower().replace('_', '-')}-{intent.intent_id}-sys"
    )
    assert isr.provenance.mutation_description == f"intent:{intent.intent_id}"


def test_dry_run_is_deterministic(campaign_harness):
    assert campaign_harness.dry_run().harness_deterministic is True


def test_dry_run_respects_resource_budget(campaign_harness):
    assert campaign_harness.dry_run().resource_budget_respected is True


def test_every_failure_is_classified(campaign_harness):
    """No silent UNKNOWNs in the dry run — failures are understood, not
    buried."""
    assert campaign_harness.dry_run().all_failures_classified is True


def test_ledger_intact_under_parallel_load(campaign_harness):
    assert campaign_harness.dry_run().ledger_intact_under_load is True


def test_every_successful_outcome_carries_a_provenance_chain(campaign_harness):
    result = campaign_harness.run_dry()
    assert result.success_count == len(result.outcomes)
    assert result.failure_count == 0
    for outcome in result.outcomes:
        assert outcome.succeeded
        assert outcome.metrics is not None
        assert outcome.metrics.provenance_chain_ref is not None
        assert outcome.metrics.artifact_hash is not None
        event = campaign_harness.ledger.event_by_ref(
            outcome.metrics.provenance_chain_ref
        )
        assert event is not None
        assert event.event_type is EventType.GENERATION_OUTCOME
        assert event.payload["intent_id"] == outcome.intent_id
        assert event.payload["artifact_hash"] == outcome.metrics.artifact_hash
        assert event.payload["verification_verified"] is True


def test_dry_run_verdict_is_ready_to_scale(campaign_harness):
    verdict = campaign_harness.dry_run()
    assert verdict.ready_to_scale
    assert verdict.corpus_category_coverage == len(ProjectCategory)


def test_failure_taxonomy_distinguishes_contract_violation_from_transient(campaign_harness):
    """A compilation-contract violation is non-recoverable; a timeout is
    recoverable. The taxonomy keeps Phase 31's metrics diagnosable."""
    assert (
        classify_failure(
            CompilationContractViolation("gate D"), "compilation"
        ).recoverable
        is False
    )
    assert (
        classify_failure(CompilationContractViolation("gate D"), "compilation")
        .category
        is FailureCategory.COMPILATION_CONTRACT_VIOLATION
    )
    assert (
        classify_failure(TimeoutError(), "compilation").recoverable is True
    )
    assert (
        classify_failure(TimeoutError(), "compilation").category
        is FailureCategory.TIMEOUT
    )


def test_matrix_and_recipe_identity_unchanged(campaign_harness):
    assert campaign_harness.matrix_summary() == (12, 18, 0, 0)
    assert campaign_harness.recipe_isr_hash() == RECIPE_HASH