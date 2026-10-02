"""Deterministic review gate for engineering deliberations."""
from __future__ import annotations
from dataclasses import dataclass
from .engineering_deliberation import EngineeringDeliberation, validate_deliberation


@dataclass(frozen=True)
class EngineeringReview:
    approved_for_architecture: bool
    findings: tuple[str, ...]


def review_deliberation(d: EngineeringDeliberation) -> EngineeringReview:
    findings = list(validate_deliberation(d))
    alternatives = {a.alternative_id for a in d.alternatives}
    challenged = {c.target for c in d.challenges}
    for aid in alternatives:
        if aid not in challenged:
            findings.append(f"unchallenged architecture alternative: {aid}")
    if d.selected_alternative:
        required = {t.alternative_id for t in d.tradeoffs if t.evidence_required}
        if d.selected_alternative not in alternatives:
            findings.append("selection references undeclared alternative")
        if not required:
            findings.append("selection has no evidence-bearing trade-off")
    if d.unresolved:
        findings.append("unresolved engineering questions remain")
    return EngineeringReview(not findings, tuple(findings))
