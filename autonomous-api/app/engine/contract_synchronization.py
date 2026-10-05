"""Cross-layer contract synchronization gate for ESAP.

A contract change is not complete until affected producers and consumers are
re-verified. Unknown compatibility remains unknown; it is never treated as
safe by inference.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

from .contract_propagation import ContractLink, PropagationReport, propagate_contract_change


@dataclass(frozen=True)
class ContractSyncDecision:
    contract_id: str
    report: PropagationReport
    verified_artifacts: tuple[str, ...]
    missing_artifacts: tuple[str, ...]
    passed: bool


def evaluate_contract_synchronization(
    contract: ContractLink,
    verification_results: Mapping[str, Mapping[str, object]],
) -> ContractSyncDecision:
    report=propagate_contract_change(contract, True)
    affected=(contract.producer_id, contract.consumer_id)
    missing=[]; verified=[]
    for artifact in affected:
        result=verification_results.get(artifact)
        if not result or result.get("passed") is not True or not result.get("evidence_ids"):
            missing.append(artifact)
        else:
            verified.append(artifact)
    passed=not missing and contract.compatibility == "compatible"
    return ContractSyncDecision(
        contract.contract_id, report, tuple(sorted(verified)),
        tuple(sorted(missing)), passed,
    )


def require_contract_synchronization(decision: ContractSyncDecision) -> None:
    if not decision.passed:
        raise ValueError("contract-synchronization-not-certified")
