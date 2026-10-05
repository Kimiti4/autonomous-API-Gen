from app.engine.existing_codebase_audit import audit_existing_codebase


FILES = (
    ("app.py", "from service import run\ndef main():\n    run()\n"),
    ("service.py", "def run():\n    try:\n        work()\n    except Exception:\n        return None\n"),
)


def test_audit_produces_deterministic_evidence_bundle():
    a = audit_existing_codebase(FILES, expected_files=2, repair_evidence_complete=True)
    b = audit_existing_codebase(FILES, expected_files=2, repair_evidence_complete=True)
    assert a.digest == b.digest
    assert a.audit_decision.may_claim_full_audit
    assert len(a.analyses) == 1
    assert a.analyses[0].finding.rule == "broad-exception"
    assert a.analyses[0].impact.source_path == "service.py"
    assert a.analyses[0].candidates


def test_partial_inventory_cannot_claim_full_audit():
    audit = audit_existing_codebase(FILES, expected_files=3)
    assert not audit.audit_decision.may_claim_full_audit
    assert not audit.audit_decision.may_certify_repair


def test_advisory_structural_findings_do_not_create_repair_candidates():
    files = (("a.py", "x = 1\n" + ("#" * 121) + "\n"),)
    audit = audit_existing_codebase(files, expected_files=1)
    assert audit.structure_scan.findings[0].rule == "long-line"
    assert audit.analyses == ()


def test_missing_inventory_size_cannot_claim_full_audit():
    audit = audit_existing_codebase(FILES)
    assert not audit.audit_decision.may_claim_full_audit
