from app.engine.evolution_domains import *

def test_frontend_generates_multiple_improvement_directions():
    o=EvolutionObservation("o1","frontend","stale UI",("trace-1",))
    cs=generate_candidates(o)
    assert {c.candidate_id for c in cs}=={"o1:FE-RESILIENCE","o1:FE-UX"}

def test_backend_candidates_preserve_engineering_properties():
    o=EvolutionObservation("o2","backend","duplicate retry",("trace-2",))
    cs=generate_candidates(o)
    assert any("idempotency" in c.expected_properties for c in cs)

def test_security_evolution_is_explicitly_negative_test_oriented():
    o=EvolutionObservation("o3","security","authorization bypass",("security-test-1",))
    cs=generate_candidates(o)
    assert any("negative-tests" in c.expected_properties for c in cs)

def test_candidates_require_evidence_basis():
    o=EvolutionObservation("o4","fullstack","inconsistent state",())
    assert not any(candidate_is_evidence_backed(c) for c in generate_candidates(o))
