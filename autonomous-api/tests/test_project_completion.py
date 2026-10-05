from app.engine.project_completion import (
    Advisory,
    Evidence,
    Obligation,
    ProjectCompletionEngine,
)


def evidence(evidence_id: str, authoritative: bool = True) -> Evidence:
    return Evidence(evidence_id, f"evidence:{evidence_id}", authoritative)


def test_empty_project_is_unknown_not_complete() -> None:
    engine = ProjectCompletionEngine(project_id="p1")
    assert engine.reconstruct().status == "UNKNOWN"
    assert not engine.is_stopped()


def test_complete_only_when_every_obligation_is_certified() -> None:
    engine = ProjectCompletionEngine(
        project_id="p1",
        evidence=[evidence("e1"), evidence("e2")],
        obligations=[
            Obligation("r1", "p1", "requirement", "Login"),
            Obligation("r2", "p1", "requirement", "Logout"),
        ],
    )
    engine.certify("r1", ["e1"])
    assert engine.reconstruct().status == "IN_PROGRESS"
    engine.certify("r2", ["e2"])
    state = engine.reconstruct()
    assert state.status == "COMPLETE"
    assert state.remaining_obligation_ids == ()
    assert engine.is_stopped()


def test_certification_cannot_use_advisory_or_missing_evidence() -> None:
    engine = ProjectCompletionEngine(
        project_id="p1",
        evidence=[evidence("a", authoritative=False)],
        obligations=[Obligation("r1", "p1", "requirement", "Feature")],
    )
    try:
        engine.certify("r1", ["a"])
    except ValueError as exc:
        assert str(exc) == "certification-requires-authoritative-evidence"
    else:
        raise AssertionError("expected certification rejection")


def test_unjustified_feature_work_is_rejected() -> None:
    engine = ProjectCompletionEngine(project_id="p1")
    try:
        engine.reject_unjustified_work("Add another feature because it might help")
    except ValueError as exc:
        assert str(exc) == "ungoverned-work-rejected"
    else:
        raise AssertionError("expected rejection")


def test_advisory_is_not_a_required_obligation() -> None:
    engine = ProjectCompletionEngine(
        project_id="p1",
        advisories=[Advisory("a1", "p1", "Consider caching")],
    )
    state = engine.reconstruct()
    assert state.status == "UNKNOWN"
    assert state.required_obligation_ids == ()
    assert state.advisory_ids == ("a1",)


def test_maintenance_reopens_a_completed_project_without_rewriting_history() -> None:
    engine = ProjectCompletionEngine(
        project_id="p1",
        evidence=[evidence("e1")],
        obligations=[Obligation("r1", "p1", "requirement", "Login")],
    )
    engine.certify("r1", ["e1"])
    assert engine.is_stopped()

    reopened = engine.request_maintenance("Improve login error handling")
    assert reopened.obligation.kind == "maintenance"
    assert reopened.obligation.status == "UNKNOWN"
    assert not engine.is_stopped()
    assert engine.reconstruct().certified_obligation_ids == ("r1",)


def test_regression_reopens_only_through_explicit_regression_obligation() -> None:
    engine = ProjectCompletionEngine(
        project_id="p1",
        evidence=[evidence("e1")],
        obligations=[Obligation("r1", "p1", "requirement", "Login")],
    )
    engine.certify("r1", ["e1"])
    regression = engine.reopen_for_regression("r1", "Login now returns 500")
    assert regression.kind == "regression"
    assert regression.parent_obligation_id == "r1"
    assert engine.reconstruct().status == "IN_PROGRESS"
    assert engine.reconstruct().certified_obligation_ids == ("r1",)


def test_wrong_project_and_invalid_reopen_are_rejected() -> None:
    engine = ProjectCompletionEngine(project_id="p1")
    try:
        engine.add_obligation(Obligation("r2", "p2", "requirement", "Other"))
    except ValueError as exc:
        assert str(exc) == "obligation-project-mismatch"
    else:
        raise AssertionError("expected project mismatch")

    try:
        engine.add_obligation(
            Obligation("r3", "p1", "requirement", "Bad", status="REOPENED")
        )
    except ValueError as exc:
        assert str(exc) == "only-regression-or-maintenance-may-reopen"
    else:
        raise AssertionError("expected invalid reopen")


def test_state_digest_is_deterministic() -> None:
    kwargs = dict(
        project_id="p1",
        evidence=[evidence("e1")],
        obligations=[Obligation("r1", "p1", "requirement", "Login")],
    )
    a = ProjectCompletionEngine(**kwargs).reconstruct()
    b = ProjectCompletionEngine(**kwargs).reconstruct()
    assert a.state_digest == b.state_digest
