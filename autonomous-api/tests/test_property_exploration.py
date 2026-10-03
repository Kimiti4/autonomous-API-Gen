from app.engine.property_exploration import derive_property_scenarios, mutation_targets
from app.engine.state_machine_ir import StateMachineIR, State, Transition

def sm():
    return StateMachineIR("A","wallet",
        (State("pending"),State("done",True)),
        (Transition("pay","pending","done","pay",effects=("ledger-commit",)),),
        "pending",("no-duplicate-effect",))

def test_replay_and_retry_properties_are_derived():
    s=derive_property_scenarios(sm())
    assert any(x.category=="replay" for x in s)
    assert any(x.category=="effect-idempotency" for x in s)

def test_effect_mutation_targets_are_explicit():
    assert mutation_targets(sm())==("ledger-commit",)

def test_competing_transitions_create_ordering_scenarios():
    m=StateMachineIR("A","x",(State("p"),State("d",True)),
        (Transition("a","p","d","a",effects=("e",)),
         Transition("b","p","d","b",effects=("e",))),"p")
    s=derive_property_scenarios(m)
    assert any(x.category=="ordering" for x in s)
    assert any(x.category=="concurrency" for x in s)
