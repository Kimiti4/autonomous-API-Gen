"""Semantic sensitivity gate -- discrimination before certification."""
from __future__ import annotations

from dataclasses import dataclass

from tiannara.application.evolution.ledger import EvolutionEvent, EvolutionLedger, EventType


@dataclass(frozen=True)
class SensitivityCase:
    case_id: str
    artifact_ref: str
    defect_class: str | None
    expected_verdict: str
    expected_gate: str | None
    actual_verdict: str
    sensitive: bool


@dataclass(frozen=True)
class SensitivityVerdict:
    sensitive: bool
    cases: tuple[SensitivityCase, ...]
    insensitive_cases: tuple[str, ...]
    sensitivity_event_ref: str


class CertificationInsensitivity(RuntimeError):
    pass


class SemanticSensitivityGate:
    def __init__(self, cases=None):
        self._cases_spec = cases or (
            ("known_good", None, "CERTIFIED", None),
            ("security_defect", "hardcoded_secret", "NOT_CERTIFIED", "security"),
            ("authorization_bypass", "missing_authz_check", "NOT_CERTIFIED", "security"),
            ("architectural_defect", "boundary_violation", "NOT_CERTIFIED", "isr_conformance"),
            ("responsibility_defect", "god_module", "NOT_CERTIFIED", "phase32_quality_gates"),
            ("complexity_defect", "cyclomatic_explosion", "NOT_CERTIFIED", "phase32_quality_gates"),
            ("failure_omission", "no_timeout_handling", "NOT_CERTIFIED", "phase32_quality_gates"),
        )

    def validate(self, certifier, ledger: EvolutionLedger) -> SensitivityVerdict:
        results = []
        for case_id, defect, expected, gate in self._cases_spec:
            artifact_ref = f"artifact-{case_id}"
            actual = certifier.certify(artifact_ref, defect_class=defect)
            verdict_str = getattr(actual, "verdict", str(actual))
            # Handle enum
            if hasattr(verdict_str, "value"):
                verdict_str = verdict_str.value
            sensitive = (verdict_str == expected)
            results.append(SensitivityCase(case_id, artifact_ref, defect, expected, gate, verdict_str, sensitive))
        insensitive = tuple(r.case_id for r in results if not r.sensitive)
        sensitive = not insensitive
        # Record to ledger
        ev = EvolutionEvent(
            event_id=f"sensitivity-{canonical_hash(str(results))[:8]}",
            evolution_id="sensitivity",
            sequence=0,
            event_type=EventType.CERTIFICATION,
            subject_id="sensitivity",
            payload={"sensitive": sensitive, "insensitive_cases": list(insensitive), "cases": [c.case_id for c in results]},
        )
        ref = ledger.append_event(ev, evolution_id="sensitivity")
        return SensitivityVerdict(sensitive, tuple(results), insensitive, ref)


def canonical_hash(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()
