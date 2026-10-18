import pytest
from tiannara.application.security.security_policy_compiler import compile_policy, validate_obligation, SecurityObligation
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
def test_derives_from_isr_not_code():
    facts={"external_api": ["isr:api-1"], "user_input": ["isr:input-1"]}
    obs=compile_policy(facts)
    assert any(o.rule_id=="SEC-SQL-001" for o in obs)
    assert all(o.source_refs for o in obs)
    # No code inspection: same facts give same obligations
    assert compile_policy(facts)==compile_policy(facts)
def test_idempotent_deterministic():
    facts={"authentication_requirement": ["isr:auth-1"]}
    assert compile_policy(facts)[0].obligation_id==compile_policy(facts)[0].obligation_id
def test_rejects_without_provenance():
    with pytest.raises(ValueError):
        validate_obligation(SecurityObligation("id", (), "rule", "1.0", "fam", "ev"))
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
