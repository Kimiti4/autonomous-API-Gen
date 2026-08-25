"""GovernanceSubsystem — command handler + projector (§2.1, §2.7).

The ONLY subsystem authorized to advance a candidate's lifecycle state.
Validates invariants G-1..G-7 before appending events; the event log is
the audit trail and the source of truth for materialization.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.core.contracts.governance import (
    CouncilComposition,
    GateOutcome,
    GovernanceDecision,
)
from app.core.governance.commands import (
    GrantCertification,
    RecordGateEvaluation,
    RegisterGate,
    RegisterPolicy,
    RequestGovernanceDecision,
    RevokeCertification,
    UpdateCouncil,
)
from app.core.governance.events import (
    CertificationGranted,
    CertificationRevoked,
    CouncilUpdated,
    GateEvaluated,
    GateRegistered,
    GovernanceDecisionMade,
    PolicyRegistered,
)
from app.core.governance.invariants import (
    check_g1_transition_legality,
    check_g2_gates_satisfied,
    check_g3_waiver_accountability,
    check_g5_decider_authorization,
    check_g7_quorum_weight,
)
from app.governance.aggregate import CandidateGovernanceState


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class GovernanceSubsystem:
    def __init__(
        self,
        *,
        event_store,
        reference_store,
        quorum_threshold: float = 1.0,
        recognized_certifiers: Optional[set] = None,
    ) -> None:
        self._events = event_store
        self._refs = reference_store
        self._quorum = quorum_threshold
        self._certifiers = recognized_certifiers or set()

    # ---- command handlers ------------------------------------------------

    async def request_decision(self, cmd: RequestGovernanceDecision) -> GovernanceDecision:
        council = await self._refs.load_council() or CouncilComposition()
        gates = await self._refs.load_gates()
        state = await self.materialize_candidate(cmd.candidateId)

        decision = GovernanceDecision(
            decisionId="dec-%s-%d" % (
                cmd.candidateId, len(state.decisions) + 1
            ),
            candidateId=cmd.candidateId,
            generation=cmd.generation,
            verdict=cmd.verdict,  # type: ignore[arg-type]
            fromState=cmd.fromState,
            toState=cmd.toState,
            authorizesTransition=cmd.authorizesTransition,
            decidedBy=list(cmd.decidedBy),
            rationale=cmd.rationale,
            supersedesDecisionId=cmd.supersedesDecisionId,
            evidenceRefs=list(cmd.evidenceRefs),
            decidedAt=_now_iso(),
        )

        # Invariants BEFORE append — the log only holds valid facts.
        if cmd.authorizesTransition:
            check_g1_transition_legality(decision)
            # G-1 also requires the transition to start at the CURRENT state.
            if state.current_state != cmd.fromState:
                raise Exception(
                    "G-1 violated: candidate is in state %r, not %r"
                    % (state.current_state, cmd.fromState)
                )
        check_g5_decider_authorization(cmd.decidedBy, council)
        if cmd.verdict == "approve":
            check_g2_gates_satisfied(decision, state.gate_outcomes, gates)
            check_g7_quorum_weight(cmd.decidedBy, council, self._quorum)

        event = GovernanceDecisionMade(decision=decision)
        await self._events.append(cmd.candidateId, [event])
        return decision

    async def record_gate_evaluation(
        self, cmd: RecordGateEvaluation
    ) -> GateOutcome:
        outcome = GateOutcome(
            gateId=cmd.gateId,
            candidateId=cmd.candidateId,
            status=cmd.status,
            evaluatedBy=cmd.evaluatedBy,
            waivedBy=cmd.waivedBy,
            evidenceRefs=list(cmd.evidenceRefs),
            note=cmd.note,
            evaluatedAt=_now_iso(),
        )
        check_g3_waiver_accountability(outcome)
        await self._events.append(
            cmd.candidateId, [GateEvaluated(outcome=outcome)]
        )
        return outcome

    async def grant_certification(self, cmd: GrantCertification):
        if self._certifiers and cmd.certifiedBy not in self._certifiers:
            raise Exception(
                "G-6 violated: %r is not a recognized certifying authority"
                % cmd.certifiedBy
            )
        certification = {
            "certificationId": cmd.certificationId,
            "candidateId": cmd.candidateId,
            "certifiedBy": cmd.certifiedBy,
            "criteria": cmd.criteria,
            "scope": cmd.scope,
            "validUntil": cmd.validUntil,
            "evidenceRefs": list(cmd.evidenceRefs),
            "grantedAt": _now_iso(),
        }
        from app.core.contracts.governance import Certification

        cert = Certification(**certification)
        await self._events.append(
            cmd.candidateId, [CertificationGranted(certification=cert)]
        )
        return cert

    async def revoke_certification(self, cmd: RevokeCertification):
        event = CertificationRevoked(
            certificationId=cmd.certificationId,
            revokedAt=_now_iso(),
            revokedBy=cmd.revokedBy,
        )
        # Revocation events go to the registry stream; the aggregate finds
        # them via load_generation / full-log scans.
        await self._events.append("_registry", [event])

    async def update_council(self, cmd: UpdateCouncil):
        composition = CouncilComposition(
            members=list(cmd.members), updatedAt=_now_iso()
        )
        await self._refs.save_council(composition)
        await self._events.append(
            "_registry",
            [CouncilUpdated(composition=composition, updatedBy=cmd.updatedBy,
                            updatedAt=_now_iso())],
        )
        return composition

    async def register_gate(self, cmd: RegisterGate):
        await self._refs.save_gate(cmd.gate)
        await self._events.append(
            "_registry", [GateRegistered(gate=cmd.gate)]
        )
        return cmd.gate

    async def register_policy(self, cmd: RegisterPolicy):
        await self._refs.save_policy(cmd.policy)
        await self._events.append(
            "_registry", [PolicyRegistered(policy=cmd.policy)]
        )
        return cmd.policy

    # ---- materialization (read side of this subsystem) --------------------

    async def materialize_candidate(self, candidate_id: str):
        events = await self._events.load(candidate_id)
        return CandidateGovernanceState.fold(candidate_id, events)

    async def materialize_generation(self, generation: int) -> list:
        events_by_candidate = await self._events.load_generation(generation)
        return [
            CandidateGovernanceState.fold(cid, events)
            for cid, events in sorted(events_by_candidate.items())
        ]