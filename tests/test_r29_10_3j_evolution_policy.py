"""R2.10.3-J — evolution_objectives_protected_regions: the constitutional capstone.

J answers two distinct questions:
  1. What is this evolution allowed to optimize?   -> EvolutionObjective
  2. What must this evolution never sacrifice?     -> ProtectedRegion

Objective = tradeable optimization preference. ProtectedRegion = non-tradeable
constitutional constraint. An objective may be traded against another
objective; a protected region may NOT be traded away for fitness.

The crucial constitutional boundary: protection is enforced as a FEASIBILITY
GATE (EvolutionProtectionEvaluator removes violating candidates from the
feasible space BEFORE objective evaluation) — never a fitness penalty, which
a sufficiently large competing fitness could overwhelm.

The three architectural proofs that gate promotion to EXPRESSED:
  1. No self-authorization — ConstitutionalAuthorization is governance-owned
     (constitutional_architecture.governance); the evolution package cannot
     import or construct it (module-boundary test), and ordinary evolution
     cannot satisfy a CONSTITUTIONAL authorization.
  2. No fitness/objective conflation — no measured-value field structurally;
     changing objective weights cannot produce a scalar objective artifact
     inside the ISR projection (lexicographic tiers, never weighted sums).
  3. No authority duplication between E/H/J — J protects identities by
     reference; E stays authoritative for boundaries, H for anchors; no
     ownership transfers.

The audit gate embeds the pre-landing matrix (11/18/0/1 — after R2.10.3-I)
and asserts the delta is exactly {evolution_objectives_protected_regions:
MISSING -> EXPRESSED} -> 12/18/0/0, the final R2.10.3 matrix.
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import pathlib
import tempfile
from typing import Any

import pytest

from constitutional_architecture.governance.constitutional_authorization import (
    ConstitutionalAuthorizationRegistry,
)
from constitutional_architecture.isr.model import (
    AcceptanceCriterion,
    AnchorAuthority,
    ArchitecturalBoundary,
    BusinessCapability,
    CompatibilityPolicy,
    DataMigrationIntent,
    DegradationPolicy,
    DeploymentIntent,
    DocumentationAudience,
    DocumentationIntent,
    DocumentationPurpose,
    Entity,
    EvolutionObjective,
    EvolutionPolicy,
    EvolutionPolicyValidationError,
    FailureMode,
    ISR,
    Interface,
    InterfaceType,
    Module,
    ObjectiveDimension,
    ObjectiveDirection,
    ObjectiveTier,
    ObligationKind,
    PreservationInvariant,
    ProtectedRegion,
    ProtectionKind,
    ProtectionPolicy,
    RecoveryBehavior,
    RecoveryObjective,
    ReliabilityRequirement,
    Requirement,
    RolloutStrategy,
    StateType,
    System,
    TemporalConstraint,
    TemporalConstraintKind,
    TestingAnchor,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.evolution_policy import (
    EVOLUTION_MECHANISM_TERMS,
    assert_evolution_technology_agnostic,
    evolution_mechanism_hits as mechanism_hits,
    evolution_policy_has_no_scalar_aggregation,
    project_evolution_policy,
)
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.evolution.evolution_policy_mutation import (
    EvolutionPolicyOperator,
)
from tiannara.application.evolution.isr_capability_audit import (
    CapabilityStatus,
    ISRCapabilityAudit,
    MutationLocalityProbe,
    gene_index,
)
from tiannara.application.evolution.ledger import EventType, EvolutionLedger
from tiannara.application.evolution.primitive_contract import TECHNOLOGY_COUPLING_TERMS
from tiannara.application.evolution.primitive_gate import (
    PRIMITIVE_GATE,
    GateResult,
    assert_all_gates,
)
from tiannara.application.evolution.protection import (
    EvolutionDiff,
    EvolutionProtectionEvaluator,
    ProtectionResult,
)


def _entity(entity_id: str) -> Entity:
    return Entity(id=entity_id, name=entity_id)


def _workflow(workflow_id: str, trigger: str) -> Workflow:
    return Workflow(
        id=workflow_id,
        name=f"workflow {workflow_id}",
        states=(
            WorkflowState(
                id=f"{workflow_id}-start",
                name="started",
                state_type=StateType.INTERMEDIATE,
                metadata={"awaits": trigger},
            ),
            WorkflowState(
                id=f"{workflow_id}-done",
                name="done",
                state_type=StateType.FINAL,
            ),
        ),
        transitions=(
            WorkflowTransition(
                id=f"{workflow_id}-t1",
                name="resolve",
                from_state_id=f"{workflow_id}-start",
                to_state_id=f"{workflow_id}-done",
                trigger=trigger,
            ),
        ),
    )


class EvolutionPolicyPrimitiveHarness:
    """The eleven-gate harness for evolution objectives + protected regions."""

    primitive_id = "evolution_objectives_protected_regions"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = EvolutionPolicyOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()
        self.evaluator = EvolutionProtectionEvaluator()
        self.authority = ConstitutionalAuthorizationRegistry()

    # -- recipes ------------------------------------------------------------

    def valid_objective(
        self,
        dimension: ObjectiveDimension = ObjectiveDimension.RELIABILITY,
        tier: ObjectiveTier = ObjectiveTier.OPTIMIZATION,
    ) -> EvolutionObjective:
        return EvolutionObjective(
            objective_id="obj1",
            dimension=dimension,
            direction=ObjectiveDirection.MAXIMIZE,
            tier=tier,
            priority=0,
            weight=1.0,
            subject_refs=("capability_pay",),
        )

    def valid_region(
        self,
        protection_kind: ProtectionKind = ProtectionKind.IMMUTABLE,
        subject_refs: tuple[str, ...] = ("capability_pay",),
    ) -> ProtectedRegion:
        return ProtectedRegion(
            region_id="region1",
            subject_refs=subject_refs,
            protection_kind=protection_kind,
            invariants=(
                (
                    PreservationInvariant(
                        kind=ObligationKind.PRESENCE,
                        subject_refs=subject_refs,
                        statement="the capability must remain present",
                    ),
                )
                if protection_kind is ProtectionKind.PRESERVATION
                else ()
            ),
        )

    def valid_policy(
        self,
        objective_refs: tuple[str, ...] = ("obj1",),
        region_refs: tuple[str, ...] = ("region1",),
    ) -> EvolutionPolicy:
        return EvolutionPolicy(
            policy_id="policy1",
            objective_refs=objective_refs,
            protected_region_refs=region_refs,
            selection_constraints=(
                "no candidate may sacrifice the declared reliability",),
        )

    def isr_with(
        self,
        objectives: tuple[EvolutionObjective, ...] = (),
        regions: tuple[ProtectedRegion, ...] = (),
        policies: tuple[EvolutionPolicy, ...] = (),
    ) -> ISR:
        return ISR(
            system=System(
                id="j-sys",
                name="EvolutionPolicySystem",
                modules=(
                    Module(
                        id="m",
                        name="M",
                        entities=tuple(_entity(eid) for eid in ("e1", "e2")),
                        workflows=(_workflow("w1", "op_w1"),),
                        interfaces=(
                            Interface(id="i1", name="i1", interface_type=InterfaceType.REST),
                        ),
                        temporal_constraints=(
                            TemporalConstraint(
                                constraint_id="t1.deadline",
                                kind=TemporalConstraintKind.TRANSITION_DEADLINE,
                                target_ref="w1-t1",
                                duration_ms=250,
                            ),
                        ),
                        data_migrations=(
                            DataMigrationIntent(
                                migration_id="m1",
                                source_schema_ref="e1",
                                target_schema_ref="e2",
                                compatibility_policy=CompatibilityPolicy.BACKWARD,
                                preservation_refs=("e1",),
                                rollback_required=True,
                                rollback_target_ref="e1",
                                rollback_invariants=("e1 intact",),
                                postconditions=("e2 valid",),
                            ),
                        ),
                    ),
                ),
                business_capabilities=(
                    BusinessCapability(
                        capability_id="capability_pay",
                        intent="process a payment",
                        behavior_refs=("w1",),
                        interface_refs=("i1",),
                    ),
                ),
                reliability_requirements=(
                    ReliabilityRequirement(
                        requirement_id="rr1",
                        target_refs=("capability_pay",),
                        failure_modes=(FailureMode.TRANSIENT_DEPENDENCY_FAILURE,),
                        recovery_objectives=(
                            RecoveryObjective(
                                failure_mode=FailureMode.TRANSIENT_DEPENDENCY_FAILURE,
                                required_behavior=RecoveryBehavior.EVENTUAL_RECOVERY,
                                max_recovery_duration_ms=5000,
                            ),
                        ),
                        degradation_policy=DegradationPolicy.NO_DEGRADATION,
                        preservation_invariants=("pay coherent",),
                    ),
                ),
                architectural_boundaries=(
                    ArchitecturalBoundary(
                        boundary_id="b1",
                        member_refs=("m",),
                        forbidden_dependency_refs=(),
                        protected=False,
                        crossing_invariants=("no cross without declared intent",),
                    ),
                ),
                requirements=(
                    Requirement(
                        requirement_id="req.cancel",
                        statement="Cancellation must become effective before settlement",
                        target_refs=("capability_pay",),
                        acceptance_refs=("crit.cancel",),
                        constraint_refs=("w1",),
                    ),
                ),
                acceptance_criteria=(
                    AcceptanceCriterion(
                        criterion_id="crit.cancel",
                        obligation="Order cancellation must become effective before settlement",
                        kind=ObligationKind.ORDERING,
                        subject_refs=("w1",),
                    ),
                ),
                deployment_intents=(
                    DeploymentIntent(
                        deployment_id="dep1",
                        target_refs=("capability_pay",),
                        rollout_strategy=RolloutStrategy.CANARY,
                        rollback_required=True,
                        rollback_target_ref="capability_pay",
                        rollback_invariants=("payment state preserved",),
                    ),
                ),
                testing_anchors=(
                    TestingAnchor(
                        anchor_id="anchor1",
                        subject_refs=("w1",),
                        obligation_refs=("crit.cancel",),
                        evidence_requirements=(
                            "ORDERING before authorization demonstrated",),
                        protection_policy=ProtectionPolicy.EVOLVABLE,
                        authority=AnchorAuthority.DERIVED,
                    ),
                ),
                documentation_intents=(
                    DocumentationIntent(
                        documentation_id="doc1",
                        subject_refs=("capability_pay",),
                        purpose=DocumentationPurpose.OPERATIONAL_REFERENCE,
                        audience=DocumentationAudience.DEVELOPER,
                        obligations=(
                            "the capability's declared behavior must be documented",),
                    ),
                ),
                evolution_objectives=objectives,
                protected_regions=regions,
                evolution_policies=policies,
            )
        )

    def isr_without_policy(self) -> ISR:
        return self.isr_with()

    def isr_with_policy(self) -> ISR:
        return self.isr_with(
            objectives=(self.valid_objective(),),
            regions=(self.valid_region(),),
            policies=(self.valid_policy(),),
        )

    def isr_with_constitutional_region(self, region_id: str = "region1") -> ISR:
        return self.isr_with(
            objectives=(self.valid_objective(),),
            regions=(
                self.valid_region(
                    protection_kind=ProtectionKind.CONSTITUTIONAL
                ),
            ),
            policies=(self.valid_policy(),),
        )

    def isr_with_constitutional_objective(self) -> ISR:
        return self.isr_with(
            objectives=(
                self.valid_objective(tier=ObjectiveTier.CONSTITUTIONAL),
            ),
            regions=(self.valid_region(),),
            policies=(self.valid_policy(),),
        )

    def isr_with_preservation_region(self) -> ISR:
        return self.isr_with(
            objectives=(self.valid_objective(),),
            regions=(self.valid_region(ProtectionKind.PRESERVATION),),
            policies=(self.valid_policy(),),
        )

    def with_empty_policy(self, isr: ISR) -> ISR:
        return isr.with_system(
            dataclasses.replace(
                isr.system,
                evolution_objectives=(),
                protected_regions=(),
                evolution_policies=(),
            )
        )

    def governance_authorization_for(
        self,
        region_ref: str,
        affected: tuple[str, ...] = ("capability_pay",),
        authorization_id: str = "auth1",
    ) -> Any:
        return self.authority.issue(
            authorization_id=authorization_id,
            region_ref=region_ref,
            subject_refs=affected,
            rationale="governance-reviewed constitutional change",
            authorizer="governance-kernel",
        )

    # -- candidate mutations -------------------------------------------------

    def ordinary_operator_mutation_into(self, isr: ISR, subject: str) -> ISR:
        """Ordinary evolution mutating the gene of one semantic identity —
        what operators legitimately do to a protected subject's own
        implementation gene (capabilities, requirements, criteria,
        boundaries, anchors, reliability requirements, deployment intents,
        documentation intents, migrations, temporal constraints, behaviors)."""
        system = isr.system
        for capability in system.business_capabilities:
            if capability.capability_id == subject:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        business_capabilities=tuple(
                            dataclasses.replace(c, intent=f"{c.intent} (evolved)")
                            if c.capability_id == subject else c
                            for c in system.business_capabilities
                        ),
                    )
                )
        for requirement in system.requirements:
            if requirement.requirement_id == subject:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        requirements=tuple(
                            dataclasses.replace(
                                r, statement=f"{r.statement} (evolved)"
                            )
                            if r.requirement_id == subject else r
                            for r in system.requirements
                        ),
                    )
                )
        for criterion in system.acceptance_criteria:
            if criterion.criterion_id == subject:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        acceptance_criteria=tuple(
                            dataclasses.replace(
                                c, obligation=f"{c.obligation} (evolved)"
                            )
                            if c.criterion_id == subject else c
                            for c in system.acceptance_criteria
                        ),
                    )
                )
        for boundary in system.architectural_boundaries:
            if boundary.boundary_id == subject:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        architectural_boundaries=tuple(
                            dataclasses.replace(
                                b,
                                crossing_invariants=(
                                    b.crossing_invariants[0] + " (evolved)",
                                ),
                            )
                            if b.boundary_id == subject else b
                            for b in system.architectural_boundaries
                        ),
                    )
                )
        for anchor in system.testing_anchors:
            if anchor.anchor_id == subject:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        testing_anchors=tuple(
                            dataclasses.replace(
                                a,
                                evidence_requirements=(
                                    a.evidence_requirements[0] + " (evolved)",
                                ),
                            )
                            if a.anchor_id == subject else a
                            for a in system.testing_anchors
                        ),
                    )
                )
        for rr in system.reliability_requirements:
            if rr.requirement_id == subject:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        reliability_requirements=tuple(
                            dataclasses.replace(
                                r,
                                preservation_invariants=(
                                    r.preservation_invariants[0] + " (evolved)",
                                ),
                            )
                            if r.requirement_id == subject else r
                            for r in system.reliability_requirements
                        ),
                    )
                )
        for dep in system.deployment_intents:
            if dep.deployment_id == subject:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        deployment_intents=tuple(
                            dataclasses.replace(
                                d,
                                rollback_invariants=(
                                    d.rollback_invariants[0] + " (evolved)",
                                ),
                            )
                            if d.deployment_id == subject else d
                            for d in system.deployment_intents
                        ),
                    )
                )
        for doc in system.documentation_intents:
            if doc.documentation_id == subject:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        documentation_intents=tuple(
                            dataclasses.replace(
                                d,
                                obligations=(d.obligations[0] + " (evolved)",),
                            )
                            if d.documentation_id == subject else d
                            for d in system.documentation_intents
                        ),
                    )
                )
        modules = []
        for module in system.modules:
            workflows = tuple(
                dataclasses.replace(w, description=f"{w.description} (evolved)")
                if w.id == subject else w
                for w in module.workflows
            )
            data_migrations = tuple(
                dataclasses.replace(
                    m,
                    postconditions=(m.postconditions[0] + " (evolved)",),
                )
                if m.migration_id == subject else m
                for m in module.data_migrations
            )
            temporal_constraints = tuple(
                dataclasses.replace(t, duration_ms=t.duration_ms + 1)
                if t.constraint_id == subject else t
                for t in module.temporal_constraints
            )
            module = dataclasses.replace(
                module,
                workflows=workflows,
                data_migrations=data_migrations,
                temporal_constraints=temporal_constraints,
            )
            modules.append(module)
        return isr.with_system(dataclasses.replace(system, modules=tuple(modules)))

    def remove_subject(self, isr: ISR, subject: str) -> ISR:
        """Ordinary evolution removing a semantic identity outright."""
        system = isr.system
        for capability in system.business_capabilities:
            if capability.capability_id == subject:
                return isr.with_system(
                    dataclasses.replace(
                        system,
                        business_capabilities=tuple(
                            c for c in system.business_capabilities
                            if c.capability_id != subject
                        ),
                    )
                )
        modules = []
        for module in system.modules:
            workflows = tuple(w for w in module.workflows if w.id != subject)
            module = dataclasses.replace(module, workflows=workflows)
            modules.append(module)
        return isr.with_system(dataclasses.replace(system, modules=tuple(modules)))

    def evaluate(
        self,
        parent: ISR,
        candidate: ISR,
        authorization: Any = None,
        authority: Any = None,
    ) -> ProtectionResult:
        evaluator = EvolutionProtectionEvaluator(
            authority=authority if authority is not None else self.authority
        )
        return evaluator.evaluate(
            parent, candidate, self.valid_policy(), authorization
        )

    def set_objective_weight(self, isr: ISR, objective_id: str, weight: float) -> ISR:
        return self.operator.respecify_objective(
            isr, objective_id=objective_id, weight=weight
        ).candidate_isr

    # -- gene addressing ------------------------------------------------------

    def all_gene_hashes(self, isr: ISR) -> dict[str, str]:
        """Every gene except the three evolution-policy gene classes."""
        return {
            path: h
            for path, h in gene_index(isr).items()
            if "evolution_objectives" not in path
            and "protected_regions" not in path
            and "evolution_policies" not in path
        }

    def gene_hashes(self, isr: ISR, domain: str) -> dict[str, str]:
        return {p: h for p, h in gene_index(isr).items() if domain in p}

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """("objective", oid) / ("region", rid) / ("policy", pid) /
        ("boundary", bid) / ("anchor", aid) / ("behavior", wf_id) /
        ("capability", cid)."""
        idx = gene_index(isr)
        kind, name = gene
        if kind == "objective":
            for oi, objective in enumerate(isr.system.evolution_objectives):
                if objective.objective_id == name:
                    return idx[f"system.evolution_objectives[{oi}]"]
        if kind == "region":
            for ri, region in enumerate(isr.system.protected_regions):
                if region.region_id == name:
                    return idx[f"system.protected_regions[{ri}]"]
        if kind == "policy":
            for pi, policy in enumerate(isr.system.evolution_policies):
                if policy.policy_id == name:
                    return idx[f"system.evolution_policies[{pi}]"]
        if kind == "boundary":
            for bi, boundary in enumerate(isr.system.architectural_boundaries):
                if boundary.boundary_id == name:
                    return idx[f"system.architectural_boundaries[{bi}]"]
        if kind == "anchor":
            for ai, anchor in enumerate(isr.system.testing_anchors):
                if anchor.anchor_id == name:
                    return idx[f"system.testing_anchors[{ai}]"]
        if kind == "capability":
            for ci, capability in enumerate(isr.system.business_capabilities):
                if capability.capability_id == name:
                    return idx[f"system.business_capabilities[{ci}]"]
        for mi, module in enumerate(isr.system.modules):
            if kind == "behavior":
                for wi, workflow in enumerate(module.workflows):
                    if workflow.id == name:
                        return idx[f"system.modules[{mi}].workflows[{wi}]"]
        return ""

    def has_gene(self, isr: ISR, gene: tuple) -> bool:
        return self.gene_hash(isr, gene) != ""

    # -- gates ----------------------------------------------------------------

    def run_gate(self, gate: str) -> GateResult:
        method = getattr(self, f"_gate_{gate}", None)
        if method is None:
            raise AssertionError(f"no implementation for gate '{gate}'")
        return method()

    def _gate_representation(self):
        system_fields = {f.name for f in dataclasses.fields(System)}
        ok = all(
            f in system_fields
            for f in ("evolution_objectives", "protected_regions", "evolution_policies")
        )
        try:
            self.valid_objective()
            self.valid_region()
            self.valid_policy()
        except EvolutionPolicyValidationError:
            ok = False
        measured_fields = {
            f.name
            for f in dataclasses.fields(EvolutionObjective)
            if any(bad in f.name.lower() for bad in (
                "value", "score", "fitness", "measurement", "metric", "result",
            ))
        }
        ok = ok and not measured_fields
        mechanism_fields = {
            f.name
            for f in dataclasses.fields(EvolutionPolicy)
            if any(bad in f.name.lower() for bad in (
                "population", "mutation_rate", "selection_algorithm",
                "optimizer", "algorithm",
            ))
        }
        ok = ok and not mechanism_fields
        dimensions = {d.value for d in ObjectiveDimension}
        ok = ok and dimensions == {
            "CORRECTNESS", "RELIABILITY", "PERFORMANCE", "COMPLEXITY", "COST",
            "SECURITY", "MAINTAINABILITY", "ADAPTABILITY",
        }
        kinds = {k.value for k in ProtectionKind}
        ok = ok and kinds == {"IMMUTABLE", "CONSTITUTIONAL", "PRESERVATION"}
        return _result(
            "representation",
            ok,
            f"three carriers on System; objective/region/policy constructs; "
            f"no measured-value fields: {measured_fields or 'none'}; "
            f"no mechanism fields: {mechanism_fields or 'none'}; "
            f"dimensions x8; protection kinds x3",
        )

    def _gate_canonicalization(self):
        isr = self.isr_without_policy()
        same = self.with_empty_policy(isr).content_hash == isr.content_hash
        return _result(
            "canonicalization",
            same,
            f"empty evolution-policy carriers identity-neutral: {same}",
        )

    def _gate_semantic_identity(self):
        isr = self.isr_with()
        with_policy = self.operator.add_objective(
            isr, self.valid_objective()
        ).candidate_isr
        with_policy = self.operator.add_region(
            with_policy, self.valid_region()
        ).candidate_isr
        step1 = with_policy.content_hash != isr.content_hash
        respecified = self.operator.respecify_objective(
            with_policy, objective_id="obj1",
            dimension=ObjectiveDimension.PERFORMANCE,
        ).candidate_isr
        step2 = respecified.content_hash != with_policy.content_hash
        removed = self.operator.remove_objective(
            respecified, objective_id="obj1"
        ).candidate_isr
        removed = self.operator.remove_region(
            removed, region_id="region1"
        ).candidate_isr
        step3 = removed.content_hash == isr.content_hash
        return _result(
            "semantic_identity",
            step1 and step2 and step3,
            f"add changes hash: {step1}; respecify changes hash: {step2}; "
            f"remove restores hash: {step3}",
        )

    def _gate_validation(self):
        ok = True
        for bad in (
            dict(objective_id="", dimension=ObjectiveDimension.COST),
            dict(region_id="", subject_refs=("w1",)),
            dict(policy_id=""),
        ):
            try:
                if "objective_id" in bad:
                    EvolutionObjective(
                        direction=ObjectiveDirection.MINIMIZE, **bad
                    )
                elif "region_id" in bad:
                    ProtectedRegion(
                        protection_kind=ProtectionKind.IMMUTABLE, **bad
                    )
                else:
                    EvolutionPolicy(**bad)
                ok = False
            except EvolutionPolicyValidationError:
                pass
        dangling_objective = self.isr_with(
            objectives=(
                dataclasses.replace(
                    self.valid_objective(), subject_refs=("no-such-gene",)
                ),
            ),
        )
        ok = ok and dangling_objective.validate_structure() is False
        dangling_policy = self.isr_with(
            objectives=(self.valid_objective(),),
            regions=(self.valid_region(),),
            policies=(
                self.valid_policy(objective_refs=("no-such-objective",)),
            ),
        )
        ok = ok and dangling_policy.validate_structure() is False
        empty_policy = self.isr_with(policies=(self.valid_policy((), ()),))
        ok = ok and empty_policy.validate_structure() is False
        ok = ok and self.isr_with_policy().validate_structure() is True
        return _result(
            "validation",
            ok,
            "construction contracts enforced; dangling subject/policy refs "
            "rejected pre-execution; policies that govern nothing rejected; "
            "valid declarations validate",
        )

    def _gate_locality(self):
        isr = self.isr_with()
        mutated = self.operator.add_objective(
            isr, self.valid_objective()
        ).candidate_isr
        result = self.locality_probe.probe(
            isr, mutated, "system.evolution_objectives[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.isr_with_policy()
        projected = project_evolution_policy(isr)
        deterministic = projected == project_evolution_policy(isr)
        reflects = any(
            o.get("objective_id") == "obj1"
            and o.get("dimension") == "RELIABILITY"
            and o.get("direction") == "MAXIMIZE"
            for o in projected.get("objectives", ())
        ) and any(
            r.get("region_id") == "region1"
            and r.get("protection_kind") == "IMMUTABLE"
            for r in projected.get("protected_regions", ())
        )
        no_scalar = evolution_policy_has_no_scalar_aggregation(projected)
        text = str(projected)
        coupled = [term for term in TECHNOLOGY_COUPLING_TERMS if term in text]
        mechanism = [term for term in EVOLUTION_MECHANISM_TERMS if term in text]
        return _result(
            "projection",
            deterministic and reflects and no_scalar and not coupled and not mechanism,
            f"deterministic: {deterministic}; reflects declarations: {reflects}; "
            f"no scalar aggregation: {no_scalar}; coupling terms: {coupled}; "
            f"mechanism terms: {mechanism}",
        )

    def _gate_compilation(self):
        isr = self.isr_with()
        mutated = self.operator.add_objective(
            isr, self.valid_objective()
        ).candidate_isr
        before = self.backend.async_resolution_module(isr.system.modules[0].workflows)
        after = self.backend.async_resolution_module(mutated.system.modules[0].workflows)
        compatible = before == after
        deterministic = self.backend.async_resolution_module(
            mutated.system.modules[0].workflows
        ) == after
        return _result(
            "compilation",
            compatible and deterministic,
            f"existing backend byte-identical with policy present: "
            f"{compatible}; deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.isr_with_policy()
        projected = project_evolution_policy(isr)
        observable = any(
            o.get("objective_id") == "obj1" for o in projected.get("objectives", ())
        ) and any(
            r.get("region_id") == "region1"
            for r in projected.get("protected_regions", ())
        )
        empty = project_evolution_policy(
            self.isr_without_policy()
        ) == {"objectives": (), "protected_regions": (), "policies": ()}
        return _result(
            "evidence",
            observable and empty,
            f"declarations observable in semantic projection: {observable}; "
            f"no policy -> empty projection: {empty}",
        )

    def _gate_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = EvolutionPolicyOperator(ledger=ledger)
            isr = self.isr_with()
            candidate = operator.add_objective(isr, self.valid_objective())
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "evolution_policy"
                and event.payload["subject_id"] == "obj1"
            )
            hashes_ok = (
                event is not None
                and event.payload["isr_hash_before"] == isr.content_hash
                and event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash
            )
        return _result(
            "lineage",
            chain_ok and attributed and hashes_ok,
            f"chain anchored: {chain_ok}; operator attribution: {attributed}; "
            f"before/after hashes: {hashes_ok}",
        )

    def _gate_reproducibility(self):
        isr = self.isr_with()
        c1 = self.operator.generate(isr, seed=7, population_size=1)
        c2 = self.operator.generate(isr, seed=7, population_size=1)
        same = len(c1) == len(c2) == 1 and all(
            a.candidate_id == b.candidate_id
            and a.candidate_isr.content_hash == b.candidate_isr.content_hash
            and a.mutation_delta == b.mutation_delta
            for a, b in zip(c1, c2)
        )
        return _result(
            "reproducibility",
            same,
            "same ISR + seed -> same candidate ids, hashes, and deltas",
        )

    def _gate_audit(self):
        result = self.audit.run(self.isr_with())
        by_id = {c.capability_id: c.status for c in result.capabilities}
        expressed = {cid for cid, s in by_id.items() if s is CapabilityStatus.EXPRESSED}
        partial = {cid for cid, s in by_id.items() if s is CapabilityStatus.PARTIAL}
        missing = {cid for cid, s in by_id.items() if s is CapabilityStatus.MISSING}
        post_expressed = {
            "behavior_transitions", "behavior_await_surface",
            "behavior_temporal_semantics", "business_capabilities",
            "data_migrations", "reliability_resilience",
            "architecture_boundaries", "requirements_acceptance_traceability",
            "deployment_rollout_rollback", "testing_anchoring",
            "documentation", "evolution_objectives_protected_regions",
        }
        post_partial = {
            "behavior_guards_actions", "behavior_state_semantics",
            "behavior_events_triggers", "behavior_error_states",
            "architecture_modules", "architecture_components",
            "architecture_interfaces_apis", "architecture_dependencies",
            "deployment_topology", "data_entities_schema",
            "data_persistence_consistency", "security_authorization",
            "security_authentication_trust", "requirements_constraints",
            "performance_scalability", "observability",
            "operational_policies", "evolution_lineage_provenance",
        }
        post_missing = set()
        matrix_ok = (
            expressed == post_expressed
            and partial == post_partial
            and missing == post_missing
            and CapabilityStatus.PROJECTED not in by_id.values()
        )
        # Exactly one row moved vs the pre-landing (R2.10.3-I) matrix 11/18/0/1.
        pre_expressed = post_expressed - {"evolution_objectives_protected_regions"}
        pre_missing = {"evolution_objectives_protected_regions"}
        one_row_only = (
            expressed - pre_expressed == {"evolution_objectives_protected_regions"}
            and missing == pre_missing - {"evolution_objectives_protected_regions"}
            and partial == post_partial
        )
        return _result(
            "audit",
            matrix_ok and one_row_only,
            f"summary: {result.summary()}; expected 12/18/0/0 with exactly "
            f"evolution_objectives_protected_regions: MISSING -> EXPRESSED "
            f"and the other 29 rows untouched",
        )


def _result(gate: str, passed: bool, evidence: str) -> GateResult:
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def j_harness() -> EvolutionPolicyPrimitiveHarness:
    return EvolutionPolicyPrimitiveHarness()


# =============================================================================
# PROOF 1 — No self-authorization (module boundary, not convention)
# =============================================================================

def test_operators_cannot_import_or_construct_constitutional_authorization():
    """The evolution package must never import from the governance module nor
    reference ConstitutionalAuthorization: the process being constrained does
    not control the constraint."""
    package = pathlib.Path(inspect.getfile(EvolutionPolicyOperator)).parent
    violations: list[str] = []
    for source in package.glob("*.py"):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.startswith("constitutional_architecture.governance"):
                    violations.append(
                        f"{source.name}: imports governance ({module})"
                    )
                if any(
                    alias.name == "ConstitutionalAuthorization"
                    for alias in node.names
                ):
                    violations.append(
                        f"{source.name}: imports ConstitutionalAuthorization"
                    )
            elif isinstance(node, ast.Import):
                if any(
                    alias.name.startswith("constitutional_architecture.governance")
                    for alias in node.names
                ):
                    violations.append(
                        f"{source.name}: imports governance"
                    )
    assert not violations, "evolution package crosses the governance boundary: " \
        + "; ".join(violations)


def test_ordinary_evolution_cannot_satisfy_constitutional(j_harness):
    isr = j_harness.isr_with_constitutional_region("region1")
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    result = j_harness.evaluate(isr, candidate, authorization=None)
    assert result.protected_ok is False
    assert result.kind is ProtectionKind.CONSTITUTIONAL


def test_wrong_region_authorization_rejected(j_harness):
    isr = j_harness.isr_with_constitutional_region("region1")
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    auth = j_harness.governance_authorization_for("region_OTHER")
    result = j_harness.evaluate(isr, candidate, authorization=auth)
    assert result.protected_ok is False
    assert result.kind is ProtectionKind.CONSTITUTIONAL


def test_unissued_authorization_rejected(j_harness):
    """An authorization that was never issued through the governance seam
    does not verify — its anchor is not in the governance registry."""
    isr = j_harness.isr_with_constitutional_region("region1")
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    from constitutional_architecture.governance.constitutional_authorization import (
        ConstitutionalAuthorization,
    )
    forged = ConstitutionalAuthorization(
        authorization_id="forged",
        region_ref="region1",
        subject_refs=("capability_pay",),
        rationale="forged",
        authorizer="ordinary-evolution",
        anchor_ref="not-in-registry",
    )
    result = j_harness.evaluate(isr, candidate, authorization=forged)
    assert result.protected_ok is False
    assert result.kind is ProtectionKind.CONSTITUTIONAL


def test_governance_issued_authorization_permits_constitutional_change(j_harness):
    isr = j_harness.isr_with_constitutional_region("region1")
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    auth = j_harness.governance_authorization_for("region1")
    assert j_harness.authority.chain_verifies is True
    result = j_harness.evaluate(isr, candidate, authorization=auth)
    assert result.protected_ok is True


# =============================================================================
# PROOF 2 — No fitness/objective conflation (structural + behavioral)
# =============================================================================

def test_objective_has_no_measured_value_fields():
    fields = {f.name for f in dataclasses.fields(EvolutionObjective)}
    measured = {
        f for f in fields
        if any(bad in f.lower() for bad in (
            "value", "score", "fitness", "measurement", "metric", "result",
        ))
    }
    assert not measured, f"objective carries a measured-value field: {measured}"


def test_weight_change_cannot_produce_scalar_objective(j_harness):
    """Changing objective weights changes per-objective declarations only —
    the projection can never contain a combined weighted-scalar artifact."""
    isr = j_harness.isr_with_policy()
    mutated = j_harness.set_objective_weight(isr, "obj1", 5.0)
    projection = project_evolution_policy(mutated)
    assert evolution_policy_has_no_scalar_aggregation(projection) is True
    assert float(projection["objectives"][0]["weight"]) == 5.0  # per-objective only


def test_objective_has_no_measurement_artifact(j_harness):
    projected = project_evolution_policy(j_harness.isr_with_policy())
    text = str(projected).lower()
    assert "fitness" not in text
    assert "score" not in text
    assert "measured" not in text


def test_lexicographic_tiers_never_weighted_sum(j_harness):
    """A weighted scalar is structurally impossible: the ISR projection has no
    mechanism to combine objectives."""
    isr = j_harness.isr_with_policy()
    mutated = j_harness.set_objective_weight(isr, "obj1", 0.3)
    projection = project_evolution_policy(mutated)
    objectives = projection["objectives"]
    assert len(objectives) == 1
    assert objectives[0]["weight"] == "0.3"
    assert float(objectives[0]["weight"]) == 0.3
    assert evolution_policy_has_no_scalar_aggregation(projection) is True


def test_constitutional_objective_subject_removal_is_infeasible(j_harness):
    """Clarification #2: constitutional objectives are feasibility gates —
    a candidate that removes a constitutional objective's subject is
    INFEASIBLE even though no region mentions it (the presence gate)."""
    isr = j_harness.isr_with(
        objectives=(
            j_harness.valid_objective(tier=ObjectiveTier.CONSTITUTIONAL),
        ),
        # the region protects a DIFFERENT subject — the gate that fires is
        # the objective presence gate, not a region
        regions=(
            j_harness.valid_region(
                ProtectionKind.IMMUTABLE, subject_refs=("w1",)
            ),
        ),
        policies=(j_harness.valid_policy(),),
    )
    candidate = j_harness.remove_subject(isr, "capability_pay")
    result = j_harness.evaluate(isr, candidate)
    assert result.protected_ok is False
    assert result.kind is None  # objective presence gate, not a region
    assert "constitutional objective" in result.notes[0]


def test_optimization_objective_does_not_gate_presence(j_harness):
    """OPTIMIZATION-tier objectives are preferences, not gates: subject
    presence is not a feasibility condition for them."""
    isr = j_harness.isr_with_policy()
    candidate = j_harness.ordinary_operator_mutation_into(isr, "w1")
    result = j_harness.evaluate(isr, candidate)
    assert result.protected_ok is True


# =============================================================================
# PROOF 3 — No authority duplication between E/H/J
# =============================================================================

def test_j_region_mutation_never_touches_boundary_or_anchor_genes(j_harness):
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(j_harness.valid_region(),),
        policies=(j_harness.valid_policy(),),
    )
    before = j_harness.gene_hash(isr, ("boundary", "b1"))
    anchor_before = j_harness.gene_hash(isr, ("anchor", "anchor1"))
    mutated = j_harness.operator.respecify_region(
        isr,
        region_id="region1",
        protection_kind=ProtectionKind.PRESERVATION,
        invariants=(
            PreservationInvariant(
                kind=ObligationKind.PRESENCE,
                subject_refs=("capability_pay",),
                statement="the capability must remain present",
            ),
        ),
    ).candidate_isr
    assert j_harness.gene_hash(mutated, ("boundary", "b1")) == before
    assert j_harness.gene_hash(mutated, ("anchor", "anchor1")) == anchor_before
    assert j_harness.gene_hash(mutated, ("region", "region1")) != \
        j_harness.gene_hash(isr, ("region", "region1"))


def test_boundary_and_anchor_mutations_never_touch_region_genes(j_harness):
    """The reverse: E/H mutations leave J's region gene byte-identical."""
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(j_harness.valid_region(subject_refs=("w1",)),),
        policies=(j_harness.valid_policy(),),
    )
    region_before = j_harness.gene_hash(isr, ("region", "region1"))
    objective_before = j_harness.gene_hash(isr, ("objective", "obj1"))
    modules = []
    for module in isr.system.modules:
        workflows = tuple(
            dataclasses.replace(w, description="evolved by ordinary evolution")
            for w in module.workflows
        )
        module = dataclasses.replace(module, workflows=workflows)
        modules.append(module)
    evolved = isr.with_system(dataclasses.replace(isr.system, modules=tuple(modules)))
    assert j_harness.gene_hash(evolved, ("region", "region1")) == region_before
    assert j_harness.gene_hash(evolved, ("objective", "obj1")) == objective_before


