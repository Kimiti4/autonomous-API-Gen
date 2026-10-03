import pytest
from app.engine.migration_planner import *

def test_diff_detects_added_and_removed_architecture_artifacts():
    d=diff_artifacts(
        {"contracts":["old"],"services":["api"]},
        {"contracts":["new"],"services":["api","worker"]},
    )
    assert {x.action+":"+x.artifact_id for x in d}=={
        "add:new","remove:old","add:worker"
    }

def test_deploy_and_cutover_require_verification():
    p=MigrationPlan("e1","a","b",
        (ArchitectureChange("c","service","worker","add","x"),),
        (MigrationStep("s","c","deploy"),))
    assert "missing-verification:s" in validate_migration(p)

def test_unknown_dependencies_are_rejected():
    p=MigrationPlan("e1","a","b",(),(MigrationStep("s","c","build",("missing",)),))
    assert "step-references-unknown-change:s" in validate_migration(p)
    assert "unknown-step-dependency:s:missing" in validate_migration(p)

def test_steps_are_topologically_ordered():
    p=MigrationPlan("e1","a","b",(),(
        MigrationStep("cutover","c","cutover",("verify",),verification_obligations=("v",)),
        MigrationStep("verify","c","verify",("deploy",),verification_obligations=("v",)),
        MigrationStep("deploy","c","deploy",()),
    ))
    assert topological_steps(p)==("deploy","verify","cutover")

def test_cycles_are_rejected():
    p=MigrationPlan("e1","a","b",(),(
        MigrationStep("a","c","build",("b",)),
        MigrationStep("b","c","build",("a",)),
    ))
    with pytest.raises(ValueError, match="migration-dependency-cycle"):
        topological_steps(p)
