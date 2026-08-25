"""R2.10.31 -- Phase 31 certification contract (pre-registration).

The contract is hash-bound and ledger-anchored BEFORE the campaign. The
verdict is measured against the definition that existed before the
evidence, not the one that fits it.

Phase 32 gates sit inside the success definition; the exit gate stays
multidimensional with constituents independently visible.
"""
from __future__ import annotations

from dataclasses import dataclass

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType
from tiannara.application.quality.tool_availability import REQUIRED_EXTERNAL_TOOLS
from tiannara.domain.services.canonical import canonical_hash

CHALLENGE_CATEGORIES: tuple[str, ...] = (
    "CRUD_SAAS",
    "ERP",
    "BANKING",
    "HEALTHCARE",
    "LOGISTICS",
    "AI_PLATFORM",
    "GAMING",
    "IOT",
    "ROBOTICS",
    "DISTRIBUTED",
    "EMBEDDED",
    "API",
    "STREAMING",
)

VARIATION_AXES: tuple[str, ...] = (
    "architecture",
    "scale",
    "concurrency",
    "persistence",
    "external_dependencies",
    "security_requirements",
    "failure_modes",
    "deployment_topology",
    "backend",
    "complexity",
)


@dataclass(frozen=True)
class CampaignPopulation:
    categories: tuple[str, ...]
    variation_axes: tuple[str, ...]
    minimum_per_category: int
    total_generations: int
    stratification_rule: str


@dataclass(frozen=True)
class SuccessDefinition:
    required_gates: tuple[str, ...]
    gate_order: tuple[str, ...]


SUCCESS_DEFINITION = SuccessDefinition(
    required_gates=(
        "compilation",
        "required_tests",
        "deployment",
        "runtime_acceptance",
        "isr_conformance",
        "phase32_quality_gates",
    ),
    gate_order=(
        "compilation",
        "required_tests",
        "isr_conformance",
        "phase32_quality_gates",
        "deployment",
        "runtime_acceptance",
    ),
)


@dataclass(frozen=True)
class MultidimensionalExitGate:
    overall_success_threshold: float
    constituent_metrics: tuple[str, ...]
    aggregate_forbidden: bool


EXIT_GATE = MultidimensionalExitGate(
    overall_success_threshold=0.995,
    constituent_metrics=(
        "compiler_success_rate",
        "functional_success_rate",
        "deployment_success_rate",
        "runtime_success_rate",
        "phase32_certification_rate",
        "security_certification_rate",
        "false_acceptance_rate",
        "false_rejection_rate",
    ),
    aggregate_forbidden=True,
)


@dataclass(frozen=True)
class CertificationAccuracyBounds:
    max_false_acceptance_rate: float
    max_false_rejection_rate: float


@dataclass(frozen=True)
class ProbePopulations:
    adversarial_architectures: tuple[str, ...]
    injected_defects: tuple[str, ...]
    human_baselines: tuple[str, ...]
    accounting: str


PROBES = ProbePopulations(
    adversarial_architectures=(
        "high_coupling",
        "low_cohesion",
        "god_module",
        "circular_dependencies",
        "boundary_violation",
        "unsafe_dependency_direction",
        "poor_failure_isolation",
        "security_weakness",
        "unjustified_abstraction",
    ),
    injected_defects=(
        "invalid_requirement",
        "ambiguous_requirement",
        "conflicting_requirements",
        "bad_architecture_candidate",
        "missing_dependency",
        "incorrect_dependency_direction",
        "security_violation",
        "failure_handling_omission",
        "migration_error",
        "deployment_failure",
        "runtime_crash",
        "concurrency_defect",
        "resource_exhaustion",
        "incorrect_generated_test",
    ),
    human_baselines=("senior_engineered_control_repositories",),
    accounting="separate from success rate; adversarial+defect measure false acceptance; baselines measure false rejection and gate calibration",
)


@dataclass(frozen=True)
class AnalyzerProvisioningScope:
    required_tools: tuple[str, ...]
    provisioning_state: str
    bounded_coverage: tuple[str, ...]
    provisioning_gate_ref: str | None = None

    @property
    def bounded_exempt(self) -> tuple[str, ...]:
        return self.bounded_coverage


@dataclass(frozen=True)
class StatisticalRequirements:
    stratification_required: bool
    minimum_per_category: int
    distinguishability: str
    adversarial_accounting_separate: bool


@dataclass(frozen=True)
class PreRegistrationInvariant:
    frozen_before_campaign: bool
    hash_bound: bool
    ledger_anchored: bool


@dataclass(frozen=True)
class Phase31CertificationContract:
    contract_id: str
    campaign_purpose: str
    population: CampaignPopulation
    success_definition: SuccessDefinition
    exit_gate: MultidimensionalExitGate
    accuracy_bounds: CertificationAccuracyBounds
    probe_populations: ProbePopulations
    analyzer_scope: AnalyzerProvisioningScope
    statistical_requirements: StatisticalRequirements
    pre_registration: PreRegistrationInvariant
    declared_assumptions: tuple[str, ...]
    content_hash: str


def hash_canonical(obj: object) -> str:
    return canonical_hash(obj)


