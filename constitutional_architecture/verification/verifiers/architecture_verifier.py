from __future__ import annotations

import time

from constitutional_architecture.verification.verification_context import VerificationContext
from constitutional_architecture.verification.verification_result import (
    CheckSeverity,
    CheckStatus,
    VerificationCheck,
    VerificationLevel,
    VerificationResult,
)
from constitutional_architecture.verification.verifiers.verifier_interface import Verifier


class ArchitectureVerifier(Verifier):
    @property
    def name(self) -> str:
        return "architecture"

    @property
    def description(self) -> str:
        return "Verify architectural invariants on the ISR"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L0_ARCHITECTURAL

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []
        isr = ctx.isr

        checks.append(self._check_module_count(isr))
        checks.append(self._check_cyclic_dependencies(isr))
        checks.append(self._check_entity_ownership(isr))
        checks.append(self._check_service_dependencies(isr))
        checks.append(self._check_interface_completeness(isr))
        checks.append(self._check_module_cohesion(isr))
        checks.append(self._check_orphaned_entities(isr))

        duration = (time.perf_counter() - start) * 1000
        success = all(c.passed or c.status == CheckStatus.WARNING for c in checks)

        return VerificationResult(
            verifier_name=self.name,
            level=self.level,
            checks=tuple(checks),
            duration_ms=duration,
            success=success,
        )

    def _check_module_count(self, isr) -> VerificationCheck:
        count = isr.system.module_count
        passed = count > 0
        return VerificationCheck(
            check_id="ARCH-001",
            name="module_count",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.BLOCKER if not passed else CheckSeverity.INFO,
            message=f"System has {count} module(s)",
            isr_node_id=isr.system.id,
            isr_node_type="system",
        )

    def _check_cyclic_dependencies(self, isr) -> VerificationCheck:
        modules = isr.system.modules
        module_ids = {m.id for m in modules}
        adjacency: dict[str, list[str]] = {m.id: [] for m in modules}
        for m in modules:
            for dep in m.dependencies:
                if dep in module_ids:
                    adjacency[m.id].append(dep)

        visited: set[str] = set()
        rec_stack: set[str] = set()
        has_cycle = False
        cycle_path: list[str] = []

        def dfs(node: str) -> bool:
            nonlocal has_cycle
            visited.add(node)
            rec_stack.add(node)
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    has_cycle = True
                    cycle_path.append(f"{node} → {neighbor}")
                    return True
            rec_stack.discard(node)
            return False

        for mid in module_ids:
            if mid not in visited:
                dfs(mid)

        passed = not has_cycle
        return VerificationCheck(
            check_id="ARCH-002",
            name="acyclic_dependencies",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.BLOCKER if not passed else CheckSeverity.INFO,
            message="No cyclic dependencies" if passed else f"Cycle detected: {'; '.join(cycle_path)}",
            suggested_repair="" if passed else "Break cycle via interface extraction or event-driven communication",
            repair_mutation_type="" if passed else "extract_interface",
            repair_confidence=0.0 if passed else 0.8,
        )

    def _check_entity_ownership(self, isr) -> VerificationCheck:
        all_entities: list[str] = []
        for m in isr.system.modules:
            for e in m.entities:
                all_entities.append(e.id)

        duplicates = [eid for eid in all_entities if all_entities.count(eid) > 1]
        passed = len(duplicates) == 0
        return VerificationCheck(
            check_id="ARCH-003",
            name="entity_ownership",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
            message="All entities uniquely owned" if passed else f"Duplicate entities: {set(duplicates)}",
        )

    def _check_service_dependencies(self, isr) -> VerificationCheck:
        all_service_ids: set[str] = set()
        for m in isr.system.modules:
            for s in m.services:
                all_service_ids.add(s.id)

        missing: list[str] = []
        for m in isr.system.modules:
            for s in m.services:
                for dep in s.dependencies:
                    if dep.target_service_id not in all_service_ids:
                        missing.append(f"{s.id} → {dep.target_service_id}")

        passed = len(missing) == 0
        return VerificationCheck(
            check_id="ARCH-004",
            name="service_dependency_resolution",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
            message="All service dependencies resolve" if passed else f"Unresolved: {missing[:5]}",
        )

    def _check_interface_completeness(self, isr) -> VerificationCheck:
        services_without_iface: list[str] = []
        for m in isr.system.modules:
            has_interface = len(m.interfaces) > 0
            if not has_interface and m.services:
                services_without_iface.append(m.name)

        passed = len(services_without_iface) == 0
        return VerificationCheck(
            check_id="ARCH-005",
            name="interface_completeness",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="All modules have interfaces" if passed else f"Modules without interfaces: {services_without_iface}",
        )

    def _check_module_cohesion(self, isr) -> VerificationCheck:
        low_cohesion: list[str] = []
        for m in isr.system.modules:
            if m.entities and not m.services:
                low_cohesion.append(f"{m.name} (entities only)")
            elif m.services and not m.entities:
                low_cohesion.append(f"{m.name} (services only)")

        passed = len(low_cohesion) == 0
        return VerificationCheck(
            check_id="ARCH-006",
            name="module_cohesion",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="All modules are cohesive" if passed else f"Low cohesion: {low_cohesion}",
        )

    def _check_orphaned_entities(self, isr) -> VerificationCheck:
        orphaned: list[str] = []
        for m in isr.system.modules:
            for e in m.entities:
                if not e.fields:
                    orphaned.append(e.name)

        passed = len(orphaned) == 0
        return VerificationCheck(
            check_id="ARCH-007",
            name="entity_completeness",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="All entities have fields" if passed else f"Entities without fields: {orphaned}",
        )
