import pytest

from app.engine.counterfactual_execution import execute_counterfactual_work
from app.engine.counterfactual_plan import materialize_counterfactual_plan
from app.engine.counterfactual_work import materialize_counterfactual_work
from app.engine.fullstack_genome import *
from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.rejection_analysis import derive_counterfactual_requirements, record_rejection
from app.engine.specialized_mutations import frontend_mutation


def genome():
    return FullStackGenome(
        FrontendGenome("render","state","interaction","a11y","resilience"),
        BackendGenome("service","strong","safe","retry","contract"),
        DataGenome("sql","integrity","expand-contract","strong"),
        SecurityGenome("identity","rbac",("api",),("audit",),"vault"),
        OperationalGenome("containers","metrics","rollback","bounded"),
        "v1","frontend->api->backend")


def test_executes_counterfactual_work_through_domain_mutation_gate():
    objectives = (Objective("quality","maximize"),)
    frontier = ArchitectureScore("frontier", {"quality": 0.95}, ("frontier:evidence",))
    candidate = ArchitectureScore("candidate", {"quality": 0.90}, ("candidate:evidence",))
    rejection = record_rejection(
        candidate, reasons=("successor-dominated",),
        frontier_scores=(frontier,), objectives=objectives,
    )
    requirements = derive_counterfactual_requirements(rejection, (frontier,), objectives)
    plan = materialize_counterfactual_plan(rejection, requirements)
    work = materialize_counterfactual_work(
        plan, work_id_prefix="cf",
        acceptance_properties_by_objective={"quality": ("accessibility",)},
    )
    mutation = frontend_mutation(
        "quality-repair", ("frontend",), "improve quality",
        ("repair:evidence",), lambda g: g
    )

    result = execute_counterfactual_work(
        work, genome(),
        {"quality": mutation},
        {"quality": ()},
        {},
    )

    assert result.candidate_architecture_id == "candidate"
    assert len(result.executions) == 1
    assert result.executions[0].mutation_id == "quality-repair"
    assert result.executions[0].evaluation.evidence == ("repair:evidence",)


def test_execution_requires_matching_acceptance_property():
    objectives = (Objective("quality","maximize"),)
    frontier = ArchitectureScore("frontier", {"quality": 0.95}, ("evidence",))
    candidate = ArchitectureScore("candidate", {"quality": 0.90}, ("evidence",))
    rejection = record_rejection(candidate, reasons=("dominated",), frontier_scores=(frontier,), objectives=objectives)
    req = derive_counterfactual_requirements(rejection, (frontier,), objectives)
    work = materialize_counterfactual_work(
        materialize_counterfactual_plan(rejection, req),
        work_id_prefix="cf",
        acceptance_properties_by_objective={"quality": ("wrong-property",)},
    )
    mutation = frontend_mutation("repair", ("frontend",), "repair", ("evidence",), lambda g:g)

    with pytest.raises(ValueError, match="counterfactual-execution-acceptance-mismatch:quality"):
        execute_counterfactual_work(work, genome(), {"quality": mutation}, {"quality": ()}, {})


def test_execution_fails_closed_without_mutation():
    objectives = (Objective("quality","maximize"),)
    frontier = ArchitectureScore("frontier", {"quality": 0.95}, ("evidence",))
    candidate = ArchitectureScore("candidate", {"quality": 0.90}, ("evidence",))
    rejection = record_rejection(candidate, reasons=("dominated",), frontier_scores=(frontier,), objectives=objectives)
    req = derive_counterfactual_requirements(rejection, (frontier,), objectives)
    work = materialize_counterfactual_work(
        materialize_counterfactual_plan(rejection, req),
        work_id_prefix="cf",
        acceptance_properties_by_objective={"quality": ("accessibility",)},
    )
    with pytest.raises(ValueError, match="counterfactual-execution-missing-mutation:quality"):
        execute_counterfactual_work(work, genome(), {}, {"quality": ()}, {})
