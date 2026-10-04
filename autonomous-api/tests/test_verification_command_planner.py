import pytest

from app.engine.execution_policy import ExecutionPolicy
from app.engine.scope_verification import ChangeScope, derive_verification_plan
from app.engine.verification_command_planner import (
    VerificationCommandRule, compile_verification_commands,
)
from app.engine.verification_executor import VerificationKind


def rule(kind):
    return VerificationCommandRule(
        kind=kind,
        command=("python", "-c", "print('verified')"),
        timeout_seconds=5,
        policy=ExecutionPolicy(("python",), max_timeout_seconds=5),
    )


def test_scope_plan_compiles_to_executable_commands():
    plan = derive_verification_plan((ChangeScope.BACKEND,))
    compiled = compile_verification_commands(
        plan, workspace_id="ws-1",
        command_rules=(rule(VerificationKind.TEST), rule(VerificationKind.TYPECHECK)),
    )
    assert [s.kind for s in compiled.specs] == [
        VerificationKind.TEST, VerificationKind.TYPECHECK
    ]
    assert compiled.specs[0].verification_id == "ws-1:test"
    assert set(compiled.policies) == {"TEST", "TYPECHECK"}


def test_missing_command_mapping_fails_closed():
    plan = derive_verification_plan((ChangeScope.API,))
    with pytest.raises(ValueError, match="missing-verification-command:TEST"):
        compile_verification_commands(
            plan, workspace_id="ws-1",
            command_rules=(rule(VerificationKind.SMOKE_TEST),),
        )
