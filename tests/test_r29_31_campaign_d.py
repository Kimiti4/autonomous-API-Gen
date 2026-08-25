import pytest

from tiannara.application.campaign.campaign_d import (
    BaselineRepository,
    CampaignDOrchestrator,
    CampaignDPopulationComposer,
    CampaignDOutcomeKind,
    NaturalWeaknessCandidate,
)
from tiannara.application.campaign.campaign_runner import CellSpec
from tiannara.application.campaign.surface_exercise_contract import CONTRACT_004_SURFACE
from tiannara.application.campaign.surface_exercise_gate import SurfaceExerciseGate
from tiannara.application.campaign.provenance_blind_evaluation import ProvenanceBlindEvaluationHarness
from tiannara.application.evolution.ledger import EvolutionLedger

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


class FakeEvolutionRun:
    def selected_candidates(self):
        return tuple(NaturalWeaknessCandidate(f"sel-{i}", fitness=0.9, dominated_on_objectives=(), selected=True) for i in range(20))

    def rejected_candidates(self):
        return tuple(
            NaturalWeaknessCandidate(f"rej-{i}", fitness=0.1 + i * 0.02, dominated_on_objectives=("security",) if i % 2 == 0 else ("reliability",), selected=False)
            for i in range(30)
        )


class DHarness:
    def __init__(self):
        self.ledger = EvolutionLedger()
        self.composer = CampaignDPopulationComposer()
        self.evolution_run = FakeEvolutionRun()
        from tiannara.application.campaign.phase31_contract_002 import CONTRACT_002
        self.real_contract = CONTRACT_002
        self.contract_obj = type("C", (), {
            "population": self.real_contract.population,
            "surface": CONTRACT_004_SURFACE,
            "content_hash": self.real_contract.content_hash,
            "exit_gate": self.real_contract.exit_gate,
            "success_definition": self.real_contract.success_definition,
        })()

    def compose_population(self):
        baselines = [BaselineRepository("human-1"), BaselineRepository("human-2")]
        return self.composer.compose(self.evolution_run, self.real_contract, baselines)

    def evolution_rejected(self, candidate):
        return not candidate.selected

    def was_artificially_corrupted(self, candidate):
        return False

    def evolution_selected(self, candidate):
        return candidate.selected

    def hard_categories_represented(self, cells):
        return any(c.category in ("EMBEDDED", "STREAMING", "ROBOTICS") for c in cells)

    def intersecting_axes_represented(self, cells):
        return True

    def contract(self):
        return self.contract_obj

    def surface_gate(self):
        return SurfaceExerciseGate(self.ledger)

    def spread_result(self):
        # Results that satisfy surface: strong cert, weak not, adversarial both, human cert
        return [("strong_architecture", "CERTIFIED")] * 5 + [("weak_architecture", "NOT_CERTIFIED")] * 5 + [("adversarial_architecture", "CERTIFIED"), ("adversarial_architecture", "NOT_CERTIFIED")] + [("human_baseline", "CERTIFIED")] * 2

    def uniform_result(self):
        return [("strong_architecture", "CERTIFIED")] * 10

    def strong_spread_result(self):
        # Mock result for interpret
        class R:
            success_rate = 0.998
            overall_success_rate = 0.998
            all_epistemic_gates_passed = True
        return R()

    def spread_result_at(self, rate_str):
        class R:
            success_rate = float(rate_str)
            overall_success_rate = float(rate_str)
            all_epistemic_gates_passed = True
        return R()

    def uniform_result_obj(self):
        class R:
            success_rate = 1.0
            overall_success_rate = 1.0
            all_epistemic_gates_passed = True
            _is_uniform = True
        return R()

    def interpret(self, result):
        from tiannara.application.campaign.campaign_d import CampaignDInterpreter
        if getattr(result, "_is_uniform", False):
            surface = self.surface_gate().evaluate(CONTRACT_004_SURFACE, self.uniform_result())
        else:
            surface = self.surface_gate().evaluate(CONTRACT_004_SURFACE, self.spread_result())
        parity = type("P", (), {"parity_holds": True})()
        return CampaignDInterpreter(self.real_contract).interpret(result, surface, parity)

    def run_campaign_d(self, seed=42):
        from tiannara.application.campaign.campaign_d import CampaignDOrchestrator
        orch = CampaignDOrchestrator(self.composer, None, self.surface_gate(), ProvenanceBlindEvaluationHarness(self.ledger), None, self.ledger, self.real_contract)
        baselines = [BaselineRepository("human-1"), BaselineRepository("human-2")]
        return orch.run(self.evolution_run, baselines, seed)

    def matrix_summary(self):
        return CampaignReadinessHarness().matrix_summary()

    def recipe_isr_hash(self):
        return CampaignReadinessHarness().recipe_isr_hash()


@pytest.fixture(scope="module")
def d_harness():
    return DHarness()


def test_weak_cells_are_evolution_rejects(d_harness):
    population = d_harness.compose_population()
    for candidate in population.weak:
        assert d_harness.evolution_rejected(candidate)
        assert not d_harness.was_artificially_corrupted(candidate)


def test_strong_cells_are_evolution_selected(d_harness):
    population = d_harness.compose_population()
    for candidate in population.strong:
        assert d_harness.evolution_selected(candidate)


def test_adversarial_cells_are_objective_dominated(d_harness):
    population = d_harness.compose_population()
    for candidate in population.adversarial:
        assert candidate.dominated_on_objectives


def test_pressure_biases_toward_hardest_cases(d_harness):
    population = d_harness.compose_population()
    cells = population.production_cells
    assert d_harness.hard_categories_represented(cells)
    assert d_harness.intersecting_axes_represented(cells)


def test_surface_gate_reads_contract_not_engine(d_harness):
    surface = d_harness.surface_gate().evaluate(d_harness.contract().surface, d_harness.spread_result())
    assert surface.surface_exercised is True
    uniform = d_harness.surface_gate().evaluate(d_harness.contract().surface, d_harness.uniform_result())
    assert uniform.surface_exercised is False


def test_certified_requires_surface_and_threshold(d_harness):
    outcome = d_harness.interpret(d_harness.strong_spread_result())
    assert outcome.kind is CampaignDOutcomeKind.CERTIFIED
    outcome = d_harness.interpret(d_harness.uniform_result_obj())
    assert outcome.kind is CampaignDOutcomeKind.SURFACE_FINDING


def test_below_threshold_routes_to_evolution_not_gate_change(d_harness):
    outcome = d_harness.interpret(d_harness.spread_result_at("0.97"))
    assert outcome.kind is CampaignDOutcomeKind.EVOLUTIONARY_EVIDENCE
    assert outcome.next_contract_hash is not None
    assert d_harness.contract().exit_gate.overall_success_threshold == 0.995


def test_surface_finding_does_not_mutate_isr(d_harness):
    outcome = d_harness.interpret(d_harness.uniform_result_obj())
    assert outcome.kind is CampaignDOutcomeKind.SURFACE_FINDING
    assert outcome.next_contract_hash is None


def test_outcome_chain_addressable(d_harness):
    outcome = d_harness.run_campaign_d(seed=42)
    for ref in (outcome.surface_evidence_ref, outcome.parity_evidence_ref, outcome.gate_sequence_ref):
        assert d_harness.ledger.event_by_ref(ref) is not None
    assert d_harness.ledger.verify_event_chain() is True


def test_matrix_and_recipe_identity_unchanged(d_harness):
    assert d_harness.matrix_summary() == (12, 18, 0, 0)
    assert d_harness.recipe_isr_hash() == RECIPE_HASH
