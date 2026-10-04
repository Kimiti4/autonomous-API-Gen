import pytest

from app.engine.trust_boundary import (
    TrustBoundaryViolation,
    TrustContext,
    validate_allowed_commands,
    validate_environment,
    validate_transaction_identity,
    validate_trust_context,
)


def test_valid_trust_context_passes():
    context = TrustContext("esap", "tx-1", "source", "candidate", ("python",))
    validate_trust_context(context, command=("python",))


@pytest.mark.parametrize(
    "kwargs,error",
    [
        ({"transaction_id": "", "source_architecture_id": "s", "candidate_architecture_id": "c"}, "missing-transaction-id"),
        ({"transaction_id": " tx", "source_architecture_id": "s", "candidate_architecture_id": "c"}, "non-canonical-transaction-id"),
        ({"transaction_id": "tx", "source_architecture_id": "", "candidate_architecture_id": "c"}, "missing-source-architecture-id"),
        ({"transaction_id": "tx", "source_architecture_id": "s", "candidate_architecture_id": ""}, "missing-candidate-architecture-id"),
    ],
)
def test_identity_is_fail_closed(kwargs, error):
    with pytest.raises(TrustBoundaryViolation, match=error):
        validate_transaction_identity(**kwargs)


def test_untrusted_command_is_rejected():
    with pytest.raises(TrustBoundaryViolation, match="command-not-trusted"):
        validate_allowed_commands(("rm", "-rf", "/"), allowed_commands=("python",))


def test_untrusted_environment_is_rejected():
    with pytest.raises(TrustBoundaryViolation, match="environment-not-trusted"):
        validate_environment({"SECRET": "value"}, allowed_environment=("PATH",))


def test_context_rejects_untrusted_command():
    context = TrustContext("esap", "tx", "source", "candidate", ("python",))
    with pytest.raises(TrustBoundaryViolation):
        validate_trust_context(context, command=("shell",))


def test_context_rejects_missing_actor():
    context = TrustContext("", "tx", "source", "candidate")
    with pytest.raises(TrustBoundaryViolation, match="missing-trust-context:actor"):
        validate_trust_context(context)
