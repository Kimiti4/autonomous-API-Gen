import pytest

from app.engine.execution_policy import ExecutionPolicy
from app.engine.verification_command_planner import VerificationCommandRule
from app.engine.verification_executor import VerificationKind
from app.engine.work_scope_verification import derive_work_verification_plan


def rule(kind):
    return VerificationCommandRule(
        kind, ("python", "-c", "print('ok')"), 5,
        ExecutionPolicy(("python",), max_timeout_seconds=5),
    )


def test_materialized_domains_derive_executable_obligations():
    plan = derive_work_verification_plan(
        ("frontend", "backend"), workspace_id="candidate-1",
        command_rules=(
            rule(VerificationKind.BUILD),
            rule(VerificationKind.TEST),
            rule(VerificationKind.TYPECHECK),
        ),
    )
    assert plan.scopes
    assert plan.executable.specs
    assert [s.kind for s in plan.executable.specs] == [
        VerificationKind.BUILD,
        VerificationKind.TEST,
        VerificationKind.TYPECHECK,
    ]


def test_unknown_work_domain_fails_closed():
    with pytest.raises(ValueError, match="missing-domain-scope:quantum"):
        derive_work_verification_plan(
            ("quantum",), workspace_id="candidate-1", command_rules=()
        )


def test_empty_work_scope_fails_closed():
    with pytest.raises(ValueError, match="missing-work-domains"):
        derive_work_verification_plan(
            (), workspace_id="candidate-1", command_rules=()
        )
