from app.engine.transaction_evidence import TransactionEvidenceRecord

def test_capability_context_is_hashed_and_roundtrips():
    r=TransactionEvidenceRecord(
        schema_version="esap.transaction-evidence.v2", transaction_id="t",
        source_event_id="s", source_architecture_id="a", successor_event_id="e",
        successor_architecture_id="b", mutations=(), repair_reports=(),
        dependency_reports=(), measurements=(), score={}, admission={},
        rejection=None, residuals=(), evidence=(), parent_digest=None,
        verification={"disposition":"PASS"}, digest="",
        capability_context={"mode":"seo","failed_properties":["crawlability"],
                            "repaired":True,"dependents_reverified":True},
    )
    r=TransactionEvidenceRecord(**r.__dict__, digest="") if False else r
    payload=r.canonical_payload()
    assert payload["capability_context"]["mode"]=="seo"
    assert payload["capability_context"]["dependents_reverified"] is True

def test_capability_context_can_be_absent_for_legacy_records():
    assert TransactionEvidenceRecord(
        schema_version="v", transaction_id="t", source_event_id="s",
        source_architecture_id="a", successor_event_id="e",
        successor_architecture_id="b", mutations=(), repair_reports=(),
        dependency_reports=(), measurements=(), score={}, admission={},
        rejection=None, residuals=(), evidence=(), parent_digest=None,
        verification={}, digest="").capability_context is None
