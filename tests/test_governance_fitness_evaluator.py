"""Tests for the evolution-loop governance-aware fitness evaluator.

Validates the genome splice (constitutional_architecture/governance/schemas.py,
evolution/genome_mutations.py:strengthen_governance, evolution/fitness.py,
evolution/pareto.py:select_pareto) as a closed, dimension-set-consistent
governance fitness signal feeding the live evolution selection loop.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from constitutional_architecture.governance.governance_design_fitness import (
    baseline_governance_design,
)
from constitutional_architecture.governance.governance_fitness import ALL_OBJECTIVES
from constitutional_architecture.governance.schemas import GovernanceDesignISR
from evolution.fitness import FitnessEvaluator
from evolution.governance_fitness_evaluator import (
    GovernanceAwareFitnessEvaluator,
    fail_closed_governance_objectives,
    governance_objectives_for,
)
from evolution.models import (
    CandidateArchitecture,
    CandidateEvaluationRecord,
    ParetoSelectionPolicy,
    SimulationResult,
    VerificationReport,
)
from evolution.pareto import select_pareto

_NOW = datetime.now(timezone.utc).isoformat()


def _arch_isr(extra_governance=None):
    isr: dict = {
        "domains": [{"name": "core"}],
        "services": [{"name": "svc"}],
        "security": {"scheme": "oauth"},
        "observability": {"metrics": True},
        "deployment": {"strategy": "blue-green"},
        "testing": {"coverage": True},
    }
    if extra_governance is not None:
        isr["governance"] = extra_governance
    return isr


def _candidate(isr, cid="c1"):
    return CandidateArchitecture(
        id=cid,
        proposal_id="p1",
        mutation_spec_id="base",
        base_isr_hash="a" * 12,
        content_hash="b" * 12,
        isr=isr,
        created_at=_NOW,
    )


def _sim_ver(cid="c1"):
    sim = SimulationResult(
        id="s-" + cid,
        candidate_id=cid,
        status="PASSED",
        metrics={"complexity": 10.0},
        created_at=_NOW,
    )
    ver = VerificationReport(
        candidate_id=cid,
        valid=True,
        created_at=_NOW,
    )
    return sim, ver


FULLY_COMPLIANT = {
    "design_id": "governance_design_v1",
    "voting_rule": "unanimity",
    "quorum": 5,
    "approval_stage_count": 3,
    "policy_rule_count": 10,
    "fail_closed_default": True,
    "exception_max_severity": "low",
    "exception_review_required": True,
    "audit_chaining_required": True,
    "compliance_evaluation_required": True,
    "versioning_strategy": "semver_chain",
}


def test_fail_closed_vector_has_all_objective_keys():
    vec = fail_closed_governance_objectives()
    assert set(vec) == set(ALL_OBJECTIVES)
    assert all(value == 0.0 for value in vec.values())


def test_absent_governance_scores_fail_closed_and_preserves_architecture():
    evaluator = GovernanceAwareFitnessEvaluator()
    base = FitnessEvaluator()
    cand = _candidate(_arch_isr(extra_governance=None), cid="c1")
    sim, ver = _sim_ver(cand.id)

    base_ev = base.evaluate(cand, sim, ver)
    gov_ev = evaluator.evaluate(cand, sim, ver)

    # architecture objectives untouched, governance objectives fail-closed
    arch_keys = set(base_ev.objectives)
    assert set(gov_ev.objectives) == arch_keys | set(ALL_OBJECTIVES)
    for name in ALL_OBJECTIVES:
        assert gov_ev.objectives[name] == 0.0
    for name in arch_keys:
        assert gov_ev.objectives[name] == base_ev.objectives[name]
    # pass gate is inherited, not flipped by the governance zeros
    assert gov_ev.passed == base_ev.passed


def test_governance_objectives_for_helper_is_fail_closed_on_empty():
    assert governance_objectives_for({}) == fail_closed_governance_objectives()
    assert governance_objectives_for({"governance": None}) == fail_closed_governance_objectives()
    assert governance_objectives_for({"governance": {}}) == fail_closed_governance_objectives()


def test_malformed_governance_design_scores_fail_closed():
    evaluator = GovernanceAwareFitnessEvaluator()
    # missing required field (voting_rule) -> GovernanceDesignISR validation error
    cand = _candidate(_arch_isr(extra_governance={"design_id": "x"}), cid="c3")
    sim, ver = _sim_ver(cand.id)
    ev = evaluator.evaluate(cand, sim, ver)
    assert {k: ev.objectives[k] for k in ALL_OBJECTIVES} == fail_closed_governance_objectives()


def test_fully_compliant_governance_design_scores_ones():
    evaluator = GovernanceAwareFitnessEvaluator()
    cand = _candidate(_arch_isr(extra_governance=FULLY_COMPLIANT), cid="c4")
    sim, ver = _sim_ver(cand.id)
    ev = evaluator.evaluate(cand, sim, ver)
    for name in ALL_OBJECTIVES:
        assert ev.objectives[name] == pytest.approx(1.0)


def test_partial_governance_scores_selectively():
    evaluator = GovernanceAwareFitnessEvaluator()
    weak = dict(FULLY_COMPLIANT, audit_chaining_required=False)
    cand = _candidate(_arch_isr(extra_governance=weak), cid="c5")
    sim, ver = _sim_ver(cand.id)
    ev = evaluator.evaluate(cand, sim, ver)
    # audit_integrity drops to the no-audit floor (0.2) when chaining is disabled
    assert ev.objectives["audit_integrity"] == pytest.approx(0.2)
    for name in ALL_OBJECTIVES:
        if name != "audit_integrity":
            assert ev.objectives[name] == pytest.approx(1.0)


def test_select_pareto_ranks_governance_candidate_over_absent():
    evaluator = GovernanceAwareFitnessEvaluator()
    # A: architecture only, no governance -> six zeros -> fail-closed gate dropped
    cand_a = _candidate(_arch_isr(), cid="c_a")
    # B: fully expressed governance design -> six ones -> feasible
    cand_b = _candidate(_arch_isr(FULLY_COMPLIANT), cid="c_b")

    records = []
    for cand in (cand_a, cand_b):
        sim, ver = _sim_ver(cand.id)
        fitness = evaluator.evaluate(cand, sim, ver)
        records.append(
            CandidateEvaluationRecord(
                candidate_id=cand.id,
                feasible=True,
                fitness=fitness,
                created_at=_NOW,
            )
        )

    result = select_pareto(
        "p1",
        records,
        ParetoSelectionPolicy(max_selected=1, min_objective_value=0.2),
    )

    # A is filtered by the per-objective gate (governance zeros); B is selected
    assert result.selected_candidate_id == "c_b"
    assert len(result.fronts[0]) == 1
    assert result.fronts[0][0].candidate_id == "c_b"


# --- Activation: baseline governance + default-flip closure -------------------


def test_baseline_governance_design_is_a_valid_design_above_gate():
    baseline = baseline_governance_design()
    # Single source of truth: the baseline round-trips through the schema.
    GovernanceDesignISR(**baseline)
    objectives = governance_objectives_for({"governance": baseline})
    assert set(objectives) == set(ALL_OBJECTIVES)
    # Scores committed to in the baseline policy table; all clear the 0.2 gate.
    assert objectives["ratification_rigor"] == pytest.approx(0.3444, abs=1e-3)
    assert objectives["policy_coverage"] == pytest.approx(0.3, abs=1e-3)
    assert objectives["exception_hygiene"] == pytest.approx(0.4, abs=1e-3)
    assert objectives["audit_integrity"] == pytest.approx(1.0)
    assert objectives["compliance_posture"] == pytest.approx(1.0)
    assert objectives["constitutional_currency"] == pytest.approx(1.0)
    assert all(value >= 0.2 for value in objectives.values())


def test_mutation_engine_injects_baseline_governance_on_non_governance_mutation():
    from evolution.genome_mutations import ChromosomeFamily, DEFAULT_MUTATION_TEMPLATES
    from evolution.models import MutationOperationSpec, MutationOperationType, MutationSpec
    from evolution.mutation import MutationEngine

    spec = MutationSpec(
        operator="strengthen_security",
        chromosome_family="security",
        gene_id="security.encryption",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.MERGE_OBJECT,
                path="security",
                value={"encryption_in_transit": True},
            )
        ],
    )
    mutated = MutationEngine().apply(
        {"domains": [{"name": "core"}], "security": {"scheme": "oauth"}},
        spec,
    )
    # Non-governance mutations still carry the baseline governance floor.
    assert mutated.get("governance") == dict(baseline_governance_design())


def test_governance_mutation_overrides_baseline():
    from evolution.genome_mutations import ChromosomeFamily, DEFAULT_MUTATION_TEMPLATES
    from evolution.models import MutationSpec
    from evolution.mutation import MutationEngine

    template = DEFAULT_MUTATION_TEMPLATES[ChromosomeFamily.GOVERNANCE]
    spec = MutationSpec(
        operator=template.name,
        chromosome_family="governance",
        gene_id=template.name,
        operations=list(template.operations),
    )
    mutated = MutationEngine().apply({"domains": [{"name": "core"}]}, spec)
    # strengthen_governance writes the fully-compliant design; the baseline
    # setdefault is a no-op because the mutation already expressed governance.
    assert mutated["governance"]["voting_rule"] == "unanimity"
    assert mutated["governance"]["policy_rule_count"] == 10


def test_select_pareto_steers_toward_stronger_governance_design():
    # Baseline-governed candidate A vs fully-governed candidate B (same arch).
    # Under the governance-aware evaluator, B dominates A on the governance
    # dimensions, so selection favours B even though architecture is equal.
    evaluator = GovernanceAwareFitnessEvaluator()
    arch = _arch_isr()
    cand_a = _candidate({**arch, "governance": baseline_governance_design()}, cid="c_base")
    cand_b = _candidate({**arch, "governance": FULLY_COMPLIANT}, cid="c_strong")

    records = []
    for cand in (cand_a, cand_b):
        sim, ver = _sim_ver(cand.id)
        fitness = evaluator.evaluate(cand, sim, ver)
        records.append(
            CandidateEvaluationRecord(
                candidate_id=cand.id,
                feasible=True,
                fitness=fitness,
                created_at=_NOW,
            )
        )

    result = select_pareto(
        "p1",
        records,
        ParetoSelectionPolicy(max_selected=1, min_objective_value=0.2),
    )
    assert result.selected_candidate_id == "c_strong"


def test_default_engine_uses_governance_aware_evaluator():
    from evolution.engine import SelfEvolutionEngine

    engine = SelfEvolutionEngine()
    # The live loop defaults to the governance-aware evaluator (closed loop).
    assert isinstance(engine.fitness_evaluator, GovernanceAwareFitnessEvaluator)
