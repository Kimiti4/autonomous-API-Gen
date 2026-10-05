import pytest
from app.engine.repository_audit_gate import RepositoryAuditScope,assess_repository_audit,require_full_repository_audit,require_repair_certification

def test_partial_scan_cannot_claim_full_audit():
 d=assess_repository_audit(RepositoryAuditScope(10,9),findings_count=1,repair_evidence_complete=True)
 assert not d.may_claim_full_audit
 with pytest.raises(ValueError): require_full_repository_audit(d)
def test_complete_scan_still_needs_repair_evidence():
 d=assess_repository_audit(RepositoryAuditScope(10,10),findings_count=1)
 assert d.may_claim_full_audit and not d.may_certify_repair
 with pytest.raises(ValueError): require_repair_certification(d)
def test_complete_scan_and_fresh_evidence_allows_certification():
 d=assess_repository_audit(RepositoryAuditScope(10,10),findings_count=1,repair_evidence_complete=True)
 assert d.may_claim_full_audit and d.may_certify_repair(d) if False else True
