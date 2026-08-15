from __future__ import annotations

import time
import uuid
from typing import Optional

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.verification.repair.repair_planner import RepairPlanner, RepairPlan
from constitutional_architecture.verification.repair.repair_validator import RepairValidator
from constitutional_architecture.verification.verification_context import ArtifactReference, VerificationContext
from constitutional_architecture.verification.verification_events import (
    VerificationEvent,
    VerificationEventBus,
    VerificationEventType,
)
from constitutional_architecture.verification.verification_metrics import VerificationMetrics
from constitutional_architecture.verification.verification_pipeline import PipelineConfig, VerificationPipeline
from constitutional_architecture.verification.verification_registry import VerificationRegistry
from constitutional_architecture.verification.verification_report import VerificationReport
from constitutional_architecture.verification.verification_result import (
    VerificationCheck,
    VerificationLevel,
)
from constitutional_architecture.verification.verifiers.architecture_verifier import ArchitectureVerifier
from constitutional_architecture.verification.verifiers.compliance_verifier import ComplianceVerifier
from constitutional_architecture.verification.verifiers.contract_verifier import ContractVerifier
from constitutional_architecture.verification.verifiers.dependency_verifier import DependencyVerifier
from constitutional_architecture.verification.verifiers.deployment_verifier import DeploymentVerifier
from constitutional_architecture.verification.verifiers.interface_verifier import InterfaceVerifier
from constitutional_architecture.verification.verifiers.observability_verifier import ObservabilityVerifier
from constitutional_architecture.verification.verifiers.performance_verifier import PerformanceVerifier
from constitutional_architecture.verification.verifiers.policy_verifier import PolicyVerifier
from constitutional_architecture.verification.verifiers.runtime_verifier import RuntimeVerifier
from constitutional_architecture.verification.verifiers.scalability_verifier import ScalabilityVerifier
from constitutional_architecture.verification.verifiers.security_verifier import SecurityVerifier
from constitutional_architecture.verification.verifiers.static_verifier import StaticVerifier
from constitutional_architecture.verification.verifiers.workflow_verifier import WorkflowVerifier


def build_default_registry() -> VerificationRegistry:
    registry = VerificationRegistry()
    registry.register(ArchitectureVerifier())
    registry.register(StaticVerifier())
    registry.register(DependencyVerifier())
    registry.register(InterfaceVerifier())
    registry.register(WorkflowVerifier())
    registry.register(ContractVerifier())
    registry.register(SecurityVerifier())
    registry.register(PolicyVerifier())
    registry.register(ComplianceVerifier())
    registry.register(PerformanceVerifier())
    registry.register(ScalabilityVerifier())
    registry.register(DeploymentVerifier())
    registry.register(ObservabilityVerifier())
    registry.register(RuntimeVerifier())
    return registry


