"""Effect consequence and replay-safety verification."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .effect_coherence import EffectPath
from .implementation_ir import BackendIR


@dataclass(frozen=True)
class EffectConsequence:
    effect_id: str
    persistence: str
    event: str = ""
    idempotency_key: str = ""
    uniqueness_constraint: str = ""
    retry_policy: str = ""
    concurrency_policy: str = ""
    recovery_policy: str = ""


@dataclass(frozen=True)
class ConsequenceFinding:
    code: str
    effect_id: str
    message: str


def verify_effect_consequences(
    effects: tuple[EffectPath, ...],
    consequences: tuple[EffectConsequence, ...],
    backend: BackendIR,
) -> tuple[ConsequenceFinding, ...]:
    """Validate declared consequence coverage without silently resolving ambiguity.

    This checks the completeness and uniqueness of the *declarations*. It does
    not prove that the backend enforces the declared policies at runtime.
    """
    del backend  # Backend realization is verified by separate implementation evidence.
    findings: list[ConsequenceFinding] = []

    effect_counts = Counter(effect.effect_id for effect in effects)
    consequence_counts = Counter(c.effect_id for c in consequences)
    effect_ids = set(effect_counts)
    consequence_ids = set(consequence_counts)

    for effect_id, count in sorted(effect_counts.items()):
        if not effect_id:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-009", effect_id, "effect has an empty identity"
            ))
        if count > 1:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-008", effect_id,
                "effect identity is duplicated; consequence binding is ambiguous"
            ))

    for effect_id, count in sorted(consequence_counts.items()):
        if count > 1:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-008", effect_id,
                "multiple consequence records share one effect identity"
            ))
        if effect_id not in effect_ids:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-010", effect_id,
                "consequence record does not bind to a declared effect"
            ))

    by_id = {
        c.effect_id: c for c in consequences
        if consequence_counts[c.effect_id] == 1
    }
    for effect in effects:
        if not effect.effect_id:
            continue
        if effect_counts[effect.effect_id] > 1:
            continue
        c = by_id.get(effect.effect_id)
        if c is None:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-001", effect.effect_id,
                "effect has no unique concrete consequence"
            ))
            continue
        if not c.persistence and not c.event:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-002", effect.effect_id,
                "effect has neither persistence nor event consequence"
            ))
        if not c.idempotency_key:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-003", effect.effect_id,
                "effect has no replay/idempotency key"
            ))
        if not c.uniqueness_constraint:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-004", effect.effect_id,
                "effect has no uniqueness constraint or equivalent deduplication authority"
            ))
        if not c.retry_policy:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-005", effect.effect_id,
                "effect has no retry policy"
            ))
        if not c.concurrency_policy:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-006", effect.effect_id,
                "effect has no concurrency policy"
            ))
        if not c.recovery_policy:
            findings.append(ConsequenceFinding(
                "EFFECT-CONS-007", effect.effect_id,
                "effect has no recovery policy"
            ))
    return tuple(findings)
