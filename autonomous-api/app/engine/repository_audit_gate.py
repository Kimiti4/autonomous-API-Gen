"""Completeness gate for repository/codebase audits.

A finding from a partial scan is useful evidence, but it cannot support a
claim that the codebase was fully audited. Repairs require an explicit scan
scope and a complete-enough inventory.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class RepositoryAuditScope:
    expected_files: int
    scanned_files: int
    excluded_paths: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.expected_files >= 0 and self.scanned_files == self.expected_files


@dataclass(frozen=True)
class RepositoryAuditDecision:
    scope: RepositoryAuditScope
    findings_count: int
    may_claim_full_audit: bool
    may_certify_repair: bool
    reason: str | None


def assess_repository_audit(
    scope: RepositoryAuditScope,
    *,
    findings_count: int,
    repair_evidence_complete: bool = False,
) -> RepositoryAuditDecision:
    if not scope.complete:
        return RepositoryAuditDecision(
            scope, findings_count, False, False, "repository-scan-incomplete"
        )
    if not repair_evidence_complete:
        return RepositoryAuditDecision(
            scope, findings_count, True, False, "repair-requires-fresh-verification-evidence"
        )
    return RepositoryAuditDecision(scope, findings_count, True, True, None)


def require_full_repository_audit(decision: RepositoryAuditDecision) -> None:
    if not decision.may_claim_full_audit:
        raise ValueError("full-repository-audit-not-established")


def require_repair_certification(decision: RepositoryAuditDecision) -> None:
    if not decision.may_certify_repair:
        raise ValueError(decision.reason or "repair-certification-not-established")
