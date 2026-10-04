import pytest
from app.observation.contracts.work_scope import WorkScopeDeclared
from app.observation.mutation_authorization_events import MutationAuthorizationObserved
from app.observation.mutation_execution_events import MutationExecutionObserved
from app.observation.mutation_verification_events import MutationVerificationObserved
from app.observation.work_scope_lifecycle import project_work_scope_lifecycle


def scope():
    return WorkScopeDeclared(
        projectIntent="improve", projectKind="existing_project",
        generationScope="frontend_only", allowedSurfaces=["frontend"],
        preservedSurfaces=["backend","api_contract"],
    )


def test_projects_complete_lifecycle_counts():
    lifecycle = project_work_scope_lifecycle((
        type("E", (), {"eventType":"scope.declared","payload":scope()})(),
        type("E", (), {"eventType":"mutation.authorization","payload":MutationAuthorizationObserved(surface="frontend",operation="edit",target="a",decision="AUTHORIZED")})(),
        type("E", (), {"eventType":"mutation.authorization","payload":MutationAuthorizationObserved(surface="backend",operation="edit",target="b",decision="BLOCKED",reason="scope")})(),
        type("E", (), {"eventType":"mutation.execution","payload":MutationExecutionObserved(surface="frontend",operation="edit",target="a",status="EXECUTED")})(),
        type("E", (), {"eventType":"mutation.verification","payload":MutationVerificationObserved(surface="frontend",operation="edit",target="a",status="VERIFIED",evidenceDigest="a"*64,admission="ADMITTED")})(),
    ))
    assert lifecycle.authorized_count == 1
    assert lifecycle.blocked_count == 1
    assert lifecycle.executed_count == 1
    assert lifecycle.verified_count == 1
    assert lifecycle.admitted_count == 1


def test_missing_scope_is_rejected():
    with pytest.raises(ValueError, match="missing-work-scope-declaration"):
        project_work_scope_lifecycle(())


def test_multiple_scope_declarations_are_rejected():
    with pytest.raises(ValueError, match="multiple-work-scope-declarations"):
        project_work_scope_lifecycle((
            type("E", (), {"eventType":"scope.declared","payload":scope()})(),
            type("E", (), {"eventType":"scope.declared","payload":scope()})(),
        ))
