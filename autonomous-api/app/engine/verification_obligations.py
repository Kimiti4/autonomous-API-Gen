"""Executable verification obligations derived from engineering IR."""
from __future__ import annotations
from dataclasses import dataclass
from .api_ir import ApiContractIR
from .implementation_ir import BackendIR, FrontendIR
from .effect_coherence import EffectPath
from .effect_consequences import EffectConsequence


@dataclass(frozen=True)
class VerificationObligation:
    obligation_id: str
    category: str
    target: str
    scenario: str
    expected: str
    severity: str = "required"


def derive_verification_obligations(
    frontend: FrontendIR,
    api: ApiContractIR,
    backend: BackendIR,
    effects: tuple[EffectPath, ...] = (),
    consequences: tuple[EffectConsequence, ...] = (),
) -> tuple[VerificationObligation, ...]:
    obligations: list[VerificationObligation] = []

    for op in api.operations:
        if op.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
            obligations.append(VerificationObligation(
                f"VERIFY-AUTH-{op.operation_id}", "authorization", op.operation_id,
                "invoke without required authorization",
                "request is rejected without executing the effect"))
            obligations.append(VerificationObligation(
                f"VERIFY-REPLAY-{op.operation_id}", "idempotency", op.operation_id,
                "repeat the same state-changing request",
                "at most one authoritative effect is committed"))
            obligations.append(VerificationObligation(
                f"VERIFY-CONCURRENCY-{op.operation_id}", "concurrency", op.operation_id,
                "submit equivalent state-changing requests concurrently",
                "effect invariants remain satisfied"))
            obligations.append(VerificationObligation(
                f"VERIFY-RECOVERY-{op.operation_id}", "recovery", op.operation_id,
                "interrupt execution at a recoverable failure boundary",
                "system resumes without duplicate or lost authoritative effect"))

        obligations.append(VerificationObligation(
            f"VERIFY-CONTRACT-{op.operation_id}", "contract", op.operation_id,
            "send valid and invalid contract inputs",
            "implementation behavior matches the API contract"))

    for flow in frontend.interaction_flows:
        obligations.append(VerificationObligation(
            f"VERIFY-UI-FLOW-{flow}", "frontend", flow,
            "exercise the interaction through loading, success, empty and failure states",
            "state transitions remain coherent and user-visible failure is handled"))

    for flow in frontend.data_flows:
        obligations.append(VerificationObligation(
            f"VERIFY-FLOW-{flow.flow_id}", "integration", flow.flow_id,
            "execute the frontend-to-service data flow",
            "request, response/error and resulting state remain contract-compatible"))

    for effect in effects:
        obligations.append(VerificationObligation(
            f"VERIFY-EFFECT-{effect.effect_id}", "effect", effect.effect_id,
            "trace the effect from authorization through consequence",
            "every committed effect has an authorized, attributable consequence"))

    for consequence in consequences:
        if consequence.event:
            obligations.append(VerificationObligation(
                f"VERIFY-EVENT-{consequence.effect_id}", "event", consequence.effect_id,
                "replay or redeliver the resulting event",
                "downstream processing remains idempotent or explicitly duplicate-safe"))

    return tuple(obligations)