def test_j_never_reimplements_boundary_or_anchor_mechanics(j_harness):
    """J's constructs carry no boundary/anchor mechanics — a region declares
    participation, never enforcement structure."""
    fields = {f.name for f in dataclasses.fields(ProtectedRegion)}
    assert "forbidden_dependency_refs" not in fields  # E's field
    assert "protection_policy" not in fields  # H's field
    assert "obligation_refs" not in fields  # H's field
    assert "evidence_requirements" not in fields  # H's field


# =============================================================================
# The feasibility gate — IMMUTABLE / CONSTITUTIONAL / PRESERVATION
# =============================================================================

def test_immutable_region_rejects_any_touch(j_harness):
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(j_harness.valid_region(ProtectionKind.IMMUTABLE),),
        policies=(j_harness.valid_policy(),),
    )
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    result = j_harness.evaluate(isr, candidate)
    assert result.protected_ok is False
    assert result.kind is ProtectionKind.IMMUTABLE
    assert result.affected_subjects == ("capability_pay",)


def test_immutable_region_untouched_subject_passes(j_harness):
    """The gate is subject-relative: evolution elsewhere in the candidate is
    untouched by the region."""
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(j_harness.valid_region(ProtectionKind.IMMUTABLE),),
        policies=(j_harness.valid_policy(),),
    )
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    evaluator = EvolutionProtectionEvaluator(authority=j_harness.authority)
    policy = j_harness.valid_policy(region_refs=())
    result = evaluator.evaluate(isr, candidate, policy)
    assert result.protected_ok is True


