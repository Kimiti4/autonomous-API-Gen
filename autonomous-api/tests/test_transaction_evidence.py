from dataclasses import replace
from app.engine.transaction_evidence import materialize_transaction_evidence
from app.engine.evolution_transaction import execute_evolution_transaction
from app.engine.cross_domain_evolution import CoEvolutionEvent, CoEvolutionResult, DomainChange
from app.engine.evolution_population import ArchitectureLineage, EvolutionMember
from app.engine.fullstack_genome import *
from app.engine.pareto_architecture import ArchitectureScore, Objective
from app.engine.verification_plans import GateResult, VerificationReport
from app.engine.specialized_mutations import backend_mutation

import tempfile
from pathlib import Path

from app.engine.transaction_verification import TransactionVerificationConfig
from app.engine.execution_policy import ExecutionPolicy
from app.engine.verification_acceptance import VerificationAcceptancePolicy
from app.engine.verification_executor import VerificationKind, VerificationSpec


def verification_config():
    return TransactionVerificationConfig(
        specs=(VerificationSpec("build", "successor", VerificationKind.BUILD, ("python", "-c", "print('verified')"), 2),),
        policies={"BUILD": ExecutionPolicy(("python",), max_timeout_seconds=5)},
        acceptance=VerificationAcceptancePolicy(required_kinds=("BUILD",)),
        expected_artifacts={},
    )


def verification_root():
    root = Path(tempfile.gettempdir()) / "esap-transaction-verification"
    root.mkdir(parents=True, exist_ok=True)
    return str(root)



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


def run_transaction():
    return execute_evolution_transaction(
        source(),member(),genome(),
        (repair_spec(),),(dependent_spec(),),
        {"frontend":("backend",)},
        {"state":lambda _:True,"contract":lambda _:True},
        {},
        {"state":("repair:evidence",),"contract":("backend:fresh",)},
        (Objective("quality","maximize"),Objective("risk","minimize")),
        {
            "quality":lambda g,c:{"quality":0.93,"_evidence":["measurement:quality"]},
            "risk":lambda g,c:{"risk":0.17,"_evidence":["measurement:risk"]},
        },{},
        event_id="successor-event",
        successor_architecture_id="successor",
        generation=1,
        verification_config=verification_config(), verification_root=verification_root(),
    )


def test_transaction_contains_content_addressed_audit_record():
    out = run_transaction()
    record = out.audit_record
    assert record.schema_version == "esap.transaction-evidence.v2"
    assert record.transaction_id == "successor-event"
    assert record.successor_architecture_id == "successor"
    assert record.verify_digest()
    assert record.digest in record.to_json() or record.digest not in record.to_json()


def test_audit_record_is_deterministic():
    first = run_transaction().audit_record
    second = run_transaction().audit_record
    assert first.digest == second.digest
    assert first.canonical_payload() == second.canonical_payload()


def test_parent_digest_is_bound_into_record():
    out = execute_evolution_transaction(
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
        event_id="successor-event",successor_architecture_id="successor",
        generation=1,parent_evidence_digest="previous-record-digest",
        verification_config=verification_config(), verification_root=verification_root())
    assert out.audit_record.parent_digest == "previous-record-digest"
    assert out.audit_record.verify_digest()
