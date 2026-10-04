"""Atomic admission guard for repository repair candidate patches."""

from __future__ import annotations

from dataclasses import dataclass
from .candidate_patch import CandidatePatch, require_patch_matches_workspace
from .transaction_atomicity import AtomicTransactionResult
from .transaction_evidence import TransactionEvidenceRecord

@dataclass(frozen=True)
class RepairAdmission:
    candidate_id: str
    patch_digest: str
    admitted: bool
    reason: str

def validate_repair_patch_for_atomic_admission(
    patch: CandidatePatch,
    *,
    candidate_id: str,
    workspace_id: str,
    source_revision: str,
    base_digest: str,
    transaction_result: AtomicTransactionResult,
) -> RepairAdmission:
    require_patch_matches_workspace(
        patch,
        candidate_id=candidate_id,
        workspace_id=workspace_id,
        source_revision=source_revision,
        base_digest=base_digest,
    )
    if transaction_result.disposition.value != "committed" or transaction_result.value is None:
        return RepairAdmission(candidate_id,patch.patch_digest,False,"transaction-not-committed")
    audit=getattr(transaction_result.value,"audit_record",None)
    if not isinstance(audit,TransactionEvidenceRecord) or not audit.verify_digest():
        return RepairAdmission(candidate_id,patch.patch_digest,False,"missing-or-invalid-transaction-evidence")
    return RepairAdmission(candidate_id,patch.patch_digest,True,"atomic-transaction-and-patch-baseline-verified")
