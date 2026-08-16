"""R2.10.3 — the enforceable primitive landing protocol.

The R2.10.2 extension contract becomes mechanical: every primitive landing
runs the SAME eleven gates. This turns the contract from documentation into
an enforceable protocol — a primitive that fails any gate cannot land.

The ``audit`` gate is the hold-firm one: landing a primitive must move
EXACTLY the intended matrix row and leave every other row untouched.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


PRIMITIVE_GATE: tuple[str, ...] = (
    "representation",     # native ISR construct exists
    "canonicalization",   # empty carriers identity-neutral
    "semantic_identity",  # hash reflects meaningful change
    "validation",         # invalid states rejected pre-execution
    "locality",           # mutation changes only the intended gene
    "projection",         # backend-independent semantic projection
    "compilation",        # existing backend still compatible
    "evidence",           # mutation/evaluation observable
    "lineage",            # evolution event captures the change
    "reproducibility",    # same ISR + seed -> same candidate
    "audit",              # capability matrix changes ONLY as expected
)


@dataclass(frozen=True)
class GateResult:
    """Outcome of one gate for one primitive landing."""

    gate: str
    passed: bool
    evidence: str = ""


class PrimitiveGateHarness(Protocol):
    """A harness implementing the eleven gates for one primitive."""

    primitive_id: str

    def run_gate(self, gate: str) -> GateResult: ...


def assert_all_gates(harness: PrimitiveGateHarness) -> tuple[GateResult, ...]:
    """Run every gate; raise AssertionError with evidence on the first failure."""
    results = tuple(harness.run_gate(gate) for gate in PRIMITIVE_GATE)
    failed = [r for r in results if not r.passed]
    if failed:
        raise AssertionError(
            f"primitive '{harness.primitive_id}' failed gate(s): "
            + "; ".join(f"{r.gate}: {r.evidence}" for r in failed)
        )
    return results