def test_preservation_presence_invariant_holds_on_change(j_harness):
    """PRESERVATION allows change that keeps the invariant: PRESENCE of the
    subject is preserved even though the subject's implementation changed."""
    isr = j_harness.isr_with_preservation_region()
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    result = j_harness.evaluate(isr, candidate)
    assert result.protected_ok is True


def test_preservation_invariant_fails_on_removal(j_harness):
    """PRESENCE fails when the diff removes the subject entirely."""
    isr = j_harness.isr_with_preservation_region()
    removed = isr.with_system(
        dataclasses.replace(
            isr.system,
            business_capabilities=tuple(
                c for c in isr.system.business_capabilities
                if c.capability_id != "capability_pay"
            ),
        )
    )
    result = j_harness.evaluate(isr, removed)
    assert result.protected_ok is False
    assert result.kind is ProtectionKind.PRESERVATION


def test_preservation_threshold_invariant(j_harness):
    """THRESHOLD bounds how many of the invariant's subjects may change."""
    region = ProtectedRegion(
        region_id="region1",
        subject_refs=("w1",),
        protection_kind=ProtectionKind.PRESERVATION,
        invariants=(
            PreservationInvariant(
                kind=ObligationKind.THRESHOLD,
                subject_refs=("w1",),
                statement="at most one workflow may change",
                bound=1.0,
            ),
        ),
    )
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(region,),
        policies=(j_harness.valid_policy(),),
    )
    candidate = j_harness.ordinary_operator_mutation_into(isr, "w1")
    result = j_harness.evaluate(isr, candidate)
    assert result.protected_ok is True
    zero_tolerance = dataclasses.replace(
        region,
        invariants=(
            dataclasses.replace(region.invariants[0], bound=0.0),
        ),
    )
    strict = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(zero_tolerance,),
        policies=(j_harness.valid_policy(),),
    )
    result2 = j_harness.evaluate(strict, candidate)
    assert result2.protected_ok is False
    assert result2.kind is ProtectionKind.PRESERVATION


