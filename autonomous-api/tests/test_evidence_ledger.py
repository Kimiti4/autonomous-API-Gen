from dataclasses import replace

import pytest

from app.engine.evidence_ledger import EvidenceLedger, replay_ledger
from app.engine.evolution_transaction import execute_evolution_transaction
from app.engine.cross_domain_evolution import CoEvolutionEvent, CoEvolutionResult, DomainChange
from app.engine.evolution_population import ArchitectureLineage, EvolutionMember
from app.engine.fullstack_genome import *
from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.verification_plans import GateResult, VerificationReport
from app.engine.specialized_mutations import backend_mutation


def genome():
    return FullStackGenome(
        FrontendGenome("render","state","interaction","a11y","resilience"),
        BackendGenome("service","strong","safe","retry","contract"),
        DataGenome("sql","integrity","expand-contract","strong"),
        SecurityGenome("identity","rbac",("api",),("audit",),"vault"),
        OperationalGenome("containers","metrics","rollback","bounded"),
        "v1","frontend->api->backend")


def source():
    event=CoEvolutionEvent("source-event","parent",(DomainChange("frontend","f1",("state",)),),("impact",))
    report=VerificationReport("f1",(GateResult("frontend:state","state",False,("counterexample",)),),False)
    return CoEvolutionResult(event,"parent",(report,),False)


def member():
    return EvolutionMember(
        ArchitectureLineage("parent",(),0,("parent",)),
        ArchitectureScore("parent",{"quality":1.0,"risk":5.0},("parent",)))


def repair_spec():
    return backend_mutation("f1-repair",("frontend.state",),"repair frontend",("state",),lambda g:g)


def dependent_spec():
    return backend_mutation("b1",("backend.api",),"reverify backend",("contract",),lambda g:g)


def transaction(event_id, successor_id, parent_digest=None):
    return execute_evolution_transaction(
        source(),member(),genome(),
        (repair_spec(),),(dependent_spec(),),
        {"frontend":("backend",)},
        {"state":lambda _:True,"contract":lambda _:True},{},
        {"state":("repair:evidence",),"contract":("backend:fresh",)},
        (Objective("quality","maximize"),Objective("risk","minimize")),
        {
            "quality":lambda g,c:{"quality":0.93,"_evidence":["measurement:quality"]},
            "risk":lambda g,c:{"risk":0.17,"_evidence":["measurement:risk"]},
        },{},
        event_id=event_id,successor_architecture_id=successor_id,
        generation=1,parent_evidence_digest=parent_digest,
    )


def test_ledger_accepts_valid_genesis_record():
    record = transaction("event-1", "successor-1").audit_record
    ledger = EvidenceLedger().append(record)
    assert ledger.verify()
    assert ledger.head_digest == record.digest
    assert ledger.transaction("event-1") == record


def test_ledger_requires_exact_parent_digest():
    first = transaction("event-1", "successor-1").audit_record
    second = transaction("event-2", "successor-2", parent_digest=first.digest).audit_record
    assert EvidenceLedger().append(first).append(second).verify()


def test_ledger_rejects_forged_parent_chain():
    first = transaction("event-1", "successor-1").audit_record
    forged = transaction("event-2", "successor-2", parent_digest="wrong").audit_record
    with pytest.raises(ValueError, match="ledger-parent-digest-mismatch"):
        EvidenceLedger().append(first).append(forged)


def test_ledger_rejects_duplicate_transaction():
    first = transaction("event-1", "successor-1").audit_record
    with pytest.raises(ValueError, match="ledger-duplicate-transaction"):
        EvidenceLedger().append(first).append(first)


def test_ledger_rejects_tampered_record():
    first = transaction("event-1", "successor-1").audit_record
    tampered = replace(first, evidence=first.evidence + ("forged",))
    with pytest.raises(ValueError, match="ledger-invalid-record-digest"):
        EvidenceLedger().append(tampered)


def test_replay_reconstructs_same_chain():
    first = transaction("event-1", "successor-1").audit_record
    second = transaction("event-2", "successor-2", parent_digest=first.digest).audit_record
    ledger = replay_ledger((first, second))
    assert ledger.verify()
    assert tuple(r.digest for r in ledger.records) == (first.digest, second.digest)
