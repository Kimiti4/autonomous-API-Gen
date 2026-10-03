from app.engine.verification_plans import *
from app.engine.specialized_mutations import backend_mutation

def spec():
    return backend_mutation(
        "b1",("backend.api",),"improve",("mutation-evidence",),lambda x:x)

def test_plan_requires_all_domain_verifiers():
    try:
        build_verification_plan(spec(), {"api-contract": lambda o: True})
    except ValueError as e:
        assert str(e).startswith("missing-verifiers:")
        return
    assert False

def test_plan_contains_executable_gates():
    s=spec()
    v={p:(lambda o: True) for p in s.verification_properties}
    p=build_verification_plan(s,v)
    assert len(p.gates)==3
    assert all(callable(g.verifier) for g in p.gates)

def test_missing_gate_evidence_rejected():
    s=spec()
    v={p:(lambda o: True) for p in s.verification_properties}
    p=build_verification_plan(s,v)
    try:
        execute_verification(p,{}, {})
    except ValueError as e:
        assert str(e).startswith("missing-evidence:")
        return
    assert False

def test_failed_gate_fails_report():
    s=spec()
    v={p:(lambda o, p=p: p != "effect-safety") for p in s.verification_properties}
    p=build_verification_plan(s,v)
    evidence={g.gate_id: ("trace",) for g in p.gates}
    r=execute_verification(p,{},evidence)
    assert not r.passed
    try:
        require_verification_pass(r)
    except ValueError as e:
        assert "effect-safety" in str(e)
        return
    assert False

def test_all_gates_pass():
    s=spec()
    v={p:(lambda o: True) for p in s.verification_properties}
    p=build_verification_plan(s,v)
    evidence={g.gate_id: ("trace",) for g in p.gates}
    r=execute_verification(p,{},evidence)
    assert r.passed
