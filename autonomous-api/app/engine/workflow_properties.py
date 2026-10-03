"""System-level workflow invariants and property evaluation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class PropertyAssertion:
    assertion_id: str
    description: str
    predicate: Callable[[Mapping[str, Any]], bool]


@dataclass(frozen=True)
class PropertyResult:
    assertion_id: str
    passed: bool
    evidence: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class PropertyReport:
    results: tuple[PropertyResult, ...]

    @property
    def passed(self) -> bool:
        return bool(self.results) and all(r.passed for r in self.results)


def evaluate_properties(
    observations: Mapping[str, Any],
    assertions: tuple[PropertyAssertion, ...],
) -> PropertyReport:
    results = []
    for assertion in assertions:
        try:
            passed = bool(assertion.predicate(observations))
            reason = "predicate satisfied" if passed else "predicate violated"
            evidence = tuple(observations.get("evidence", ()))
        except Exception as exc:
            passed = False
            reason = f"predicate-error:{type(exc).__name__}"
            evidence = tuple(observations.get("evidence", ()))
        results.append(PropertyResult(
            assertion.assertion_id, passed, evidence, reason
        ))
    return PropertyReport(tuple(results))


def standard_invariants() -> tuple[PropertyAssertion, ...]:
    return (
        PropertyAssertion(
            "INV-NO-DUPLICATE-EFFECT",
            "A committed effect identity is not committed twice.",
            lambda o: len(o.get("committed_effect_ids", ())) ==
                      len(set(o.get("committed_effect_ids", ()))),
        ),
        PropertyAssertion(
            "INV-AUTHORIZATION-PRESERVED",
            "Every committed protected effect has an authorization decision.",
            lambda o: set(o.get("committed_effect_ids", ())).issubset(
                set(o.get("authorized_effect_ids", ()))
            ),
        ),
        PropertyAssertion(
            "INV-STATE-VALID",
            "Observed final states belong to the declared valid state set.",
            lambda o: set(o.get("final_states", ())).issubset(
                set(o.get("valid_states", ()))
            ),
        ),
        PropertyAssertion(
            "INV-UI-BACKEND-CONSISTENCY",
            "Final UI state is compatible with the backend outcome.",
            lambda o: bool(o.get("ui_backend_consistent", False)),
        ),
        PropertyAssertion(
            "INV-RECOVERY-CONVERGES",
            "Recovery reaches a declared terminal state.",
            lambda o: bool(o.get("recovery_converged", False)),
        ),
    )
