from app.engine.fullstack_genome import *

def genome():
    return FullStackGenome(
        FrontendGenome("adaptive","state-machine","event-driven","semantic","retry-recovery"),
        BackendGenome("modular","transactional","controlled","isolated","versioned"),
        DataGenome("relational","constraints","expand-contract","transactional"),
        SecurityGenome("strong-session","object-level",("api","data"),("validation","authz"),"vault"),
        OperationalGenome("immutable","trace+metrics","atomic","bounded"),
        "versioned-contract","explicit-state-flow",
    )

def test_genome_contains_all_engineering_domains():
    assert genome_domains(genome())==("frontend","backend","data","security","operations")

def test_complete_genome_validates():
    assert validate_genome(genome())==()

def test_missing_security_boundary_is_rejected():
    g=genome()
    s=SecurityGenome(g.security.authentication_model,g.security.authorization_model,(),g.security.threat_controls,g.security.secret_handling)
    broken=FullStackGenome(g.frontend,g.backend,g.data,s,g.operations,g.api_contract,g.state_flow)
    assert "missing:security.trust_boundaries" in validate_genome(broken)

def test_missing_contract_is_rejected():
    g=genome()
    broken=FullStackGenome(g.frontend,g.backend,g.data,g.security,g.operations,"",g.state_flow)
    assert "missing:api_contract" in validate_genome(broken)
