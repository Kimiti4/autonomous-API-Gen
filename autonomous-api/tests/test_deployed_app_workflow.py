import pytest
from app.engine.deployed_app_workflow import (
    DeploymentAccess, DeploymentBaseline, DeployedWorkIntent, plan_deployed_app_work
)

def baseline():
    return DeploymentBaseline("abc123","env-digest",("health:pass",),"release-previous")

def test_professional_bug_fix_requires_observation_and_baseline():
    p=plan_deployed_app_work(
        DeployedWorkIntent.BUG_FIX,target="production-app",
        access=DeploymentAccess(True,True,True,False),baseline=baseline())
    assert "repository-scan" in p.required_stages
    assert "verification" in p.required_stages
    assert "human-authorization-required-before-production-deployment" in p.required_stages

def test_production_write_requires_deployment_access():
    with pytest.raises(ValueError, match="production-write-requires-deployment-access"):
        plan_deployed_app_work(
            DeployedWorkIntent.ENHANCE,target="app",
            access=DeploymentAccess(True,True,False,True),baseline=baseline())

def test_missing_runtime_observation_fails_closed():
    with pytest.raises(ValueError, match="missing-runtime-observation-access"):
        plan_deployed_app_work(
            DeployedWorkIntent.MAINTAIN,target="app",
            access=DeploymentAccess(True,False),baseline=baseline())
