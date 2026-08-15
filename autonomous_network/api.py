"""
API routes for the Autonomous Software Engineering Network.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from .engine import (
    AutonomousSoftwareEngineeringNetwork,
    StaticNetworkGovernanceGateway,
)


router = APIRouter(
    prefix="/v1/autonomous-network",
    tags=["autonomous-software-engineering-network"],
)


def enable_autonomous_network(
    app: FastAPI,
    governance: Optional[StaticNetworkGovernanceGateway] = None,
    policy_version: str = "constitution.v1",
) -> AutonomousSoftwareEngineeringNetwork:
    """Enable autonomous network endpoints."""

    network = AutonomousSoftwareEngineeringNetwork(
        governance=governance,
        policy_version=policy_version,
    )

    app.state.autonomous_network = network

    app.include_router(router)

    return network


def _network(request: Request) -> AutonomousSoftwareEngineeringNetwork:
    network = getattr(request.app.state, "autonomous_network", None)

    if not network:
        raise HTTPException(
            status_code=500,
            detail="Autonomous software engineering network is not configured.",
        )

    return network


class RegisterOrganizationRequest(BaseModel):
    org_id: str
    name: str
    capabilities: List[str] = Field(default_factory=list)
    policy_version: str
    public_key_ref: str


class CreateContractRequest(BaseModel):
    parties: List[str]
    objective: str
    obligations: List[str] = Field(default_factory=list)


class ApproveContractRequest(BaseModel):
    approver_id: str


class SubmitObjectiveRequest(BaseModel):
    contract_id: str
    objective: str
    requirements: Dict = Field(default_factory=dict)


@router.post("/organizations", status_code=201)
def register_organization(payload: RegisterOrganizationRequest, request: Request):
    network = _network(request)

    return network.register_organization(
        org_id=payload.org_id,
        name=payload.name,
        capabilities=payload.capabilities,
        policy_version=payload.policy_version,
        public_key_ref=payload.public_key_ref,
    )


@router.post("/contracts", status_code=201)
def create_contract(payload: CreateContractRequest, request: Request):
    network = _network(request)

    try:
        return network.create_contract(
            parties=payload.parties,
            objective=payload.objective,
            obligations=payload.obligations,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/contracts/{contract_id}/approve")
def approve_contract(
    contract_id: str,
    payload: ApproveContractRequest,
    request: Request,
):
    network = _network(request)

    try:
        return network.approve_contract(
            contract_id=contract_id,
            approver_id=payload.approver_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/objectives", status_code=201)
def submit_objective(payload: SubmitObjectiveRequest, request: Request):
    network = _network(request)

    try:
        return network.submit_objective(
            contract_id=payload.contract_id,
            objective=payload.objective,
            requirements=payload.requirements,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/runs/{run_id}/run")
def run_pipeline(run_id: str, request: Request):
    network = _network(request)

    try:
        return network.run_pipeline(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request):
    network = _network(request)

    try:
        return network._get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/monitoring")
def monitoring(request: Request):
    network = _network(request)

    return network.monitoring_snapshot()


@router.get("/events")
def events(request: Request):
    network = _network(request)

    return network.events


@router.post("/events/verify")
def verify_events(request: Request):
    network = _network(request)

    return {
        "valid": network.verify_events(),
    }


@router.get("/memory")
def query_memory(
    request: Request,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
):
    network = _network(request)

    return network.memory.query(
        entity_type=entity_type,
        entity_id=entity_id,
    )
