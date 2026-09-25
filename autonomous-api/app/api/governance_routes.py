"""Authenticated governance control-plane routes.

These routes expose the existing immutable command DTOs; they do not bypass
GovernanceSubsystem invariants. All mutation endpoints are protected by the
same fail-closed API-key boundary as the evolution control plane.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.governance.commands import (
    GrantCertification,
    RecordGateEvaluation,
    RegisterGate,
    RegisterPolicy,
    RequestGovernanceDecision,
    RevokeCertification,
    UpdateCouncil,
)
from app.middleware.security import require_auth
from app.governance.runtime import get_governance

router = APIRouter(prefix="/governance", tags=["governance"])


@router.post("/council")
async def update_council(
    command: UpdateCouncil, _auth=Depends(require_auth)
):
    return await get_governance().update_council(command)


@router.post("/gates")
async def register_gate(
    command: RegisterGate, _auth=Depends(require_auth)
):
    return await get_governance().register_gate(command)


@router.post("/policies")
async def register_policy(
    command: RegisterPolicy, _auth=Depends(require_auth)
):
    return await get_governance().register_policy(command)


@router.post("/gate-evaluations")
async def record_gate_evaluation(
    command: RecordGateEvaluation, _auth=Depends(require_auth)
):
    return await get_governance().record_gate_evaluation(command)


@router.post("/decisions")
async def request_decision(
    command: RequestGovernanceDecision, _auth=Depends(require_auth)
):
    return await get_governance().request_decision(command)


@router.post("/certifications")
async def grant_certification(
    command: GrantCertification, _auth=Depends(require_auth)
):
    return await get_governance().grant_certification(command)


@router.post("/certifications/revoke")
async def revoke_certification(
    command: RevokeCertification, _auth=Depends(require_auth)
):
    return await get_governance().revoke_certification(command)


@router.get("/candidate/{candidate_id}")
async def candidate_governance(
    candidate_id: str, _auth=Depends(require_auth)
):
    state = await get_governance().materialize_candidate(candidate_id)
    return {
        "candidateId": candidate_id,
        "currentState": state.current_state,
        "decisions": [d.model_dump(mode="json") for d in state.decisions],
        "gateOutcomes": [g.model_dump(mode="json") for g in state.gate_outcomes],
        "certifications": [
            c.model_dump(mode="json") for c in state.certifications
        ],
    }


@router.get("/generation/{generation}")
async def generation_governance(
    generation: int, _auth=Depends(require_auth)
):
    states = await get_governance().materialize_generation(generation)
    return {
        "generation": generation,
        "candidates": [
            {
                "candidateId": state.candidate_id,
                "currentState": state.current_state,
                "decisions": [
                    d.model_dump(mode="json") for d in state.decisions
                ],
                "gateOutcomes": [
                    g.model_dump(mode="json") for g in state.gate_outcomes
                ],
                "certifications": [
                    c.model_dump(mode="json") for c in state.certifications
                ],
            }
            for state in states
        ],
    }
