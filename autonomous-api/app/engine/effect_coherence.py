"""Domain/effect coherence across full-stack engineering IR.

This layer does not choose implementation technology. It checks that an
externally visible operation has an explicit domain/effect path and that
authorization, persistence/event consequences, and idempotency obligations
remain connected.
"""
from __future__ import annotations
from dataclasses import dataclass
from .api_ir import ApiContractIR
from .implementation_ir import BackendIR, FrontendIR


@dataclass(frozen=True)
class EffectPath:
    operation_id: str
    frontend_flow_id: str
    domain_module: str
    effect_id: str
    authorization_boundary: str
    consequence: str


@dataclass(frozen=True)
class EffectCoherenceFinding:
    code: str
    operation_id: str
    message: str


def verify_effect_coherence(
    frontend: FrontendIR,
    api: ApiContractIR,
    backend: BackendIR,
    effects: tuple[EffectPath, ...] = (),
) -> tuple[EffectCoherenceFinding, ...]:
    findings: list[EffectCoherenceFinding] = []
    by_operation = {e.operation_id: e for e in effects}

    for op in api.operations:
        if op.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            effect = by_operation.get(op.operation_id)
            if effect is None:
                findings.append(EffectCoherenceFinding(
                    "FS-EFFECT-002", op.operation_id,
                    "state-changing API operation has no explicit domain effect path"
                ))
                continue

            if not effect.domain_module:
                findings.append(EffectCoherenceFinding(
                    "FS-EFFECT-003", op.operation_id,
                    "effect has no authoritative domain module"
                ))
            if not effect.effect_id:
                findings.append(EffectCoherenceFinding(
                    "FS-EFFECT-004", op.operation_id,
                    "effect has no stable effect identity"
                ))
            if not effect.authorization_boundary:
                findings.append(EffectCoherenceFinding(
                    "FS-EFFECT-005", op.operation_id,
                    "effect has no authorization boundary"
                ))
            if not effect.consequence:
                findings.append(EffectCoherenceFinding(
                    "FS-EFFECT-006", op.operation_id,
                    "effect has no declared persistence/event consequence"
                ))

            frontend_ids = {f.flow_id for f in frontend.data_flows}
            if effect.frontend_flow_id not in frontend_ids:
                findings.append(EffectCoherenceFinding(
                    "FS-EFFECT-007", op.operation_id,
                    f"effect references unknown frontend flow: {effect.frontend_flow_id}"
                ))

    return tuple(findings)
