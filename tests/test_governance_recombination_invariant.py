"""Recombination invariant: a recombined candidate's expressed governance design
always validates as GovernanceDesignISR and clears the 0.2 selection gate.

Locks the live variation->selection loop's assumption that the ARCHITECTURAL_BLOCKS
crossover treats ``governance`` as an atomic block: each offspring inherits one
parent's complete, valid governance design rather than a field-level hybrid that
could fail GovernanceDesignISR validation (or fall below the gate).

This is verified rather than assumed -- the constitution's discipline applied to
a newly-activated dimension.
"""
from __future__ import annotations

from constitutional_architecture.governance.governance_design_fitness import (
    baseline_governance_design,
)
from constitutional_architecture.governance.governance_fitness import ALL_OBJECTIVES
from constitutional_architecture.governance.schemas import GovernanceDesignISR
from evolution.governance_fitness_evaluator import governance_objectives_for
from evolution.recombination import (
    PolicyBlockCrossover,
    RecombinationContext,
    RecombinationPolicy,
)

# Parent B: a distinct, fully-compliant governance design (different from baseline).
STRONGLY_GOVERNED = {
    "design_id": "gd-strongly-governed",
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


def _arch_isr(governance):
    return {
        "domains": [{"name": "core"}],
        "services": [{"name": "svc"}],
        "security": {"scheme": "oauth"},
        "observability": {"metrics": True},
        "deployment": {"strategy": "blue-green"},
        "testing": {"coverage": True},
        "governance": governance,
    }


def test_recombined_governance_is_valid_and_feasible():
    parent_a_isr = _arch_isr(baseline_governance_design())
    parent_b_isr = _arch_isr(STRONGLY_GOVERNED)

    offspring_isrs = PolicyBlockCrossover().recombine(
        parent_a=parent_a_isr,
        parent_b=parent_b_isr,
        policy=RecombinationPolicy(),
        context=RecombinationContext(parent_candidate_ids=["a", "b"]),
    )

    assert offspring_isrs, "recombination must produce at least one offspring"

    for isr in offspring_isrs:
        assert "governance" in isr, "governance block must survive recombination"
        # Validates as a real GovernanceDesignISR — no malformed field hybrid.
        GovernanceDesignISR.model_validate(isr["governance"])
        # And clears the 0.2 selection gate (feasibility survives recombination).
        objectives = governance_objectives_for({"governance": isr["governance"]})
        assert set(objectives) == set(ALL_OBJECTIVES)
        assert all(value >= 0.2 for value in objectives.values())
