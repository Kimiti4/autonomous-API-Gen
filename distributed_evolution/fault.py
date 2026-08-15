"""
Fault tolerance and recovery engine.
"""

from __future__ import annotations

from typing import Dict

from .models import (
    DistributedJobISR,
    FaultRecoveryPlanISR,
    JobStatus,
)


class FaultToleranceEngine:
    """Manages recovery plans and job retries."""

    def __init__(self) -> None:
        self.plans: Dict[str, FaultRecoveryPlanISR] = {}

    def create_recovery_plan(
        self,
        campaign_id: str,
        max_job_attempts: int = 3,
    ) -> FaultRecoveryPlanISR:
        plan = FaultRecoveryPlanISR(
            campaign_id=campaign_id,
            max_job_attempts=max_job_attempts,
        )

        self.plans[campaign_id] = plan

        return plan

    def get_recovery_plan(self, campaign_id: str) -> FaultRecoveryPlanISR:
        plan = self.plans.get(campaign_id)

        if not plan:
            plan = self.create_recovery_plan(campaign_id)

        return plan

    def recover_job(
        self,
        job: DistributedJobISR,
        plan: FaultRecoveryPlanISR,
    ) -> bool:
        if job.attempt >= plan.max_job_attempts:
            job.status = JobStatus.FAILED
            return False

        job.attempt += 1
        job.status = JobStatus.PENDING
        job.node_id = None
        job.error = None

        return True