def test_preservation_threshold_requires_bound(j_harness):
    with pytest.raises(EvolutionPolicyValidationError):
        PreservationInvariant(
            kind=ObligationKind.THRESHOLD,
            subject_refs=("w1",),
            statement="threshold without bound",
        )


def test_preservation_invariants_only_for_preservation(j_harness):
    with pytest.raises(EvolutionPolicyValidationError):
        ProtectedRegion(
            region_id="x",
            subject_refs=("w1",),
            protection_kind=ProtectionKind.IMMUTABLE,
            invariants=(
                PreservationInvariant(
                    kind=ObligationKind.PRESENCE,
                    subject_refs=("w1",),
                    statement="s",
                ),
            ),
        )


def test_preservation_requires_an_invariant(j_harness):
    with pytest.raises(EvolutionPolicyValidationError):
        ProtectedRegion(
            region_id="x",
            subject_refs=("w1",),
            protection_kind=ProtectionKind.PRESERVATION,
            invariants=(),
        )


def test_gate_is_feasibility_not_penalty(j_harness):
    """The crucial constitutional boundary: a violating candidate is
    INFEASIBLE regardless of any fitness it might carry — protection is a
    hard gate, not a penalty term some objective could overwhelm."""
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(j_harness.valid_region(ProtectionKind.IMMUTABLE),),
        policies=(j_harness.valid_policy(),),
    )
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    result = j_harness.evaluate(isr, candidate)
    assert result.protected_ok is False
    assert result.kind is ProtectionKind.IMMUTABLE
    # No objective can rescue it: a candidate is feasible ONLY if every
    # region it touches is satisfied.
    evaluator = EvolutionProtectionEvaluator(authority=j_harness.authority)
    policy_with_priority = j_harness.valid_policy()
    result_with_objective = evaluator.evaluate(isr, candidate, policy_with_priority)
    assert result_with_objective.protected_ok is False


