from app.engine.problem_synthesis import ProblemModel, synthesize_strategies
from app.engine.exploration_engine import ExplorationRequest

def test_problem_structure_changes_strategy_space():
    r=ExplorationRequest("EV",("correctness","reliability"))
    p=ProblemModel("mobility",workflows=("swap","settle"),failure_modes=("offline",))
    s=synthesize_strategies(r,p)
    assert any(x.family=="workflow_composed" for x in s)
    assert any("workflow-structure" in x.derivation for x in s)

def test_constraints_can_create_new_strategy():
    r=ExplorationRequest("IOT",("throughput",))
    p=ProblemModel("telemetry",constraints=("high throughput",))
    s=synthesize_strategies(r,p)
    assert any(x.family=="throughput_optimized" for x in s)

def test_domain_entities_are_preserved_as_components():
    r=ExplorationRequest("EV",("correctness",))
    p=ProblemModel("mobility",entities=("vehicle","station","battery"))
    s=synthesize_strategies(r,p)
    assert all(set(p.entities).issubset(set(x.components)) for x in s)
