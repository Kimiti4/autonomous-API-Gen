"""
Safety Gate.

Constitutional hash verification and rollback support.
Ensures the Meta-Evolution Engine never crosses constitutional boundaries.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from constitutional_architecture.meta.platform_genome import PlatformGenome


CONSTITUTIONAL_HASH = hashlib.sha256(
    b"Constitutional Architecture Principles v1.0: "
    b"ISR is sole source of truth; "
    b"ISR is immutable; "
    b"Evolution operates exclusively on ISR; "
    b"Frameworks are compiler backends; "
    b"Verification gate is mandatory; "
    b"Deterministic compilation; "
    b"Source mapping required; "
    b"Rollback always available; "
    b"Agent isolation enforced; "
    b"Knowledge is append-only"
).hexdigest()


@dataclass(frozen=True)
class SafetyCheckResult:
    passed: bool
    checks_performed: int = 0
    checks_passed: int = 0
    violations: tuple[str, ...] = ()
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SafetyGate:
    def __init__(self) -> None:
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._rollback_stack: list[PlatformGenome] = []
        self._max_rollback_depth: int = 100

    def verify_constitutional_integrity(self) -> bool:
        return self._constitutional_hash == CONSTITUTIONAL_HASH

    def check_mutation_safety(self, current_genome: PlatformGenome, proposed_genome: PlatformGenome) -> SafetyCheckResult:
        violations: list[str] = []
        checks_performed = 0
        checks_passed = 0

        checks_performed += 1
        if self.verify_constitutional_integrity():
            checks_passed += 1
        else:
            violations.append("CONSTITUTIONAL INTEGRITY VIOLATED \u2014 HALT")

        checks_performed += 1
        locked_violations = self._check_locked_parameters(current_genome, proposed_genome)
        if not locked_violations:
            checks_passed += 1
        else:
            violations.extend(locked_violations)

        checks_performed += 1
        if proposed_genome.parent_hash == current_genome.content_hash:
            checks_passed += 1
        else:
            violations.append("Lineage broken: parent_hash does not match current genome")

        checks_performed += 1
        if proposed_genome.version == current_genome.version + 1:
            checks_passed += 1
        else:
            violations.append(f"Version not incremented: {current_genome.version} \u2192 {proposed_genome.version}")

        checks_performed += 1
        if current_genome.content_hash:
            checks_passed += 1
        else:
            violations.append("Rollback not possible: no current genome hash")

        return SafetyCheckResult(
            passed=len(violations) == 0,
            checks_performed=checks_performed,
            checks_passed=checks_passed,
            violations=tuple(violations),
        )

    def _check_locked_parameters(self, current: PlatformGenome, proposed: PlatformGenome) -> list[str]:
        violations: list[str] = []
        for param_id, current_param in current.parameters.items():
            if not current_param.locked:
                continue
            proposed_param = proposed.parameters.get(param_id)
            if proposed_param is None:
                violations.append(f"Locked parameter '{param_id}' was removed")
            elif proposed_param.value != current_param.value:
                violations.append(f"Locked parameter '{param_id}' was modified: {current_param.value} \u2192 {proposed_param.value}")
        return violations

    def push_rollback_point(self, genome: PlatformGenome) -> None:
        self._rollback_stack.append(genome)
        if len(self._rollback_stack) > self._max_rollback_depth:
            self._rollback_stack = self._rollback_stack[-self._max_rollback_depth:]

    def rollback(self) -> Optional[PlatformGenome]:
        if not self._rollback_stack:
            return None
        return self._rollback_stack.pop()

    @property
    def rollback_depth(self) -> int:
        return len(self._rollback_stack)

    @property
    def can_rollback(self) -> bool:
        return len(self._rollback_stack) > 0
