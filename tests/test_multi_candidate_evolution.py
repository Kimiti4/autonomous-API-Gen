"""
Tests for Phase 21.1 multi-candidate evolution and Pareto selection.
"""

from evolution.engine import EvolutionPolicy, SelfEvolutionEngine
from evolution.governance import StaticGovernanceClient
from evolution.models import (
    EvolutionProposalRequest,
    EvolutionTargetType,
    GenerateCandidatesRequest,
    MutationOperationSpec,
    MutationOperationType,
    MutationSpec,
    ParetoSelectionPolicy,
)
from evolution.multi import MultiCandidateEvolutionEngine
from evolution.pareto import dominates, non_dominated_sort


def base_isr() -> dict:
    return {
        "isr_id": "isr_billing_001",
        "version": "1.0.0",
        "name": "Billing System",
        "domains": [
            {
                "name": "billing",
                "services": [
                    {
                        "name": "BillingService",
                        "apis": [
                            {
                                "name": "createInvoice"
                            }
                        ],
                        "depends_on": [],
                    }
                ],
            }
        ],
        "security": {
            "authentication": "OIDC",
        },
        "observability": {
            "metrics": True,
        },
        "deployment": {
            "container": True,
        },
        "testing": {
            "unit_tests": True,
        },
    }


def base_mutation_spec() -> MutationSpec:
    return MutationSpec(
        id="mutation_add_list_invoices",
        operator="architecture_mutator",
        chromosome_family="backend",
        gene_id="billing_api_surface",
        rationale="Add invoice listing capability.",
        operations=[
            MutationOperationSpec(
                operation=MutationOperationType.ADD_ITEM,
                path="domains.0.services.0.apis",
                value={
                    "name": "listInvoices"
                },
            )
        ],
    )


def extra_mutation_specs() -> list[MutationSpec]:
    return [
        MutationSpec(
            id="mutation_add_get_invoice",
            operator="architecture_mutator",
            chromosome_family="backend",
            gene_id="billing_api_surface",
            rationale="Add invoice retrieval capability.",
            operations=[
                MutationOperationSpec(
                    operation=MutationOperationType.ADD_ITEM,
                    path="domains.0.services.0.apis",
                    value={
                        "name": "getInvoice"
                    },
                )
            ],
        ),
        MutationSpec(
            id="mutation_remove_testing",
            operator="architecture_mutator",
            chromosome_family="testing",
            gene_id="test_policy",
            rationale="Remove testing policy, which should become infeasible.",
            operations=[
                MutationOperationSpec(
                    operation=MutationOperationType.REMOVE_ITEM,
                    path="testing",
                )
            ],
        ),
    ]


def base_proposal_request() -> EvolutionProposalRequest:
    return EvolutionProposalRequest(
        title="Evolve billing architecture",
        description="Generate competing billing architecture candidates.",
        target_type=EvolutionTargetType.APPLICATION_ARCHITECTURE,
        target_ref="billing_system",
        base_isr=base_isr(),
        mutation=base_mutation_spec(),
        high_impact=False,
        allow_breaking_changes=False,
        environment="development",
    )


def build_engines() -> tuple[SelfEvolutionEngine, MultiCandidateEvolutionEngine]:
    base_engine = SelfEvolutionEngine(
        governance_client=StaticGovernanceClient(
            decision="ALLOW",
            reason="Static governance decision.",
        ),
        policy=EvolutionPolicy(),
    )

    multi_engine = MultiCandidateEvolutionEngine(base_engine)

    return base_engine, multi_engine


def test_dominance():
    a = {
        "x": 1.0,
        "y": 0.8,
    }

    b = {
        "x": 0.9,
        "y": 0.8,
    }

    c = {
        "x": 1.0,
        "y": 0.9,
    }

    assert dominates(a, b, ["x", "y"]) is True
    assert dominates(b, a, ["x", "y"]) is False
    assert dominates(c, a, ["x", "y"]) is True


def test_non_dominated_sort():
    values = {
        "a": {
            "x": 1.0,
            "y": 0.8,
        },
        "b": {
            "x": 0.9,
            "y": 0.8,
        },
        "c": {
            "x": 0.95,
            "y": 0.95,
        },
    }

    fronts = non_dominated_sort(values, ["x", "y"])

    assert fronts[0] == ["c", "a"] or fronts[0] == ["a", "c"]
    assert "b" not in fronts[0]


def test_multi_candidate_generation_evaluation_and_selection():
    base_engine, multi_engine = build_engines()

    proposal = base_engine.propose(base_proposal_request(), "tester")

    generated = multi_engine.generate_candidates(
        proposal.id,
        GenerateCandidatesRequest(
            mutations=extra_mutation_specs(),
            include_base_mutation=True,
        ),
        "tester",
    )

    assert len(generated) == 3

    evaluations = multi_engine.evaluate_candidates(
        proposal.id,
        "tester",
    )

    assert len(evaluations) == 3

    feasible_candidate_ids = {
        evaluation.candidate_id
        for evaluation in evaluations
        if evaluation.feasible
    }

    # The mutation that removes testing should be infeasible.
    assert len(feasible_candidate_ids) == 2

    selection = multi_engine.select_pareto(
        proposal.id,
        ParetoSelectionPolicy(
            max_selected=1,
            min_objective_value=0.2,
        ),
        "tester",
    )

    assert selection.selected_candidate_id is not None
    assert selection.selected_candidate_id in feasible_candidate_ids

    refreshed = base_engine._get_proposal(proposal.id)

    assert refreshed.selected_candidate_id == selection.selected_candidate_id


def test_selected_candidate_can_be_promoted():
    base_engine, multi_engine = build_engines()

    proposal = base_engine.propose(base_proposal_request(), "tester")

    multi_engine.generate_candidates(
        proposal.id,
        GenerateCandidatesRequest(
            mutations=extra_mutation_specs(),
            include_base_mutation=True,
        ),
        "tester",
    )

    multi_engine.evaluate_candidates(proposal.id, "tester")

    selection = multi_engine.select_pareto(
        proposal.id,
        ParetoSelectionPolicy(max_selected=1),
        "tester",
    )

    proposal = base_engine.submit_for_approval(proposal.id, "tester")

    assert proposal.status.value == "APPROVED"

    promotion = base_engine.promote(
        proposal.id,
        "staging",
        "tester",
    )

    assert promotion.candidate_id == selection.selected_candidate_id
