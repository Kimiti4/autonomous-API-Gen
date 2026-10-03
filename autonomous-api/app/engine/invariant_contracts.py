"""Domain invariant contracts for evolutionary mutations."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping, Any, Callable


@dataclass(frozen=True)
class Invariant:
    invariant_id: str
    domain: str
    description: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class InvariantResult:
    invariant_id: str
    passed: bool
    evidence: tuple[str, ...]
    details: str = ""


@dataclass(frozen=True)
class InvariantContract:
    domain: str
    invariants: tuple[Invariant, ...]


def validate_contract(contract: InvariantContract) -> None:
    if contract.domain not in {"frontend", "backend", "data", "security", "operations", "fullstack"}:
        raise ValueError("unknown-invariant-domain")
    if not contract.invariants:
        raise ValueError("contract-requires-invariants")
    for invariant in contract.invariants:
        if invariant.domain != contract.domain:
            raise ValueError("invariant-domain-mismatch")
        if not invariant.evidence:
            raise ValueError("invariant-requires-evidence")


def evaluate_contract(
    contract: InvariantContract,
    observations: Mapping[str, Any],
) -> tuple[InvariantResult, ...]:
    validate_contract(contract)
    results = []
    for invariant in contract.invariants:
        raw = observations.get(invariant.invariant_id)
        if not isinstance(raw, bool):
            raise ValueError("invariant-observation-missing")
        results.append(InvariantResult(
            invariant.invariant_id,
            raw,
            invariant.evidence,
            "passed" if raw else "violated",
        ))
    return tuple(results)


def contract_passes(results: tuple[InvariantResult, ...]) -> bool:
    return bool(results) and all(result.passed for result in results)


def require_contract_pass(results: tuple[InvariantResult, ...]) -> None:
    if not contract_passes(results):
        failed = ",".join(r.invariant_id for r in results if not r.passed)
        raise ValueError("invariant-contract-failed:" + failed)
