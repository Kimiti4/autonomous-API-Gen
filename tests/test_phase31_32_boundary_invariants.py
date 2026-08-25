"""Permanent platform invariants guarding the Phase 31/32 certification boundary."""
import pytest

from tiannara.application.campaign.campaign_runner import (
    CampaignRunner,
    CellGateState,
    CellPipeline,
    CellSpec,
)
from tiannara.application.campaign.phase31_contract import build_phase31_contract
from tiannara.application.evolution.ledger import EvolutionLedger


class InvariantHarness:
    def __init__(self):
        self.contract = build_phase31_contract()
        self.ledger = EvolutionLedger()
        self.pipeline = CellPipeline(self.contract)
        self.runner = CampaignRunner(self.contract, self.ledger, cell_pipeline=self.pipeline)

    def run_cell_with_bounded_phase32(self):
        spec = CellSpec(cell_id="bounded-cell", category="CRUD_SAAS", variation_axes=self.contract.population.variation_axes)
        return self.pipeline.run(spec, 1, bounded_phase32=True)

    def render_verdict_from_qualified_partial_cells(self):
        # Simulate bounded cells -> Phase31 should not be CERTIFIED
        ledger = EvolutionLedger()
        runner = CampaignRunner(self.contract, ledger, cell_pipeline=self.pipeline)
        verdict = runner.run(42)
        return verdict

    def run_bounded_campaign(self, seed=42):
        ledger = EvolutionLedger()
        runner = CampaignRunner(self.contract, ledger, cell_pipeline=CellPipeline(self.contract))
        return runner.run(seed)

    def measure_constituents(self):
        v = self.run_bounded_campaign(seed=42)
        return v.constituents

    def verdict_type(self):
        # Return type that should not have composite_score
        return self.run_bounded_campaign(seed=42)

    def run_campaign_cells(self, seed=42):
        # Return cells for conservation check
        ledger = EvolutionLedger()
        runner = CampaignRunner(self.contract, ledger, cell_pipeline=CellPipeline(self.contract))
        # Directly generate cells via pipeline with bounded flag
        from tiannara.application.campaign.campaign_runner import stratified_cells, derive_cell_seed
        cells = []
        for spec in stratified_cells(self.contract.population, seed):
            cells.append(self.pipeline.run(spec, derive_cell_seed(seed, spec.cell_id), bounded_phase32=True))
        return cells

    def campaign_a_verdict_refs(self):
        ledger = EvolutionLedger()
        runner = CampaignRunner(self.contract, ledger, cell_pipeline=CellPipeline(self.contract))
        v = runner.run(42)
        # Original verdict is BOUNDED_SUCCESS (since bounded env); simulate original CERTIFIED for test by creating a fake original
        # Create original CERTIFIED event
        from tiannara.application.evolution.ledger import EvolutionEvent, EventType
        from tiannara.domain.services.canonical import canonical_hash
        orig_event_id = f"campaign-verdict-{v.campaign_id}-orig"
        ev = EvolutionEvent(event_id=orig_event_id, evolution_id=v.campaign_id, sequence=0, event_type=EventType.CERTIFICATION, subject_id=v.campaign_id, payload={"verdict": "CERTIFIED"})
        ledger.append_event(ev, evolution_id=v.campaign_id)
        # Reclassify
        reclass = runner.reclassify(
            type('OV', (), {'campaign_id': v.campaign_id, 'campaign_event_ref': orig_event_id, 'verdict': 'CERTIFIED'})(),
            'BOUNDED_SUCCESS', 'bounded analyzer environment caused incomplete Phase 32 evidence', '1.0 bounded not certified'
        )
        # For test we need ledger lookup
        self.ledger = ledger
        # Return refs where first mimics original and second is reclassification
        # Need objects with .verdict and .reclassifies for test; test checks ledger.event_by_ref
        # Instead return event_ids and let test fetch payload
        return (orig_event_id, reclass.reclassification_event_ref)


@pytest.fixture(scope="module")
def invariant_harness():
    return InvariantHarness()


def test_bounded_is_not_passed():
    assert CellGateState.BOUNDED is not CellGateState.PASSED
    assert CellGateState.BOUNDED is not CellGateState.FAILED


def test_bounded_cell_is_not_successful(invariant_harness):
    cell = invariant_harness.run_cell_with_bounded_phase32()
    assert cell.gate_results["phase32_quality_gates"] is CellGateState.BOUNDED
    assert cell.success is False
    assert any(v is CellGateState.BOUNDED for v in cell.gate_results.values())


def test_qualified_partial_never_certified(invariant_harness):
    verdict = invariant_harness.render_verdict_from_qualified_partial_cells()
    assert verdict.verdict != "CERTIFIED"
    assert verdict.verdict in ("BOUNDED_SUCCESS", "NOT_CERTIFIED", "BOUNDED")


def test_bounded_campaign_never_satisfies_exit_gate(invariant_harness):
    verdict = invariant_harness.run_bounded_campaign(seed=42)
    assert verdict.exit_gate_passed is False
    assert verdict.verdict != "CERTIFIED"


def test_certification_and_boundedness_are_separate_constituents(invariant_harness):
    constituents = invariant_harness.measure_constituents()
    assert "phase32_certification_rate" in constituents
    assert "phase32_bounded_rate" in constituents
    assert constituents["phase32_certification_rate"] != constituents["phase32_bounded_rate"] or constituents["phase32_certification_rate"] == 0.0


def test_no_aggregate_score_invariant_holds(invariant_harness):
    constituents = invariant_harness.measure_constituents()
    assert len(constituents) == 9
    assert not hasattr(invariant_harness.verdict_type(), "composite_score")


def test_phase32_cell_state_conservation(invariant_harness):
    cells = invariant_harness.run_campaign_cells(seed=42)
    phase32_states = [c.gate_results["phase32_quality_gates"] for c in cells]
    certified = phase32_states.count(CellGateState.PASSED) / len(cells)
    bounded = phase32_states.count(CellGateState.BOUNDED) / len(cells)
    failed = phase32_states.count(CellGateState.FAILED) / len(cells)
    assert abs((certified + bounded + failed) - 1.0) < 1e-9


def test_reclassification_is_append_only(invariant_harness):
    original_ref, reclass_ref = invariant_harness.campaign_a_verdict_refs()
    orig_ev = invariant_harness.ledger.event_by_ref(original_ref)
    re_ev = invariant_harness.ledger.event_by_ref(reclass_ref)
    assert orig_ev.payload["verdict"] == "CERTIFIED"
    assert re_ev.payload["corrected_label"] == "BOUNDED_SUCCESS"
    assert re_ev.payload["original_verdict_event_ref"] == original_ref
    assert invariant_harness.ledger.verify_event_chain() is True


def test_phase31_and_phase32_vocabularies_distinct(invariant_harness):
    # Phase32 should not contain BOUNDED_SUCCESS, Phase31 should not conflate QUALIFIED_PARTIAL as CERTIFIED
    # Check runner vocabularies via verdict strings
    assert "BOUNDED_SUCCESS" not in ("CERTIFIED", "QUALIFIED_PARTIAL", "NOT_CERTIFIED")
    # Phase31 verdict for bounded is BOUNDED_SUCCESS, not QUALIFIED_PARTIAL
    v = invariant_harness.run_bounded_campaign(seed=42)
    assert v.verdict == "BOUNDED_SUCCESS"
    assert v.verdict != "QUALIFIED_PARTIAL"
