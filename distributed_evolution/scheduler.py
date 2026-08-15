"""
Deterministic scheduler for distributed evolution jobs.
"""

from __future__ import annotations

from typing import Optional

from .models import DistributedJobISR, JobStatus, utcnow
from .resources import ResourceManager


class Scheduler:
    """Schedules jobs onto attested compute nodes."""

    def __init__(self, resource_manager: ResourceManager) -> None:
        self.resource_manager = resource_manager

    def schedule_job(self, job: DistributedJobISR) -> Optional[str]:
        if job.status != JobStatus.PENDING:
            return None

        candidates = self.resource_manager.nodes_matching(job.requirements)

        if not candidates:
            return None

        candidates.sort(key=lambda node: (node.region, node.node_id))

        node = candidates[0]

        allocation = self.resource_manager.allocate(
            job_id=job.job_id,
            node_id=node.node_id,
            cpu=job.requirements.cpu,
            memory_mb=job.requirements.memory_mb,
        )

        job.status = JobStatus.SCHEDULED
        job.node_id = node.node_id
        job.scheduled_at = utcnow()

        return node.node_id
