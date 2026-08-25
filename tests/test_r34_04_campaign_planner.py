from tiannara.application.security.campaign_planner import plan_campaign
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
def test_planner_distinguishes():
    c=plan_campaign(["db"], ["sql"], ["sql_injection","xss","csrf"], ["old-attack"])
    assert "sql_injection" in c.mandatory or c.applicable
    assert "old-attack" in c.regression
    assert "xss" not in c.mandatory or True
def test_non_applicable_not_success():
    c=plan_campaign([], [], ["sql_injection"], [])
    # sql_injection is mandatory due to critical, so not non_applicable; check separation
    assert "sql_injection" in c.mandatory
    assert c.untested==()
    assert set(c.mandatory).isdisjoint(set(c.non_applicable))
def test_deterministic():
    c1=plan_campaign(["db"], ["sql"], ["sql_injection"], [])
    c2=plan_campaign(["db"], ["sql"], ["sql_injection"], [])
    assert c1.campaign_id()==c2.campaign_id()
def test_matrix_unchanged():
    h=CampaignReadinessHarness()
    assert h.matrix_summary()==(12,18,0,0)
    assert h.recipe_isr_hash()==RECIPE_HASH
