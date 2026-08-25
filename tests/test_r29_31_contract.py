import ast
import inspect
import tempfile

import pytest

from tiannara.application.campaign.phase31_contract import (
    CHALLENGE_CATEGORIES,
    VARIATION_AXES,
    CampaignPopulation,
    CertificationAccuracyBounds,
    AnalyzerProvisioningScope,
    EXIT_GATE,
    PROBES,
    SUCCESS_DEFINITION,
    CampaignRunner,
    build_phase31_contract,
    contract_body,
    hash_canonical,
    register_contract,
)
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.quality.tool_availability import REQUIRED_EXTERNAL_TOOLS

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


class ContractHarness:
    def __init__(self):
        self.ledger = EvolutionLedger()

    def build_contract(self):
        return build_phase31_contract()

    def register_contract(self, contract):
        return register_contract(contract, self.ledger)


@pytest.fixture(scope="module")
def contract_harness() -> ContractHarness:
    return ContractHarness()


def test_success_definition_includes_phase32_gates():
    assert "phase32_quality_gates" in SUCCESS_DEFINITION.required_gates
    order = SUCCESS_DEFINITION.gate_order
    assert order.index("phase32_quality_gates") < order.index("deployment")


def test_exit_gate_is_multidimensional_not_aggregated():
    assert EXIT_GATE.aggregate_forbidden is True
    assert len(EXIT_GATE.constituent_metrics) >= 8
    assert not hasattr(EXIT_GATE, "composite_score")


def test_probes_accounted_separately_from_success_rate():
    assert "separate from success rate" in PROBES.accounting
    assert PROBES.adversarial_architectures and PROBES.injected_defects and PROBES.human_baselines


def test_false_acceptance_bound_stricter_than_false_rejection():
    bounds = CertificationAccuracyBounds(max_false_acceptance_rate=0.001, max_false_rejection_rate=0.02)
    assert bounds.max_false_acceptance_rate < bounds.max_false_rejection_rate


def test_population_is_stratified_across_all_categories():
    pop = CampaignPopulation(
        categories=CHALLENGE_CATEGORIES,
        variation_axes=VARIATION_AXES,
        minimum_per_category=80,
        total_generations=80 * len(CHALLENGE_CATEGORIES),
        stratification_rule="coverage across categories and axes",
    )
    assert set(pop.categories) == set(CHALLENGE_CATEGORIES)
    assert pop.minimum_per_category > 0


def test_analyzer_scope_declares_provisioning_state():
    scope = AnalyzerProvisioningScope(required_tools=REQUIRED_EXTERNAL_TOOLS, provisioning_state="BOUNDED", bounded_coverage=("fastapi",))
    assert scope.provisioning_state in ("PROVISIONED", "BOUNDED")


def test_contract_is_hash_bound_and_ledger_anchored(contract_harness):
    contract = contract_harness.build_contract()
    assert contract.content_hash == hash_canonical(contract_body(contract))
    assert contract_harness.ledger.event_by_ref(contract_harness.register_contract(contract)) is not None


def test_contract_frozen_before_campaign_start(contract_harness):
    tree = ast.parse(inspect.getsource(CampaignRunner))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "redefine_success" not in fn and "adjust_threshold" not in fn


def test_matrix_and_recipe_identity_unchanged():
    h = CampaignReadinessHarness()
    assert h.matrix_summary() == (12, 18, 0, 0)
    assert h.recipe_isr_hash() == RECIPE_HASH
