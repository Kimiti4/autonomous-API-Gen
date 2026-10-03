from app.engine.workflow_graph import *

def graph():
    return WorkflowGraph("swap",(
        WorkflowNode("ui","ui","Swap"),
        WorkflowNode("submit","action","Submit"),
        WorkflowNode("api","api","POST /swap"),
        WorkflowNode("svc","backend","Swap service"),
        WorkflowNode("db","persistence","Swap DB"),
        WorkflowNode("recover","recovery","Retry"),
    ),(
        WorkflowEdge("ui","submit","click"),
        WorkflowEdge("submit","api","request"),
        WorkflowEdge("api","svc","dispatch"),
        WorkflowEdge("svc","db","commit"),
        WorkflowEdge("api","recover","failure"),
    ))

def test_workflow_graph_validates():
    assert validate_workflow(graph())==()

def test_reachability_crosses_ui_api_backend_and_persistence():
    assert set(reachable(graph(),"ui"))=={"ui","submit","api","svc","db","recover"}

def test_failure_scenarios_include_adversarial_user_and_runtime_conditions():
    xs=derive_failure_scenarios(graph())
    assert {x.perturbation for x in xs}=={
        "api-timeout","request-retry","duplicate-submit",
        "network-disconnect","backend-failure","stale-client-state",
    }

def test_invalid_reference_is_rejected():
    g=graph()
    g=WorkflowGraph(g.workflow_id,g.nodes,g.edges+(WorkflowEdge("missing","api","x"),))
    assert "unknown-source:missing" in validate_workflow(g)
