import ast
import inspect

import pytest

from tiannara.application.campaign.campaign_runner import (
    CampaignEnvironment,
    CampaignRunner,
    CampaignVerdict,
    CellPipeline,
    CellSpec,
)
from tiannara.application.campaign.phase31_contract import build_phase31_contract
from tiannara.application.evolution.ledger import EvolutionLedger
from tiannara.application.quality.tool_adapters import ToolExecutionState
from tiannara.application.quality.tool_availability import REQUIRED_EXTERNAL_TOOLS

from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


class RunnerHarness:
    def __init__(self):
        self._contract = build_phase31_contract()
        self.ledger = EvolutionLedger()
        self._pipeline = CellPipeline(self._contract)
        self.runner = CampaignRunner(self._contract, self.ledger, cell_pipeline=self._pipeline)

    def contract(self):
        return self._contract

    def cell_spec(self, sid: str) -> CellSpec:
        return CellSpec(cell_id=f"cell-{sid}", category="CRUD_SAAS", variation_axes=self._contract.population.variation_axes)

    def cell_failing_phase32(self) -> CellSpec:
        spec = CellSpec(cell_id="failing-phase32", category="BANKING", variation_axes=self._contract.population.variation_axes)
        # Mark as failing via attribute
        object.__setattr__(spec, "failing_phase32", True)
        return spec

    def run_cell(self, spec=None, seed=1):
        if spec is None:
            spec = self.cell_spec("A")
        # Handle overloaded call: run_cell(spec, seed) vs run_cell(spec)
        if isinstance(spec, str):
            spec = self.cell_spec(spec)
        return self._pipeline.run(spec, seed)

    def run_campaign(self, seed=42) -> CampaignVerdict:
        # Fresh ledger per campaign for determinism test -- but reuse ledger to keep chain
        # For determinism we create fresh ledger each run? Spec expects deterministic constituents.
        # Use new ledger per run to isolate
        ledger = EvolutionLedger()
        runner = CampaignRunner(self._contract, ledger, cell_pipeline=self._pipeline)
        # Store ledger for later checks -- use the runner's ledger
        self.ledger = ledger
        self.runner = runner
        return runner.run(seed)

    def run_campaign_in_incomplete_environment(self, seed=42) -> CampaignVerdict:
        env = CampaignEnvironment(
            environment_id="incomplete-env",
            analyzer_availability={tool: ToolExecutionState.TOOL_NOT_INSTALLED for tool in REQUIRED_EXTERNAL_TOOLS},
            backend_availability={"fastapi": False},
            compiler_identity="compiler-001",
            runtime_identity="runtime-001",
        )
        ledger = EvolutionLedger()
        runner = CampaignRunner(self._contract, ledger, cell_pipeline=self._pipeline)
        self.ledger = ledger
        return runner.run(seed, environment=env)

    def cell_evidence_refs(self, campaign_id: str):
        # Return cell event refs from ledger
        refs = []
        for ev in self.ledger.events():
            if ev.event_id.startswith(f"campaign-cell-{campaign_id}"):
                refs.append(ev.event_id)
        return refs

    def matrix_summary(self):
        h = CampaignReadinessHarness()
        return h.matrix_summary()

    def recipe_isr_hash(self):
        h = CampaignReadinessHarness()
        return h.recipe_isr_hash()


@pytest.fixture(scope="module")
def runner_harness() -> RunnerHarness:
    return RunnerHarness()


def test_runner_reads_contract_never_mutates(runner_harness):
    tree = ast.parse(inspect.getsource(CampaignRunner))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = ast.unparse(node.func)
            assert "redefine_success" not in fn and "adjust_threshold" not in fn
            assert "mutate_contract" not in fn


def test_campaign_anchored_to_frozen_contract(runner_harness):
    verdict = runner_harness.run_campaign(seed=42)
    assert verdict.contract_hash == runner_harness.contract().content_hash
    assert runner_harness.ledger.event_by_ref(verdict.campaign_event_ref) is not None


def test_cell_gate_order_respects_phase32_before_deployment(runner_harness):
    result = runner_harness.run_cell(runner_harness.cell_failing_phase32())
    from tiannara.application.campaign.campaign_runner import CellGateState
    assert result.gate_results["phase32_quality_gates"] == CellGateState.FAILED
    assert result.gate_results["deployment"] == CellGateState.FAILED
    assert result.success is False


def test_per_cell_isolation(runner_harness):
    r1 = runner_harness.run_cell(runner_harness.cell_spec("A"), seed=1)
    r2 = runner_harness.run_cell(runner_harness.cell_spec("B"), seed=1)
    assert r1.isr_hash != r2.isr_hash


def test_campaign_deterministic(runner_harness):
    v1 = runner_harness.run_campaign(seed=42)
    v2 = runner_harness.run_campaign(seed=42)
    assert v1.constituents == v2.constituents and v1.overall_success_rate == v2.overall_success_rate


def test_absent_analyzer_yields_bounded_not_certified(runner_harness):
    verdict = runner_harness.run_campaign_in_incomplete_environment(seed=42)
    assert verdict.verdict in ("BOUNDED", "BOUNDED_SUCCESS")
    assert verdict.bounded_reasons
    assert verdict.exit_gate_passed is False


def test_probes_excluded_from_success_denominator(runner_harness):
    verdict = runner_harness.run_campaign(seed=42)
    assert "false_acceptance_rate" in verdict.constituents


def test_no_aggregate_score(runner_harness):
    verdict = runner_harness.run_campaign(seed=42)
    assert len(verdict.constituents) == 9
    assert "phase32_certification_rate" in verdict.constituents and "phase32_bounded_rate" in verdict.constituents
    assert not hasattr(verdict, "composite_score") and not hasattr(verdict, "aggregate")


def test_every_cell_chain_addressable(runner_harness):
    verdict = runner_harness.run_campaign(seed=42)
    for ref in runner_harness.cell_evidence_refs(verdict.campaign_id):
        assert runner_harness.ledger.event_by_ref(ref) is not None
    assert runner_harness.ledger.verify_event_chain() is True


def test_matrix_and_recipe_identity_unchanged(runner_harness):
    assert runner_harness.matrix_summary() == (12, 18, 0, 0)
    assert runner_harness.recipe_isr_hash() == RECIPE_HASH
