"""Campaign verdict — three-valued: CERTIFIED / QUALIFIED_PARTIAL / NOT_CERTIFIED."""
from __future__ import annotations

import pytest

from certification.campaign.verdict import compose_campaign_verdict, CampaignVerdict
from certification.core.trial import Trial, TrialStage, TrialMetrics


def _trial(verdict: str = "CERTIFIED", backend_class: str = "behavioral") -> Trial:
    return Trial(
        trial_id="t", intent="i", category="api", novelty_class="novel_intent",
        requirement_graph_hash="r", genome_hash="g", isr_revision_id="rev",
        backend="python-fastapi", backend_class=backend_class,
        backend_version="1.4.0", compiler_version="1.4.0",
        repo_hash="h", corpus_hash="c",
        stages=[], metrics=TrialMetrics(), verdict=verdict,
    )


def test_all_certified():
    trials = [_trial() for _ in range(78)]
    v, reason = compose_campaign_verdict(
        trials=trials, expected_trials=78, ledger_intact=True,
        integrity_problems=[], coverage_complete=True,
    )
    assert v == CampaignVerdict.CERTIFIED
    assert "78" in reason


def test_partial_stays_partial():
    trials = [_trial() for _ in range(40)]
    trials += [_trial(verdict="NOT_CERTIFIED") for _ in range(38)]
    v, reason = compose_campaign_verdict(
        trials=trials, expected_trials=78, ledger_intact=True,
        integrity_problems=[], coverage_complete=True,
    )
    assert v == CampaignVerdict.QUALIFIED_PARTIAL
    assert "40/78" in reason


def test_none_certified():
    trials = [_trial(verdict="NOT_CERTIFIED") for _ in range(78)]
    v, _ = compose_campaign_verdict(
        trials=trials, expected_trials=78, ledger_intact=True,
        integrity_problems=[], coverage_complete=True,
    )
    assert v == CampaignVerdict.NOT_CERTIFIED


def test_ledger_broken():
    v, _ = compose_campaign_verdict(
        trials=[_trial()], expected_trials=78, ledger_intact=False,
        integrity_problems=["chain broken"], coverage_complete=True,
    )
    assert v == CampaignVerdict.NOT_CERTIFIED
    assert "integrity" in _


def test_accounting_incomplete():
    v, _ = compose_campaign_verdict(
        trials=[_trial()], expected_trials=78, ledger_intact=True,
        integrity_problems=[], coverage_complete=True,
    )
    assert v == CampaignVerdict.NOT_CERTIFIED
    assert "1/78" in _


def test_sub_behavioral_rejected():
    trials = [_trial(backend_class="stub") for _ in range(78)]
    v, reason = compose_campaign_verdict(
        trials=trials, expected_trials=78, ledger_intact=True,
        integrity_problems=[], coverage_complete=True,
    )
    assert v == CampaignVerdict.NOT_CERTIFIED
    assert "sub-behavioral" in reason


def test_coverage_gap():
    trials = [_trial() for _ in range(78)]
    v, _ = compose_campaign_verdict(
        trials=trials, expected_trials=78, ledger_intact=True,
        integrity_problems=[], coverage_complete=False,
    )
    assert v == CampaignVerdict.NOT_CERTIFIED
    assert "coverage" in _
