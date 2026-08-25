import pytest
from tiannara.application.security.security_policy_compiler import compile_policy, validate_obligation, SecurityObligation
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
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
