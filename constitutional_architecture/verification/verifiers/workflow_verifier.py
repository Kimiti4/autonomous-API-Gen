from __future__ import annotations

import time

from constitutional_architecture.isr.model.workflow import StateType
from constitutional_architecture.verification.verification_context import VerificationContext
from constitutional_architecture.verification.verification_result import (
    CheckSeverity,
    CheckStatus,
    VerificationCheck,
    VerificationLevel,
    VerificationResult,
)
from constitutional_architecture.verification.verifiers.verifier_interface import Verifier


class WorkflowVerifier(Verifier):
    @property
    def name(self) -> str:
        return "workflow"

    @property
    def description(self) -> str:
        return "Verify workflow state machine correctness"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L2_BEHAVIOURAL

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []
        isr = ctx.isr

        for module in isr.system.modules:
            for workflow in module.workflows:
                checks.append(self._check_initial_state(workflow, module.name))
                checks.append(self._check_final_state(workflow, module.name))
                checks.append(self._check_reachability(workflow, module.name))
                checks.append(self._check_transition_integrity(workflow, module.name))

        if not checks:
            checks.append(VerificationCheck(
                check_id="WF-000",
                name="no_workflows",
                verifier=self.name,
                level=self.level,
                status=CheckStatus.SKIPPED,
                severity=CheckSeverity.INFO,
                message="No workflows defined in ISR",
            ))

        duration = (time.perf_counter() - start) * 1000
        success = all(c.passed or c.status in (CheckStatus.WARNING, CheckStatus.SKIPPED) for c in checks)

        return VerificationResult(
            verifier_name=self.name,
            level=self.level,
            checks=tuple(checks),
            duration_ms=duration,
            success=success,
        )

    def _check_initial_state(self, workflow, module_name: str) -> VerificationCheck:
        initial = [s for s in workflow.states if s.state_type == StateType.INITIAL]
        passed = len(initial) == 1
        return VerificationCheck(
            check_id=f"WF-001-{workflow.id}",
            name="initial_state",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
            message=f"Workflow '{workflow.name}' has {len(initial)} initial state(s)",
            isr_node_id=workflow.id,
            isr_node_type="workflow",
        )

    def _check_final_state(self, workflow, module_name: str) -> VerificationCheck:
        final = [s for s in workflow.states if s.state_type == StateType.FINAL]
        passed = len(final) >= 1
        return VerificationCheck(
            check_id=f"WF-002-{workflow.id}",
            name="final_state",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message=f"Workflow '{workflow.name}' has {len(final)} final state(s)",
            isr_node_id=workflow.id,
            isr_node_type="workflow",
        )

    def _check_reachability(self, workflow, module_name: str) -> VerificationCheck:
        if not workflow.states:
            return VerificationCheck(
                check_id=f"WF-003-{workflow.id}",
                name="reachability",
                verifier=self.name,
                level=self.level,
                status=CheckStatus.SKIPPED,
                severity=CheckSeverity.INFO,
                message="No states",
            )

        initial_ids = {s.id for s in workflow.states if s.state_type == StateType.INITIAL}
        reachable: set[str] = set(initial_ids)
        queue = list(initial_ids)

        while queue:
            current = queue.pop(0)
            for t in workflow.transitions:
                if t.from_state_id == current and t.to_state_id not in reachable:
                    reachable.add(t.to_state_id)
                    queue.append(t.to_state_id)

        all_ids = {s.id for s in workflow.states}
        unreachable = all_ids - reachable
        passed = len(unreachable) == 0

        return VerificationCheck(
            check_id=f"WF-003-{workflow.id}",
            name="state_reachability",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="All states reachable" if passed else f"Unreachable states: {unreachable}",
            isr_node_id=workflow.id,
            isr_node_type="workflow",
        )

    def _check_transition_integrity(self, workflow, module_name: str) -> VerificationCheck:
        state_ids = {s.id for s in workflow.states}
        invalid: list[str] = []
        for t in workflow.transitions:
            if t.from_state_id not in state_ids:
                invalid.append(f"{t.id}: from '{t.from_state_id}'")
            if t.to_state_id not in state_ids:
                invalid.append(f"{t.id}: to '{t.to_state_id}'")

        passed = len(invalid) == 0
        return VerificationCheck(
            check_id=f"WF-004-{workflow.id}",
            name="transition_integrity",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
            message="All transitions valid" if passed else f"Invalid transitions: {invalid[:5]}",
            isr_node_id=workflow.id,
            isr_node_type="workflow",
        )
