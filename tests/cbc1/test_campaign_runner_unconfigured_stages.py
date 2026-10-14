from certification.campaign.runner import _unconfigured_stage
from certification.core.trial import TrialStage, compose_verdict


def test_unconfigured_execution_stages_fail_closed():
    for stage in (
        TrialStage.BUILD,
        TrialStage.TEST,
        TrialStage.DEPLOY,
        TrialStage.RUNTIME,
        TrialStage.DESTROY,
    ):
        passed, detail = _unconfigured_stage(stage)
        assert passed is False
        assert "not_configured" in detail
        assert stage.value in detail


def test_unconfigured_stage_cannot_certify_trial():
    stages = {stage: True for stage in (
        TrialStage.STRUCTURAL,
        TrialStage.SEMANTIC,
        TrialStage.BUILD,
        TrialStage.TEST,
        TrialStage.DEPLOY,
        TrialStage.RUNTIME,
        TrialStage.DESTROY,
        TrialStage.VERIFY,
    )}
    stages[TrialStage.DEPLOY] = _unconfigured_stage(TrialStage.DEPLOY)[0]
    assert compose_verdict(stages, evidence_present=True) == "NOT_CERTIFIED"