def test_evaluation_is_diff_relative(j_harness):
    """Constraint #3: PRESERVATION operates on the semantic diff only —
    EvolutionDiff(added/removed/changed/ordering) is the evaluator's only
    input; affected_subjects is a projection output, not a J-owned
    primitive. Subjects are semantic identity ids, resolved from the gene
    index."""
    policy = j_harness.valid_policy(region_refs=("region1",))
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(
            j_harness.valid_region(
                ProtectionKind.IMMUTABLE, subject_refs=("w1",)
            ),
        ),
        policies=(policy,),
    )
    candidate = j_harness.ordinary_operator_mutation_into(isr, "w1")
    evaluator = EvolutionProtectionEvaluator(authority=j_harness.authority)
    diff = evaluator._semantic_diff(isr, candidate)
    assert isinstance(diff, EvolutionDiff)
    assert "w1" in diff.changed_subjects
    assert diff.affected_subjects == (
        diff.added_subjects | diff.removed_subjects | diff.changed_subjects
    )
    result = evaluator.evaluate(isr, candidate, policy)
    assert result.protected_ok is False
    assert result.affected_subjects == ("w1",)  # projection output


# =============================================================================
# E/H interaction — protection by reference, no ownership transfer
# =============================================================================

def test_protected_region_protects_boundary_by_reference(j_harness):
    """A region may protect a boundary identity; E stays authoritative for
    the boundary's mechanics (J only declares participation)."""
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(
            j_harness.valid_region(
                ProtectionKind.IMMUTABLE, subject_refs=("b1",)
            ),
        ),
        policies=(j_harness.valid_policy(),),
    )
    candidate = isr.with_system(
        dataclasses.replace(
            isr.system,
            architectural_boundaries=(
                dataclasses.replace(
                    isr.system.architectural_boundaries[0], protected=True
                ),
            ),
        )
    )
    result = j_harness.evaluate(isr, candidate)
    assert result.protected_ok is False
    assert result.kind is ProtectionKind.IMMUTABLE


