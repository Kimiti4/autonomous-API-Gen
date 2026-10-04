import pytest
from app.engine.repair_report import build_repair_report

def test_report_is_self_verifying():
    r=build_repair_report(
        report_id="r",target="app",source_revision="abc",
        finding_ids=("f1",),root_causes=({"id":"h1"},),
        candidates_considered=({"id":"c1"},),selected_candidate_id="c1",
        patch_digest="p",verification=({"passed":True},),
        regressions=(),measurements=({"score":1},),residuals=(),
        deployment_ready=True)
    assert r.verify_digest()

def test_deployment_ready_requires_selected_repair():
    with pytest.raises(ValueError,match="deployment-ready-report-without-selected-repair"):
        build_repair_report(
            report_id="r",target="app",source_revision="abc",
            finding_ids=("f1",),root_causes=(),candidates_considered=(),
            selected_candidate_id=None,patch_digest=None,verification=(),
            regressions=(),measurements=(),residuals=(),deployment_ready=True)

def test_residuals_block_deployment_ready():
    with pytest.raises(ValueError,match="deployment-ready-report-has-residuals"):
        build_repair_report(
            report_id="r",target="app",source_revision="abc",
            finding_ids=("f1",),root_causes=(),candidates_considered=(),
            selected_candidate_id="c1",patch_digest="p",verification=(),
            regressions=(),measurements=(),residuals=("unknown",),deployment_ready=True)
