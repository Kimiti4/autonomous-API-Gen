from app.engine.problem_synthesis import ProblemModel, synthesize_strategies
from app.engine.exploration_engine import ExplorationRequest

def test_domain_and_workflow_signals_drive_synthesis():
    m=ProblemModel("fleet",entities=("vehicle","station"),workflows=("swap",),failure_modes=("timeout",))
    s=synthesize_strategies(ExplorationRequest("F",("reliability",)),m)
    assert len(s)>=3
    assert all("problem-derived" in x.principles for x in s)
    assert any("workflow-structure" in x.derivation for x in s)

def test_offline_constraint_creates_distinct_strategy():
    m=ProblemModel("mobile",constraints=("offline operation required",))
    s=synthesize_strategies(ExplorationRequest("M",("availability",)),m)
    assert any(x.family=="offline_resilient" for x in s)

def test_failure_modes_are_preserved_as_risks():
    m=ProblemModel("payments",failure_modes=("duplicate-effect","timeout"))
    s=synthesize_strategies(ExplorationRequest("P",("correctness",)),m)
    assert all("duplicate-effect" in x.known_risks for x in s)
