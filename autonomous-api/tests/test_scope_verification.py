import pytest

from app.engine.scope_verification import ChangeScope, derive_verification_plan


def test_frontend_scope_requires_build_and_test():
    plan = derive_verification_plan((ChangeScope.FRONTEND,))
    assert plan.required_kinds == (
        __import__("app.engine.verification_executor", fromlist=["VerificationKind"]).VerificationKind.BUILD,
        __import__("app.engine.verification_executor", fromlist=["VerificationKind"]).VerificationKind.TEST,
    )


def test_backend_api_scope_unions_requirements_without_duplicates():
    from app.engine.verification_executor import VerificationKind
    plan = derive_verification_plan((ChangeScope.BACKEND, ChangeScope.API))
    assert plan.required_kinds == (
        VerificationKind.TEST,
        VerificationKind.TYPECHECK,
        VerificationKind.SMOKE_TEST,
    )


def test_unknown_scope_rule_fails_closed():
    from app.engine.scope_verification import ScopeVerificationRule
    with pytest.raises(ValueError, match="missing-verification-rule"):
        derive_verification_plan(
            (ChangeScope.FRONTEND,),
            rules=(ScopeVerificationRule(ChangeScope.BACKEND, ()),),
        )
