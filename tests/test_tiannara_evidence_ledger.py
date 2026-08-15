import json

from tiannara.domain.models.evidence import CertificationEvidence
from tiannara.infrastructure.ledger.jsonl_evidence_ledger import JsonlEvidenceLedger


def _ev(pid="p1"):
    return CertificationEvidence(
        project_id=pid, isr_hash="h", genome_id="g", backend_name="minimal",
        compilation_success=True,
    )


def test_append_mints_hash_chain_and_verifies(tmp_path):
    ledger = JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    a = ledger.append(_ev("p1"))
    b = ledger.append(_ev("p2"))
    assert a.previous_hash is None
    assert a.record_hash is not None
    assert b.previous_hash == a.record_hash
    assert ledger.verify_chain() is True
    assert len(ledger.all()) == 2


def test_tampering_record_content_breaks_chain(tmp_path):
    ledger = JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    ledger.append(_ev("p1"))
    ledger.append(_ev("p2"))
    path = tmp_path / "ev.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["isr_hash"] = "tampered"
    lines[0] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert ledger.verify_chain() is False


def test_tampering_hash_field_breaks_chain(tmp_path):
    ledger = JsonlEvidenceLedger(tmp_path / "ev.jsonl")
    ledger.append(_ev("p1"))
    path = tmp_path / "ev.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    rec = json.loads(lines[0])
    rec["record_hash"] = "deadbeef"
    lines[0] = json.dumps(rec)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert ledger.verify_chain() is False


def test_empty_ledger_verifies(tmp_path):
    assert JsonlEvidenceLedger(tmp_path / "none.jsonl").verify_chain() is True
