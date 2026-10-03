from app.engine.workflow_analysis import analyze_races, derive_verifications, verify_workflow_alignment, RaceCandidate
from app.engine.state_machine_ir import StateMachineIR, State, Transition
from app.engine.flow_ir import FlowIR, FlowNode, FailureRecovery

def sm():
    return StateMachineIR("A","swap",
        (State("pending"),State("done",True)),
        (Transition("complete","pending","done","complete",effects=("commit",)),
         Transition("cancel","pending","done","cancel",effects=("commit",))),
        "pending")

def test_shared_effect_transitions_are_race_candidates():
    races=analyze_races(sm())
    assert len(races)==1
    assert races[0].shared_effects==("commit",)

def test_verification_is_derived_for_transitions_races_and_recovery():
    flow=FlowIR("A",(FlowNode("x","backend","swap"),),(),
                (FailureRecovery("timeout","timeout","retry",2,True),))
    v=derive_verifications(sm(),flow)
    assert any(x.category=="concurrency" for x in v)
    assert any(x.category=="failure-recovery" for x in v)
    assert any(x.category=="state-transition" for x in v)

def test_workflow_layers_share_architecture_identity():
    assert verify_workflow_alignment(sm(),FlowIR("B",(),()))==("architecture-id-mismatch",)
