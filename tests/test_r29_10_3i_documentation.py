"""R2.10.3-I — documentation: intent, never artifact.

Documentation as an ISR-owned SEMANTIC artifact — NOT generated Markdown,
HTML, source comments, or diagrams. A DocumentationIntent declares what must
be documented, for whom, and why; the realization is a compiler/backend
concern and never part of this primitive.

Direction is one-way: **ISR semantics → documentation intent → realization**.
The constraint this slice holds firm on: documentation must NOT become a
second source of truth. That non-authority is made STRUCTURAL — the
construct carries no override/redefine/replace/author field (there is no
mechanism to author anything but its own intent), and locality is proven
both ways: changing documentation moves only the documentation gene; a
subject's implementation evolves while the documentation gene holds.

Two-layer defense as always: structural exclusion (no format/path/template/
generator field anywhere) + DOCUMENTATION_MECHANISM_TERMS lint over the
canonical semantic form (purpose=OPERATIONAL_REFERENCE passes;
render_markdown_via_mkdocs fails).

The audit gate embeds the pre-landing matrix (10/18/0/2 — after R2.10.3-H)
and asserts the delta is exactly {documentation: MISSING -> EXPRESSED} ->
11/18/0/1.
"""
from __future__ import annotations

import dataclasses
import tempfile
from typing import Any

import pytest

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
    DocumentationValidationError,
    Entity,
    FailureMode,
    ISR,
    Interface,
    InterfaceType,
    Module,
    ObligationKind,
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
from constitutional_architecture.isr.semantics.documentation import (
    DOCUMENTATION_MECHANISM_TERMS,
    assert_documentation_technology_agnostic,
    documentation_mechanism_hits as mechanism_hits,
    project_documentation_intents,
)
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.evolution.documentation_mutation import DocumentationOperator
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


