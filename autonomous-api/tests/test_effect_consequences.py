from app.engine.effect_coherence import EffectPath
from app.engine.effect_consequences import EffectConsequence, verify_effect_consequences
from app.engine.implementation_ir import BackendIR


def effect(effect_id="effect:transfer"):
    return EffectPath("transfer", "ui-transfer", "wallet", effect_id, "wallet-auth", "ledger")


def consequence(effect_id="effect:transfer"):
    return EffectConsequence(
        effect_id, "ledger", "transfer.created", "transfer-id",
        "unique transfer-id", "retry same key", "serialize account", "reconcile ledger"
    )


def test_incomplete_consequence_is_rejected():
    b = BackendIR("1", "backend:x", ("wallet",), "x")
    findings = verify_effect_consequences((effect(),), (EffectConsequence("effect:transfer", "ledger"),), b)
    codes = {finding.code for finding in findings}
    assert {"EFFECT-CONS-003", "EFFECT-CONS-004", "EFFECT-CONS-005", "EFFECT-CONS-006", "EFFECT-CONS-007"} <= codes


def test_replay_safe_effect_declaration_passes():
    b = BackendIR("1", "backend:x", ("wallet",), "x")
    assert not verify_effect_consequences((effect(),), (consequence(),), b)


def test_missing_effect_consequence_is_rejected():
    b = BackendIR("1", "backend:x", ("wallet",), "x")
    findings = verify_effect_consequences((effect(),), (), b)
    assert any(f.code == "EFFECT-CONS-001" for f in findings)


def test_duplicate_consequence_records_fail_closed_instead_of_last_write_wins():
    b = BackendIR("1", "backend:x", ("wallet",), "x")
    findings = verify_effect_consequences((effect(),), (consequence(), consequence()), b)
    assert any(f.code == "EFFECT-CONS-008" for f in findings)
    assert any("ambiguous" in f.message for f in findings)


def test_orphan_consequence_is_rejected():
    b = BackendIR("1", "backend:x", ("wallet",), "x")
    findings = verify_effect_consequences((), (consequence("effect:orphan"),), b)
    assert any(f.code == "EFFECT-CONS-010" for f in findings)


def test_duplicate_effect_identity_is_rejected():
    b = BackendIR("1", "backend:x", ("wallet",), "x")
    findings = verify_effect_consequences((effect(), effect()), (consequence(),), b)
    assert any(f.code == "EFFECT-CONS-008" for f in findings)


def test_empty_effect_identity_is_rejected():
    b = BackendIR("1", "backend:x", ("wallet",), "x")
    findings = verify_effect_consequences((effect(""),), (), b)
    assert any(f.code == "EFFECT-CONS-009" for f in findings)
