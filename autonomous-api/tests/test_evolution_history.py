import pytest

from app.engine.evidence_ledger import EvidenceLedger
from app.engine.evolution_history import (
    explain_architecture_decision,
    reconstruct_architecture_history,
)
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


def test_reconstructs_complete_architecture_decision():
    first = transaction("event-1", "successor-1").audit_record
    ledger = EvidenceLedger().append(first)

    history = reconstruct_architecture_history(ledger, "successor-1")
    assert history.chain_valid
    assert history.root_architecture_id == "parent"
    assert len(history.decisions) == 1
    assert history.decisions[0].source_architecture_id == "parent"
    assert history.decisions[0].successor_architecture_id == "successor-1"
    assert history.decisions[0].mutations
    assert history.decisions[0].repairs
    assert history.decisions[0].dependency_effects
    assert history.decisions[0].measurements


def test_explanation_contains_admission_score_and_evidence():
    first = transaction("event-1", "successor-1").audit_record
    ledger = EvidenceLedger().append(first)
    explanation = explain_architecture_decision(ledger, "successor-1")

    assert explanation["status"] == "admitted"
    assert explanation["score"]["values"] == {"quality": 0.93, "risk": 0.17}
    assert "measurement:quality" in explanation["evidence"]
    assert explanation["decision_digest"] == first.digest


def test_reconstruction_fails_closed_on_invalid_ledger():
    first = transaction("event-1", "successor-1").audit_record
    invalid = type(ledger := EvidenceLedger().append(first))(
        ledger.records[:-1] + (ledger.records[-1].__class__(**{
            **ledger.records[-1].__dict__,
            "evidence": ledger.records[-1].evidence + ("forged",),
        }),)
    )
    with pytest.raises(ValueError, match="history-invalid-ledger"):
        reconstruct_architecture_history(invalid, "successor-1")


def test_unknown_architecture_is_explicit():
    ledger = EvidenceLedger()
    result = explain_architecture_decision(ledger, "unknown")
    assert result["status"] == "no-evolution-record"


def test_reconstructed_decision_exposes_rejection_when_present():
    from dataclasses import replace
    from app.engine.transaction_evidence import TransactionEvidenceRecord

    first = transaction("event-1", "successor-1").audit_record
    rejected = replace(
        first,
        admission={"admitted": False, "architecture_id": None, "generation": None},
        rejection={
            "status": "rejected",
            "reasons": ["successor-dominated"],
            "frontier": ["frontier"],
            "counterfactuals": [{"objective": "quality", "required_value": 0.95}],
        },
    )
    payload = rejected.canonical_payload()
    rejected = replace(
        rejected,
        digest=__import__("hashlib").sha256(
            __import__("json").dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    )
    ledger = EvidenceLedger().append(rejected)
    explanation = explain_architecture_decision(ledger, "successor-1")
    assert explanation["status"] == "not-admitted"
    assert explanation["rejection"]["status"] == "rejected"
    assert explanation["rejection"]["counterfactuals"]
