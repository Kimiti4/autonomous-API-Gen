import ast
import inspect
import pytest

from tiannara.application.campaign.defect_injection import (
    DEFECT_MUTATIONS,
    DefectInjector,
    DefectInjectionCampaign,
    CampaignCGate,
    semantic_hash,
)
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.domain.services.canonical import canonical_hash

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


def _strong_isr():
    h = CampaignReadinessHarness()
    # Build a simple strong ISR via direct construction
    from constitutional_architecture.isr.model import ISR, System, BusinessCapability, Module, Entity
    cap = BusinessCapability(capability_id="CAP-STRONG", intent="strong capability")
    mod = Module(id="MOD-STRONG", name="MOD-STRONG", entities=(Entity(id="e1", name="e1"),))
    sys = System(id="strong-sys", name="StrongSystem", modules=(mod,), business_capabilities=(cap,))
    return ISR(system=sys)


class DefectHarness:
    def __init__(self):
        self.ledger = EvolutionLedger()
        self.injector = DefectInjector(self.ledger)
        self.campaign = DefectInjectionCampaign(self.ledger)
        self._strong = _strong_isr()

    def strong_isr(self):
        return self._strong

    def inject(self, isr, mutation):
        return self.injector.inject(isr, mutation)

    def run(self):
        return self.campaign.run([self._strong], None, 42)

    def run_with_blind_certifier(self):
        return self.campaign.run_with_blind_certifier()

    def good_discrimination(self):
        return self.run()

    def false_acceptance_discrimination(self):
        return self.run_with_blind_certifier()

    def zero_failure_verdict(self):
        return type("V", (), {"failures": 0, "overall_success_rate": 1.0})()

    def verdict(self):
        return self.zero_failure_verdict()

    def campaign_c_gate(self):
        return CampaignCGate()

    def matrix_summary(self):
        return CampaignReadinessHarness().matrix_summary()

    def recipe_isr_hash(self):
        return CampaignReadinessHarness().recipe_isr_hash()


@pytest.fixture(scope="module")
def defect_harness():
    return DefectHarness()


def test_defects_are_isr_mutations_not_verdict_inserts(defect_harness):
    tree = ast.parse(inspect.getsource(DefectInjector))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "set_verdict" not in fn and "force_rejection" not in fn


def test_defective_isr_flows_through_normal_pipeline(defect_harness):
    defective = defect_harness.inject(defect_harness.strong_isr(), DEFECT_MUTATIONS[0])
    assert defective.source_isr_hash == semantic_hash(defect_harness.strong_isr())
    assert semantic_hash(defective.isr) != defective.source_isr_hash


def test_strong_repositories_certify(defect_harness):
    report = defect_harness.run()
    strong_cells = [c for c in report.matrix if c.repository_kind == "strong"]
    assert all(c.observed_verdict == "CERTIFIED" for c in strong_cells)


def test_defective_repositories_rejected(defect_harness):
    report = defect_harness.run()
    defect_cells = [c for c in report.matrix if c.defect_mutation_ref is not None]
    assert all(c.observed_verdict != "CERTIFIED" for c in defect_cells)
    assert report.false_negatives == 0


def test_false_acceptance_fails_campaign(defect_harness):
    report = defect_harness.run_with_blind_certifier()
    assert report.false_negatives > 0
    assert report.discrimination_passed is False


def test_confusion_matrix_conservation(defect_harness):
    report = defect_harness.run()
    total = report.true_positives + report.false_negatives + report.true_negatives + report.false_positives
    assert total == len(report.matrix)


def test_campaign_c_gate_never_mutates_on_zero_failures_alone(defect_harness):
    decision = defect_harness.campaign_c_gate().decide(defect_harness.good_discrimination(), defect_harness.zero_failure_verdict())
    assert decision.action == "ENRICH_POPULATION"
    assert decision.mutation_target is None


def test_false_acceptance_routes_to_certification_fix(defect_harness):
    decision = defect_harness.campaign_c_gate().decide(defect_harness.false_acceptance_discrimination(), defect_harness.verdict())
    assert decision.action == "FIX_CERTIFICATION"
    assert decision.mutation_target == "gates_and_analyzers"


def test_defect_mutation_provenance_chain_addressable(defect_harness):
    report = defect_harness.run()
    for cell in report.matrix:
        for ref in cell.evidence_refs:
            assert defect_harness.ledger.event_by_ref(ref) is not None
    assert defect_harness.ledger.verify_event_chain() is True


def test_matrix_and_recipe_identity_unchanged(defect_harness):
    assert defect_harness.matrix_summary() == (12, 18, 0, 0)
    assert defect_harness.recipe_isr_hash() == RECIPE_HASH
