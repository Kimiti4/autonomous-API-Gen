from app.engine.repository_audit_gate import RepositoryAuditScope
from app.engine.work_mode import WorkMode
from app.engine.existing_codebase_workflow import (
    ExistingCodebaseRequest,
    plan_existing_codebase_work,
    require_admissible_existing_codebase_work,
)


def request(mode=WorkMode.MAINTAIN, surface="backend"):
    return ExistingCodebaseRequest(
        project_id="p1",
        project_kind="existing_project",
        mode=mode,
        surface=surface,
        authoritative_obligation_ids=("o1",),
        known_obligation_ids=("o1",),
    )


def test_existing_codebase_requires_complete_inventory():
    gate = plan_existing_codebase_work(
        request(),
        audit_scope=RepositoryAuditScope(expected_files=10, scanned_files=9),
        findings_count=1,
        repair_evidence_complete=True,
    )
    assert not gate.admissible


def test_existing_codebase_is_admissible_only_with_authoritative_scope():
    gate = plan_existing_codebase_work(
        request(),
        audit_scope=RepositoryAuditScope(expected_files=10, scanned_files=10),
        findings_count=1,
        repair_evidence_complete=True,
    )
    assert gate.admissible
    require_admissible_existing_codebase_work(gate)


def test_advisory_scan_cannot_expand_scope():
    gate = plan_existing_codebase_work(
        ExistingCodebaseRequest(
            project_id="p1", project_kind="existing_project",
            mode=WorkMode.MAINTAIN, surface="backend",
            authoritative_obligation_ids=(), known_obligation_ids=(),
        ),
        audit_scope=RepositoryAuditScope(expected_files=1, scanned_files=1),
        findings_count=3,
        repair_evidence_complete=True,
    )
    assert not gate.admissible


def test_surface_only_modes_are_bounded():
    for mode, surface in (
        (WorkMode.FRONTEND_ONLY, "frontend"),
        (WorkMode.BACKEND_ONLY, "backend"),
        (WorkMode.API_CONTRACT_ONLY, "api_contract"),
    ):
        gate = plan_existing_codebase_work(
            request(mode, surface),
            audit_scope=RepositoryAuditScope(expected_files=1, scanned_files=1),
            findings_count=0,
            repair_evidence_complete=True,
        )
        assert gate.admissible


def test_surface_only_mode_rejects_other_surface():
    try:
        plan_existing_codebase_work(
            request(WorkMode.FRONTEND_ONLY, "backend"),
            audit_scope=RepositoryAuditScope(expected_files=1, scanned_files=1),
            findings_count=0,
            repair_evidence_complete=True,
        )
    except ValueError as exc:
        assert str(exc) == "surface-not-authorized-by-mode:backend"
    else:
        raise AssertionError("expected bounded surface rejection")
