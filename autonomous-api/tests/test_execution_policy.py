import pytest

from app.engine.execution_policy import ExecutionPolicy, validate_command, validate_execution_environment


def policy():
    return ExecutionPolicy(
        allowed_commands=("python", "pytest"),
        allowed_environment=("CI",),
        max_timeout_seconds=10,
        max_output_bytes=1000,
    )


def test_policy_accepts_allowed_command_and_environment():
    p = policy()
    validate_command(("python", "-c", "print(1)"), policy=p, timeout_seconds=5)
    assert validate_execution_environment(
        requested_environment={"CI": "true"}, policy=p
    ) == {"CI": "true"}


def test_policy_rejects_unapproved_command_and_environment():
    p = policy()
    with pytest.raises(ValueError, match="execution-policy-command-not-allowed"):
        validate_command(("sh", "-c", "echo x"), policy=p, timeout_seconds=1)
    with pytest.raises(ValueError, match="execution-policy-environment-not-allowed"):
        validate_execution_environment({"SECRET": "x"}, policy=p)


def test_policy_rejects_excessive_timeout_and_invalid_limits():
    p = policy()
    with pytest.raises(ValueError, match="execution-policy-timeout-exceeded"):
        validate_command(("python",), policy=p, timeout_seconds=11)
    with pytest.raises(ValueError, match="execution-policy-invalid-output-limit"):
        ExecutionPolicy(("python",), max_output_bytes=0).validate()
