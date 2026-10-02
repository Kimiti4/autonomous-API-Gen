from app.engine.effect_coherence import EffectPath
from app.engine.effect_consequences import EffectConsequence, verify_effect_consequences
from app.engine.implementation_ir import BackendIR

def effect():
    return EffectPath("transfer","ui-transfer","wallet","effect:transfer","wallet-auth","ledger")

def test_incomplete_consequence_is_rejected():
    b=BackendIR("1","backend:x",("wallet",),"x")
    f=verify_effect_consequences((effect(),),(EffectConsequence("effect:transfer","ledger"),),b)
    codes={x.code for x in f}
    assert "EFFECT-CONS-003" in codes
    assert "EFFECT-CONS-004" in codes
    assert "EFFECT-CONS-005" in codes
    assert "EFFECT-CONS-006" in codes
    assert "EFFECT-CONS-007" in codes

def test_replay_safe_effect_passes():
    b=BackendIR("1","backend:x",("wallet",),"x")
    c=EffectConsequence("effect:transfer","ledger","transfer.created","transfer-id","unique transfer-id","retry same key","serialize account","reconcile ledger")
    assert not verify_effect_consequences((effect(),),(c,),b)

def test_missing_effect_consequence_is_rejected():
    b=BackendIR("1","backend:x",("wallet",),"x")
    f=verify_effect_consequences((effect(),),(),b)
    assert any(x.code=="EFFECT-CONS-001" for x in f)
