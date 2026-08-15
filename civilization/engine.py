"""
Autonomous Engineering Civilization engine.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol

from pydantic import BaseModel

from .bus import InMemoryCommunicationBus
from .memory import OrganizationalMemory
from .models import (
    AgentProfile,
    AgentRecommendation,
    AgentStatus,
    CollaborationDecision,
    ConflictRecord,
    ConflictStatus,
    DecisionStatus,
    EngineeringTask,
    LeadershipTerm,
    Membership,
    MembershipStatus,
    Organization,
    OrganizationCharter,
    OrganizationStatus,
    RecommendationInput,
    RoleDefinition,
    TaskStatus,
)
from .roles import default_role_definitions
from .utils import deterministic_id, utcnow


class CivilizationError(Exception):
    """Base error for civilization operations."""


class CivilizationGovernanceDecision(BaseModel):
    """Governance decision for civilization actions."""

    decision: str
    reason: str = ""


class CivilizationGovernanceGateway(Protocol):
    """Abstract governance gateway for civilization actions."""

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> CivilizationGovernanceDecision:
        ...


class StaticCivilizationGovernanceGateway:
    """Static governance gateway for tests and local development."""

    def __init__(
        self,
        decision: str = "ALLOW",
        reason: str = "Static governance decision.",
    ) -> None:
        self._decision = decision
        self._reason = reason

    def evaluate_action(
        self,
        action: str,
        context: Dict,
    ) -> CivilizationGovernanceDecision:
        return CivilizationGovernanceDecision(
            decision=self._decision,
            reason=self._reason,
        )


class AgentRuntime(Protocol):
    """Abstract agent runtime adapter."""

    def work(
        self,
        task: EngineeringTask,
        agent: AgentProfile,
        context: Dict,
    ) -> RecommendationInput:
        ...


class StaticAgentRuntime:
    """
    Deterministic reference agent runtime.

    Production deployments should replace this with LLM-backed,
    tool-backed, or specialist agent runtimes.
    """

    def work(
        self,
        task: EngineeringTask,
        agent: AgentProfile,
        context: Dict,
    ) -> RecommendationInput:
        role = context.get("role")

        role_authority = getattr(role, "authority_weight", 0.5)

        confidence = 0.45 + (agent.trust_level * 0.35) + (role_authority * 0.15)
        confidence = min(0.95, max(0.05, confidence))

        target_ref = str(task.inputs.get("target_ref", task.id))

        return RecommendationInput(
            action=f"{task.task_type}:{agent.role_id}:recommend",
            target_ref=target_ref,
            rationale=(
                f"{agent.role_id} produced an evidence-based recommendation "
                f"for task objective: {task.objective}"
            ),
            evidence_refs=[
                f"task:{task.id}",
                f"agent:{agent.agent_id}",
                f"organization:{task.organization_id}",
            ],
            confidence=confidence,
        )


class CivilizationEngine:
    """Coordinates autonomous engineering organizations."""

    def __init__(
        self,
        roles: Optional[List[RoleDefinition]] = None,
        bus: Optional[InMemoryCommunicationBus] = None,
        memory: Optional[OrganizationalMemory] = None,
        governance_gateway: Optional[CivilizationGovernanceGateway] = None,
    ) -> None:
        role_definitions = roles or default_role_definitions()

        self.roles: Dict[str, RoleDefinition] = {
            role.role_id: role
            for role in role_definitions
        }

        self.bus = bus or InMemoryCommunicationBus()
        self.memory = memory or OrganizationalMemory()

        self.governance_gateway = (
            governance_gateway
            or StaticCivilizationGovernanceGateway()
        )

        self.organizations: Dict[str, Organization] = {}
        self.agents: Dict[str, AgentProfile] = {}
        self.memberships: Dict[str, Membership] = {}

        self.tasks: Dict[str, EngineeringTask] = {}

        self.recommendations_by_task: Dict[str, Dict[str, AgentRecommendation]] = {}
        self.conflicts_by_task: Dict[str, Dict[str, ConflictRecord]] = {}
        self.decisions_by_task: Dict[str, CollaborationDecision] = {}

        self.leadership_terms: List[LeadershipTerm] = []

        self.agent_runtimes: Dict[str, AgentRuntime] = {}

    # ------------------------------------------------------------------
    # Organizations, roles, agents
    # ------------------------------------------------------------------

    def register_role(self, role: RoleDefinition) -> RoleDefinition:
        self.roles[role.role_id] = role
        return role

    def create_organization(
        self,
        name: str,
        charter: OrganizationCharter,
    ) -> Organization:
        created_at = utcnow().isoformat()

        organization_id = deterministic_id(
            "organization",
            {
                "name": name,
                "mission": charter.mission,
                "created_at": created_at,
            },
        )

        organization = Organization(
            id=organization_id,
            name=name,
            charter=charter,
            status=OrganizationStatus.ACTIVE,
            created_at=created_at,
            updated_at=created_at,
        )

        self.organizations[organization_id] = organization

        self.memory.add(
            organization_id=organization_id,
            record_type="ORGANIZATION_CREATED",
            subject_id=organization_id,
            content={
                "name": name,
                "mission": charter.mission,
            },
        )

        self.bus.publish(
            topic="ORGANIZATION_CREATED",
            organization_id=organization_id,
            payload={
                "name": name,
                "mission": charter.mission,
            },
        )

        return organization

    def create_agent(
        self,
        name: str,
        role_id: str,
        capabilities: Optional[List[str]] = None,
        trust_level: float = 0.5,
        agent_id: Optional[str] = None,
    ) -> AgentProfile:
        if role_id not in self.roles:
            raise CivilizationError(f"Unknown role: {role_id}")

        created_at = utcnow().isoformat()

        if not agent_id:
            agent_id = deterministic_id(
                "agent",
                {
                    "name": name,
                    "role_id": role_id,
                    "created_at": created_at,
                },
            )

        agent = AgentProfile(
            agent_id=agent_id,
            name=name,
            role_id=role_id,
            capabilities=capabilities or [],
            trust_level=trust_level,
            status=AgentStatus.ACTIVE,
        )

        self.agents[agent_id] = agent

        return agent

    def register_agent_runtime(
        self,
        agent_id: str,
        runtime: AgentRuntime,
    ) -> None:
        if agent_id not in self.agents:
            raise CivilizationError(f"Unknown agent: {agent_id}")

        self.agent_runtimes[agent_id] = runtime

    def assign_agent_to_organization(
        self,
        organization_id: str,
        agent_id: str,
    ) -> Membership:
        organization = self._get_organization(organization_id)
        agent = self._get_agent(agent_id)

        if organization.status != OrganizationStatus.ACTIVE:
            raise CivilizationError("Organization is not active.")

        if agent.status != AgentStatus.ACTIVE:
            raise CivilizationError("Agent is not active.")

        current_members = self.get_organization_members(organization_id)

        if len(current_members) >= organization.charter.max_agents:
            raise CivilizationError("Organization has reached max agents.")

        membership = Membership(
            organization_id=organization_id,
            agent_id=agent_id,
            role_id=agent.role_id,
            status=MembershipStatus.ACTIVE,
            joined_at=utcnow().isoformat(),
        )

        self.memberships[agent_id] = membership

        self.memory.add(
            organization_id=organization_id,
            record_type="AGENT_ASSIGNED",
            subject_id=agent_id,
            content={
                "agent_name": agent.name,
                "role_id": agent.role_id,
            },
        )

        self.bus.publish(
            topic="AGENT_ASSIGNED",
            organization_id=organization_id,
            sender_agent_id=agent_id,
            payload={
                "role_id": agent.role_id,
            },
        )

        return membership

    def get_organization_members(
        self,
        organization_id: str,
    ) -> List[AgentProfile]:
        members: List[AgentProfile] = []

        for membership in self.memberships.values():
            if membership.organization_id != organization_id:
                continue

            if membership.status != MembershipStatus.ACTIVE:
                continue

            agent = self.agents.get(membership.agent_id)

            if agent and agent.status == AgentStatus.ACTIVE:
                members.append(agent)

        return members

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def create_task(
        self,
        organization_id: str,
        title: str,
        objective: str,
        task_type: str,
        required_roles: Optional[List[str]] = None,
        inputs: Optional[Dict] = None,
        priority: int = 50,
        high_impact: bool = False,
        proposal_id: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> EngineeringTask:
        organization = self._get_organization(organization_id)

        if organization.status != OrganizationStatus.ACTIVE:
            raise CivilizationError("Organization is not active.")

        created_at = utcnow().isoformat()

        task_id = deterministic_id(
            "engineering_task",
            {
                "organization_id": organization_id,
                "title": title,
                "objective": objective,
                "task_type": task_type,
                "created_at": created_at,
            },
        )

        task = EngineeringTask(
            id=task_id,
            organization_id=organization_id,
            title=title,
            objective=objective,
            task_type=task_type,
            required_roles=required_roles or [],
            inputs=inputs or {},
            priority=priority,
            high_impact=high_impact,
            status=TaskStatus.OPEN,
            proposal_id=proposal_id,
            campaign_id=campaign_id,
            created_at=created_at,
            updated_at=created_at,
        )

        self.tasks[task_id] = task

        self.bus.publish(
            topic="TASK_CREATED",
            organization_id=organization_id,
            task_id=task_id,
            payload={
                "title": title,
                "task_type": task_type,
                "high_impact": high_impact,
            },
        )

        return task

    def allocate_task(self, task_id: str) -> List[str]:
        task = self._get_task(task_id)

        members = self.get_organization_members(task.organization_id)

        if task.required_roles:
            eligible = [
                agent
                for agent in members
                if agent.role_id in task.required_roles
            ]
        else:
            eligible = members

        if not eligible:
            raise CivilizationError("No eligible agents for task.")

        workload: Dict[str, int] = {}

        active_task_statuses = {
            TaskStatus.ASSIGNED,
            TaskStatus.IN_PROGRESS,
            TaskStatus.REVIEW,
        }

        for agent in eligible:
            workload[agent.agent_id] = sum(
                1
                for existing_task in self.tasks.values()
                if agent.agent_id in existing_task.assigned_agent_ids
                and existing_task.status in active_task_statuses
            )

        eligible.sort(
            key=lambda agent: (
                -self.roles[agent.role_id].authority_weight,
                -agent.trust_level,
                workload[agent.agent_id],
                agent.agent_id,
            )
        )

        if task.required_roles:
            max_assign = min(len(eligible), len(task.required_roles))
        else:
            max_assign = min(len(eligible), 3)

        selected = eligible[:max_assign]

        task.assigned_agent_ids = [agent.agent_id for agent in selected]
        task.status = TaskStatus.ASSIGNED
        task.updated_at = utcnow().isoformat()

        self.bus.publish(
            topic="TASK_ASSIGNED",
            organization_id=task.organization_id,
            task_id=task.id,
            payload={
                "assigned_agent_ids": task.assigned_agent_ids,
            },
        )

        return task.assigned_agent_ids

    def run_task(self, task_id: str) -> List[AgentRecommendation]:
        task = self._get_task(task_id)

        if task.status == TaskStatus.OPEN:
            self.allocate_task(task_id)

        if task.status != TaskStatus.ASSIGNED:
            raise CivilizationError(
                "Task must be ASSIGNED before running."
            )

        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = utcnow().isoformat()

        recommendations: List[AgentRecommendation] = []

        for agent_id in task.assigned_agent_ids:
            agent = self._get_agent(agent_id)
            role = self.roles[agent.role_id]

            runtime = self.agent_runtimes.get(agent_id)

            if not runtime:
                runtime = StaticAgentRuntime()

            recommendation_input = runtime.work(
                task=task,
                agent=agent,
                context={
                    "role": role,
                    "organization_id": task.organization_id,
                },
            )

            recommendation = self.submit_recommendation(
                task_id=task.id,
                agent_id=agent_id,
                payload=recommendation_input,
            )

            recommendations.append(recommendation)

        task.status = TaskStatus.REVIEW
        task.updated_at = utcnow().isoformat()

        return recommendations

    def submit_recommendation(
        self,
        task_id: str,
        agent_id: str,
        payload: RecommendationInput,
    ) -> AgentRecommendation:
        task = self._get_task(task_id)
        agent = self._get_agent(agent_id)

        if agent_id not in task.assigned_agent_ids:
            raise CivilizationError(
                "Agent is not assigned to this task."
            )

        created_at = utcnow().isoformat()

        recommendation_id = deterministic_id(
            "agent_recommendation",
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "action": payload.action,
                "target_ref": payload.target_ref,
                "created_at": created_at,
            },
        )

        recommendation = AgentRecommendation(
            id=recommendation_id,
            task_id=task_id,
            agent_id=agent_id,
            role_id=agent.role_id,
            action=payload.action,
            target_ref=payload.target_ref,
            rationale=payload.rationale,
            evidence_refs=payload.evidence_refs,
            confidence=payload.confidence,
            created_at=created_at,
        )

        task_recommendations = self.recommendations_by_task.setdefault(
            task_id,
            {},
        )

        task_recommendations[recommendation_id] = recommendation

        self.memory.add(
            organization_id=task.organization_id,
            record_type="RECOMMENDATION_SUBMITTED",
            subject_id=recommendation_id,
            content={
                "task_id": task_id,
                "agent_id": agent_id,
                "action": payload.action,
                "target_ref": payload.target_ref,
            },
            evidence_refs=payload.evidence_refs,
        )

        self.bus.publish(
            topic="RECOMMENDATION_SUBMITTED",
            organization_id=task.organization_id,
            task_id=task_id,
            sender_agent_id=agent_id,
            payload={
                "recommendation_id": recommendation_id,
                "action": payload.action,
            },
        )

        return recommendation

    # ------------------------------------------------------------------
    # Conflicts and decisions
    # ------------------------------------------------------------------

    def detect_conflicts(self, task_id: str) -> List[ConflictRecord]:
        task = self._get_task(task_id)

        recommendations = list(
            self.recommendations_by_task.get(task_id, {}).values()
        )

        by_target: Dict[str, List[AgentRecommendation]] = {}

        for recommendation in recommendations:
            by_target.setdefault(recommendation.target_ref, []).append(
                recommendation
            )

        conflicts = self.conflicts_by_task.setdefault(task_id, {})

        for target_ref, target_recommendations in by_target.items():
            if len(target_recommendations) < 2:
                continue

            actions = {
                recommendation.action
                for recommendation in target_recommendations
            }

            if len(actions) < 2:
                continue

            recommendation_ids = sorted(
                recommendation.id
                for recommendation in target_recommendations
            )

            conflict_id = deterministic_id(
                "conflict",
                {
                    "task_id": task_id,
                    "target_ref": target_ref,
                    "recommendation_ids": recommendation_ids,
                },
            )

            if conflict_id in conflicts:
                continue

            conflict = ConflictRecord(
                id=conflict_id,
                task_id=task_id,
                recommendation_ids=recommendation_ids,
                conflict_type="OPPOSING_RECOMMENDATIONS",
                status=ConflictStatus.OPEN,
                created_at=utcnow().isoformat(),
            )

            conflicts[conflict_id] = conflict

            self.bus.publish(
                topic="CONFLICT_DETECTED",
                organization_id=task.organization_id,
                task_id=task_id,
                payload={
                    "conflict_id": conflict_id,
                    "target_ref": target_ref,
                },
            )

        return list(conflicts.values())

    def resolve_conflicts(
        self,
        task_id: str,
        resolved_by: str = "conflict_engine",
    ) -> List[ConflictRecord]:
        task = self._get_task(task_id)

        conflicts = self.conflicts_by_task.get(task_id, {})
        recommendations = self.recommendations_by_task.get(task_id, {})

        for conflict in conflicts.values():
            if conflict.status != ConflictStatus.OPEN:
                continue

            conflict_recommendations = [
                recommendations[recommendation_id]
                for recommendation_id in conflict.recommendation_ids
                if recommendation_id in recommendations
            ]

            if not conflict_recommendations:
                conflict.status = ConflictStatus.ESCALATED
                conflict.resolution_note = "No recommendations available."
                continue

            def score(recommendation: AgentRecommendation) -> float:
                agent = self.agents.get(recommendation.agent_id)

                if not agent:
                    return 0.0

                role = self.roles.get(agent.role_id)

                authority_weight = role.authority_weight if role else 0.5

                return (
                    recommendation.confidence
                    * agent.trust_level
                    * authority_weight
                )

            ranked = sorted(
                conflict_recommendations,
                key=lambda recommendation: (
                    -score(recommendation),
                    recommendation.created_at,
                    recommendation.agent_id,
                ),
            )

            selected = ranked[0]

            conflict.status = ConflictStatus.RESOLVED
            conflict.selected_recommendation_id = selected.id
            conflict.resolved_by = resolved_by
            conflict.resolution_note = (
                "Selected recommendation using confidence, agent trust, "
                "and role authority."
            )

            self.bus.publish(
                topic="CONFLICT_RESOLVED",
                organization_id=task.organization_id,
                task_id=task_id,
                payload={
                    "conflict_id": conflict.id,
                    "selected_recommendation_id": selected.id,
                },
            )

        return list(conflicts.values())

    def finalize_task(
        self,
        task_id: str,
        actor_id: str = "civilization_engine",
    ) -> CollaborationDecision:
        task = self._get_task(task_id)

        if task.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            raise CivilizationError("Task is already finalized.")

        self.detect_conflicts(task_id)
        self.resolve_conflicts(task_id)

        recommendations = list(
            self.recommendations_by_task.get(task_id, {}).values()
        )

        conflicts = list(self.conflicts_by_task.get(task_id, {}).values())

        open_conflicts = [
            conflict
            for conflict in conflicts
            if conflict.status == ConflictStatus.OPEN
        ]

        escalated_conflicts = [
            conflict
            for conflict in conflicts
            if conflict.status == ConflictStatus.ESCALATED
        ]

        created_at = utcnow().isoformat()

        decision_id = deterministic_id(
            "collaboration_decision",
            {
                "task_id": task_id,
                "created_at": created_at,
            },
        )

        if not recommendations:
            decision = CollaborationDecision(
                id=decision_id,
                task_id=task_id,
                status=DecisionStatus.FAILED,
                rationale="No recommendations were produced.",
                created_at=created_at,
            )

            task.status = TaskStatus.FAILED
            task.updated_at = created_at

            self.decisions_by_task[task_id] = decision

            return decision

        if open_conflicts or escalated_conflicts:
            decision = CollaborationDecision(
                id=decision_id,
                task_id=task_id,
                status=DecisionStatus.ESCALATED,
                conflict_ids=[conflict.id for conflict in conflicts],
                rationale="Unresolved or escalated conflicts remain.",
                created_at=created_at,
            )

            task.status = TaskStatus.ESCALATED
            task.updated_at = created_at

            self.decisions_by_task[task_id] = decision

            return decision

        organization = self._get_organization(task.organization_id)

        if task.high_impact and organization.charter.high_impact_requires_governance:
            governance_decision = self.governance_gateway.evaluate_action(
                action="FINALIZE_ENGINEERING_TASK",
                context={
                    "task_id": task.id,
                    "organization_id": organization.id,
                    "high_impact": task.high_impact,
                    "recommendation_count": len(recommendations),
                },
            )

            if governance_decision.decision != "ALLOW":
                decision = CollaborationDecision(
                    id=decision_id,
                    task_id=task_id,
                    status=DecisionStatus.FAILED,
                    rationale=(
                        "Governance denied task finalization: "
                        f"{governance_decision.reason}"
                    ),
                    conflict_ids=[conflict.id for conflict in conflicts],
                    created_at=created_at,
                )

                task.status = TaskStatus.FAILED
                task.updated_at = created_at

                self.decisions_by_task[task_id] = decision

                self.bus.publish(
                    topic="GOVERNANCE_DENIED",
                    organization_id=organization.id,
                    task_id=task.id,
                    payload={
                        "decision_id": decision_id,
                        "reason": governance_decision.reason,
                    },
                )

                return decision

        conflict_recommendation_ids = {
            recommendation_id
            for conflict in conflicts
            for recommendation_id in conflict.recommendation_ids
        }

        selected_recommendation_ids: List[str] = []

        for conflict in conflicts:
            if (
                conflict.status == ConflictStatus.RESOLVED
                and conflict.selected_recommendation_id
            ):
                selected_recommendation_ids.append(
                    conflict.selected_recommendation_id
                )

        for recommendation in recommendations:
            if recommendation.id not in conflict_recommendation_ids:
                selected_recommendation_ids.append(recommendation.id)

        decision = CollaborationDecision(
            id=decision_id,
            task_id=task_id,
            status=DecisionStatus.COMPLETED,
            selected_recommendation_ids=selected_recommendation_ids,
            conflict_ids=[conflict.id for conflict in conflicts],
            rationale="Collaboration completed with resolved recommendations.",
            created_at=created_at,
        )

        task.status = TaskStatus.COMPLETED
        task.updated_at = created_at

        self.decisions_by_task[task_id] = decision

        self.memory.add(
            organization_id=task.organization_id,
            record_type="COLLABORATION_DECISION",
            subject_id=decision_id,
            content={
                "task_id": task_id,
                "status": decision.status.value,
                "selected_recommendation_ids": selected_recommendation_ids,
            },
        )

        self.bus.publish(
            topic="DECISION_MADE",
            organization_id=task.organization_id,
            task_id=task_id,
            payload={
                "decision_id": decision_id,
                "status": decision.status.value,
            },
        )

        return decision

    # ------------------------------------------------------------------
    # Leadership
    # ------------------------------------------------------------------

    def elect_leader(
        self,
        organization_id: str,
        method: str = "trust_weighted",
    ) -> LeadershipTerm:
        organization = self._get_organization(organization_id)

        members = self.get_organization_members(organization_id)

        if not members:
            raise CivilizationError("Organization has no active members.")

        def leadership_score(agent: AgentProfile) -> float:
            role = self.roles.get(agent.role_id)

            authority_weight = role.authority_weight if role else 0.5

            return agent.trust_level * authority_weight

        ranked = sorted(
            members,
            key=lambda agent: (
                -leadership_score(agent),
                agent.agent_id,
            ),
        )

        leader = ranked[0]

        elected_at = utcnow().isoformat()

        term_id = deterministic_id(
            "leadership_term",
            {
                "organization_id": organization_id,
                "leader_agent_id": leader.agent_id,
                "elected_at": elected_at,
            },
        )

        term = LeadershipTerm(
            id=term_id,
            organization_id=organization_id,
            leader_agent_id=leader.agent_id,
            method=method,
            rationale="Elected by trust-weighted role authority.",
            elected_at=elected_at,
        )

        self.leadership_terms.append(term)

        organization.leader_agent_id = leader.agent_id
        organization.updated_at = elected_at

        self.memory.add(
            organization_id=organization_id,
            record_type="LEADERSHIP_ELECTED",
            subject_id=term_id,
            content={
                "leader_agent_id": leader.agent_id,
                "method": method,
            },
        )

        self.bus.publish(
            topic="LEADERSHIP_ELECTED",
            organization_id=organization_id,
            payload={
                "term_id": term_id,
                "leader_agent_id": leader.agent_id,
            },
        )

        return term

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_task(self, task_id: str) -> EngineeringTask:
        return self._get_task(task_id)

    def list_recommendations(self, task_id: str) -> List[AgentRecommendation]:
        return list(self.recommendations_by_task.get(task_id, {}).values())

    def list_conflicts(self, task_id: str) -> List[ConflictRecord]:
        return list(self.conflicts_by_task.get(task_id, {}).values())

    def get_decision(self, task_id: str) -> Optional[CollaborationDecision]:
        return self.decisions_by_task.get(task_id)

    def get_memory(
        self,
        organization_id: str,
        record_type: Optional[str] = None,
        limit: int = 100,
    ):
        return self.memory.list_records(
            organization_id=organization_id,
            record_type=record_type,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_organization(self, organization_id: str) -> Organization:
        organization = self.organizations.get(organization_id)

        if not organization:
            raise CivilizationError(
                f"Organization not found: {organization_id}"
            )

        return organization

    def _get_agent(self, agent_id: str) -> AgentProfile:
        agent = self.agents.get(agent_id)

        if not agent:
            raise CivilizationError(f"Agent not found: {agent_id}")

        return agent

    def _get_task(self, task_id: str) -> EngineeringTask:
        task = self.tasks.get(task_id)

        if not task:
            raise CivilizationError(f"Task not found: {task_id}")

        return task
