import pytest

from app.engine.final_closure import ClosureStatus, assess_final_closure, require_final_closure


def test_closure_stops_only_when_authoritative_obligations_and_evidence_are_complete():
    assessment = assess_final_closure(
        work_id="work-1",
        authorized_obligation_ids=("req-2", "req-1"),
        completed_obligation_ids=("req-1", "req-2"),
        verification_evidence_complete=True,
        advisory_findings=("optional-feature-observed",),
    )
    assert assessment.status is ClosureStatus.READY_TO_STOP
    assert assessment.missing_obligation_ids == ()
    assert assessment.advisory_findings == ("optional-feature-observed",)
    require_final_closure(assessment)


def test_missing_authoritative_obligation_blocks_stop():
    assessment = assess_final_closure(
        work_id="work-2",
        authorized_obligation_ids=("req-1", "req-2"),
        completed_obligation_ids=("req-1",),
        verification_evidence_complete=True,
    )
    assert assessment.status is ClosureStatus.BLOCKED
    assert assessment.missing_obligation_ids == ("req-2",)
    with pytest.raises(ValueError, match="closure-not-ready-to-stop"):
        require_final_closure(assessment)


def test_incomplete_verification_blocks_stop():
    assessment = assess_final_closure(
        work_id="work-3",
        authorized_obligation_ids=("req-1",),
        completed_obligation_ids=("req-1",),
        verification_evidence_complete=False,
    )
    assert assessment.status is ClosureStatus.BLOCKED


def test_required_deployment_must_be_ready():
    assessment = assess_final_closure(
        work_id="work-4",
        authorized_obligation_ids=("req-1",),
        completed_obligation_ids=("req-1",),
        verification_evidence_complete=True,
        deployment_required=True,
        deployment_ready=False,
    )
    assert assessment.status is ClosureStatus.BLOCKED


def test_blocking_findings_block_but_advisory_findings_do_not():
    blocked = assess_final_closure(
        work_id="work-5",
        authorized_obligation_ids=("req-1",),
        completed_obligation_ids=("req-1",),
        verification_evidence_complete=True,
        blocking_findings=("regression",),
        advisory_findings=("optional-improvement",),
    )
    assert blocked.status is ClosureStatus.BLOCKED
    assert blocked.advisory_findings == ("optional-improvement",)


def test_missing_work_and_authority_fail_closed():
    with pytest.raises(ValueError, match="closure-missing-work-id"):
        assess_final_closure(
            work_id="", authorized_obligation_ids=("req-1",),
            completed_obligation_ids=("req-1",), verification_evidence_complete=True,
        )
    with pytest.raises(ValueError, match="closure-missing-authoritative-obligations"):
        assess_final_closure(
            work_id="work-6", authorized_obligation_ids=(),
            completed_obligation_ids=(), verification_evidence_complete=True,
        )


def test_closure_digest_is_deterministic():
    kwargs = dict(
        work_id="work-7",
        authorized_obligation_ids=("req-2", "req-1"),
        completed_obligation_ids=("req-1", "req-2"),
        verification_evidence_complete=True,
    )
    assert assess_final_closure(**kwargs).digest == assess_final_closure(**kwargs).digest
