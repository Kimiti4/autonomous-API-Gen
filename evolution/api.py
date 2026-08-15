"""
Self-Evolution Engine API.
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from .engine import SelfEvolutionEngine
from .errors import (
    EvolutionError,
    InvalidStateError,
    MutationError,
    ProposalNotFoundError,
)
from .governance import StaticGovernanceClient
from .models import EvolutionProposalRequest


class ProposalSubmission(BaseModel):
    request: EvolutionProposalRequest
    actor_id: Optional[str] = None


class ApprovalRequest(BaseModel):
    approver_id: str
    decision: Literal["APPROVED", "REJECTED"]
    comments: str = ""


class PromotionRequest(BaseModel):
    environment: str = "staging"


class RollbackRequest(BaseModel):
    reason: str = ""


def create_app(engine: Optional[SelfEvolutionEngine] = None) -> FastAPI:
    app = FastAPI(
        title="Self-Evolution Engine",
        version="0.1.0",
        description=(
            "Phase 21 Self-Evolution Engine. "
            "Evolves ISR architectures under constitutional governance."
        ),
    )

    if engine is None:
        engine = SelfEvolutionEngine(
            governance_client=StaticGovernanceClient(
                decision="ALLOW",
                reason="Default local governance policy.",
            )
        )

    app.state.engine = engine

    @app.exception_handler(ProposalNotFoundError)
    async def proposal_not_found_handler(request, exc):
        return JSONResponse(status_code=404, content={"message": str(exc)})

    @app.exception_handler(InvalidStateError)
    async def invalid_state_handler(request, exc):
        return JSONResponse(status_code=409, content={"message": str(exc)})

    @app.exception_handler(MutationError)
    async def mutation_error_handler(request, exc):
        return JSONResponse(status_code=400, content={"message": str(exc)})

    @app.exception_handler(EvolutionError)
    async def evolution_error_handler(request, exc):
        return JSONResponse(status_code=400, content={"message": str(exc)})

    def _engine(request: Request) -> SelfEvolutionEngine:
        return request.app.state.engine

    @app.get("/health/live")
    def health_live():
        return {"status": "live"}

    @app.get("/health/ready")
    def health_ready():
        return {"status": "ready"}

    @app.post("/v1/evolution/proposals")
    def create_proposal(
        request: Request,
        payload: ProposalSubmission,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        actor = payload.actor_id or x_actor_id
        return _engine(request).propose(payload.request, actor)

    @app.post("/v1/evolution/proposals/{proposal_id}/mutate")
    def mutate_proposal(
        request: Request,
        proposal_id: str,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        return _engine(request).mutate(proposal_id, x_actor_id)

    @app.post("/v1/evolution/proposals/{proposal_id}/simulate")
    def simulate_proposal(
        request: Request,
        proposal_id: str,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        return _engine(request).simulate(proposal_id, x_actor_id)

    @app.post("/v1/evolution/proposals/{proposal_id}/verify")
    def verify_proposal(
        request: Request,
        proposal_id: str,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        return _engine(request).verify(proposal_id, x_actor_id)

    @app.post("/v1/evolution/proposals/{proposal_id}/fitness")
    def evaluate_fitness(
        request: Request,
        proposal_id: str,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        return _engine(request).evaluate_fitness(proposal_id, x_actor_id)

    @app.post("/v1/evolution/proposals/{proposal_id}/submit")
    def submit_for_approval(
        request: Request,
        proposal_id: str,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        return _engine(request).submit_for_approval(proposal_id, x_actor_id)

    @app.post("/v1/evolution/proposals/{proposal_id}/approve")
    def approve_proposal(
        request: Request,
        proposal_id: str,
        payload: ApprovalRequest,
    ):
        return _engine(request).approve(
            proposal_id,
            payload.approver_id,
            payload.decision,
            payload.comments,
        )

    @app.post("/v1/evolution/proposals/{proposal_id}/promote")
    def promote_proposal(
        request: Request,
        proposal_id: str,
        payload: PromotionRequest,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        return _engine(request).promote(
            proposal_id,
            payload.environment,
            x_actor_id,
        )

    @app.post("/v1/evolution/promotions/{promotion_id}/rollback")
    def rollback_promotion(
        request: Request,
        promotion_id: str,
        payload: RollbackRequest,
        x_actor_id: str = Header(default="anonymous", alias="X-Actor-Id"),
    ):
        return _engine(request).rollback(
            promotion_id,
            payload.reason,
            x_actor_id,
        )

    @app.get("/v1/evolution/proposals/{proposal_id}")
    def get_proposal(
        request: Request,
        proposal_id: str,
    ):
        return _engine(request)._get_proposal(proposal_id)

    @app.get("/v1/evolution/history")
    def get_history(
        request: Request,
        proposal_id: Optional[str] = None,
    ):
        return _engine(request).history.list_events(proposal_id)

    @app.get("/v1/evolution/metrics")
    def get_metrics(request: Request):
        return _engine(request).metrics()

    return app


app = create_app()
