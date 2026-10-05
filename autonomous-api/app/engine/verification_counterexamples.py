"""Evidence-bounded verification counterexamples and repair strategies."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class VerificationCounterexample:
    counterexample_id: str
    obligation_id: str
    verification_id: str
    implementation_ids: tuple[str, ...]
    observed_failure: str
    evidence_ids: tuple[str, ...]
    expected: str = ""
    observed: str = ""

    def __post_init__(self) -> None:
        if not self.counterexample_id or not self.obligation_id or not self.verification_id:
            raise ValueError("counterexample-identity-required")
        if not self.implementation_ids:
            raise ValueError("counterexample-implementation-required")
        if not self.observed_failure:
            raise ValueError("counterexample-observation-required")
        if not self.evidence_ids:
            raise ValueError("counterexample-evidence-required")

@dataclass(frozen=True)
class RepairStrategy:
    strategy_id: str
    counterexample_id: str
    operator: str
    target_implementation_ids: tuple[str, ...]
    rationale: str
    required_verification_ids: tuple[str, ...]
    bounded: bool = True

@dataclass(frozen=True)
class CounterexampleRepairResult:
    counterexample: VerificationCounterexample
    strategies: tuple[RepairStrategy, ...]
    findings: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return bool(self.strategies) and not self.findings

def derive_verification_counterexample(*, counterexample_id: str, obligation_id: str,
    verification_id: str, implementation_ids: tuple[str, ...],
    observed_failure: str, evidence_ids: tuple[str, ...],
    expected: str = "", observed: str = "") -> VerificationCounterexample:
    return VerificationCounterexample(
        counterexample_id, obligation_id, verification_id,
        tuple(sorted(set(implementation_ids))), observed_failure,
        tuple(sorted(set(evidence_ids))), expected, observed)

def derive_repair_strategies(counterexample: VerificationCounterexample, *,
    candidate_operators: tuple[str, ...], rationale_by_operator: dict[str, str],
    required_verification_ids: tuple[str, ...]) -> CounterexampleRepairResult:
    findings: list[str] = []
    strategies: list[RepairStrategy] = []
    for operator in sorted(set(candidate_operators)):
        if not operator.strip():
            findings.append("empty-repair-operator")
            continue
        rationale = rationale_by_operator.get(operator, "").strip()
        if not rationale:
            findings.append(f"missing-repair-rationale:{operator}")
            continue
        strategies.append(RepairStrategy(
            f"{counterexample.counterexample_id}:{operator}",
            counterexample.counterexample_id, operator,
            counterexample.implementation_ids, rationale,
            tuple(sorted(set(required_verification_ids)))))
    if not strategies:
        findings.append("no-bounded-repair-strategy")
    if not required_verification_ids:
        findings.append("missing-repair-verification")
    return CounterexampleRepairResult(
        counterexample, tuple(strategies), tuple(sorted(set(findings))))

def select_repair_strategy(result: CounterexampleRepairResult, *,
    strategy_id: str) -> RepairStrategy:
    for strategy in result.strategies:
        if strategy.strategy_id == strategy_id:
            return strategy
    raise ValueError("repair-strategy-not-admitted")
