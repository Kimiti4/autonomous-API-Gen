"""Distributed Evolution Cloud — canonical Phase 29 package.

This package implements policy-governed, ISR-audited distributed evolution
across a compute node federation.  It supersedes the retired
``evolution.cloud`` draft package.
"""

from .models import (
    AuditEvent,
    CampaignStatus,
    CloudMetrics,
    ComputeClusterISR,
    ComputeNodeISR,
    DistributedCompilationPlanISR,
    DistributedJobISR,
    FederationAgreementISR,
    FaultRecoveryPlanISR,
    JobKind,
    JobStatus,
    ResourceAllocationISR,
    ResourceRequirements,
    SimulationCampaignISR,
    canonical_json,
    new_id,
    sha256_hex,
    utcnow,
)
from .artifacts import ArtifactRepository, ArtifactRecord
from .resources import ResourceManager
from .scheduler import Scheduler
from .fault import FaultToleranceEngine
from .engine import DistributedEvolutionCloudEngine
from .api import enable_distributed_evolution

__all__ = [
    "AuditEvent",
    "CampaignStatus",
    "CloudMetrics",
    "ComputeClusterISR",
    "ComputeNodeISR",
    "DistributedCompilationPlanISR",
    "DistributedJobISR",
    "FederationAgreementISR",
    "FaultRecoveryPlanISR",
    "JobKind",
    "JobStatus",
    "ResourceAllocationISR",
    "ResourceRequirements",
    "SimulationCampaignISR",
    "canonical_json",
    "new_id",
    "sha256_hex",
    "utcnow",
    "ArtifactRepository",
    "ArtifactRecord",
    "ResourceManager",
    "Scheduler",
    "FaultToleranceEngine",
    "DistributedEvolutionCloudEngine",
    "enable_distributed_evolution",
]
