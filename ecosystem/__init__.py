"""
Autonomous Ecosystem and Cross-Marketplace Federation.

This package implements federation treaties, partner identity, trust scoring,
cross-marketplace routing, B2B contracts, and SLA monitoring behind a
governance gateway.
"""

from __future__ import annotations

from .contracts import ContractSLAEngine
from .engine import EcosystemEngine, EcosystemSyncEngine
from .federation import FederationEngine
from .gateway import (
    GovernanceDecision,
    GovernanceGateway,
    GovernanceKernelGateway,
    StaticGovernanceGateway,
    build_ecosystem_governance_kernel,
    ecosystem_allow_all_rules,
)
from .models import (
    B2BContract,
    ContractStatus,
    EcosystemReport,
    EcosystemSyncRecord,
    FederationTreaty,
    PartnerOrganization,
    PartnerStatus,
    PartnerType,
    PenaltyRecord,
    PenaltyStatus,
    RoutingDecision,
    RoutingRequest,
    SLAOperator,
    SLABreach,
    SLADefinition,
    TreatyStatus,
)
from .partners import PartnerEngine
from .routing import RoutingEngine

__version__ = "0.1.0"

__all__ = [
    "EcosystemEngine",
    "EcosystemSyncEngine",
    "FederationEngine",
    "PartnerEngine",
    "RoutingEngine",
    "ContractSLAEngine",
    "GovernanceGateway",
    "GovernanceDecision",
    "StaticGovernanceGateway",
    "GovernanceKernelGateway",
    "build_ecosystem_governance_kernel",
    "ecosystem_allow_all_rules",
    "FederationTreaty",
    "PartnerOrganization",
    "B2BContract",
    "SLADefinition",
    "SLABreach",
    "RoutingRequest",
    "RoutingDecision",
    "EcosystemSyncRecord",
    "EcosystemReport",
    "TreatyStatus",
    "PartnerStatus",
    "PartnerType",
    "ContractStatus",
    "SLAOperator",
    "PenaltyRecord",
    "PenaltyStatus",
]
