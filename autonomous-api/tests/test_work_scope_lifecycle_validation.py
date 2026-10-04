from app.observation.work_scope_lifecycle_validation import validate_work_scope_lifecycle


def event(t, p, n):
    return type("E", (), {"eventType": t, "payload": p, "sequence": n})()


class P:
    pass


def scope():
    p=P(); p.projectIntent="improve"; p.projectKind="existing_project"; p.generationScope="frontend_only"; return p


def mutation(surface, decision="AUTHORIZED", status=None):
    p=P(); p.surface=surface; p.operation="edit"; p.target="a"; p.decision=decision
    if status: p.status=status
    return p


def verification():
    p=P(); p.surface="frontend"; p.operation="edit"; p.target="a"; p.status="VERIFIED"; return p


def test_valid_order_is_accepted():
    result=validate_work_scope_lifecycle((
        event("scope.declared",scope(),0),
        event("mutation.authorization",mutation("frontend"),1),
        event("mutation.execution",mutation("frontend",status="EXECUTED"),2),
        event("mutation.verification",verification(),3),
    ))
    assert result.valid
    assert not result.issues


def test_execution_without_authorization_is_rejected():
    result=validate_work_scope_lifecycle((
        event("scope.declared",scope(),0),
        event("mutation.execution",mutation("frontend",status="EXECUTED"),1),
    ))
    assert not result.valid
    assert any(x.code == "EXECUTION_WITHOUT_AUTHORIZATION" for x in result.issues)


def test_verification_without_execution_is_rejected():
    result=validate_work_scope_lifecycle((
        event("scope.declared",scope(),0),
        event("mutation.authorization",mutation("frontend"),1),
        event("mutation.verification",verification(),2),
    ))
    assert not result.valid
    assert any(x.code == "VERIFICATION_WITHOUT_EXECUTION" for x in result.issues)


def test_authorization_before_scope_is_rejected():
    result=validate_work_scope_lifecycle((
        event("mutation.authorization",mutation("frontend"),0),
        event("scope.declared",scope(),1),
    ))
    assert not result.valid
    assert any(x.code == "AUTH_BEFORE_SCOPE" for x in result.issues)
