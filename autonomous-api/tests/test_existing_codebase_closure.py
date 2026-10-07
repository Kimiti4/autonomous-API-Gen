from app.engine.existing_codebase_audit import audit_existing_codebase
from app.engine.existing_codebase_closure import ClosureDecision, close_existing_codebase_work
from app.engine.project_completion import Evidence, Obligation, ProjectCompletionEngine


def _state():
    engine = ProjectCompletionEngine(
        project_id="p1",
        evidence=(Evidence("e1", "verification passed", authoritative=True),),
        obligations=(
            Obligation("o1", "p1", "requirement", "authorized maintenance"),
        ),
    )
    engine.certify("o1", ("e1",))
    return engine.reconstruct()


def _audit():
    return audit_existing_codebase(
        (("app.py", "def main():\n    return 1\n"),),
        expected_files=1,
        repair_evidence_complete=True,
    )


def test_closure_stops_only_when_all_final_evidence_is_present():
    result = close_existing_codebase_work(
        _audit(), _state(),
        verification_complete=True,
        documentation_complete=True,
        deployment_ready=True,
    )
    assert result.decision is ClosureDecision.STOP
    assert result.stopped


def test_closure_continues_when_any_final_gate_is_missing():
    result = close_existing_codebase_work(
        _audit(), _state(),
        verification_complete=False,
        documentation_complete=True,
        deployment_ready=True,
    )
    assert result.decision is ClosureDecision.CONTINUE
    assert "verification-incomplete" in result.reasons


def test_closure_cannot_stop_without_repair_certification_evidence():
    audit = audit_existing_codebase(
        (("app.py", "def main():\n    return 1\n"),),
        expected_files=1,
        repair_evidence_complete=False,
    )
    result = close_existing_codebase_work(
        audit, _state(),
        verification_complete=True,
        documentation_complete=True,
        deployment_ready=True,
    )
    assert result.decision is ClosureDecision.CONTINUE
    assert "repair-certification-evidence-incomplete" in result.reasons
