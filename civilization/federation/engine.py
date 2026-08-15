"""
Federation engine for cross-organization governance and coordination.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional, Protocol

from pydantic import BaseModel

from ..engine import CivilizationEngine
from ..utils import deterministic_id, utcnow
from .models import (
    CouncilDecision,
    CouncilDecisionStatus,
    CouncilVote,
    CrossOrganizationConflict,
    CrossOrganizationConflictStatus,
    DelegatedTaskRecord,
    Federation,
    FederationCharter,
    FederationDecisionPolicy,
    FederationInitiative,
    FederationMembership,
    FederationMembershipStatus,
    FederationStatus,
    InitiativeStatus,
    VotePosition,
)


class FederationError(Exception):
    """Base error for federation operations."""


class FederationGovernanceDecision(BaseModel):
    """Decision returned by federation governance."""

    decision: Literal["ALLOW", "DENY"]
    reason: str = ""


class FederationGovernanceGateway(Protocol):
    """Abstract governance gateway for federation actions."""

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> FederationGovernanceDecision:
        ...


class StaticFederationGovernanceGateway:
    """Static governance gateway for tests and local development."""

    def __init__(
        self,
        decision: str = "ALLOW",
        reason: str = "Static federation governance decision.",
    ) -> None:
        self._decision = decision
        self._reason = reason

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> FederationGovernanceDecision:
        return FederationGovernanceDecision(
            decision=self._decision,
            reason=self._reason,
        )


class FederationEngine:
    """Coordinates federations, initiatives, councils, and conflicts."""

    def __init__(
        self,
        civilization_engine: CivilizationEngine,
        governance_gateway: Optional[FederationGovernanceGateway] = None,
    ) -> None:
        self.civilization = civilization_engine
        self.governance = governance_gateway or StaticFederationGovernanceGateway()

        self.federations: Dict[str, Federation] = {}
        self.memberships: Dict[str, Dict[str, FederationMembership]] = {}

        self.initiatives: Dict[str, FederationInitiative] = {}
        self.delegations_by_initiative: Dict[str, List[DelegatedTaskRecord]] = {}

        self.conflicts: Dict[str, CrossOrganizationConflict] = {}

        self.decisions: Dict[str, CouncilDecision] = {}
        self.votes: Dict[str, Dict[str, CouncilVote]] = {}

        self.bus = civilization_engine.bus
        self.memory = civilization_engine.memory

    # ------------------------------------------------------------------
    # Federation lifecycle
    # ------------------------------------------------------------------

    def create_federation(
        self,
        name: str,
        charter: FederationCharter,
    ) -> Federation:
        created_at = utcnow().isoformat()

        federation_id = deterministic_id(
            "federation",
            {
                "name": name,
                "mission": charter.mission,
                "created_at": created_at,
            },
        )

        federation = Federation(
            id=federation_id,
            name=name,
            charter=charter,
            status=FederationStatus.ACTIVE,
            created_at=created_at,
            updated_at=created_at,
        )

        self.federations[federation_id] = federation
        self.memberships[federation_id] = {}

        self.memory.add(
            organization_id=federation_id,
            record_type="FEDERATION_CREATED",
            subject_id=federation_id,
            content={
                "name": name,
                "mission": charter.mission,
            },
        )

        self.bus.publish(
            topic="FEDERATION_CREATED",
            organization_id=federation_id,
            payload={
                "name": name,
                "mission": charter.mission,
            },
        )

        return federation

    def join_federation(
        self,
        federation_id: str,
        organization_id: str,
        weight: float = 1.0,
        jurisdictions: Optional[List[str]] = None,
    ) -> FederationMembership:
        federation = self._get_federation(federation_id)

        if federation.status != FederationStatus.ACTIVE:
            raise FederationError("Federation is not active.")

        if organization_id not in self.civilization.organizations:
            raise FederationError(
                f"Organization not found: {organization_id}"
            )

        members = self.memberships.setdefault(federation_id, {})

        existing = members.get(organization_id)

        if existing and existing.status == FederationMembershipStatus.ACTIVE:
            raise FederationError(
                "Organization is already an active member of this federation."
            )

        membership = FederationMembership(
            federation_id=federation_id,
            organization_id=organization_id,
            status=FederationMembershipStatus.ACTIVE,
            weight=weight,
            jurisdictions=jurisdictions or [],
            joined_at=utcnow().isoformat(),
        )

        members[organization_id] = membership

        self.memory.add(
            organization_id=federation_id,
            record_type="FEDERATION_MEMBER_JOINED",
            subject_id=organization_id,
            content={
                "weight": weight,
                "jurisdictions": jurisdictions or [],
            },
        )

        self.bus.publish(
            topic="FEDERATION_MEMBER_JOINED",
            organization_id=federation_id,
            payload={
                "member_organization_id": organization_id,
                "weight": weight,
            },
        )

        return membership

    def suspend_membership(
        self,
        federation_id: str,
        organization_id: str,
        reason: str = "",
    ) -> FederationMembership:
        membership = self._get_membership(federation_id, organization_id)

        membership.status = FederationMembershipStatus.SUSPENDED

        self.bus.publish(
            topic="FEDERATION_MEMBER_SUSPENDED",
            organization_id=federation_id,
            payload={
                "member_organization_id": organization_id,
                "reason": reason,
            },
        )

        return membership

    def remove_membership(
        self,
        federation_id: str,
        organization_id: str,
        reason: str = "",
    ) -> FederationMembership:
        membership = self._get_membership(federation_id, organization_id)

        membership.status = FederationMembershipStatus.REMOVED

        self.bus.publish(
            topic="FEDERATION_MEMBER_REMOVED",
            organization_id=federation_id,
            payload={
                "member_organization_id": organization_id,
                "reason": reason,
            },
        )

        return membership

    # ------------------------------------------------------------------
    # Initiatives
    # ------------------------------------------------------------------

    def create_initiative(
        self,
        federation_id: str,
        title: str,
        objective: str,
        initiative_type: str,
        required_roles: Optional[List[str]] = None,
        member_organization_ids: Optional[List[str]] = None,
        inputs: Optional[Dict] = None,
        high_impact: bool = False,
        proposal_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> FederationInitiative:
        federation = self._get_federation(federation_id)

        if federation.status != FederationStatus.ACTIVE:
            raise FederationError("Federation is not active.")

        active_members = self._active_memberships(federation_id)

        active_member_ids = {
            membership.organization_id
            for membership in active_members
        }

        if not member_organization_ids:
            member_organization_ids = sorted(active_member_ids)

        if not member_organization_ids:
            raise FederationError(
                "Federation has no active member organizations."
            )

        for organization_id in member_organization_ids:
            if organization_id not in active_member_ids:
                raise FederationError(
                    f"Organization is not an active member: {organization_id}"
                )

        created_at = utcnow().isoformat()

        initiative_id = deterministic_id(
            "federation_initiative",
            {
                "federation_id": federation_id,
                "title": title,
                "objective": objective,
                "initiative_type": initiative_type,
                "created_at": created_at,
            },
        )

        initiative = FederationInitiative(
            id=initiative_id,
            federation_id=federation_id,
            title=title,
            objective=objective,
            initiative_type=initiative_type,
            required_roles=required_roles or [],
            member_organization_ids=member_organization_ids,
            inputs=inputs or {},
            high_impact=high_impact,
            status=InitiativeStatus.OPEN,
            proposal_id=proposal_id,
            campaign_id=campaign_id,
            created_at=created_at,
            updated_at=created_at,
        )

        self.initiatives[initiative_id] = initiative

        self.bus.publish(
            topic="FEDERATION_INITIATIVE_CREATED",
            organization_id=federation_id,
            payload={
                "initiative_id": initiative_id,
                "title": title,
                "high_impact": high_impact,
            },
        )

        return initiative

    def authorize_initiative(
        self,
        initiative_id: str,
        actor_id: str = "federation_engine",
    ) -> FederationInitiative:
        initiative = self._get_initiative(initiative_id)

        if initiative.status != InitiativeStatus.OPEN:
            raise FederationError(
                "Only OPEN initiatives can be authorized."
            )

        federation = self._get_federation(initiative.federation_id)

        requires_governance = (
            initiative.high_impact
            and federation.charter.high_impact_requires_governance
        )

        if not requires_governance:
            initiative.status = InitiativeStatus.COORDINATING
            initiative.updated_at = utcnow().isoformat()

            self.bus.publish(
                topic="FEDERATION_INITIATIVE_AUTHORIZED",
                organization_id=federation.id,
                payload={
                    "initiative_id": initiative.id,
                    "actor_id": actor_id,
                },
            )

            return initiative

        governance_decision = self.governance.evaluate_action(
            action="AUTHORIZE_FEDERATION_INITIATIVE",
            context={
                "federation_id": federation.id,
                "initiative_id": initiative.id,
                "high_impact": initiative.high_impact,
                "actor_id": actor_id,
            },
        )

        if governance_decision.decision == "ALLOW":
            initiative.status = InitiativeStatus.COORDINATING

            self.bus.publish(
                topic="FEDERATION_INITIATIVE_AUTHORIZED",
                organization_id=federation.id,
                payload={
                    "initiative_id": initiative.id,
                    "actor_id": actor_id,
                },
            )
        else:
            initiative.status = InitiativeStatus.FAILED

            self.bus.publish(
                topic="FEDERATION_INITIATIVE_DENIED",
                organization_id=federation.id,
                payload={
                    "initiative_id": initiative.id,
                    "reason": governance_decision.reason,
                },
            )

        initiative.updated_at = utcnow().isoformat()

        return initiative

    def delegate_initiative_tasks(
        self,
        initiative_id: str,
        actor_id: str = "federation_engine",
    ) -> List[DelegatedTaskRecord]:
        initiative = self._get_initiative(initiative_id)

        federation = self._get_federation(initiative.federation_id)

        if initiative.status == InitiativeStatus.OPEN:
            requires_governance = (
                initiative.high_impact
                and federation.charter.high_impact_requires_governance
            )

            if not requires_governance:
                initiative.status = InitiativeStatus.COORDINATING
                initiative.updated_at = utcnow().isoformat()

        if initiative.status != InitiativeStatus.COORDINATING:
            raise FederationError(
                "Initiative must be COORDINATING before delegation."
            )

        delegations: List[DelegatedTaskRecord] = []

        for organization_id in initiative.member_organization_ids:
            task = self.civilization.create_task(
                organization_id=organization_id,
                title=f"{initiative.title} — delegated work",
                objective=initiative.objective,
                task_type=initiative.initiative_type,
                required_roles=initiative.required_roles,
                inputs={
                    **initiative.inputs,
                    "federation_id": federation.id,
                    "initiative_id": initiative.id,
                },
                high_impact=initiative.high_impact,
                proposal_id=initiative.proposal_id,
                campaign_id=initiative.campaign_id,
            )

            created_at = utcnow().isoformat()

            delegation_id = deterministic_id(
                "delegated_task",
                {
                    "initiative_id": initiative.id,
                    "organization_id": organization_id,
                    "task_id": task.id,
                    "created_at": created_at,
                },
            )

            delegation = DelegatedTaskRecord(
                id=delegation_id,
                initiative_id=initiative.id,
                federation_id=federation.id,
                organization_id=organization_id,
                task_id=task.id,
                created_at=created_at,
            )

            delegations.append(delegation)

        self.delegations_by_initiative[initiative.id] = delegations

        initiative.status = InitiativeStatus.EXECUTING
        initiative.updated_at = utcnow().isoformat()

        self.bus.publish(
            topic="FEDERATION_INITIATIVE_DELEGATED",
            organization_id=federation.id,
            payload={
                "initiative_id": initiative.id,
                "delegation_count": len(delegations),
                "actor_id": actor_id,
            },
        )

        return delegations

    # ------------------------------------------------------------------
    # Conflicts
    # ------------------------------------------------------------------

    def create_conflict(
        self,
        federation_id: str,
        party_organization_ids: List[str],
        subject_ref: str,
        conflict_type: str,
        initiative_id: Optional[str] = None,
        recommendation_ids: Optional[List[str]] = None,
        high_impact: bool = False,
    ) -> CrossOrganizationConflict:
        federation = self._get_federation(federation_id)

        if federation.status != FederationStatus.ACTIVE:
            raise FederationError("Federation is not active.")

        if len(party_organization_ids) < 2:
            raise FederationError(
                "A cross-organization conflict requires at least two parties."
            )

        active_member_ids = {
            membership.organization_id
            for membership in self._active_memberships(federation_id)
        }

        for organization_id in party_organization_ids:
            if organization_id not in active_member_ids:
                raise FederationError(
                    f"Organization is not an active member: {organization_id}"
                )

        created_at = utcnow().isoformat()

        conflict_id = deterministic_id(
            "cross_organization_conflict",
            {
                "federation_id": federation_id,
                "subject_ref": subject_ref,
                "conflict_type": conflict_type,
                "party_organization_ids": sorted(party_organization_ids),
                "created_at": created_at,
            },
        )

        conflict = CrossOrganizationConflict(
            id=conflict_id,
            federation_id=federation_id,
            initiative_id=initiative_id,
            party_organization_ids=party_organization_ids,
            subject_ref=subject_ref,
            conflict_type=conflict_type,
            recommendation_ids=recommendation_ids or [],
            high_impact=high_impact,
            status=CrossOrganizationConflictStatus.OPEN,
            created_at=created_at,
            updated_at=created_at,
        )

        self.conflicts[conflict_id] = conflict

        self.bus.publish(
            topic="FEDERATION_CONFLICT_CREATED",
            organization_id=federation_id,
            payload={
                "conflict_id": conflict_id,
                "subject_ref": subject_ref,
                "conflict_type": conflict_type,
            },
        )

        return conflict

    def resolve_conflict(
        self,
        conflict_id: str,
        resolved_by: str,
        selected_recommendation_id: Optional[str] = None,
        rationale: str = "",
    ) -> CrossOrganizationConflict:
        conflict = self._get_conflict(conflict_id)

        if conflict.status != CrossOrganizationConflictStatus.OPEN:
            raise FederationError("Conflict is not open.")

        if conflict.high_impact:
            governance_decision = self.governance.evaluate_action(
                action="RESOLVE_CROSS_ORGANIZATION_CONFLICT",
                context={
                    "conflict_id": conflict.id,
                    "federation_id": conflict.federation_id,
                    "subject_ref": conflict.subject_ref,
                    "resolved_by": resolved_by,
                },
            )

            if governance_decision.decision != "ALLOW":
                conflict.status = CrossOrganizationConflictStatus.ESCALATED
                conflict.resolution_note = governance_decision.reason
                conflict.updated_at = utcnow().isoformat()

                self.bus.publish(
                    topic="FEDERATION_CONFLICT_ESCALATED",
                    organization_id=conflict.federation_id,
                    payload={
                        "conflict_id": conflict.id,
                        "reason": governance_decision.reason,
                    },
                )

                return conflict

        conflict.status = CrossOrganizationConflictStatus.RESOLVED
        conflict.selected_recommendation_id = selected_recommendation_id
        conflict.resolved_by = resolved_by
        conflict.resolution_note = rationale or "Conflict resolved."
        conflict.updated_at = utcnow().isoformat()

        self.bus.publish(
            topic="FEDERATION_CONFLICT_RESOLVED",
            organization_id=conflict.federation_id,
            payload={
                "conflict_id": conflict.id,
                "resolved_by": resolved_by,
            },
        )

        return conflict

    # ------------------------------------------------------------------
    # Council decisions
    # ------------------------------------------------------------------

    def propose_decision(
        self,
        federation_id: str,
        title: str,
        decision_type: str,
        initiative_id: Optional[str] = None,
        conflict_id: Optional[str] = None,
        rationale: Optional[str] = None,
    ) -> CouncilDecision:
        federation = self._get_federation(federation_id)

        if federation.status != FederationStatus.ACTIVE:
            raise FederationError("Federation is not active.")

        if initiative_id:
            self._get_initiative(initiative_id)

        if conflict_id:
            self._get_conflict(conflict_id)

        created_at = utcnow().isoformat()

        decision_id = deterministic_id(
            "council_decision",
            {
                "federation_id": federation_id,
                "title": title,
                "decision_type": decision_type,
                "initiative_id": initiative_id,
                "conflict_id": conflict_id,
                "created_at": created_at,
            },
        )

        decision = CouncilDecision(
            id=decision_id,
            federation_id=federation_id,
            title=title,
            decision_type=decision_type,
            initiative_id=initiative_id,
            conflict_id=conflict_id,
            status=CouncilDecisionStatus.PROPOSED,
            rationale=rationale,
            created_at=created_at,
            updated_at=created_at,
        )

        self.decisions[decision_id] = decision
        self.votes[decision_id] = {}

        self.bus.publish(
            topic="FEDERATION_DECISION_PROPOSED",
            organization_id=federation_id,
            payload={
                "decision_id": decision_id,
                "title": title,
                "decision_type": decision_type,
            },
        )

        return decision

    def cast_vote(
        self,
        decision_id: str,
        organization_id: str,
        position: VotePosition,
        reason: str = "",
    ) -> CouncilVote:
        decision = self._get_decision(decision_id)

        if decision.status not in {
            CouncilDecisionStatus.PROPOSED,
            CouncilDecisionStatus.VOTING,
        }:
            raise FederationError("Decision is not open for voting.")

        membership = self._get_membership(
            decision.federation_id,
            organization_id,
        )

        if membership.status != FederationMembershipStatus.ACTIVE:
            raise FederationError("Membership is not active.")

        created_at = utcnow().isoformat()

        vote_id = deterministic_id(
            "council_vote",
            {
                "decision_id": decision_id,
                "organization_id": organization_id,
                "position": position.value,
                "created_at": created_at,
            },
        )

        vote = CouncilVote(
            id=vote_id,
            decision_id=decision_id,
            organization_id=organization_id,
            position=position,
            weight=membership.weight,
            reason=reason,
            created_at=created_at,
        )

        self.votes.setdefault(decision_id, {})[organization_id] = vote

        decision.status = CouncilDecisionStatus.VOTING
        decision.updated_at = utcnow().isoformat()

        self.bus.publish(
            topic="FEDERATION_VOTE_CAST",
            organization_id=decision.federation_id,
            payload={
                "decision_id": decision_id,
                "member_organization_id": organization_id,
                "position": position.value,
            },
        )

        return vote

    def tally_decision(
        self,
        decision_id: str,
        actor_id: str = "federation_engine",
    ) -> CouncilDecision:
        decision = self._get_decision(decision_id)

        if decision.status not in {
            CouncilDecisionStatus.PROPOSED,
            CouncilDecisionStatus.VOTING,
        }:
            raise FederationError("Decision cannot be tallied.")

        federation = self._get_federation(decision.federation_id)

        active_memberships = self._active_memberships(decision.federation_id)

        total_weight = sum(
            membership.weight
            for membership in active_memberships
        )

        votes = list(self.votes.get(decision_id, {}).values())

        voted_weight = sum(vote.weight for vote in votes)

        if total_weight <= 0:
            decision.status = CouncilDecisionStatus.ESCALATED
            decision.result = "NO_ACTIVE_MEMBERS"
            decision.updated_at = utcnow().isoformat()

            return decision

        quorum_met = voted_weight >= (
            federation.charter.quorum_ratio * total_weight
        )

        if not quorum_met:
            decision.status = CouncilDecisionStatus.ESCALATED
            decision.result = "QUORUM_NOT_MET"
            decision.updated_at = utcnow().isoformat()

            self.bus.publish(
                topic="FEDERATION_DECISION_ESCALATED",
                organization_id=federation.id,
                payload={
                    "decision_id": decision.id,
                    "reason": "QUORUM_NOT_MET",
                },
            )

            return decision

        approve_weight = sum(
            vote.weight
            for vote in votes
            if vote.position == VotePosition.APPROVE
        )

        reject_weight = sum(
            vote.weight
            for vote in votes
            if vote.position == VotePosition.REJECT
        )

        veto_reason = self._detect_veto(decision, votes)

        if veto_reason:
            self._apply_decision_outcome(
                decision=decision,
                approved=False,
                result=veto_reason,
            )

            return decision

        from .models import FederationDecisionPolicy

        if federation.charter.decision_policy == FederationDecisionPolicy.CONSENSUS:
            approved = reject_weight == 0 and approve_weight > 0
        else:
            approved = approve_weight > reject_weight

        result = "APPROVED" if approved else "REJECTED"

        self._apply_decision_outcome(
            decision=decision,
            approved=approved,
            result=result,
        )

        return decision

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def federation_report(self, federation_id: str) -> Dict:
        federation = self._get_federation(federation_id)

        memberships = list(self.memberships.get(federation_id, {}).values())

        initiatives = [
            initiative
            for initiative in self.initiatives.values()
            if initiative.federation_id == federation_id
        ]

        conflicts = [
            conflict
            for conflict in self.conflicts.values()
            if conflict.federation_id == federation_id
        ]

        decisions = [
            decision
            for decision in self.decisions.values()
            if decision.federation_id == federation_id
        ]

        return {
            "federation": federation,
            "memberships": memberships,
            "initiatives": initiatives,
            "conflicts": conflicts,
            "decisions": decisions,
            "counts": {
                "members": len(memberships),
                "initiatives": len(initiatives),
                "conflicts": len(conflicts),
                "decisions": len(decisions),
            },
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_federation(self, federation_id: str) -> Federation:
        federation = self.federations.get(federation_id)

        if not federation:
            raise FederationError(
                f"Federation not found: {federation_id}"
            )

        return federation

    def _get_initiative(self, initiative_id: str) -> FederationInitiative:
        initiative = self.initiatives.get(initiative_id)

        if not initiative:
            raise FederationError(
                f"Initiative not found: {initiative_id}"
            )

        return initiative

    def _get_conflict(self, conflict_id: str) -> CrossOrganizationConflict:
        conflict = self.conflicts.get(conflict_id)

        if not conflict:
            raise FederationError(f"Conflict not found: {conflict_id}")

        return conflict

    def _get_decision(self, decision_id: str) -> CouncilDecision:
        decision = self.decisions.get(decision_id)

        if not decision:
            raise FederationError(f"Decision not found: {decision_id}")

        return decision

    def _get_membership(
        self,
        federation_id: str,
        organization_id: str,
    ) -> FederationMembership:
        membership = self.memberships.get(federation_id, {}).get(
            organization_id
        )

        if not membership:
            raise FederationError(
                f"Membership not found for organization: {organization_id}"
            )

        return membership

    def _active_memberships(
        self,
        federation_id: str,
    ) -> List[FederationMembership]:
        return [
            membership
            for membership in self.memberships.get(federation_id, {}).values()
            if membership.status == FederationMembershipStatus.ACTIVE
        ]

    def _detect_veto(
        self,
        decision: CouncilDecision,
        votes: List[CouncilVote],
    ) -> Optional[str]:
        federation = self._get_federation(decision.federation_id)

        for vote in votes:
            if vote.position != VotePosition.REJECT:
                continue

            membership = self.memberships.get(
                decision.federation_id,
                {},
            ).get(vote.organization_id)

            if not membership:
                continue

            jurisdictions = {
                jurisdiction.lower()
                for jurisdiction in membership.jurisdictions
            }

            if (
                federation.charter.security_veto
                and "security" in jurisdictions
            ):
                return "SECURITY_VETO"

            if (
                federation.charter.architecture_veto
                and "architecture" in jurisdictions
            ):
                return "ARCHITECTURE_VETO"

        return None

    def _apply_decision_outcome(
        self,
        decision: CouncilDecision,
        approved: bool,
        result: str,
    ) -> None:
        decision.result = result
        decision.updated_at = utcnow().isoformat()

        if approved:
            decision.status = CouncilDecisionStatus.APPROVED

            if decision.initiative_id:
                initiative = self.initiatives.get(decision.initiative_id)

                if initiative and initiative.status == InitiativeStatus.OPEN:
                    initiative.status = InitiativeStatus.COORDINATING
                    initiative.updated_at = utcnow().isoformat()

            if decision.conflict_id:
                conflict = self.conflicts.get(decision.conflict_id)

                if (
                    conflict
                    and conflict.status
                    == CrossOrganizationConflictStatus.OPEN
                ):
                    conflict.status = CrossOrganizationConflictStatus.RESOLVED
                    conflict.resolution_note = (
                        decision.rationale
                        or "Resolved by council decision."
                    )
                    conflict.resolved_by = f"council:{decision.id}"
                    conflict.updated_at = utcnow().isoformat()

        else:
            decision.status = CouncilDecisionStatus.REJECTED

            if (
                decision.initiative_id
                and decision.decision_type == "INITIATIVE_AUTHORIZATION"
            ):
                initiative = self.initiatives.get(decision.initiative_id)

                if initiative:
                    initiative.status = InitiativeStatus.FAILED
                    initiative.updated_at = utcnow().isoformat()

            if decision.conflict_id:
                conflict = self.conflicts.get(decision.conflict_id)

                if conflict:
                    conflict.status = (
                        CrossOrganizationConflictStatus.ESCALATED
                    )
                    conflict.updated_at = utcnow().isoformat()

        self.bus.publish(
            topic="FEDERATION_DECISION_TALLIED",
            organization_id=decision.federation_id,
            payload={
                "decision_id": decision.id,
                "status": decision.status.value,
                "result": decision.result,
            },
        )
