"""Fail-closed trust-boundary validation for ESAP transaction inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


class TrustBoundaryViolation(ValueError):
    """Raised when untrusted transaction input crosses a governed boundary."""


@dataclass(frozen=True)
class TrustContext:
    actor: str
    transaction_id: str
    source_architecture_id: str
    candidate_architecture_id: str
    allowed_commands: tuple[str, ...] = ()

    def validate(self) -> None:
        for name, value in (
            ("actor", self.actor),
            ("transaction-id", self.transaction_id),
            ("source-architecture-id", self.source_architecture_id),
            ("candidate-architecture-id", self.candidate_architecture_id),
        ):
            if not value or not value.strip():
                raise TrustBoundaryViolation(f"missing-trust-context:{name}")


def validate_transaction_identity(
    *,
    transaction_id: str,
    source_architecture_id: str,
    candidate_architecture_id: str,
) -> None:
    if not transaction_id:
        raise TrustBoundaryViolation("missing-transaction-id")
    if not source_architecture_id:
        raise TrustBoundaryViolation("missing-source-architecture-id")
    if not candidate_architecture_id:
        raise TrustBoundaryViolation("missing-candidate-architecture-id")
    if transaction_id.strip() != transaction_id:
        raise TrustBoundaryViolation("non-canonical-transaction-id")
    if source_architecture_id.strip() != source_architecture_id:
        raise TrustBoundaryViolation("non-canonical-source-architecture-id")
    if candidate_architecture_id.strip() != candidate_architecture_id:
        raise TrustBoundaryViolation("non-canonical-candidate-architecture-id")


def validate_allowed_commands(
    command: Sequence[str],
    *,
    allowed_commands: Sequence[str],
) -> None:
    if not command or not command[0]:
        raise TrustBoundaryViolation("missing-command")
    if command[0] not in set(allowed_commands):
        raise TrustBoundaryViolation("command-not-trusted:" + command[0])


def validate_environment(
    environment: Mapping[str, str] | None,
    *,
    allowed_environment: Sequence[str],
) -> dict[str, str] | None:
    if environment is None:
        return None
    allowed = set(allowed_environment)
    unexpected = sorted(set(environment) - allowed)
    if unexpected:
        raise TrustBoundaryViolation(
            "environment-not-trusted:" + ",".join(unexpected)
        )
    return dict(environment)


def validate_trust_context(
    context: TrustContext,
    *,
    command: Sequence[str] | None = None,
    environment: Mapping[str, str] | None = None,
) -> None:
    context.validate()
    validate_transaction_identity(
        transaction_id=context.transaction_id,
        source_architecture_id=context.source_architecture_id,
        candidate_architecture_id=context.candidate_architecture_id,
    )
    if command is not None:
        validate_allowed_commands(command, allowed_commands=context.allowed_commands)
    validate_environment(environment, allowed_environment=())
