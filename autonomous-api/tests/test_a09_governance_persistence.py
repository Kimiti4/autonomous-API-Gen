import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = REPO_ROOT / "autonomous-api"


def _run_restart(workdir: Path, script: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(APP_ROOT)
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=workdir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_governance_state_survives_process_restart_and_tamper_fails_closed(tmp_path):
    first = _run_restart(
        tmp_path,
        """
import asyncio
from app.storage.db import init_db
from app.governance.adapters.sqlite import SqliteGovernanceEventStore, SqliteGovernanceReferenceStore
from app.governance.subsystem import GovernanceSubsystem
from app.core.contracts.governance import CouncilMember, GovernanceGate, TransitionRef
from app.core.governance.commands import (
    UpdateCouncil, RegisterGate, RecordGateEvaluation,
    RequestGovernanceDecision, GrantCertification,
)


async def main():
    init_db()
    governance = GovernanceSubsystem(
        event_store=SqliteGovernanceEventStore("test-a09-key"),
        reference_store=SqliteGovernanceReferenceStore(),
        quorum_threshold=1.0,
        recognized_certifiers={"certifier"},
        executive_voting_weight=0.6,
    )
    await governance.update_council(UpdateCouncil(
        members=[CouncilMember(
            memberId="member-1", name="Member One", role="council", votingWeight=1.0
        )],
        updatedBy="test",
    ))
    await governance.register_gate(RegisterGate(
        gate=GovernanceGate(
            gateId="intake-1",
            name="Intake",
            category="intake",
            guards=[TransitionRef(fromState="proposed", toState="evaluating")],
        ),
        registeredBy="test",
    ))
    await governance.record_gate_evaluation(RecordGateEvaluation(
        gateId="intake-1",
        candidateId="candidate-1",
        status="passed",
        evaluatedBy="member-1",
    ))
    await governance.request_decision(RequestGovernanceDecision(
        candidateId="candidate-1",
        generation=7,
        fromState="proposed",
        toState="evaluating",
        requestedBy="member-1",
        decidedBy=["member-1"],
        verdict="approve",
        authorizesTransition=True,
        rationale="restart persistence test",
    ))
    await governance.grant_certification(GrantCertification(
        candidateId="candidate-1",
        certificationId="cert-1",
        certifiedBy="certifier",
        criteria="A09 persistence",
    ))
    assert len(await governance.audit_candidate("candidate-1")) == 3


asyncio.run(main())
""",
    )
    assert first.returncode == 0, first.stderr

    second = _run_restart(
        tmp_path,
        """
import asyncio
from app.governance.adapters.sqlite import SqliteGovernanceEventStore, SqliteGovernanceReferenceStore
from app.governance.subsystem import GovernanceSubsystem


async def main():
    governance = GovernanceSubsystem(
        event_store=SqliteGovernanceEventStore("test-a09-key"),
        reference_store=SqliteGovernanceReferenceStore(),
        quorum_threshold=1.0,
        recognized_certifiers={"certifier"},
        executive_voting_weight=0.6,
    )
    state = await governance.materialize_candidate("candidate-1")
    assert state.current_state == "evaluating"
    assert state.gate_status("intake-1") == "passed"
    assert [c.certificationId for c in state.active_certifications()] == ["cert-1"]
    assert len(await governance.audit_candidate("candidate-1")) == 3
    assert (await governance._refs.load_council()).members[0].memberId == "member-1"
    assert (await governance._refs.load_gates())[0].gateId == "intake-1"


asyncio.run(main())
""",
    )
    assert second.returncode == 0, second.stderr

    third = _run_restart(
        tmp_path,
        """
import asyncio
from app.governance.adapters.sqlite import SqliteGovernanceEventStore, SqliteGovernanceReferenceStore
from app.governance.subsystem import GovernanceSubsystem
from app.core.governance.commands import RevokeCertification


async def main():
    governance = GovernanceSubsystem(
        event_store=SqliteGovernanceEventStore("test-a09-key"),
        reference_store=SqliteGovernanceReferenceStore(),
        quorum_threshold=1.0,
        recognized_certifiers={"certifier"},
    )
    await governance.revoke_certification(RevokeCertification(
        candidateId="candidate-1",
        certificationId="cert-1",
        revokedBy="member-1",
        reason="test revocation",
    ))


asyncio.run(main())
""",
    )
    assert third.returncode == 0, third.stderr

    fourth = _run_restart(
        tmp_path,
        """
import asyncio
from app.governance.adapters.sqlite import SqliteGovernanceEventStore, SqliteGovernanceReferenceStore
from app.governance.subsystem import GovernanceSubsystem


async def main():
    governance = GovernanceSubsystem(
        event_store=SqliteGovernanceEventStore("test-a09-key"),
        reference_store=SqliteGovernanceReferenceStore(),
        quorum_threshold=1.0,
        recognized_certifiers={"certifier"},
    )
    state = await governance.materialize_candidate("candidate-1")
    assert state.active_certifications() == []
    assert state.certifications[0].revokedBy == "member-1"
    assert len(await governance.audit_candidate("candidate-1")) == 4


asyncio.run(main())
""",
    )
    assert fourth.returncode == 0, fourth.stderr

    db_path = tmp_path / "data" / "evolution.db"
    import sqlite3

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE governance_audit SET payload = ? WHERE candidate_id = ? AND sequence = 1",
            ('{"type":"tampered"}', "candidate-1"),
        )
        connection.commit()

    tampered = _run_restart(
        tmp_path,
        """
import asyncio
from app.governance.adapters.sqlite import SqliteGovernanceEventStore
from app.core.governance.audit import AuditIntegrityError


async def main():
    try:
        await SqliteGovernanceEventStore("test-a09-key").load("candidate-1")
    except AuditIntegrityError:
        return
    raise AssertionError("tampered governance history must fail closed")


asyncio.run(main())
""",
    )
    assert tampered.returncode == 0, tampered.stderr
