"""
Autonomous Software Engineering Network engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel

from .adapters import StageAdapter, StageContext, default_stage_adapters
from .models import (
    ContractStatus,
    CrossOrganizationContract,
    GlobalMonitoringSnapshot,
    MemoryRecord,
    NetworkAlert,
    NetworkEvent,
    OrganizationRegistration,
    OrganizationStatus,
    PipelineRun,
    PipelineStageName,
    PipelineStatus,
    StageRun,
    StageStatus,
    canonical_json,
    new_id,
    sha256_hex,
    utcnow,
)


PIPELINE_STAGE_ORDER: List[PipelineStageName] = [
    PipelineStageName.REQUIREMENT_ANALYSIS,
    PipelineStageName.ISR_CONSTRUCTION,
    PipelineStageName.EVOLUTION,
    PipelineStageName.VERIFICATION,
    PipelineStageName.COMPILATION,
    PipelineStageName.DEPLOYMENT,
    PipelineStageName.MONITORING,
    PipelineStageName.LEARNING,
]


HIGH_IMPACT_STAGES = {
    PipelineStageName.EVOLUTION,
    PipelineStageName.DEPLOYMENT,
    PipelineStageName.LEARNING,
}


class NetworkGovernanceDecision(BaseModel):
    """Decision returned by network governance."""

    decision: str
    reason: str = ""


class NetworkGovernanceGateway:
    """Abstract network governance gateway."""

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> NetworkGovernanceDecision:
        raise NotImplementedError


class StaticNetworkGovernanceGateway:
    """Static governance gateway for reference implementations and tests."""

    def __init__(
        self,
        decision: str = "ALLOW",
        reason: str = "Static governance decision.",
    ) -> None:
        self._decision = decision
        self._reason = reason

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> NetworkGovernanceDecision:
        return NetworkGovernanceDecision(
            decision=self._decision,
            reason=self._reason,
        )


class GlobalEngineeringMemory:
    """Global engineering memory store."""

    def __init__(self) -> None:
        self.records: List[MemoryRecord] = []

    def record(
        self,
        entity_type: str,
        entity_id: str,
        payload: Dict,
        evidence_refs: Optional[List[str]] = None,
    ) -> MemoryRecord:
        record = MemoryRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            evidence_refs=evidence_refs or [],
        )

        self.records.append(record)

        return record

    def query(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
    ) -> List[MemoryRecord]:
        results: List[MemoryRecord] = []

        for record in self.records:
            if entity_type and record.entity_type != entity_type:
                continue

            if entity_id and record.entity_id != entity_id:
                continue

            results.append(record)

        return results


class AutonomousSoftwareEngineeringNetwork:
    """Coordinates the autonomous software engineering network."""

    def __init__(
        self,
        governance: Optional[NetworkGovernanceGateway] = None,
        policy_version: str = "constitution.v1",
    ) -> None:
        self.policy_version = policy_version
        self.governance = governance or StaticNetworkGovernanceGateway()

        self.organizations: Dict[str, OrganizationRegistration] = {}
        self.contracts: Dict[str, CrossOrganizationContract] = {}
        self.pipeline_runs: Dict[str, PipelineRun] = {}

        self.memory = GlobalEngineeringMemory()

        self.stage_adapters: Dict[PipelineStageName, StageAdapter] = (
            default_stage_adapters()
        )

        self.events: List[NetworkEvent] = []
        self.last_event_hash = "genesis"

        self.alerts: List[NetworkAlert] = []

    # ------------------------------------------------------------------
    # Organization registration
    # ------------------------------------------------------------------

    def register_organization(
        self,
        org_id: str,
        name: str,
        capabilities: List[str],
        policy_version: str,
        public_key_ref: str,
    ) -> OrganizationRegistration:
        attested = policy_version == self.policy_version

        organization = OrganizationRegistration(
            org_id=org_id,
            name=name,
            capabilities=capabilities,
            policy_version=policy_version,
            public_key_ref=public_key_ref,
            status=OrganizationStatus.ACTIVE,
            attested=attested,
        )

        self.organizations[org_id] = organization

        self._append_event(
            event_type="organization_registered",
            org_id=org_id,
            payload={
                "name": name,
                "attested": attested,
                "policy_version": policy_version,
            },
        )

        if not attested:
            self._raise_alert(
                severity="HIGH",
                message=f"Organization {org_id} registered without attestation.",
            )

        return organization

    def suspend_organization(self, org_id: str) -> OrganizationRegistration:
        organization = self._get_organization(org_id)

        organization.status = OrganizationStatus.SUSPENDED

        self._append_event(
            event_type="organization_suspended",
            org_id=org_id,
            payload={},
        )

        return organization

    # ------------------------------------------------------------------
    # Contracts
    # ------------------------------------------------------------------

    def create_contract(
        self,
        parties: List[str],
        objective: str,
        obligations: Optional[List[str]] = None,
    ) -> CrossOrganizationContract:
        if len(parties) < 1:
            raise ValueError("Contract requires at least one party.")

        for party in parties:
            organization = self._get_organization(party)

            if organization.status != OrganizationStatus.ACTIVE:
                raise PermissionError(f"Organization {party} is not active.")

            if not organization.attested:
                raise PermissionError(f"Organization {party} is not attested.")

        contract_id = "contract_" + sha256_hex(
            canonical_json(
                {
                    "parties": sorted(parties),
                    "objective": objective,
                }
            )
        )[:16]

        existing = self.contracts.get(contract_id)

        if existing:
            return existing

        contract = CrossOrganizationContract(
            contract_id=contract_id,
            parties=parties,
            objective=objective,
            obligations=obligations or [],
            policy_version=self.policy_version,
        )

        self.contracts[contract_id] = contract

        self._append_event(
            event_type="contract_created",
            payload={
                "contract_id": contract_id,
                "parties": parties,
                "objective": objective,
            },
        )

        return contract

    def approve_contract(
        self,
        contract_id: str,
        approver_id: str,
    ) -> CrossOrganizationContract:
        contract = self._get_contract(contract_id)

        if contract.status != ContractStatus.DRAFT:
            raise ValueError("Contract is not in draft status.")

        decision = self.governance.evaluate_action(
            action="ACTIVATE_CONTRACT",
            context={
                "contract_id": contract_id,
                "parties": contract.parties,
                "objective": contract.objective,
                "approver_id": approver_id,
            },
        )

        if decision.decision != "ALLOW":
            contract.status = ContractStatus.REJECTED

            self._append_event(
                event_type="contract_rejected",
                payload={
                    "contract_id": contract_id,
                    "reason": decision.reason,
                },
            )

            self._raise_alert(
                severity="HIGH",
                message=f"Contract {contract_id} rejected by governance.",
            )

            raise PermissionError(
                f"Contract activation denied: {decision.reason}"
            )

        contract.status = ContractStatus.ACTIVE
        contract.approved_by = approver_id
        contract.activated_at = utcnow()

        self._append_event(
            event_type="contract_activated",
            payload={
                "contract_id": contract_id,
                "approved_by": approver_id,
            },
        )

        return contract

    # ------------------------------------------------------------------
    # Pipeline submission
    # ------------------------------------------------------------------

    def submit_objective(
        self,
        contract_id: str,
        objective: str,
        requirements: Optional[Dict] = None,
    ) -> PipelineRun:
        contract = self._get_contract(contract_id)

        if contract.status != ContractStatus.ACTIVE:
            raise PermissionError("Contract is not active.")

        for party in contract.parties:
            organization = self._get_organization(party)

            if organization.status != OrganizationStatus.ACTIVE:
                raise PermissionError(f"Organization {party} is not active.")

            if not organization.attested:
                raise PermissionError(f"Organization {party} is not attested.")

        run_id = "run_" + sha256_hex(
            canonical_json(
                {
                    "contract_id": contract_id,
                    "objective": objective,
                }
            )
        )[:16]

        existing = self.pipeline_runs.get(run_id)

        if existing:
            return existing

        stages = [
            StageRun(stage=stage)
            for stage in PIPELINE_STAGE_ORDER
        ]

        run = PipelineRun(
            run_id=run_id,
            contract_id=contract_id,
            objective=objective,
            requirements=requirements or {},
            stages=stages,
        )

        self.pipeline_runs[run_id] = run

        self._append_event(
            event_type="pipeline_submitted",
            run_id=run_id,
            payload={
                "contract_id": contract_id,
                "objective": objective,
            },
        )

        return run

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def run_pipeline(self, run_id: str) -> PipelineRun:
        run = self._get_run(run_id)

        if run.status in {
            PipelineStatus.COMPLETED,
            PipelineStatus.FAILED,
        }:
            return run

        contract = self._get_contract(run.contract_id)

        run.status = PipelineStatus.RUNNING
        run.updated_at = utcnow()

        for stage in PIPELINE_STAGE_ORDER:
            stage_run = self._execute_stage(run, contract, stage)

            if stage_run.status == StageStatus.FAILED:
                run.status = PipelineStatus.FAILED
                run.updated_at = utcnow()

                self._raise_alert(
                    severity="HIGH",
                    message=(
                        f"Pipeline {run_id} failed at stage {stage.value}."
                    ),
                )

                self._append_event(
                    event_type="pipeline_failed",
                    run_id=run_id,
                    payload={
                        "stage": stage.value,
                        "error": stage_run.error,
                    },
                )

                return run

        run.status = PipelineStatus.COMPLETED
        run.updated_at = utcnow()

        self._append_event(
            event_type="pipeline_completed",
            run_id=run_id,
            payload={},
        )

        return run

    # ------------------------------------------------------------------
    # Monitoring and audit
    # ------------------------------------------------------------------

    def monitoring_snapshot(self) -> GlobalMonitoringSnapshot:
        active_orgs = sum(
            1
            for organization in self.organizations.values()
            if organization.status == OrganizationStatus.ACTIVE
        )

        suspended_orgs = sum(
            1
            for organization in self.organizations.values()
            if organization.status == OrganizationStatus.SUSPENDED
        )

        active_contracts = sum(
            1
            for contract in self.contracts.values()
            if contract.status == ContractStatus.ACTIVE
        )

        pipeline_runs = len(self.pipeline_runs)

        completed_runs = sum(
            1
            for run in self.pipeline_runs.values()
            if run.status == PipelineStatus.COMPLETED
        )

        failed_runs = sum(
            1
            for run in self.pipeline_runs.values()
            if run.status == PipelineStatus.FAILED
        )

        return GlobalMonitoringSnapshot(
            active_orgs=active_orgs,
            suspended_orgs=suspended_orgs,
            active_contracts=active_contracts,
            pipeline_runs=pipeline_runs,
            completed_runs=completed_runs,
            failed_runs=failed_runs,
            alerts_count=len(self.alerts),
        )

    def verify_events(self) -> bool:
        previous_hash = "genesis"

        for event in self.events:
            if event.previous_hash != previous_hash:
                return False

            expected_payload = {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "org_id": event.org_id,
                "run_id": event.run_id,
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

    def _execute_stage(
        self,
        run: PipelineRun,
        contract: CrossOrganizationContract,
        stage: PipelineStageName,
    ) -> StageRun:
        stage_run = self._get_stage_run(run, stage)

        adapter = self.stage_adapters.get(stage)

        if not adapter:
            stage_run.status = StageStatus.FAILED
            stage_run.error = f"No adapter registered for stage {stage.value}."

            self._raise_alert(
                severity="HIGH",
                message=(
                    f"Missing stage adapter for {stage.value} in run {run.run_id}."
                ),
            )

            return stage_run

        try:
            self._authorize_stage(run, contract, stage)
        except PermissionError as exc:
            stage_run.status = StageStatus.FAILED
            stage_run.error = str(exc)

            self._raise_alert(
                severity="HIGH",
                message=(
                    f"Stage {stage.value} blocked by governance or security: {exc}"
                ),
            )

            return stage_run

        stage_run.status = StageStatus.RUNNING
        stage_run.started_at = utcnow()

        context = StageContext(
            objective=run.objective,
            requirements=run.requirements,
            artifacts=run.artifacts,
            contract=contract,
        )

        try:
            result = adapter.execute(context)

        except Exception as exc:
            stage_run.status = StageStatus.FAILED
            stage_run.error = str(exc)
            stage_run.completed_at = utcnow()

            return stage_run

        stage_run.status = result.status
        stage_run.completed_at = utcnow()
        stage_run.evidence_refs = result.evidence_refs
        stage_run.metrics = result.metrics
        stage_run.error = result.error

        if result.status == StageStatus.COMPLETED:
            run.artifacts[stage.value] = result.data

            for key, value in result.data.items():
                if isinstance(value, str):
                    self.memory.record(
                        entity_type="ARTIFACT",
                        entity_id=value,
                        payload={
                            "run_id": run.run_id,
                            "stage": stage.value,
                            "artifact_key": key,
                        },
                        evidence_refs=result.evidence_refs,
                    )

            self._append_event(
                event_type="stage_completed",
                run_id=run.run_id,
                payload={
                    "stage": stage.value,
                    "metrics": result.metrics,
                },
            )

        else:
            self._append_event(
                event_type="stage_failed",
                run_id=run.run_id,
                payload={
                    "stage": stage.value,
                    "error": result.error,
                },
            )

        return stage_run

    def _authorize_stage(
        self,
        run: PipelineRun,
        contract: CrossOrganizationContract,
        stage: PipelineStageName,
    ) -> None:
        if contract.status != ContractStatus.ACTIVE:
            raise PermissionError("Contract is not active.")

        for party in contract.parties:
            organization = self._get_organization(party)

            if organization.status != OrganizationStatus.ACTIVE:
                raise PermissionError(f"Organization {party} is not active.")

            if not organization.attested:
                raise PermissionError(f"Organization {party} is not attested.")

        if stage in HIGH_IMPACT_STAGES:
            decision = self.governance.evaluate_action(
                action=f"EXECUTE_STAGE_{stage.value}",
                context={
                    "run_id": run.run_id,
                    "contract_id": contract.contract_id,
                    "stage": stage.value,
                },
            )

            if decision.decision != "ALLOW":
                raise PermissionError(
                    f"Stage {stage.value} denied by governance: {decision.reason}"
                )

    def _get_organization(self, org_id: str) -> OrganizationRegistration:
        organization = self.organizations.get(org_id)

        if not organization:
            raise KeyError(f"Organization not found: {org_id}")

        return organization

    def _get_contract(self, contract_id: str) -> CrossOrganizationContract:
        contract = self.contracts.get(contract_id)

        if not contract:
            raise KeyError(f"Contract not found: {contract_id}")

        return contract

    def _get_run(self, run_id: str) -> PipelineRun:
        run = self.pipeline_runs.get(run_id)

        if not run:
            raise KeyError(f"Pipeline run not found: {run_id}")

        return run

    def _get_stage_run(
        self,
        run: PipelineRun,
        stage: PipelineStageName,
    ) -> StageRun:
        for stage_run in run.stages:
            if stage_run.stage == stage:
                return stage_run

        raise KeyError(f"Stage run not found: {stage.value}")

    def _raise_alert(self, severity: str, message: str) -> None:
        self.alerts.append(
            NetworkAlert(
                severity=severity,
                message=message,
            )
        )

    def _append_event(
        self,
        event_type: str,
        payload: Optional[Dict] = None,
        org_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> None:
        event_id = new_id("event")

        created_at = utcnow().isoformat()

        event_payload = {
            "event_id": event_id,
            "event_type": event_type,
            "org_id": org_id,
            "run_id": run_id,
            "payload": payload or {},
            "created_at": created_at,
            "previous_hash": self.last_event_hash,
        }

        event_hash = sha256_hex(canonical_json(event_payload))

        event = NetworkEvent(
            event_id=event_id,
            event_type=event_type,
            org_id=org_id,
            run_id=run_id,
            payload=payload or {},
            created_at=created_at,
            previous_hash=self.last_event_hash,
            event_hash=event_hash,
        )

        self.events.append(event)

        self.last_event_hash = event_hash
