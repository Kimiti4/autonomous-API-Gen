"""Immutable evidence for bounded ESAP command execution."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from .bounded_execution import ExecutionResult
from .execution_policy import ExecutionPolicy


@dataclass(frozen=True)
class ExecutionEvidence:
    schema_version: str
    execution_id: str
    workspace_id: str
    command: tuple[str, ...]
    policy_digest: str
    exit_code: int | None
    timed_out: bool
    duration_ms: int
    stdout_digest: str
    stderr_digest: str
    status: str
    evidence_digest: str

    def canonical_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "execution_id": self.execution_id,
            "workspace_id": self.workspace_id,
            "command": list(self.command),
            "policy_digest": self.policy_digest,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "stdout_digest": self.stdout_digest,
            "stderr_digest": self.stderr_digest,
            "status": self.status,
        }

    def verify_digest(self) -> bool:
        return self.evidence_digest == _digest(self.canonical_payload())


def materialize_execution_evidence(
    result: ExecutionResult,
    policy: ExecutionPolicy,
) -> ExecutionEvidence:
    policy.validate()
    policy_payload = {
        "allowed_commands": list(policy.allowed_commands),
        "allowed_environment": list(policy.allowed_environment),
        "max_timeout_seconds": policy.max_timeout_seconds,
        "max_output_bytes": policy.max_output_bytes,
    }
    policy_digest = _digest(policy_payload)

    if result.timed_out:
        status = "TIMEOUT"
    elif result.exit_code == 0:
        status = "PASS"
    else:
        status = "FAIL"

    payload = {
        "schema_version": "esap.execution.v1",
        "execution_id": result.execution_id,
        "workspace_id": result.workspace_id,
        "command": list(result.command),
        "policy_digest": policy_digest,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "stdout_digest": result.stdout_digest,
        "stderr_digest": result.stderr_digest,
        "status": status,
    }
    return ExecutionEvidence(duration_ms=result.duration_ms, **payload, evidence_digest=_digest(payload))


def _digest(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
