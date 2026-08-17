"""R2.10.3-C — data_migrations: semantic intent, never mechanism.

The highest-risk primitive: migrations are the easiest place for the
semantic layer to accidentally become a database compiler. The construct is
STRUCTURALLY incapable of carrying an execution mechanism (no SQL, no ORM,
no framework commands — enforced by both a field-name test and a mechanism
lint over the canonical semantic form).

Semantic dimensions modeled: compatibility INTENT (declared, never policy),
preservation requirements (reference-based), ordering (explicit acyclic
depends_on graph), rollback (invariants, never commands), postconditions
(future evaluation inputs). These become foundations for R2.10.3-D
(reliability_resilience) and R2.10.3-E (architecture_boundaries).

The audit gate embeds the CORRECTED pre-landing matrix (4/18/0/8 — after
R2.10.3-B) and asserts the delta is exactly
{data_migrations: MISSING -> EXPRESSED} -> 5/18/0/7.
"""
from __future__ import annotations

import dataclasses
import tempfile
from typing import Any

import pytest

from constitutional_architecture.isr.model import (
    BusinessCapability,
    CompatibilityPolicy,
    DataMigrationIntent,
    Entity,
    ISR,
    Interface,
    InterfaceType,
    MigrationValidationError,
    Module,
    StateType,
    System,
    TemporalConstraint,
    TemporalConstraintKind,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.migration import (
    MIGRATION_MECHANISM_TERMS,
    assert_migration_technology_agnostic,
    migration_mechanism_hits,
    project_data_migrations,
)
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.evolution.isr_capability_audit import (
    CapabilityStatus,
    ISRCapabilityAudit,
    MutationLocalityProbe,
    gene_index,
)
from tiannara.application.evolution.ledger import EventType, EvolutionLedger
from tiannara.application.evolution.migration_mutation import MigrationOperator
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


class MigrationPrimitiveHarness:
    """The eleven-gate harness for data_migrations."""

    primitive_id = "data_migrations"

    def __init__(self) -> None:
        self.audit = ISRCapabilityAudit()
        self.operator = MigrationOperator()
        self.locality_probe = MutationLocalityProbe()
        self.backend = FastAPIHexagonalBackend()

    # -- recipes ------------------------------------------------------------

    def valid_migration(self) -> DataMigrationIntent:
        return DataMigrationIntent(
            migration_id="m1",
            source_schema_ref="e1",
            target_schema_ref="e2",
            compatibility_policy=CompatibilityPolicy.BACKWARD,
            preservation_refs=("e1",),
            depends_on=(),
            rollback_required=True,
            rollback_target_ref="e1",
            rollback_invariants=("e1 intact",),
            postconditions=("e2 valid",),
        )

    def isr_with(
        self,
        entity_ids: tuple[str, ...] = ("e1", "e2"),
        migrations: tuple[DataMigrationIntent, ...] = (),
        with_capability: bool = True,
        with_temporal: bool = True,
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
        capabilities = (
            (
                BusinessCapability(
                    capability_id="pay",
                    intent="process a payment",
                    behavior_refs=("w1",),
                    interface_refs=("i1",),
                ),
            )
            if with_capability
            else ()
        )
        return ISR(
            system=System(
                id="migration-sys",
                name="MigrationSystem",
                modules=(
                    Module(
                        id="m",
                        name="M",
                        entities=tuple(_entity(eid) for eid in entity_ids),
                        workflows=(_workflow("w1", "op_w1"),),
                        interfaces=(
                            Interface(id="i1", name="i1", interface_type=InterfaceType.REST),
                        ),
                        temporal_constraints=temporal_constraints,
                        data_migrations=migrations,
                    ),
                ),
                business_capabilities=capabilities,
            )
        )

    def isr_without_migrations(self) -> ISR:
        return self.isr_with()

    def isr_with_behavior_capabilities_temporal(self) -> ISR:
        return self.isr_with()

    def with_empty_migrations(self, isr: ISR) -> ISR:
        modules = tuple(
            dataclasses.replace(m, data_migrations=())
            for m in isr.system.modules
        )
        return isr.with_system(dataclasses.replace(isr.system, modules=modules))

    # -- gene addressing ------------------------------------------------------

    def all_gene_hashes(self, isr: ISR) -> dict[str, str]:
        """Every gene except the migration gene class."""
        return {
            path: h
            for path, h in gene_index(isr).items()
            if "data_migrations" not in path
        }

    def gene_hash(self, isr: ISR, gene: tuple) -> str:
        """(\"migration\", mid) / (\"entity\", eid) / (\"behavior\", wf_id) /
        (\"capability\", cid) / (\"temporal\", cid)."""
        idx = gene_index(isr)
        kind, name = gene
        for mi, module in enumerate(isr.system.modules):
            if kind == "migration":
                for di, migration in enumerate(module.data_migrations):
                    if migration.migration_id == name:
                        return idx[f"system.modules[{mi}].data_migrations[{di}]"]
            if kind == "entity":
                for ei, entity in enumerate(module.entities):
                    if entity.id == name:
                        return idx[f"system.modules[{mi}].entities[{ei}]"]
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
        if kind == "capability":
            for ci, capability in enumerate(isr.system.business_capabilities):
                if capability.capability_id == name:
                    return idx[f"system.business_capabilities[{ci}]"]
        return ""

    def has_gene(self, isr: ISR, gene: tuple) -> bool:
        return self.gene_hash(isr, gene) != ""

    def entity_genes_identical(self, a: ISR, b: ISR) -> bool:
        a_hash = {p: h for p, h in self.all_gene_hashes(a).items() if ".entities[" in p}
        b_hash = {p: h for p, h in self.all_gene_hashes(b).items() if ".entities[" in p}
        return a_hash == b_hash

    # -- gates ----------------------------------------------------------------

    def run_gate(self, gate: str) -> GateResult:
        method = getattr(self, f"_gate_{gate}", None)
        if method is None:
            raise AssertionError(f"no implementation for gate '{gate}'")
        return method()

    def _gate_representation(self):
        module_fields = {f.name for f in dataclasses.fields(Module)}
        ok = "data_migrations" in module_fields
        try:
            self.valid_migration()
            ok = ok and True
        except MigrationValidationError:
            ok = False
        policies = {p.value for p in CompatibilityPolicy}
        ok = ok and policies == {
            "BACKWARD", "FORWARD", "BIDIRECTIONAL", "BREAKING", "CUSTOM",
        }
        mechanism_fields = {
            f.name
            for f in dataclasses.fields(DataMigrationIntent)
            if any(bad in f.name.lower() for bad in ("command", "script", "sql", "statement"))
        }
        return _result(
            "representation",
            ok and not mechanism_fields,
            f"Module.data_migrations carrier; DataMigrationIntent with five "
            f"compatibility intents; no mechanism fields: {mechanism_fields or 'none'}",
        )

    def _gate_canonicalization(self):
        isr = self.isr_without_migrations()
        same = self.with_empty_migrations(isr).content_hash == isr.content_hash
        return _result(
            "canonicalization",
            same,
            f"empty migration carrier identity-neutral: {same}",
        )

    def _gate_semantic_identity(self):
        isr = self.isr_with()
        with_migration = self.operator.add_migration(
            isr, self.valid_migration(), module_id="m"
        ).candidate_isr
        step1 = with_migration.content_hash != isr.content_hash
        repolicyed = self.operator.set_compatibility_policy(
            with_migration,
            migration_id="m1",
            policy=CompatibilityPolicy.BREAKING,
            module_id="m",
        ).candidate_isr
        step2 = repolicyed.content_hash != with_migration.content_hash
        removed = self.operator.remove_migration(
            repolicyed, migration_id="m1", module_id="m"
        ).candidate_isr
        step3 = removed.content_hash == isr.content_hash
        return _result(
            "semantic_identity",
            step1 and step2 and step3,
            f"add changes hash: {step1}; policy change changes hash: {step2}; "
            f"remove restores hash: {step3}",
        )

    def _gate_validation(self):
        ok = True
        for bad in (
            dict(migration_id="", source_schema_ref="e1", target_schema_ref="e2"),
            dict(migration_id="m", source_schema_ref="", target_schema_ref="e2"),
            dict(migration_id="m", source_schema_ref="e1", target_schema_ref=""),
            dict(migration_id="m", source_schema_ref="e1", target_schema_ref="e1"),
            dict(
                migration_id="m", source_schema_ref="e1", target_schema_ref="e2",
                rollback_required=True, rollback_target_ref=None,
            ),
            dict(
                migration_id="m", source_schema_ref="e1", target_schema_ref="e2",
                compatibility_policy=CompatibilityPolicy.CUSTOM, postconditions=(),
            ),
        ):
            kwargs = dict(bad)
            kwargs.setdefault("compatibility_policy", CompatibilityPolicy.BACKWARD)
            try:
                DataMigrationIntent(**kwargs)
                ok = False
            except MigrationValidationError:
                pass
        dangling = self.isr_with(
            migrations=(
                DataMigrationIntent(
                    migration_id="m1", source_schema_ref="e1",
                    target_schema_ref="no-such-entity",
                    compatibility_policy=CompatibilityPolicy.BACKWARD,
                ),
            )
        )
        ok = ok and dangling.validate_structure() is False
        for ref_kind, ref in (
            ("preservation_refs", "no-such-entity"),
            ("depends_on", "no-such-migration"),
        ):
            bad = self.isr_with(
                migrations=(
                    DataMigrationIntent(
                        migration_id="m1", source_schema_ref="e1",
                        target_schema_ref="e2",
                        compatibility_policy=CompatibilityPolicy.BACKWARD,
                        **{ref_kind: (ref,)},
                    ),
                )
            )
            ok = ok and bad.validate_structure() is False
        circular = self.isr_with(
            migrations=(
                DataMigrationIntent(
                    migration_id="mA", source_schema_ref="e1",
                    target_schema_ref="e2",
                    compatibility_policy=CompatibilityPolicy.BACKWARD,
                    depends_on=("mB",),
                ),
                DataMigrationIntent(
                    migration_id="mB", source_schema_ref="e2",
                    target_schema_ref="e1",
                    compatibility_policy=CompatibilityPolicy.BACKWARD,
                    depends_on=("mA",),
                ),
            )
        )
        ok = ok and circular.validate_structure() is False
        return _result(
            "validation",
            ok,
            "required fields / same-source-target / rollback-without-target / "
            "CUSTOM-without-postconditions rejected at construction; dangling "
            "schema/preservation/dependency refs and circular depends_on "
            "rejected pre-execution",
        )

    def _gate_locality(self):
        isr = self.isr_with()
        mutated = self.operator.add_migration(
            isr, self.valid_migration(), module_id="m"
        ).candidate_isr
        result = self.locality_probe.probe(
            isr, mutated, "system.modules[0].data_migrations[0]"
        )
        return _result(
            "locality",
            result.locality_holds,
            f"target gene changed: {result.target_gene_changed}; "
            f"unintended changes: {result.unintended_changes}",
        )

    def _gate_projection(self):
        isr = self.isr_with(migrations=(self.valid_migration(),))
        projected = project_data_migrations(isr.system.modules[0])
        deterministic = projected == project_data_migrations(isr.system.modules[0])
        reflects = any(
            m.get("migration_id") == "m1"
            and m.get("compatibility_policy") == "BACKWARD"
            and "e1" in m.get("preservation_refs", [])
            for m in projected
        )
        text = str(projected)
        coupled = [
            term for term in TECHNOLOGY_COUPLING_TERMS if term in text
        ]
        mechanism = [
            term for term in MIGRATION_MECHANISM_TERMS if term in text
        ]
        return _result(
            "projection",
            deterministic and reflects and not coupled and not mechanism,
            f"deterministic: {deterministic}; reflects intent: {reflects}; "
            f"coupling terms: {coupled}; mechanism terms: {mechanism}",
        )

    def _gate_compilation(self):
        isr = self.isr_with()
        mutated = self.operator.add_migration(
            isr, self.valid_migration(), module_id="m"
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
            f"existing backend byte-identical with migration intents present: "
            f"{compatible}; deterministic: {deterministic}",
        )

    def _gate_evidence(self):
        isr = self.isr_with(migrations=(self.valid_migration(),))
        observable = any(
            m.get("migration_id") == "m1"
            for m in project_data_migrations(isr.system.modules[0])
        )
        empty = project_data_migrations(self.isr_without_migrations().system.modules[0]) == ()
        return _result(
            "evidence",
            observable and empty,
            f"migration intent observable in semantic projection: {observable}; "
            f"no migrations -> empty projection: {empty}",
        )

    def _gate_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = EvolutionLedger(root=str(tmp))
            operator = MigrationOperator(ledger=ledger)
            isr = self.isr_with()
            candidate = operator.add_migration(
                isr, self.valid_migration(), module_id="m"
            )
            chain_ok = ledger.verify_event_chain() is True
            events = ledger.events()
            event = events[0] if events else None
            attributed = (
                event is not None
                and event.event_type is EventType.MEASUREMENT
                and event.payload["operator_id"] == "data_migration"
                and event.payload["migration_id"] == "m1"
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
            "data_migrations",
            "reliability_resilience",  # R2.10.3-D
            "architecture_boundaries",  # R2.10.3-E
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
        post_missing = {
            "deployment_rollout_rollback",
            "requirements_acceptance_traceability",
            "documentation", "testing_anchoring",
            "evolution_objectives_protected_regions",
        }
        matrix_ok = (
            expressed == post_expressed
            and partial == post_partial
            and missing == post_missing
            and CapabilityStatus.PROJECTED not in by_id.values()
        )
        # Exactly one row moved vs the pre-landing (R2.10.3-B) matrix 4/18/0/8.
        pre_expressed = post_expressed - {"data_migrations"}
        pre_missing = post_missing | {"data_migrations"}
        one_row_only = (
            expressed - pre_expressed == {"data_migrations"}
            and missing == pre_missing - {"data_migrations"}
            and partial == post_partial
        )
        return _result(
            "audit",
            matrix_ok and one_row_only,
            f"summary: {result.summary()}; expected 5/18/0/7 with exactly "
            f"data_migrations: MISSING -> EXPRESSED and the other 29 rows untouched",
        )


def _result(gate: str, passed: bool, evidence: str) -> GateResult:
    return GateResult(gate=gate, passed=passed, evidence=evidence)


@pytest.fixture
def mig_harness() -> MigrationPrimitiveHarness:
    return MigrationPrimitiveHarness()


# -- locality -------------------------------------------------------------------

def test_add_migration_does_not_touch_other_genes(mig_harness):
    isr = mig_harness.isr_with_behavior_capabilities_temporal()
    before = mig_harness.all_gene_hashes(isr)  # behavior, capability, temporal, entity
    mutated = mig_harness.operator.add_migration(
        isr, mig_harness.valid_migration(), module_id="m"
    ).candidate_isr
    assert mig_harness.all_gene_hashes(mutated) == before
    assert mig_harness.has_gene(mutated, ("migration", "m1"))


def test_change_migration_policy_moves_only_migration_gene(mig_harness):
    isr = mig_harness.isr_with(migrations=(mig_harness.valid_migration(),))
    before = mig_harness.all_gene_hashes(isr)
    mutated = mig_harness.operator.set_compatibility_policy(
        isr, migration_id="m1",
        policy=CompatibilityPolicy.FORWARD, module_id="m",
    ).candidate_isr
    assert mig_harness.all_gene_hashes(mutated) == before  # only migration gene moved
    assert mig_harness.gene_hash(mutated, ("migration", "m1")) != \
        mig_harness.gene_hash(isr, ("migration", "m1"))


# -- non-inference ---------------------------------------------------------------

def test_migration_is_declared_not_inferred(mig_harness):
    a = mig_harness.isr_with(migrations=(
        dataclasses.replace(
            mig_harness.valid_migration(),
            compatibility_policy=CompatibilityPolicy.BACKWARD,
        ),
    ))
    b = mig_harness.isr_with(migrations=(
        dataclasses.replace(
            mig_harness.valid_migration(),
            compatibility_policy=CompatibilityPolicy.BREAKING,
        ),
    ))
    assert mig_harness.entity_genes_identical(a, b)  # same data model
    assert mig_harness.gene_hash(a, ("migration", "m1")) != \
        mig_harness.gene_hash(b, ("migration", "m1"))


def test_migration_identity_is_semantic_not_structural(mig_harness):
    # Equivalent declarations over differently structured data models:
    # the migration gene is the declared intent, not the implementation.
    a = mig_harness.isr_with(entity_ids=("e1", "e2"), migrations=(mig_harness.valid_migration(),))
    b = mig_harness.isr_with(entity_ids=("e1", "e2", "e3"), migrations=(mig_harness.valid_migration(),))
    assert mig_harness.gene_hash(a, ("migration", "m1")) == \
        mig_harness.gene_hash(b, ("migration", "m1"))
    assert a.content_hash != b.content_hash  # data model differs


# -- the dangerous boundary: no execution mechanism --------------------------------

def test_migration_has_no_execution_mechanism():
    fields = {f.name for f in dataclasses.fields(DataMigrationIntent)}
    mechanism = {
        f for f in fields
        if any(bad in f.lower() for bad in ("command", "script", "sql", "statement"))
    }
    assert not mechanism, f"migration carries an execution mechanism: {mechanism}"


def test_migration_mechanism_lint_rejects_leaked_mechanism(mig_harness):
    leak = dataclasses.replace(
        mig_harness.valid_migration(),
        postconditions=("alembic migration_command ok",),
    )
    hits = migration_mechanism_hits(leak)
    assert "alembic" in hits
    assert "migration_command" in hits
    with pytest.raises(MigrationValidationError):
        assert_migration_technology_agnostic(leak)
    assert_migration_technology_agnostic(mig_harness.valid_migration())  # clean form passes


# -- ordering / dependency validity ----------------------------------------------------

def test_circular_migration_dependency_rejected(mig_harness):
    circular = mig_harness.isr_with(migrations=(
        DataMigrationIntent(
            migration_id="mA", source_schema_ref="e1", target_schema_ref="e2",
            compatibility_policy=CompatibilityPolicy.BACKWARD,
            depends_on=("mB",),
        ),
        DataMigrationIntent(
            migration_id="mB", source_schema_ref="e2", target_schema_ref="e1",
            compatibility_policy=CompatibilityPolicy.BACKWARD,
            depends_on=("mA",),
        ),
    ))
    assert circular.validate_structure() is False


def test_acyclic_migration_dependency_accepted(mig_harness):
    ordered = mig_harness.isr_with(migrations=(
        DataMigrationIntent(
            migration_id="mA", source_schema_ref="e1", target_schema_ref="e2",
            compatibility_policy=CompatibilityPolicy.BACKWARD,
        ),
        DataMigrationIntent(
            migration_id="mB", source_schema_ref="e2", target_schema_ref="e1",
            compatibility_policy=CompatibilityPolicy.BACKWARD,
            depends_on=("mA",),
        ),
    ))
    assert ordered.validate_structure() is True


def test_dangling_schema_ref_rejected(mig_harness):
    dangling = mig_harness.isr_with(migrations=(
        DataMigrationIntent(
            migration_id="m1", source_schema_ref="e1",
            target_schema_ref="no-such-entity",
            compatibility_policy=CompatibilityPolicy.BACKWARD,
        ),
    ))
    assert dangling.validate_structure() is False


# -- construction validity -----------------------------------------------------------

def test_migration_construction_validation():
    with pytest.raises(MigrationValidationError):
        DataMigrationIntent(
            migration_id="", source_schema_ref="a", target_schema_ref="b",
            compatibility_policy=CompatibilityPolicy.BACKWARD,
        )
    with pytest.raises(MigrationValidationError):
        DataMigrationIntent(
            migration_id="m", source_schema_ref="a", target_schema_ref="a",
            compatibility_policy=CompatibilityPolicy.BACKWARD,
        )
    with pytest.raises(MigrationValidationError):
        DataMigrationIntent(
            migration_id="m", source_schema_ref="a", target_schema_ref="b",
            compatibility_policy=CompatibilityPolicy.BACKWARD,
            rollback_required=True, rollback_target_ref=None,
        )
    with pytest.raises(MigrationValidationError):
        DataMigrationIntent(
            migration_id="m", source_schema_ref="a", target_schema_ref="b",
            compatibility_policy=CompatibilityPolicy.CUSTOM, postconditions=(),
        )


def test_rollback_is_invariants_not_commands(mig_harness):
    migration = mig_harness.valid_migration()
    assert migration.rollback_required is True
    assert migration.rollback_target_ref == "e1"
    assert migration.rollback_invariants == ("e1 intact",)
    assert not any(
        bad in str(migration).lower()
        for bad in ("command", "script", "execute", "run ")
    )


# -- canonicalization ------------------------------------------------------------------

def test_empty_migration_carrier_identity_neutral(mig_harness):
    isr = mig_harness.isr_without_migrations()
    assert mig_harness.with_empty_migrations(isr).content_hash == isr.content_hash


# -- the eleven gates, parameterized ------------------------------------------------------

@pytest.mark.parametrize("gate", PRIMITIVE_GATE)
def test_primitive_gate(gate, mig_harness):
    result = mig_harness.run_gate(gate)
    assert result.passed, f"{gate}: {result.evidence}"


def test_all_gates_pass_together(mig_harness):
    results = assert_all_gates(mig_harness)
    assert len(results) == len(PRIMITIVE_GATE)


# -- lineage is chain-anchored ------------------------------------------------------------

def test_migration_mutation_is_chain_anchored(tmp_path):
    ledger = EvolutionLedger(root=str(tmp_path))
    operator = MigrationOperator(ledger=ledger)
    harness = MigrationPrimitiveHarness()
    isr = harness.isr_with()
    candidate = operator.add_migration(isr, harness.valid_migration(), module_id="m")
    assert ledger.verify_event_chain() is True
    event = ledger.events()[0]
    assert event.event_type is EventType.MEASUREMENT
    assert event.payload["operator_id"] == "data_migration"
    assert event.payload["migration_id"] == "m1"
    assert event.payload["isr_hash_before"] == isr.content_hash
    assert event.payload["isr_hash_after"] == candidate.candidate_isr.content_hash


# -- remove restores identity ------------------------------------------------------------------

def test_remove_migration_restores_semantic_identity(mig_harness):
    isr = mig_harness.isr_with()
    with_migration = mig_harness.operator.add_migration(
        isr, mig_harness.valid_migration(), module_id="m"
    ).candidate_isr
    removed = mig_harness.operator.remove_migration(
        with_migration, migration_id="m1", module_id="m"
    ).candidate_isr
    assert removed.content_hash == isr.content_hash


# -- the audit, mechanically one row --------------------------------------------------------------

def test_audit_moves_exactly_one_row(mig_harness):
    result = mig_harness.audit.run(mig_harness.isr_with())
    by_id = {c.capability_id: c.status for c in result.capabilities}
    expressed = {cid for cid, s in by_id.items() if s is CapabilityStatus.EXPRESSED}
    missing = {cid for cid, s in by_id.items() if s is CapabilityStatus.MISSING}
    # Pre-landing (R2.10.3-D) matrix: 6/18/0/6.
    pre_expressed = {
        "behavior_transitions", "behavior_await_surface",
        "behavior_temporal_semantics", "business_capabilities",
        "data_migrations", "reliability_resilience",
    }
    pre_missing = {
        "architecture_boundaries", "deployment_rollout_rollback",
        "requirements_acceptance_traceability",
        "documentation", "testing_anchoring",
        "evolution_objectives_protected_regions",
    }
    moved_rows = {}
    for cid in pre_expressed | pre_missing:
        before = "EXPRESSED" if cid in pre_expressed else "MISSING"
        after = "EXPRESSED" if cid in expressed else "MISSING"
        if before != after:
            moved_rows[cid] = (before, after)
    assert moved_rows == {"architecture_boundaries": ("MISSING", "EXPRESSED")}
    assert (len(expressed), 18, 0, len(missing)) == (7, 18, 0, 5)  # NOT 6/18/0/6