def test_protected_region_protects_testing_anchor_by_reference(j_harness):
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(
            j_harness.valid_region(
                ProtectionKind.IMMUTABLE, subject_refs=("anchor1",)
            ),
        ),
        policies=(j_harness.valid_policy(),),
    )
    candidate = isr.with_system(
        dataclasses.replace(
            isr.system,
            testing_anchors=(
                dataclasses.replace(
                    isr.system.testing_anchors[0],
                    protection_policy=ProtectionPolicy.PROTECTED,
                ),
            ),
        )
    )
    result = j_harness.evaluate(isr, candidate)
    assert result.protected_ok is False
    assert result.kind is ProtectionKind.IMMUTABLE


def test_region_respects_existing_boundary_mechanics(j_harness):
    """E's own protected-boundary violation is still E's violation —
    J adds a layer, it does not replace or soften E."""
    from constitutional_architecture.validators import ConstitutionalViolation
    from tiannara.application.evolution.boundary_mutation import BoundaryOperator
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(j_harness.valid_region(),),
        policies=(j_harness.valid_policy(),),
    )
    protected = isr.with_system(
        dataclasses.replace(
            isr.system,
            architectural_boundaries=(
                dataclasses.replace(
                    isr.system.architectural_boundaries[0], protected=True
                ),
            ),
        )
    )
    with pytest.raises(ConstitutionalViolation):
        BoundaryOperator().remove_boundary(
            protected, boundary_id="b1"
        )


