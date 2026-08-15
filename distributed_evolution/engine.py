"""
Distributed Evolution Cloud engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .artifacts import ArtifactRepository
from .fault import FaultToleranceEngine
from .models import (
    AuditEvent,
    CampaignStatus,
    CloudMetrics,
    ComputeNodeISR,
    DistributedJobISR,
    JobKind,
    JobStatus,
    ResourceRequirements,
    SimulationCampaignISR,
    canonical_json,
    new_id,
    sha256_hex,
    utcnow,
)
from .resources import ResourceManager
from .scheduler import Scheduler


class DistributedEvolutionError(Exception):
    """Base distributed evolution error."""


class PolicyViolationError(DistributedEvolutionError):
    """Raised when a node or job violates policy."""


class ArtifactIntegrityError(DistributedEvolutionError):
    """Raised when artifact integrity verification fails."""


class NodeUnavailableError(DistributedEvolutionError):
    """Raised when the assigned node is unavailable."""


class DistributedEvolutionCloudEngine:
    """Coordinates distributed evolution campaigns."""

    def __init__(
        self,
        cluster_policy_version: str = "constitution.v1",
    ) -> None:
        self.resource_manager = ResourceManager(
            cluster_policy_version=cluster_policy_version,
        )

        self.artifacts = ArtifactRepository()
        self.scheduler = Scheduler(self.resource_manager)
        self.fault = FaultToleranceEngine()

        self.campaigns: Dict[str, SimulationCampaignISR] = {}
        self.jobs: Dict[str, DistributedJobISR] = {}

        self.audit_events: List[AuditEvent] = []
        self.last_audit_hash = "genesis"

        self.autoscale_threshold = 3

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def register_node(
        self,
        node_id: str,
        region: str,
        capabilities: List[str],
        cpu_capacity: int,
        memory_mb_capacity: int,
        policy_version: str,
        public_key_ref: str,
    ) -> ComputeNodeISR:
        node = self.resource_manager.register_node(
            node_id=node_id,
            region=region,
            capabilities=capabilities,
            cpu_capacity=cpu_capacity,
            memory_mb_capacity=memory_mb_capacity,
            policy_version=policy_version,
            public_key_ref=public_key_ref,
        )

        self._append_audit(
            event_type="node_registered",
            node_id=node_id,
            payload={
                "region": region,
                "attested": node.attested,
                "policy_version": policy_version,
            },
        )

        return node

    def heartbeat(self, node_id: str) -> ComputeNodeISR:
        return self.resource_manager.heartbeat(node_id)

    # ------------------------------------------------------------------
    # Campaign submission
    # ------------------------------------------------------------------

    def submit_campaign(
        self,
        name: str,
        objective: str,
        candidate_count: int = 1,
        target_backends: Optional[List[str]] = None,
        policy_version: Optional[str] = None,
        requirements: Optional[ResourceRequirements] = None,
        max_job_attempts: int = 3,
    ) -> SimulationCampaignISR:
        target_backends = target_backends or []

        campaign_id = "campaign_" + sha256_hex(
            canonical_json(
                {
                    "name": name,
                    "objective": objective,
                }
            )
        )[:16]

        existing = self.campaigns.get(campaign_id)

        if existing:
            return existing

        resolved_policy_version = (
            policy_version
            or self.resource_manager.cluster_policy_version
        )

        campaign = SimulationCampaignISR(
            campaign_id=campaign_id,
            name=name,
            objective=objective,
            policy_version=resolved_policy_version,
            candidate_count=candidate_count,
            target_backends=target_backends,
        )

        self.campaigns[campaign_id] = campaign

        self.fault.create_recovery_plan(
            campaign_id=campaign_id,
            max_job_attempts=max_job_attempts,
        )

        job_requirements = requirements or ResourceRequirements()

        for candidate_index in range(candidate_count):
            self._create_job(
                campaign=campaign,
                kind=JobKind.SIMULATION,
                name=f"simulation_candidate_{candidate_index}",
                requirements=job_requirements,
            )

        for backend in target_backends:
            self._create_job(
                campaign=campaign,
                kind=JobKind.COMPILATION,
                name=f"compile_{backend}",
                requirements=job_requirements,
            )

        self._create_job(
            campaign=campaign,
            kind=JobKind.VERIFICATION,
            name="verification",
            requirements=job_requirements,
        )

        self._append_audit(
            event_type="campaign_submitted",
            campaign_id=campaign_id,
            payload={
                "name": name,
                "candidate_count": candidate_count,
                "target_backends": target_backends,
            },
        )

        return campaign

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def schedule_campaign(self, campaign_id: str) -> List[str]:
        campaign = self._get_campaign(campaign_id)

        if campaign.status in {
            CampaignStatus.COMPLETED,
            CampaignStatus.FAILED,
        }:
            return []

        scheduled_job_ids: List[str] = []

        for job in self._campaign_jobs(campaign_id):
            if job.status != JobStatus.PENDING:
                continue

            node_id = self.scheduler.schedule_job(job)

            if node_id:
                scheduled_job_ids.append(job.job_id)

                self._append_audit(
                    event_type="job_scheduled",
                    campaign_id=campaign_id,
                    job_id=job.job_id,
                    node_id=node_id,
                    payload={
                        "attempt": job.attempt,
                    },
                )

        if scheduled_job_ids and campaign.status == CampaignStatus.PENDING:
            campaign.status = CampaignStatus.RUNNING

        return scheduled_job_ids

    def execute_ready_jobs(self, campaign_id: str) -> bool:
        campaign = self._get_campaign(campaign_id)

        if campaign.status in {
            CampaignStatus.COMPLETED,
            CampaignStatus.FAILED,
        }:
            return False

        executed = False

        for job in self._campaign_jobs(campaign_id):
            if job.status != JobStatus.SCHEDULED:
                continue

            job.status = JobStatus.RUNNING
            job.started_at = utcnow()

            self._append_audit(
                event_type="job_started",
                campaign_id=campaign_id,
                job_id=job.job_id,
                node_id=job.node_id,
                payload={
                    "attempt": job.attempt,
                },
            )

            try:
                self._execute_job(job)
                self._append_audit(
                    event_type="job_completed",
                    campaign_id=campaign_id,
                    job_id=job.job_id,
                    node_id=job.node_id,
                    payload={
                        "result": job.result,
                    },
                )

            except (PolicyViolationError, ArtifactIntegrityError) as exc:
                self._handle_job_failure(job, str(exc), permanent=True)

            except NodeUnavailableError as exc:
                self._handle_job_failure(job, str(exc), permanent=False)

            except Exception as exc:
                self._handle_job_failure(job, str(exc), permanent=False)

            executed = True

        self._update_campaign_status(campaign_id)

        return executed

    def run_campaign(self, campaign_id: str) -> SimulationCampaignISR:
        progress = True

        while progress:
            progress = False

            scheduled = self.schedule_campaign(campaign_id)
            if scheduled:
                progress = True

            executed = self.execute_ready_jobs(campaign_id)
            if executed:
                progress = True

            pending_jobs = [
                job
                for job in self._campaign_jobs(campaign_id)
                if job.status == JobStatus.PENDING
            ]

            new_node = self.resource_manager.autoscale(
                pending_jobs_count=len(pending_jobs),
                threshold=self.autoscale_threshold,
            )

            if new_node:
                self._append_audit(
                    event_type="node_autoscaled",
                    node_id=new_node.node_id,
                    payload={
                        "region": new_node.region,
                        "pending_jobs": len(pending_jobs),
                    },
                )

                progress = True

        self._update_campaign_status(campaign_id)

        return self._get_campaign(campaign_id)

    # ------------------------------------------------------------------
    # Fault handling
    # ------------------------------------------------------------------

    def fail_node(self, node_id: str) -> List[str]:
        self.resource_manager.mark_failed(node_id)

        recovered_job_ids: List[str] = []

        for job in self.jobs.values():
            if job.node_id != node_id:
                continue

            if job.status not in {JobStatus.SCHEDULED, JobStatus.RUNNING}:
                continue

            self.resource_manager.release_allocations_for_job(job.job_id)

            plan = self.fault.get_recovery_plan(job.campaign_id)

            recovered = self.fault.recover_job(job, plan)

            if recovered:
                recovered_job_ids.append(job.job_id)

                self._append_audit(
                    event_type="job_recovered",
                    campaign_id=job.campaign_id,
                    job_id=job.job_id,
                    node_id=node_id,
                    payload={
                        "attempt": job.attempt,
                    },
                )
            else:
                self._append_audit(
                    event_type="job_failed",
                    campaign_id=job.campaign_id,
                    job_id=job.job_id,
                    node_id=node_id,
                    payload={
                        "reason": "node_failure_recovery_exhausted",
                    },
                )

            self._update_campaign_status(job.campaign_id)

        self._append_audit(
            event_type="node_failed",
            node_id=node_id,
            payload={
                "recovered_jobs": recovered_job_ids,
            },
        )

        return recovered_job_ids

    def recover_campaign(self, campaign_id: str) -> List[str]:
        recovered: List[str] = []

        for job in self._campaign_jobs(campaign_id):
            if job.status != JobStatus.PENDING:
                continue

            recovered.append(job.job_id)

        self._append_audit(
            event_type="campaign_recovery_requested",
            campaign_id=campaign_id,
            payload={
                "pending_jobs": recovered,
            },
        )

        return recovered

    # ------------------------------------------------------------------
    # Artifacts
    # ------------------------------------------------------------------

    def verify_artifact(self, content_hash: str) -> bool:
        return self.artifacts.verify_artifact(content_hash)

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def metrics(self) -> CloudMetrics:
        active_nodes = sum(
            1
            for node in self.resource_manager.nodes.values()
            if node.status.value == "ACTIVE"
        )

        failed_nodes = sum(
            1
            for node in self.resource_manager.nodes.values()
            if node.status.value == "FAILED"
        )

        pending_jobs = sum(
            1 for job in self.jobs.values() if job.status == JobStatus.PENDING
        )

        scheduled_jobs = sum(
            1 for job in self.jobs.values() if job.status == JobStatus.SCHEDULED
        )

        running_jobs = sum(
            1 for job in self.jobs.values() if job.status == JobStatus.RUNNING
        )

        completed_jobs = sum(
            1 for job in self.jobs.values() if job.status == JobStatus.COMPLETED
        )

        failed_jobs = sum(
            1 for job in self.jobs.values() if job.status == JobStatus.FAILED
        )

        recovered_jobs = sum(1 for job in self.jobs.values() if job.attempt > 0)

        return CloudMetrics(
            active_nodes=active_nodes,
            failed_nodes=failed_nodes,
            pending_jobs=pending_jobs,
            scheduled_jobs=scheduled_jobs,
            running_jobs=running_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            artifacts_count=len(self.artifacts.artifacts),
            recovered_jobs=recovered_jobs,
        )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def verify_audit_chain(self) -> bool:
        previous_hash = "genesis"

        for event in self.audit_events:
            if event.previous_hash != previous_hash:
                return False

            expected_payload = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "campaign_id": event.campaign_id,
                "job_id": event.job_id,
                "node_id": event.node_id,
                "payload": event.payload,
                "created_at": event.created_at,
                "previous_hash": event.previous_hash,
            }

            expected_hash = sha256_hex(canonical_json(expected_payload))

            if event.event_hash != expected_hash:
                return False

            previous_hash = event.event_hash

        return True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _create_job(
        self,
        campaign: SimulationCampaignISR,
        kind: JobKind,
        name: str,
        requirements: ResourceRequirements,
    ) -> DistributedJobISR:
        job_id = "job_" + sha256_hex(
            canonical_json(
                {
                    "campaign_id": campaign.campaign_id,
                    "kind": kind.value,
                    "name": name,
                }
            )
        )[:16]

        existing = self.jobs.get(job_id)

        if existing:
            return existing

        job = DistributedJobISR(
            job_id=job_id,
            campaign_id=campaign.campaign_id,
            kind=kind,
            name=name,
            requirements=requirements,
            policy_version=campaign.policy_version,
            idempotency_key=job_id,
        )

        self.jobs[job_id] = job

        self._append_audit(
            event_type="job_created",
            campaign_id=campaign.campaign_id,
            job_id=job_id,
            payload={
                "kind": kind.value,
                "name": name,
            },
        )

        return job

    def _execute_job(self, job: DistributedJobISR) -> None:
        node = self.resource_manager.nodes.get(job.node_id or "")

        if not node:
            raise NodeUnavailableError("Assigned node not found.")

        if node.status.value != "ACTIVE":
            raise NodeUnavailableError("Assigned node is not active.")

        if not node.attested:
            raise PolicyViolationError("Node is not attested.")

        if node.policy_version != job.policy_version:
            raise PolicyViolationError("Node policy version mismatch.")

        for input_hash in job.input_artifact_hashes:
            if not self.artifacts.verify_artifact(input_hash):
                raise ArtifactIntegrityError(
                    f"Input artifact missing or invalid: {input_hash}"
                )

        output_hash = sha256_hex(
            canonical_json(
                {
                    "campaign_id": job.campaign_id,
                    "job_id": job.job_id,
                    "kind": job.kind.value,
                    "name": job.name,
                }
            )
        )

        self.artifacts.put_artifact(
            content_hash=output_hash,
            size_bytes=128,
            produced_by_job=job.job_id,
            node_id=node.node_id,
            region=node.region,
            uri=f"artifact://{output_hash}",
        )

        job.status = JobStatus.COMPLETED
        job.completed_at = utcnow()
        job.result = {
            "artifact_hash": output_hash,
        }

        self.resource_manager.release_allocations_for_job(job.job_id)

    def _handle_job_failure(
        self,
        job: DistributedJobISR,
        error: str,
        permanent: bool,
    ) -> None:
        job.error = error

        self.resource_manager.release_allocations_for_job(job.job_id)

        plan = self.fault.get_recovery_plan(job.campaign_id)

        if permanent or job.attempt >= plan.max_job_attempts:
            job.status = JobStatus.FAILED

            self._append_audit(
                event_type="job_failed",
                campaign_id=job.campaign_id,
                job_id=job.job_id,
                node_id=job.node_id,
                payload={
                    "error": error,
                    "permanent": permanent,
                },
            )
        else:
            job.attempt += 1
            job.status = JobStatus.PENDING
            job.node_id = None

            self._append_audit(
                event_type="job_retry_scheduled",
                campaign_id=job.campaign_id,
                job_id=job.job_id,
                payload={
                    "error": error,
                    "attempt": job.attempt,
                },
            )

        self._update_campaign_status(job.campaign_id)

    def _campaign_jobs(self, campaign_id: str) -> List[DistributedJobISR]:
        return [
            job
            for job in self.jobs.values()
            if job.campaign_id == campaign_id
        ]

    def _update_campaign_status(self, campaign_id: str) -> None:
        campaign = self._get_campaign(campaign_id)

        jobs = self._campaign_jobs(campaign_id)

        if not jobs:
            campaign.status = CampaignStatus.PENDING
            return

        all_completed = all(job.status == JobStatus.COMPLETED for job in jobs)

        all_terminal = all(
            job.status
            in {
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            }
            for job in jobs
        )

        any_failed = any(job.status == JobStatus.FAILED for job in jobs)

        if all_completed:
            campaign.status = CampaignStatus.COMPLETED
        elif all_terminal and any_failed:
            campaign.status = CampaignStatus.FAILED
        else:
            campaign.status = CampaignStatus.RUNNING

    def _get_campaign(self, campaign_id: str) -> SimulationCampaignISR:
        campaign = self.campaigns.get(campaign_id)

        if not campaign:
            raise KeyError(f"Campaign not found: {campaign_id}")

        return campaign

    def _append_audit(
        self,
        event_type: str,
        campaign_id: Optional[str] = None,
        job_id: Optional[str] = None,
        node_id: Optional[str] = None,
        payload: Optional[Dict] = None,
    ) -> None:
        event_id = new_id("audit")

        created_at = utcnow().isoformat()

        event_payload = {
            "event_id": event_id,
            "event_type": event_type,
            "campaign_id": campaign_id,
            "job_id": job_id,
            "node_id": node_id,
            "payload": payload or {},
            "created_at": created_at,
            "previous_hash": self.last_audit_hash,
        }

        event_hash = sha256_hex(canonical_json(event_payload))

        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            campaign_id=campaign_id,
            job_id=job_id,
            node_id=node_id,
            payload=payload or {},
            created_at=created_at,
            previous_hash=self.last_audit_hash,
            event_hash=event_hash,
        )

        self.audit_events.append(event)

        self.last_audit_hash = event_hash
