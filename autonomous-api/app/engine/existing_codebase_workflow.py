"""Governed existing-codebase maintenance workflow for Bucket 4.1.

This is a planning/admission contract. It never turns scanner findings into
requirements and never mutates a repository by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import blake2b

from .repository_audit_gate import RepositoryAuditDecision, RepositoryAuditScope, assess_repository_audit
from .scope_control import ScopeDecision, ScopeClass, ScopeControlEngine, WorkProposal
from .work_mode import WorkMode, WorkModeContract


class ExistingCodebaseStage(str, Enum):
    INTAKE = "intake"
    INVENTORY = "inventory"
    SCAN = "scan"
    DIAGNOSE = "diagnose"
    IMPACT = "impact"
    REPAIR = "repair"
    VERIFY = "verify"
    E2E = "e2e"
    CERTIFY = "certify"
    DOCUMENT = "document"
    DEPLOY = "deploy"
    STOP = "stop"


@dataclass(frozen=True)
class ExistingCodebaseRequest:
    project_id: str
    project_kind: str
    mode: WorkMode
    surface: str
    authoritative_obligation_ids: tuple[str, ...]
    known_obligation_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExistingCodebaseGate:
    audit: RepositoryAuditDecision
    scope: ScopeDecision
    required_stages: tuple[ExistingCodebaseStage, ...]
    digest: str

    @property
    def admissible(self) -> bool:
        return self.audit.may_claim_full_audit and self.scope.executable


def plan_existing_codebase_work(
    request: ExistingCodebaseRequest,
    *,
    audit_scope: RepositoryAuditScope,
    findings_count: int,
    repair_evidence_complete: bool = False,
    explicit_authorization: bool = False,
) -> ExistingCodebaseGate:
    if not request.project_id:
        raise ValueError("missing-project-id")
    mode = WorkModeContract.for_mode(request.mode)
    mode.validate_project_kind(request.project_kind)
    if not mode.allows_surface(request.surface):
        raise ValueError(f"surface-not-authorized-by-mode:{request.surface}")

    audit = assess_repository_audit(
        audit_scope,
        findings_count=findings_count,
        repair_evidence_complete=repair_evidence_complete,
    )

    proposal = WorkProposal(
        proposal_id=f"existing-codebase:{request.project_id}:{request.mode.value}:{request.surface}",
        description="bounded existing-codebase work",
        obligation_ids=tuple(request.authoritative_obligation_ids),
        dependency_ids=(),
        authority="authoritative" if request.authoritative_obligation_ids else "advisory",
        explicitly_authorized=explicit_authorization,
    )
    scope = ScopeControlEngine(
        project_id=request.project_id,
        authoritative_obligation_ids=frozenset(request.authoritative_obligation_ids),
        known_obligation_ids=frozenset(request.known_obligation_ids),
    ).decide(proposal)

    stages = (
        ExistingCodebaseStage.INTAKE,
        ExistingCodebaseStage.INVENTORY,
        ExistingCodebaseStage.SCAN,
        ExistingCodebaseStage.DIAGNOSE,
        ExistingCodebaseStage.IMPACT,
        ExistingCodebaseStage.REPAIR,
        ExistingCodebaseStage.VERIFY,
        ExistingCodebaseStage.E2E,
        ExistingCodebaseStage.CERTIFY,
        ExistingCodebaseStage.DOCUMENT,
        ExistingCodebaseStage.DEPLOY,
        ExistingCodebaseStage.STOP,
    )
    raw = "|".join((
        request.project_id, request.project_kind, request.mode.value, request.surface,
        audit.scope.expected_files.__str__(), audit.scope.scanned_files.__str__(),
        str(findings_count), scope.digest,
        "|".join(s.value for s in stages),
    ))
    return ExistingCodebaseGate(audit, scope, stages, blake2b(raw.encode(), digest_size=32).hexdigest())


def require_admissible_existing_codebase_work(gate: ExistingCodebaseGate) -> None:
    if not gate.audit.may_claim_full_audit:
        raise ValueError("existing-codebase-audit-incomplete")
    if not gate.scope.executable:
        raise ValueError(gate.scope.reasons[0] if gate.scope.reasons else "existing-codebase-scope-not-authorized")
