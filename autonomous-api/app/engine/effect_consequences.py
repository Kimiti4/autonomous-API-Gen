"""Effect consequence and replay-safety verification."""
from __future__ import annotations
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
    findings: list[ConsequenceFinding] = []
    by_id = {c.effect_id: c for c in consequences}
    for effect in effects:
        c = by_id.get(effect.effect_id)
        if c is None:
            findings.append(ConsequenceFinding("EFFECT-CONS-001", effect.effect_id, "effect has no concrete consequence"))
            continue
        if not c.persistence and not c.event:
            findings.append(ConsequenceFinding("EFFECT-CONS-002", effect.effect_id, "effect has neither persistence nor event consequence"))
        if not c.idempotency_key:
            findings.append(ConsequenceFinding("EFFECT-CONS-003", effect.effect_id, "effect has no replay/idempotency key"))
        if not c.uniqueness_constraint:
            findings.append(ConsequenceFinding("EFFECT-CONS-004", effect.effect_id, "effect has no uniqueness constraint or equivalent deduplication authority"))
        if not c.retry_policy:
            findings.append(ConsequenceFinding("EFFECT-CONS-005", effect.effect_id, "effect has no retry policy"))
        if not c.concurrency_policy:
            findings.append(ConsequenceFinding("EFFECT-CONS-006", effect.effect_id, "effect has no concurrency policy"))
        if not c.recovery_policy:
            findings.append(ConsequenceFinding("EFFECT-CONS-007", effect.effect_id, "effect has no recovery policy"))
    return tuple(findings)
