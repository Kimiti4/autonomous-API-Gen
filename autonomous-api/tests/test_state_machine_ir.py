from app.engine.state_machine_ir import *

def test_initial_state_must_exist():
    sm=StateMachineIR("A","swap",(State("pending"),),(),"missing")
    assert "missing-initial-state" in validate_state_machine(sm)

def test_terminal_states_cannot_have_outgoing_transitions():
    sm=StateMachineIR("A","swap",(State("done",True),State("x")),
        (Transition("t","done","x","retry"),),"done")
    assert "transition-from-terminal:t" in validate_state_machine(sm)

def test_unreachable_states_are_detected():
    sm=StateMachineIR("A","swap",(State("pending"),State("done"),State("orphan")),
        (Transition("t","pending","done","complete"),),"pending")
    assert find_unreachable_states(sm)==("orphan",)

def test_transition_effects_are_triggered():
    sm=StateMachineIR("A","swap",(State("pending"),State("done")),
        (Transition("t","pending","done","","",("commit",)),),"pending")
    assert "effect-without-trigger:t" in verify_transition_effects(sm)

def test_guarded_self_transition_is_allowed():
    sm=StateMachineIR("A","swap",(State("pending"),),
        (Transition("retry","pending","pending","timeout","retryable",("record-retry",)),),"pending")
    assert validate_state_machine(sm)==()
