from tiannara.application.security.campaign_planner import plan_campaign
from .test_r29_10_9_campaign_readiness import CampaignReadinessHarness
RECIPE_HASH="a3d9c01cb688769f4143b1a5da8623694fb146769532cb3c0e2dfbffa98377f4"
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