# =============================================================================
# Non-inference — protection is declared, never guessed
# =============================================================================

def test_protection_never_inferred_from_structure(j_harness):
    """Nothing about a protected region is inferred from implementation
    structure: with no declared region, the same candidate passes the gate."""
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(),
        policies=(j_harness.valid_policy(region_refs=()),),
    )
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    result = j_harness.evaluate(isr, candidate)
    assert result.protected_ok is True


def test_no_protection_for_undeclared_identities(j_harness):
    """J protects declared semantic identities by reference only — an
    undeclared identity is unprotected, no implicit guarantees."""
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(),),
        regions=(j_harness.valid_region(),),
        policies=(j_harness.valid_policy(),),
    )
    candidate = j_harness.ordinary_operator_mutation_into(isr, "capability_pay")
    evaluator = EvolutionProtectionEvaluator(authority=j_harness.authority)
    policy = j_harness.valid_policy(region_refs=("region_undeclared",))
    result = evaluator.evaluate(isr, candidate, policy)
    assert result.protected_ok is True


# =============================================================================
# Mechanism lint asymmetry
# =============================================================================

def test_mechanism_lint_passes_semantic_form(j_harness):
    assert_evolution_technology_agnostic(
        EvolutionPolicy(
            policy_id="semantic",
            objective_refs=("obj1",),
            protected_region_refs=("region1",),
            selection_constraints=("maximize reliability",),
        )
    )


