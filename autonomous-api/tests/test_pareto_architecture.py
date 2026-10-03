from app.engine.pareto_architecture import *

def s(i,a,b,e=("e",)):
    return ArchitectureScore(i,{"quality":a,"latency":b},e)

def test_dominance_respects_objective_direction():
    assert dominates(s("a",10,100),s("b",8,120),
                     (Objective("quality","maximize"),Objective("latency","minimize")))

def test_frontier_retains_non_dominated_tradeoffs():
    r=build_frontier(
        (s("a",10,100),s("b",8,80),s("c",7,120)),
        (Objective("quality","maximize"),Objective("latency","minimize")))
    assert set(r.frontier)=={"a","b"}
    assert r.dominated==("c",)

def test_unevidenced_score_is_rejected():
    try:
        build_frontier((s("a",1,1,()),), (Objective("quality","maximize"),Objective("latency","minimize")))
    except ValueError as e:
        assert str(e)=="pareto-score-requires-evidence"
        return
    assert False

def test_missing_objective_is_rejected():
    try:
        build_frontier((ArchitectureScore("a",{"quality":1},("e",)),),
                       (Objective("quality","maximize"),Objective("latency","minimize")))
    except ValueError as e:
        assert str(e)=="missing-objective-value"
        return
    assert False

def test_assessments_become_evidenced_scores():
    a=TradeoffAssessment("a",(),(),{"quality":9,"latency_ms":50},("trace",),"bounded")
    scores=scores_from_assessments((a,),{"quality":"quality","latency":"latency_ms"})
    assert scores[0].values=={"quality":9.0,"latency":50.0}
