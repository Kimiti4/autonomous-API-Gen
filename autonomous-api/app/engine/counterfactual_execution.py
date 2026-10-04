"""Execute ESAP counterfactual work through normal mutation gates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .architecture_mutation import MutationEvaluation, execute_mutation
from .counterfactual_work import CounterfactualWorkPlan
from .invariant_contracts import InvariantContract
from .specialized_mutations import EngineeringMutationSpec
from .fullstack_genome import FullStackGenome


@dataclass(frozen=True)
class ExecutedCounterfactualWork:
    work_id: str
    objective: str
    target_value: float
    mutation_id: str
    evaluation: MutationEvaluation


@dataclass(frozen=True)
class CounterfactualExecutionResult:
    candidate_architecture_id: str
    final_genome: FullStackGenome
    executions: tuple[ExecutedCounterfactualWork, ...]


def execute_counterfactual_work(
    plan: CounterfactualWorkPlan,
    genome: FullStackGenome,
    mutation_specs_by_objective: Mapping[str, EngineeringMutationSpec],
    contracts_by_objective: Mapping[str, tuple[InvariantContract, ...]],
    observations: Mapping[str, object],
) -> CounterfactualExecutionResult:
    if not plan.bounded:
        raise ValueError("counterfactual-execution-requires-bounded-plan")

    current = genome
    executions: list[ExecutedCounterfactualWork] = []

    for item in plan.work_items:
        spec = mutation_specs_by_objective.get(item.objective)
        if spec is None:
            raise ValueError(
                "counterfactual-execution-missing-mutation:" + item.objective
            )
        if tuple(spec.verification_properties) and not set(item.acceptance_properties).intersection(
            spec.verification_properties
        ):
            raise ValueError(
                "counterfactual-execution-acceptance-mismatch:" + item.objective
            )

        evaluation = execute_mutation(
            current,
            spec.mutation,
            contracts_by_objective.get(item.objective, ()),
            dict(observations),
        )
        current = evaluation.genome
        executions.append(
            ExecutedCounterfactualWork(
                work_id=item.work_id,
                objective=item.objective,
                target_value=item.target_value,
                mutation_id=evaluation.mutation_id,
                evaluation=evaluation,
            )
        )

    return CounterfactualExecutionResult(
        plan.candidate_architecture_id,
        current,
        tuple(executions),
    )