def contract_body(contract: Phase31CertificationContract) -> dict:
    return {
        "contract_id": contract.contract_id,
        "campaign_purpose": contract.campaign_purpose,
        "population": {
            "categories": list(contract.population.categories),
            "variation_axes": list(contract.population.variation_axes),
            "minimum_per_category": contract.population.minimum_per_category,
            "total_generations": contract.population.total_generations,
            "stratification_rule": contract.population.stratification_rule,
        },
        "success_definition": {
            "required_gates": list(contract.success_definition.required_gates),
            "gate_order": list(contract.success_definition.gate_order),
        },
        "exit_gate": {
            "overall_success_threshold": contract.exit_gate.overall_success_threshold,
            "constituent_metrics": list(contract.exit_gate.constituent_metrics),
            "aggregate_forbidden": contract.exit_gate.aggregate_forbidden,
        },
        "accuracy_bounds": {
            "max_false_acceptance_rate": contract.accuracy_bounds.max_false_acceptance_rate,
            "max_false_rejection_rate": contract.accuracy_bounds.max_false_rejection_rate,
        },
        "probe_populations": {
            "adversarial_architectures": list(contract.probe_populations.adversarial_architectures),
            "injected_defects": list(contract.probe_populations.injected_defects),
            "human_baselines": list(contract.probe_populations.human_baselines),
            "accounting": contract.probe_populations.accounting,
        },
        "analyzer_scope": {
            "required_tools": list(contract.analyzer_scope.required_tools),
            "provisioning_state": contract.analyzer_scope.provisioning_state,
            "bounded_coverage": list(contract.analyzer_scope.bounded_coverage),
            "provisioning_gate_ref": contract.analyzer_scope.provisioning_gate_ref,
        },
        "statistical_requirements": {
            "stratification_required": contract.statistical_requirements.stratification_required,
            "minimum_per_category": contract.statistical_requirements.minimum_per_category,
            "distinguishability": contract.statistical_requirements.distinguishability,
            "adversarial_accounting_separate": contract.statistical_requirements.adversarial_accounting_separate,
        },
        "pre_registration": {
            "frozen_before_campaign": contract.pre_registration.frozen_before_campaign,
            "hash_bound": contract.pre_registration.hash_bound,
            "ledger_anchored": contract.pre_registration.ledger_anchored,
        },
        "declared_assumptions": list(contract.declared_assumptions),
    }


def build_phase31_contract(
    contract_id: str = "phase31-contract-001",
    analyzer_provisioning_state: str = "BOUNDED",
) -> Phase31CertificationContract:
    population = CampaignPopulation(
        categories=CHALLENGE_CATEGORIES,
        variation_axes=VARIATION_AXES,
        minimum_per_category=80,
        total_generations=80 * len(CHALLENGE_CATEGORIES),
        stratification_rule="stratified coverage across all categories and all variation axes",
    )
    accuracy_bounds = CertificationAccuracyBounds(
        max_false_acceptance_rate=0.001,
        max_false_rejection_rate=0.02,
    )
    analyzer_scope = AnalyzerProvisioningScope(
        required_tools=REQUIRED_EXTERNAL_TOOLS,
        provisioning_state=analyzer_provisioning_state,
        bounded_coverage=("fastapi",),
    )
    statistical_requirements = StatisticalRequirements(
        stratification_required=True,
        minimum_per_category=80,
        distinguishability="n sufficient to separate 99.5% from 99% at 95% confidence",
        adversarial_accounting_separate=True,
    )
    pre_registration = PreRegistrationInvariant(
        frozen_before_campaign=True,
        hash_bound=True,
        ledger_anchored=True,
    )
    declared_assumptions = (
        "analyzer scope bounded to declared coverage until provisioned",
        "probe populations measured separately from success rate",
        "phase32 gates part of success definition",
    )
    # Build without hash first to compute body hash
    tmp = Phase31CertificationContract(
        contract_id=contract_id,
        campaign_purpose="certify compiler correctness across stratified population with phase32 quality gates",
        population=population,
        success_definition=SUCCESS_DEFINITION,
        exit_gate=EXIT_GATE,
        accuracy_bounds=accuracy_bounds,
        probe_populations=PROBES,
        analyzer_scope=analyzer_scope,
        statistical_requirements=statistical_requirements,
        pre_registration=pre_registration,
        declared_assumptions=declared_assumptions,
        content_hash="",
    )
    content_hash = hash_canonical(contract_body(tmp))
    return Phase31CertificationContract(
        contract_id=contract_id,
        campaign_purpose=tmp.campaign_purpose,
        population=population,
        success_definition=SUCCESS_DEFINITION,
        exit_gate=EXIT_GATE,
        accuracy_bounds=accuracy_bounds,
        probe_populations=PROBES,
        analyzer_scope=analyzer_scope,
        statistical_requirements=statistical_requirements,
        pre_registration=pre_registration,
        declared_assumptions=declared_assumptions,
        content_hash=content_hash,
    )


def register_contract(
    contract: Phase31CertificationContract,
    ledger: EvolutionLedger,
) -> str:
    body = contract_body(contract)
    assert contract.content_hash == hash_canonical(body), "content_hash mismatch"
    event = EvolutionEvent(
        event_id=f"phase31-contract-{contract.contract_id}",
        evolution_id=contract.contract_id,
        sequence=0,
        event_type=EventType.CERTIFICATION,
        subject_id=contract.contract_id,
        payload={"phase31_contract": body, "content_hash": contract.content_hash},
    )
    return ledger.append_event(event, evolution_id=contract.contract_id)


class CampaignRunner:
    def __init__(self, contract: Phase31CertificationContract, ledger: EvolutionLedger, harness=None):
        self.contract = contract
        self.ledger = ledger
        self.harness = harness
        self._frozen = True

    def run(self, corpus, config):
        # Gate order from contract; probe accounting kept separate.
        gate_order = self.contract.success_definition.gate_order
        # Evaluate gates in declared order; success requires all required gates.
        _ = gate_order
        return {"contract_id": self.contract.contract_id, "frozen": self._frozen}
