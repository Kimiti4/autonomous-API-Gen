from app.engine.architecture_mutation import *
from app.engine.invariant_contracts import Invariant, InvariantContract
from app.engine.fullstack_genome import *

def genome():
    return FullStackGenome(
        FrontendGenome("f","b","c","d","e"),
        BackendGenome("a","b","c","d","e"),
        DataGenome("a","b","c","d"),
        SecurityGenome("a","b",("t",),("c",),"d"),
        OperationalGenome("a","b","c","d"),"p","c")

def test_operator_requires_domain_and_evidence():
    m=domain_operator("m1","backend",("backend.framework",),"improve",("trace",),lambda g:g)
    assert m.request.domain=="backend"

def test_execution_checks_invariants_before_acceptance():
    contract=InvariantContract("security",(Invariant("AUTHZ","security","authz",("sec",)),))
    m=domain_operator("m1","backend",("backend.framework",),"improve",("trace",),lambda g:g)
    result=execute_mutation(genome(),m,(contract,),{"AUTHZ":True})
    assert result.mutation_id=="m1"
    assert result.invariant_results[0].passed

def test_failed_contract_rejects_candidate():
    contract=InvariantContract("security",(Invariant("AUTHZ","security","authz",("sec",)),))
    m=domain_operator("m1","security",("security.threat_model",),"change",("trace",),lambda g:g)
    try:
        execute_mutation(genome(),m,(contract,),{"AUTHZ":False})
    except ValueError as e:
        assert str(e)=="invariant-contract-failed:AUTHZ"
        return
    assert False
