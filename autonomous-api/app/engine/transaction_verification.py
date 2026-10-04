"""Executable verification bridge for ESAP evolution transactions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .admission_verification import CandidateVerification, materialize_candidate_verification, require_candidate_verification
from .execution_policy import ExecutionPolicy
from .verification_acceptance import VerificationAcceptancePolicy, assess_verification_suite
from .verification_artifacts import VerificationArtifactResult, collect_verification_outputs
from .verification_executor import VerificationResult, VerificationSpec, execute_verification_suite


@dataclass(frozen=True)
class TransactionVerificationConfig:
    specs: tuple[VerificationSpec, ...]
    policies: Mapping[str, ExecutionPolicy]
    acceptance: VerificationAcceptancePolicy
    expected_artifacts: Mapping[str, tuple[str, ...]]


def execute_transaction_verification(
    config: TransactionVerificationConfig,
    *,
    root: str,
) -> CandidateVerification:
    policies = {}
    for kind, policy in config.policies.items():
        policies[next(k for k in __import__("app.engine.verification_executor", fromlist=["VerificationKind"]).VerificationKind if k.value == kind)] = policy

    results = execute_verification_suite(
        config.specs, root=root, policies=policies,
    )
    artifact_results: list[VerificationArtifactResult] = []
    for result in results:
        paths = config.expected_artifacts.get(result.verification_id, ())
        if paths:
            artifact_results.append(
                collect_verification_outputs(result, root=root, expected_paths=paths)
            )

    disposition = assess_verification_suite(
        results, policy=config.acceptance, artifact_results=artifact_results,
    )
    candidate = materialize_candidate_verification(
        disposition, results, artifact_results,
    )
    require_candidate_verification(candidate)
    return candidate