class DocumentationPrimitiveHarness:
    """The eleven-gate harness for documentation."""

    primitive_id = "documentation"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = DocumentationOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()

    # -- recipes ------------------------------------------------------------

    def valid_doc(
        self,
        purpose: DocumentationPurpose = DocumentationPurpose.OPERATIONAL_REFERENCE,
        audience: DocumentationAudience = DocumentationAudience.DEVELOPER,
    ) -> DocumentationIntent:
        return DocumentationIntent(
            documentation_id="doc1",
            subject_refs=("capability_pay",),
            purpose=purpose,
            audience=audience,
            obligations=("the capability's declared behavior must be documented",),
        )

    def isr_with(
        self,
        documentation: tuple[DocumentationIntent, ...] = (),
        with_deployment: bool = True,
        with_requirement: bool = True,
        with_boundary: bool = True,
        with_reliability: bool = True,
        with_migration: bool = True,
        with_temporal: bool = True,
        with_capability: bool = True,
        with_anchor: bool = True,
    ) -> ISR:
        temporal_constraints = (
            (
                TemporalConstraint(
                    constraint_id="t1.deadline",
                    kind=TemporalConstraintKind.TRANSITION_DEADLINE,
                    target_ref="w1-t1",
                    duration_ms=250,
                ),
            )
            if with_temporal
            else ()
        )
        migrations = (
            (
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
            )
            if with_migration
            else ()
        )
        capabilities = (
            (
                BusinessCapability(
                    capability_id="capability_pay",
                    intent="process a payment",
                    behavior_refs=("w1",),
                    interface_refs=("i1",),
                ),
            )
            if with_capability
            else ()
        )
        reliability_requirements = (
            (
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
            )
            if with_reliability
            else ()
        )
        boundaries = (
            (
                ArchitecturalBoundary(
                    boundary_id="b1",
                    member_refs=("m",),
                    forbidden_dependency_refs=(),
                    protected=False,
                    crossing_invariants=("no cross without declared intent",),
                ),
            )
            if with_boundary
            else ()
        )
        requirements = (
            (
                Requirement(
                    requirement_id="req.cancel",
                    statement="Cancellation must become effective before settlement",
                    target_refs=("capability_pay",),
                    acceptance_refs=("crit.cancel",),
                    constraint_refs=("w1",),
                ),
            )
            if with_requirement
            else ()
        )
        criteria = (
            (
                AcceptanceCriterion(
                    criterion_id="crit.cancel",
                    obligation="Order cancellation must become effective before settlement",
                    kind=ObligationKind.ORDERING,
                    subject_refs=("w1",),
                ),
            )
            if with_requirement
            else ()
        )
        intents = (
            (
                DeploymentIntent(
                    deployment_id="dep1",
                    target_refs=("capability_pay",),
                    rollout_strategy=RolloutStrategy.CANARY,
                    rollback_required=True,
                    rollback_target_ref="capability_pay",
                    rollback_invariants=("payment state preserved",),
                ),
            )
            if with_deployment
            else ()
        )
        anchors = (
            (
                TestingAnchor(
                    anchor_id="anchor1",
                    subject_refs=("w1",),
                    obligation_refs=("crit.cancel",),
                    evidence_requirements=(
                        "ORDERING before authorization demonstrated",),
                    protection_policy=ProtectionPolicy.EVOLVABLE,
                    authority=AnchorAuthority.DERIVED,
                ),
            )
            if with_anchor
            else ()
        )
        return ISR(
            system=System(
                id="doc-sys",
                name="DocumentationSystem",
                modules=(
                    Module(
                        id="m",
                        name="M",
                        entities=tuple(_entity(eid) for eid in ("e1", "e2")),
                        workflows=(_workflow("w1", "op_w1"),),
                        interfaces=(
                            Interface(id="i1", name="i1", interface_type=InterfaceType.REST),
                        ),
                        temporal_constraints=temporal_constraints,
                        data_migrations=migrations,
                    ),
                ),
                business_capabilities=capabilities,
                reliability_requirements=reliability_requirements,
                architectural_boundaries=boundaries,
                requirements=requirements,
                acceptance_criteria=criteria,
                deployment_intents=intents,
                testing_anchors=anchors,
                documentation_intents=documentation,
            )
        )

    def isr_without_documentation(self) -> ISR:
        return self.isr_with()

    def isr_with_documentation_of(self, subject_id: str) -> ISR:
        return self.isr_with(
            documentation=(
                dataclasses.replace(
                    self.valid_doc(), subject_refs=(subject_id,)
                ),
            )
        )

    def with_empty_documentation(self, isr: ISR) -> ISR:
        return isr.with_system(
            dataclasses.replace(isr.system, documentation_intents=())
        )

    def respecify_documentation(
        self,
        isr: ISR,
        documentation_id: str,
        purpose: DocumentationPurpose,
    ) -> ISR:
        return self.operator.respecify_documentation(
            isr,
            documentation_id=documentation_id,
            purpose=purpose,
        ).candidate_isr

    def evolve_subject(self, isr: ISR, subject_id: str) -> ISR:
        """Mutate a subject's implementation while its identity is stable."""
        modules = []
        for module in isr.system.modules:
            workflows = tuple(
                dataclasses.replace(
                    w, description=f"implementation evolved under {subject_id}"
                )
                if w.id == subject_id
                else w
                for w in module.workflows
            )
            module = dataclasses.replace(module, workflows=workflows)
            modules.append(module)
        return isr.with_system(
            dataclasses.replace(isr.system, modules=tuple(modules))
        )

    # -- gene addressing ------------------------------------------------------

    def all_gene_hashes(self, isr: ISR) -> dict[str, str]:
        """Every gene except the documentation gene class."""
        return {
            path: h
            for path, h in gene_index(isr).items()
            if "documentation_intents" not in path
        }

    def gene_hashes(self, isr: ISR, domain: str) -> dict[str, str]:
        return {p: h for p, h in gene_index(isr).items() if domain in p}

    def subject_genes_identical(self, a: ISR, b: ISR) -> bool:
        return self.all_gene_hashes(a) == self.all_gene_hashes(b)

    def documentation_gene(self, isr: ISR) -> str:
        idx = gene_index(isr)
        for di in range(len(isr.system.documentation_intents)):
            path = f"system.documentation_intents[{di}]"
            if isr.system.documentation_intents[di].documentation_id == "doc1":
                return idx[path]
        return ""

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """("documentation", did) / ("capability", cid) / ("module", mid) /
        ("behavior", wf_id) / ("boundary", bid) / ("reliability", rid) /
        ("requirement", rid) / ("criterion", cid) / ("deployment", did) /
        ("anchor", aid) / ("migration", mid) / ("temporal", cid)."""
        idx = gene_index(isr)
        kind, name = gene
        if kind == "documentation":
            for di, doc in enumerate(isr.system.documentation_intents):
                if doc.documentation_id == name:
                    return idx[f"system.documentation_intents[{di}]"]
        if kind == "anchor":
            for ai, anchor in enumerate(isr.system.testing_anchors):
                if anchor.anchor_id == name:
                    return idx[f"system.testing_anchors[{ai}]"]
        if kind == "capability":
            for ci, capability in enumerate(isr.system.business_capabilities):
                if capability.capability_id == name:
                    return idx[f"system.business_capabilities[{ci}]"]
        if kind == "boundary":
            for bi, boundary in enumerate(isr.system.architectural_boundaries):
                if boundary.boundary_id == name:
                    return idx[f"system.architectural_boundaries[{bi}]"]
        if kind == "reliability":
            for ri, requirement in enumerate(isr.system.reliability_requirements):
                if requirement.requirement_id == name:
                    return idx[f"system.reliability_requirements[{ri}]"]
        if kind == "requirement":
            for ri, requirement in enumerate(isr.system.requirements):
                if requirement.requirement_id == name:
                    return idx[f"system.requirements[{ri}]"]
        if kind == "criterion":
            for ci, criterion in enumerate(isr.system.acceptance_criteria):
                if criterion.criterion_id == name:
                    return idx[f"system.acceptance_criteria[{ci}]"]
        if kind == "deployment":
            for di, intent in enumerate(isr.system.deployment_intents):
                if intent.deployment_id == name:
                    return idx[f"system.deployment_intents[{di}]"]
        for mi, module in enumerate(isr.system.modules):
            if kind == "module":
                if module.id == name:
                    return idx[f"system.modules[{mi}]"]
            if kind == "behavior":
                for wi, workflow in enumerate(module.workflows):
                    if workflow.id == name:
                        return idx[f"system.modules[{mi}].workflows[{wi}]"]
            if kind == "temporal":
                for ti, constraint in enumerate(module.temporal_constraints):
                    if constraint.constraint_id == name:
                        return idx[
                            f"system.modules[{mi}].temporal_constraints[{ti}]"
                        ]
            if kind == "migration":
                for di, migration in enumerate(module.data_migrations):
                    if migration.migration_id == name:
                        return idx[f"system.modules[{mi}].data_migrations[{di}]"]
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
        ok = "documentation_intents" in system_fields
        try:
            self.valid_doc()
        except DocumentationValidationError:
            ok = False
        realization_fields = {
            f.name
            for f in dataclasses.fields(DocumentationIntent)
            if any(bad in f.name.lower() for bad in (
                "markdown", "html", "template", "path", "format", "render",
                "generator",
            ))
        }
        ok = ok and not realization_fields
        authority_fields = {
            f.name
            for f in dataclasses.fields(DocumentationIntent)
            if any(bad in f.name.lower() for bad in (
                "override", "redefine", "replace", "author", "source_of",
            ))
        }
        ok = ok and not authority_fields
        purposes = {p.value for p in DocumentationPurpose}
        ok = ok and purposes == {
            "OPERATIONAL_REFERENCE", "ARCHITECTURAL_RATIONALE", "API_CONTRACT",
            "ONBOARDING", "COMPLIANCE",
        }
        audiences = {a.value for a in DocumentationAudience}
        ok = ok and audiences == {
            "OPERATOR", "DEVELOPER", "ARCHITECT", "SECURITY_AUDITOR", "END_USER",
        }
        return _result(
            "representation",
            ok,
            f"System.documentation_intents carrier; DocumentationIntent "
            f"(subjects/purpose/audience/obligations); Purpose x5 + "
            f"Audience x5; no realization fields: {realization_fields or 'none'}; "
            f"no authority fields: {authority_fields or 'none'}",
        )

    def _gate_canonicalization(self):
        isr = self.isr_without_documentation()
        same = self.with_empty_documentation(isr).content_hash == isr.content_hash
        return _result(
            "canonicalization",
            same,
            f"empty documentation carrier identity-neutral: {same}",
        )

    def _gate_semantic_identity(self):
        isr = self.isr_with()
        with_doc = self.operator.add_documentation(
            isr, self.valid_doc()
        ).candidate_isr
        step1 = with_doc.content_hash != isr.content_hash
        respecified = self.respecify_documentation(
            with_doc, "doc1", DocumentationPurpose.COMPLIANCE
        )
        step2 = respecified.content_hash != with_doc.content_hash
        removed = self.operator.remove_documentation(
            respecified, documentation_id="doc1"
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
            dict(documentation_id="", subject_refs=("w1",)),
            dict(documentation_id="d", subject_refs=()),
        ):
            try:
                DocumentationIntent(
                    purpose=DocumentationPurpose.ONBOARDING,
                    audience=DocumentationAudience.DEVELOPER,
                    **bad,
                )
                ok = False
            except DocumentationValidationError:
                pass
        dangling_subject = self.isr_with(
            documentation=(
                dataclasses.replace(
                    self.valid_doc(), subject_refs=("no-such-gene",)
                ),
            ),
        )
        ok = ok and dangling_subject.validate_structure() is False
        duplicate = self.isr_with(
            documentation=(self.valid_doc(), self.valid_doc()),
        )
        ok = ok and duplicate.validate_structure() is False
        ok = ok and self.isr_with_documentation_of("capability_pay").validate_structure() is True
        return _result(
            "validation",
            ok,
            "construction contracts enforced; dangling subject refs rejected "
            "pre-execution; duplicate ids rejected; valid intent validates",
        )

    def _gate_locality(self):
        isr = self.isr_with()
        mutated = self.operator.add_documentation(
            isr, self.valid_doc()
        ).candidate_isr
        result = self.locality_probe.probe(
            isr, mutated, "system.documentation_intents[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.isr_with_documentation_of("capability_pay")
        projected = project_documentation_intents(isr)
        deterministic = projected == project_documentation_intents(isr)
        reflects = any(
            d.get("documentation_id") == "doc1"
            and "capability_pay" in d.get("subject_refs", [])
            and d.get("purpose") == "OPERATIONAL_REFERENCE"
            and d.get("audience") == "DEVELOPER"
            for d in projected
        )
        text = str(projected)
        coupled = [term for term in TECHNOLOGY_COUPLING_TERMS if term in text]
        mechanism = [term for term in DOCUMENTATION_MECHANISM_TERMS if term in text]
        return _result(
            "projection",
            deterministic and reflects and not coupled and not mechanism,
            f"deterministic: {deterministic}; reflects intent: {reflects}; "
            f"coupling terms: {coupled}; mechanism terms: {mechanism}",
        )

    def _gate_compilation(self):
        isr = self.isr_with()
        mutated = self.operator.add_documentation(
            isr, self.valid_doc()
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
            f"existing backend byte-identical with documentation present: "
            f"{compatible}; deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.isr_with_documentation_of("capability_pay")
        observable = any(
            d.get("documentation_id") == "doc1"
            for d in project_documentation_intents(isr)
        )
        empty = project_documentation_intents(
            self.isr_without_documentation()
        ) == ()
        return _result(
            "evidence",
            observable and empty,
            f"intent observable in semantic projection: {observable}; "
            f"no intents -> empty projection: {empty}",
        )

    def _gate_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = DocumentationOperator(ledger=ledger)
            isr = self.isr_with()
            candidate = operator.add_documentation(isr, self.valid_doc())
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "documentation"
                and event.payload["subject_id"] == "doc1"
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
            "documentation",
            "evolution_objectives_protected_regions",  # R2.10.3-J
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
        post_missing: set[str] = set()
        matrix_ok = (
            expressed == post_expressed
            and partial == post_partial
            and missing == post_missing
            and CapabilityStatus.PROJECTED not in by_id.values()
        )
        # Exactly one row moved vs the pre-landing (R2.10.3-I) matrix 11/18/0/1.
        pre_expressed = post_expressed - {"documentation"}
        pre_missing = post_missing | {"documentation"}
        one_row_only = (
            expressed - pre_expressed == {"documentation"}
            and missing == pre_missing - {"documentation"}
            and partial == post_partial
        )
        return _result(
            "audit",
            matrix_ok and one_row_only,
            f"summary: {result.summary()}; expected 12/18/0/0 with exactly "
            f"documentation: MISSING -> EXPRESSED and the other 29 rows "
            f"untouched",
        )


def _result(gate: str, passed: bool, evidence: str) -> GateResult:
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def doc_harness() -> DocumentationPrimitiveHarness:
    return DocumentationPrimitiveHarness()


# -- locality: changing documentation moves only the documentation gene -----------------------

def test_changing_documentation_does_not_change_subject_genes(doc_harness):
    isr = doc_harness.isr_with_documentation_of("capability_pay")
    subject_before = doc_harness.gene_hash(isr, ("capability", "capability_pay"))
    mutated = doc_harness.respecify_documentation(
        isr, "doc1", DocumentationPurpose.COMPLIANCE
    )
    assert doc_harness.gene_hash(mutated, ("documentation", "doc1")) != \
        doc_harness.gene_hash(isr, ("documentation", "doc1"))  # doc moved
    assert doc_harness.gene_hash(mutated, ("capability", "capability_pay")) == \
        subject_before  # subject held


def test_changing_documentation_touches_only_documentation_gene(doc_harness):
    """The full locality of the proof: every other gene domain is byte-identical."""
    isr = doc_harness.isr_with_documentation_of("capability_pay")
    before = doc_harness.all_gene_hashes(isr)
    mutated = doc_harness.respecify_documentation(
        isr, "doc1", DocumentationPurpose.ARCHITECTURAL_RATIONALE
    )
    assert doc_harness.all_gene_hashes(mutated) == before
    assert doc_harness.gene_hash(mutated, ("documentation", "doc1")) != \
        doc_harness.gene_hash(isr, ("documentation", "doc1"))


def test_add_documentation_does_not_touch_other_genes(doc_harness):
    isr = doc_harness.isr_with()
    before = doc_harness.all_gene_hashes(isr)
    mutated = doc_harness.operator.add_documentation(
        isr, doc_harness.valid_doc()
    ).candidate_isr
    assert doc_harness.all_gene_hashes(mutated) == before
    assert doc_harness.has_gene(mutated, ("documentation", "doc1"))


# -- reference-by-identity: implementation evolves, documentation holds ------------------------

def test_documentation_stable_when_subject_evolves(doc_harness):
    isr = doc_harness.isr_with_documentation_of("w1")
    doc_before = doc_harness.gene_hash(isr, ("documentation", "doc1"))
    mutated = doc_harness.evolve_subject(isr, "w1")  # id stable
    assert doc_harness.gene_hash(mutated, ("behavior", "w1")) != \
        doc_harness.gene_hash(isr, ("behavior", "w1"))  # subject moved
    assert doc_harness.gene_hash(mutated, ("documentation", "doc1")) == doc_before


def test_documentation_stable_when_module_evolves(doc_harness):
    isr = doc_harness.isr_with_documentation_of("m")
    doc_before = doc_harness.gene_hash(isr, ("documentation", "doc1"))
    modules = []
    for module in isr.system.modules:
        if module.id == "m":
            module = dataclasses.replace(
                module, description="module implementation evolved"
            )
        modules.append(module)
    evolved = isr.with_system(
        dataclasses.replace(isr.system, modules=tuple(modules))
    )
    assert doc_harness.gene_hash(evolved, ("module", "m")) != \
        doc_harness.gene_hash(isr, ("module", "m"))
    assert doc_harness.gene_hash(evolved, ("documentation", "doc1")) == doc_before


# -- the I-specific constraint: documentation is a derived view, never an author ----------------

def test_documentation_has_no_realization_fields():
    fields = {f.name for f in dataclasses.fields(DocumentationIntent)}
    realization = {
        f for f in fields
        if any(bad in f.lower() for bad in (
            "markdown", "html", "template", "path", "format", "render",
            "generator",
        ))
    }
    assert not realization, f"documentation carries a realization field: {realization}"


def test_documentation_has_no_subject_authority_fields():
    fields = {f.name for f in dataclasses.fields(DocumentationIntent)}
    authority = {
        f for f in fields
        if any(bad in f.lower() for bad in (
            "override", "redefine", "replace", "author", "source_of",
        ))
    }
    assert not authority, f"documentation carries a subject-authority field: {authority}"


def test_documentation_respecify_never_redefines_subjects(doc_harness):
    """Respecifying what a doc must establish cannot redefine WHAT the
    subjects are — the capability's declared intent is untouched."""
    isr = doc_harness.isr_with_documentation_of("capability_pay")
    capability_before = doc_harness.gene_hash(
        isr, ("capability", "capability_pay")
    )
    mutated = doc_harness.operator.respecify_documentation(
        isr, documentation_id="doc1",
        obligations=("the capability must be documented for compliance",),
    ).candidate_isr
    assert doc_harness.gene_hash(mutated, ("capability", "capability_pay")) == \
        capability_before


# -- declared, never inferred ---------------------------------------------------------------

def test_documentation_is_declared_not_inferred(doc_harness):
    a = doc_harness.isr_with(
        documentation=(
            doc_harness.valid_doc(purpose=DocumentationPurpose.API_CONTRACT),
        ),
    )
    b = doc_harness.isr_with(
        documentation=(
            doc_harness.valid_doc(purpose=DocumentationPurpose.COMPLIANCE),
        ),
    )
    assert doc_harness.subject_genes_identical(a, b)  # same subjects
    assert doc_harness.documentation_gene(a) != doc_harness.documentation_gene(b)


def test_documentation_identity_is_semantic_not_structural(doc_harness):
    a = doc_harness.isr_with_documentation_of("capability_pay")
    b = a.with_system(dataclasses.replace(a.system, id="other-sys-id"))
    assert doc_harness.documentation_gene(a) == doc_harness.documentation_gene(b)
    assert a.content_hash != b.content_hash


# -- the lint: no realization leaks into the intent ------------------------------------------

def test_documentation_lint_rejects_leaked_realization(doc_harness):
    leak = dataclasses.replace(
        doc_harness.valid_doc(),
        purpose=DocumentationPurpose.OPERATIONAL_REFERENCE,
    )
    leak = dataclasses.replace(
        leak,
        obligations=("render markdown via mkdocs",),
    )
    hits = mechanism_hits(leak)
    assert "markdown" in hits
    assert "mkdocs" in hits
    with pytest.raises(DocumentationValidationError):
        assert_documentation_technology_agnostic(leak)


def test_documentation_lint_allows_semantic_intents(doc_harness):
    assert_documentation_technology_agnostic(doc_harness.valid_doc())
    assert_documentation_technology_agnostic(
        DocumentationIntent(
            documentation_id="doc2",
            subject_refs=("w1",),
            purpose=DocumentationPurpose.API_CONTRACT,
            audience=DocumentationAudience.OPERATOR,
            obligations=("the API contract must be documented",),
        )
    )
    assert not mechanism_hits(
        DocumentationIntent(
            documentation_id="doc3",
            subject_refs=("capability_pay",),
            purpose=DocumentationPurpose.OPERATIONAL_REFERENCE,
            audience=DocumentationAudience.SECURITY_AUDITOR,
            obligations=("the declared behavior must be documented",),
        )
    )


# -- structural validation -----------------------------------------------------------------

def test_dangling_subject_ref_rejected(doc_harness):
    dangling = doc_harness.isr_with(
        documentation=(
            dataclasses.replace(
                doc_harness.valid_doc(), subject_refs=("no-such-gene",)
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_dangling_boundary_ref_rejected(doc_harness):
    dangling = doc_harness.isr_with(
        documentation=(
            dataclasses.replace(
                doc_harness.valid_doc(), subject_refs=("no-such-boundary",)
            ),
        ),
    )
    assert dangling.validate_structure() is False


def test_duplicate_documentation_id_rejected(doc_harness):
    duplicate = doc_harness.isr_with(
        documentation=(doc_harness.valid_doc(), doc_harness.valid_doc()),
    )
    assert duplicate.validate_structure() is False


# -- construction validity ----------------------------------------------------------------

def test_documentation_construction_validation():
    with pytest.raises(DocumentationValidationError):
        DocumentationIntent(
            documentation_id="", subject_refs=("w1",),
            purpose=DocumentationPurpose.ONBOARDING,
            audience=DocumentationAudience.DEVELOPER,
        )
    with pytest.raises(DocumentationValidationError):
        DocumentationIntent(
            documentation_id="d", subject_refs=(),
            purpose=DocumentationPurpose.ONBOARDING,
            audience=DocumentationAudience.DEVELOPER,
        )


# -- canonicalization ----------------------------------------------------------------------

def test_empty_documentation_carrier_identity_neutral(doc_harness):
    isr = doc_harness.isr_without_documentation()
    assert doc_harness.with_empty_documentation(isr).content_hash == isr.content_hash


# -- the eleven gates, parameterized --------------------------------------------------------

@pytest.mark.parametrize("gate", PRIMITIVE_GATE)
def test_primitive_gate(gate, doc_harness):
    result = doc_harness.run_gate(gate)
    assert result.passed, f"{gate}: {result.evidence}"


def test_all_gates_pass_together(doc_harness):
    results = assert_all_gates(doc_harness)
    assert len(results) == len(PRIMITIVE_GATE)


# -- lineage is chain-anchored -------------------------------------------------------------

def test_documentation_mutation_is_chain_anchored(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    operator = DocumentationOperator(ledger=ledger)
    harness = DocumentationPrimitiveHarness()
    isr = harness.isr_with()
    candidate = operator.add_documentation(isr, harness.valid_doc())
    assert ledger.verify_event_chain() is True
    event = ledger.events()[0]
    assert event.event_type is EventType.MEASUREMENT
    assert event.payload["operator_id"] == "documentation"
    assert event.payload["subject_id"] == "doc1"
    assert event.payload["isr_hash_before"] == isr.content_hash
    assert event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash


def test_documentation_remove_add_round_trip(doc_harness):
    isr = doc_harness.isr_with()
    added = doc_harness.operator.add_documentation(
        isr, doc_harness.valid_doc()
    ).candidate_isr
    removed = doc_harness.operator.remove_documentation(
        added, documentation_id="doc1"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash


# -- the audit, mechanically one row ---------------------------------------------------------

def test_audit_moves_exactly_one_row(doc_harness):
    result = doc_harness.audit.run(doc_harness.isr_with())
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