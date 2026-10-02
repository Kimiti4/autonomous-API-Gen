import pytest

from app.core.contracts.governance import CouncilComposition, CouncilMember
from app.core.governance.commands import GrantCertification
from app.core.governance.invariants import (
    GovernanceInvariantError,
    check_g7_quorum_weight,
)
from app.governance.subsystem import GovernanceSubsystem


def test_g6_empty_certifier_configuration_fails_closed():
    with pytest.raises(ValueError, match="recognized_certifiers must not be empty"):
        GovernanceSubsystem(
            event_store=object(),
            reference_store=object(),
            recognized_certifiers=set(),
        )


@pytest.mark.asyncio
async def test_g6_unknown_certifier_is_denied():
    class Events:
        async def append(self, *_args):
            raise AssertionError("unknown certifier must not append")

    governance = GovernanceSubsystem(
        event_store=Events(),
        reference_store=object(),
        recognized_certifiers={"recognized"},
    )
    with pytest.raises(Exception, match="G-6 violated"):
        await governance.grant_certification(
            GrantCertification(
                candidateId="candidate",
                certificationId="cert",
                certifiedBy="unknown",
                criteria="test",
            )
        )


def test_g7_executive_weight_is_explicit_and_configurable():
    council = CouncilComposition(members=[
        CouncilMember(
            memberId="member-1", name="Member One", role="council", votingWeight=0.5
        )
    ])

    with pytest.raises(GovernanceInvariantError, match="G-7 violated"):
        check_g7_quorum_weight(["executive"], council, 0.7, executive_weight=0.6)

    check_g7_quorum_weight(["executive"], council, 0.6, executive_weight=0.6)
    check_g7_quorum_weight(["member-1", "executive"], council, 1.0, executive_weight=0.6)
