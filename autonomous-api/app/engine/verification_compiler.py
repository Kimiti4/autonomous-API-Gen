"""Technology-neutral verification plans and target compiler boundary."""
from __future__ import annotations
from dataclasses import dataclass
from .verification_obligations import VerificationObligation


@dataclass(frozen=True)
class VerificationPlan:
    plan_id: str
    obligations: tuple[VerificationObligation, ...]
    required_evidence: tuple[str, ...]
    fail_closed: bool = True


@dataclass(frozen=True)
class VerificationAdapter:
    target: str
    executor_kind: str
    supported_categories: tuple[str, ...]


def build_verification_plan(
    obligations: tuple[VerificationObligation, ...],
    plan_id: str = "verification-plan",
) -> VerificationPlan:
    evidence = tuple(sorted({
        f"{o.obligation_id}:execution-result" for o in obligations
    }))
    return VerificationPlan(plan_id, obligations, evidence)


def adapter_for(target: str) -> VerificationAdapter:
    adapters = {
        "python": VerificationAdapter(
            "python", "target-test-runner",
            ("authorization","idempotency","concurrency","recovery","contract","frontend","integration","effect","event")),
        "node": VerificationAdapter(
            "node", "target-test-runner",
            ("authorization","idempotency","concurrency","recovery","contract","frontend","integration","effect","event")),
        "swift": VerificationAdapter(
            "swift", "target-test-runner",
            ("authorization","idempotency","concurrency","recovery","contract","frontend","integration","effect","event")),
        "kotlin": VerificationAdapter(
            "kotlin", "target-test-runner",
            ("authorization","idempotency","concurrency","recovery","contract","frontend","integration","effect","event")),
    }
    if target not in adapters:
        raise ValueError(f"unsupported verification target: {target}")
    return adapters[target]