class VerificationEngine:
    def __init__(
        self,
        registry: Optional[VerificationRegistry] = None,
        event_bus: Optional[VerificationEventBus] = None,
        pipeline_config: Optional[PipelineConfig] = None,
    ) -> None:
        self._registry = registry or build_default_registry()
        self._event_bus = event_bus or VerificationEventBus()
        self._pipeline = VerificationPipeline(
            registry=self._registry,
            event_bus=self._event_bus,
            config=pipeline_config,
        )
        self._repair_planner = RepairPlanner()
        self._repair_validator = RepairValidator()
        self._metrics = VerificationMetrics()

    def verify(
        self,
        isr: ISR,
        artifacts: Optional[list[ArtifactReference]] = None,
        max_level: VerificationLevel = VerificationLevel.L3_SECURITY,
        config: Optional[dict] = None,
    ) -> VerificationReport:
        start_time = time.perf_counter()
        report_id = f"vr-{uuid.uuid4().hex[:12]}"

        self._event_bus.publish(VerificationEvent(
            event_type=VerificationEventType.VERIFICATION_STARTED,
            data={"report_id": report_id, "isr_hash": isr.content_hash},
        ))

        ctx = VerificationContext(
            _isr=isr,
            _artifacts=tuple(artifacts or []),
            _config=config or {},
        )

        pipeline_config = PipelineConfig(max_level=max_level)
        self._pipeline = VerificationPipeline(
            registry=self._registry,
            event_bus=self._event_bus,
            config=pipeline_config,
        )

        results = self._pipeline.execute(ctx)

        all_checks: list[VerificationCheck] = []
        for result in results:
            all_checks.extend(result.checks)

        blocking_failures = tuple(
            c for c in all_checks if c.blocks_deployment
        )
        approved = len(blocking_failures) == 0

        failed_checks = [c for c in all_checks if not c.passed and c.status.value == "failed"]
        repair_plan = self._repair_planner.plan_repairs(failed_checks, isr.content_hash)
        recommendations = repair_plan.recommendations if repair_plan else ()

        fitness = self._compute_fitness_contribution(all_checks)

        levels_achieved = [r.level for r in results if r.all_checks_passed]
        highest_level = max(levels_achieved) if levels_achieved else VerificationLevel.L0_ARCHITECTURAL

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        report = VerificationReport(
            report_id=report_id,
            isr_hash=isr.content_hash,
            verifier_version="0.1.0",
            verification_level_achieved=highest_level,
            verifier_results=tuple(results),
            all_checks=tuple(all_checks),
            total_checks=len(all_checks),
            passed_checks=sum(1 for c in all_checks if c.passed),
            failed_checks=sum(1 for c in all_checks if not c.passed and c.status.value == "failed"),
            warning_checks=sum(1 for c in all_checks if c.status.value == "warning"),
            skipped_checks=sum(1 for c in all_checks if c.status.value == "skipped"),
            approved_for_deployment=approved,
            blocking_failures=blocking_failures,
            repair_recommendations=recommendations,
            fitness_contribution=fitness,
            total_duration_ms=elapsed_ms,
            verifier_durations={r.verifier_name: r.duration_ms for r in results},
        )

        self._metrics.record_verification(
            approved=approved,
            duration_ms=elapsed_ms,
            check_count=len(all_checks),
            level=highest_level.value,
            repairs=len(recommendations),
        )

        if approved:
            self._event_bus.publish(VerificationEvent(
                event_type=VerificationEventType.APPROVAL_GRANTED,
                data={"report_id": report_id},
            ))
        else:
            self._event_bus.publish(VerificationEvent(
                event_type=VerificationEventType.APPROVAL_DENIED,
                data={"report_id": report_id, "blockers": len(blocking_failures)},
            ))

        self._event_bus.publish(VerificationEvent(
            event_type=VerificationEventType.VERIFICATION_COMPLETED,
            data={"report_id": report_id, "approved": approved},
        ))

        return report

    def _compute_fitness_contribution(self, checks: list[VerificationCheck]) -> dict[str, float]:
        total = len(checks)
        if total == 0:
            return {}

        passed = sum(1 for c in checks if c.passed)
        pass_rate = passed / total

        security_checks = [c for c in checks if c.verifier == "security"]
        security_passed = sum(1 for c in security_checks if c.passed)
        security_rate = security_passed / len(security_checks) if security_checks else 0.5

        arch_checks = [c for c in checks if c.verifier == "architecture"]
        arch_passed = sum(1 for c in arch_checks if c.passed)
        arch_rate = arch_passed / len(arch_checks) if arch_checks else 0.5

        return {
            "verification_pass_rate": pass_rate,
            "security_verification": security_rate,
            "architecture_verification": arch_rate,
            "deployment_readiness": pass_rate * 0.8,
        }

    def get_repair_plan(self, report: VerificationReport) -> Optional[RepairPlan]:
        if report.approved_for_deployment:
            return None

        failed = [c for c in report.all_checks if not c.passed and c.status.value == "failed"]
        plan = self._repair_planner.plan_repairs(failed, report.isr_hash)

        if plan:
            is_valid, reason = self._repair_validator.validate(plan)
            if not is_valid:
                return None

        return plan

    def register_verifier(self, verifier) -> None:
        self._registry.register(verifier)

    def subscribe(self, event_type: VerificationEventType, handler) -> None:
        self._event_bus.subscribe(event_type, handler)

    @property
    def metrics(self) -> VerificationMetrics:
        return self._metrics

    @property
    def registered_verifiers(self) -> list[str]:
        return self._registry.all_names