def test_mechanism_lint_rejects_engine_mechanics(j_harness):
    with pytest.raises(EvolutionPolicyValidationError):
        assert_evolution_technology_agnostic(
            EvolutionPolicy(
                policy_id="coupled",
                objective_refs=("obj1",),
                protected_region_refs=("region1",),
                selection_constraints=(
                    "tournament selection with population_size 100",),
            )
        )


def test_mechanism_lint_asymmetric_on_direction(j_harness):
    """maximize/minimize pass; optimizer/algorithm/fitness terms fail."""
    ok = EvolutionPolicy(
        policy_id="p1",
        objective_refs=("obj1",),
        protected_region_refs=("region1",),
        selection_constraints=("maximize reliability", "minimize cost"),
    )
    assert mechanism_hits(ok) == ()
    bad = EvolutionPolicy(
        policy_id="p2",
        objective_refs=("obj1",),
        protected_region_refs=("region1",),
        selection_constraints=("use the nsga optimizer",),
    )
    assert mechanism_hits(bad) != ()
    with pytest.raises(EvolutionPolicyValidationError):
        assert_evolution_technology_agnostic(bad)


# =============================================================================
# Validation specifics
# =============================================================================

def test_duplicate_objective_ids_rejected(j_harness):
    isr = j_harness.isr_with(
        objectives=(j_harness.valid_objective(), j_harness.valid_objective()),
    )
    assert isr.validate_structure() is False


def test_duplicate_region_ids_rejected(j_harness):
    isr = j_harness.isr_with(
        regions=(j_harness.valid_region(), j_harness.valid_region()),
    )
    assert isr.validate_structure() is False


def test_policy_governing_nothing_rejected(j_harness):
    isr = j_harness.isr_with(policies=(j_harness.valid_policy((), ()),))
    assert isr.validate_structure() is False


def test_empty_carriers_identity_neutral(j_harness):
    isr = j_harness.isr_with()
    assert j_harness.with_empty_policy(isr).content_hash == isr.content_hash


def test_subject_refs_resolve_across_ten_domains(j_harness):
    """The identity space: capabilities, requirements, boundaries, testing
    anchors, reliability requirements, deployment intents, migrations,
    temporal constraints, documentation, behaviors."""
    ids = {
        "capability_pay", "req.cancel", "b1", "anchor1", "rr1", "dep1",
        "m1", "t1.deadline", "doc1", "w1",
    }
    for subject in ids:
        isr = j_harness.isr_with(
            objectives=(j_harness.valid_objective(),),
            regions=(
                j_harness.valid_region(
                    ProtectionKind.IMMUTABLE, subject_refs=(subject,)
                ),
            ),
            policies=(j_harness.valid_policy(),),
        )
        assert isr.validate_structure() is True, f"subject '{subject}' unresolved"


# =============================================================================
# The gate protocol + the audit, mechanically one row
# =============================================================================

def test_eleven_gates_all_pass(j_harness):
    results = assert_all_gates(j_harness)
    assert len(results) == 11
    assert all(r.passed for r in results)


def test_audit_moves_exactly_one_row(j_harness):
    result = j_harness.audit.run(j_harness.isr_with())
    by_id = {c.capability_id: c.status for c in result.capabilities}
    expressed = {cid for cid, s in by_id.items() if s is CapabilityStatus.EXPRESSED}
    missing = {cid for cid, s in by_id.items() if s is CapabilityStatus.MISSING}
    # Pre-landing (R2.10.3-I) matrix: 11/18/0/1.
    pre_expressed = {
        "behavior_transitions", "behavior_await_surface",
        "behavior_temporal_semantics", "business_capabilities",
        "data_migrations", "reliability_resilience",
        "architecture_boundaries", "requirements_acceptance_traceability",
        "deployment_rollout_rollback", "testing_anchoring",
        "documentation",
    }
    pre_missing = {
        "evolution_objectives_protected_regions",
    }
    moved_rows = {}
    for cid in pre_expressed | pre_missing:
        before = "EXPRESSED" if cid in pre_expressed else "MISSING"
        after = "EXPRESSED" if cid in expressed else "MISSING"
        if before != after:
            moved_rows[cid] = (before, after)
    assert moved_rows == {
        "evolution_objectives_protected_regions": ("MISSING", "EXPRESSED")
    }
    assert (len(expressed), 18, 0, len(missing)) == (12, 18, 0, 0)  # NOT 11/18/0/1