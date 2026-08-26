"""Campaign verdict composer — three-valued: CERTIFIED / QUALIFIED_PARTIAL / NOT_CERTIFIED.

Partial success stays partial.  Dishonesty is always NOT_CERTIFIED.
"""
from __future__ import annotations
from enum import Enum

from compiler.core.protocol import BEHAVIORAL_CLASSES


class CampaignVerdict(str, Enum):
    CERTIFIED = "CERTIFIED"
    QUALIFIED_PARTIAL = "QUALIFIED_PARTIAL"
    NOT_CERTIFIED = "NOT_CERTIFIED"


def compose_campaign_verdict(
    *,
    trials: list,
    expected_trials: int,
    ledger_intact: bool,
    integrity_problems: list[str],
    coverage_complete: bool,
) -> tuple[CampaignVerdict, str]:
    """Determine the campaign-level verdict from evidence.

    Returns (verdict, reason).
    """
    if not ledger_intact or integrity_problems:
        return CampaignVerdict.NOT_CERTIFIED, f"integrity failure: {integrity_problems}"

    if len(trials) != expected_trials:
        return CampaignVerdict.NOT_CERTIFIED, (
            f"accounting incomplete {len(trials)}/{expected_trials}"
        )

    if any(
        getattr(t, "backend_class", "") not in {c.value for c in BEHAVIORAL_CLASSES}
        for t in trials
    ):
        return CampaignVerdict.NOT_CERTIFIED, "sub-behavioral backend present"

    if not coverage_complete:
        return CampaignVerdict.NOT_CERTIFIED, "category×backend coverage gap"

    n = sum(1 for t in trials if t.verdict == "CERTIFIED")

    if n == expected_trials:
        return CampaignVerdict.CERTIFIED, f"all {n} trials certified"

    if n == 0:
        return CampaignVerdict.NOT_CERTIFIED, "no certified trials"

    return CampaignVerdict.QUALIFIED_PARTIAL, (
        f"{n}/{expected_trials} certified (partial stays partial)"
    )
