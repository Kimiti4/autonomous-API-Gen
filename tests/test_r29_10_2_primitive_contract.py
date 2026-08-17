"""R2.10.2 — Primitive Design & Dependency Ordering acceptance tests.

The five contract artifacts, the Option A projection migration gates, and
the compatibility contract — all attested like the R2.10.1 matrix:

  1. Primitive specification — all ten MISSING primitives fully specified.
  2. Dependency graph        — derived mechanically, acyclic, topologically
     sorted (Refinement 1).
  3. ISR extension contract  — projection/probe/locality/tech-agnostic rules.
  4. Compatibility contract  — old ISR -> same semantic hash -> same artifact
     -> same evolution behavior (Option A: omit-empty is hash-neutral).
  5. Evolution-readiness matrix — all eight stages per primitive, EXPRESSED
     gated on the mutation-locality proof (Refinement 3).
  + Option A migration gates (before/after style, like Phase-28).
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from constitutional_architecture.isr.model import (
    ISR,
    Module,
    StateType,
    System,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.projection import (
    canonicalize,
    semantic_content_hash,
)
from tiannara.application.evolution.candidate_gate import GateContext
from tiannara.application.evolution.isr_capability_audit import ISRCapabilityAudit
from tiannara.application.evolution.ledger import EventType, EvolutionLedger
from tiannara.application.evolution.primitive_contract import (
    EXTENSION_CONTRACT,
    PRIMITIVES,
    READINESS_ORDER,
    ReadinessStage,
    TechnologyCouplingError,
    assert_acyclic,
    assert_readiness_complete,
    assert_technology_agnostic,
    derive_dependency_graph,
    derived_implementation_order,
    readiness_matrix,
)
from tiannara.application.evolution.variation import AwaitingSurfaceIntactInvariant

from .test_r29_10_1_capability_audit import RECIPE, _with_awaits

MISSING_CAPABILITY_IDS = {
    "architecture_boundaries",
    "behavior_temporal_semantics",
    "business_capabilities",
    "data_migrations",
    "deployment_rollout_rollback",
    "documentation",
    "evolution_objectives_protected_regions",
    "reliability_resilience",
    "requirements_acceptance_traceability",
    "testing_anchoring",
}

REQUIRED_SPEC_FIELDS = (
    "semantic_meaning",
    "ownership",
    "dependencies",
    "constraints",
    "mutation_surface",
    "validation_surface",
    "compiler_projection",
    "evidence_projection",
    "lineage_requirements",
)


# -- 1. primitive specification ---------------------------------------------------

def test_all_ten_missing_capabilities_are_specified() -> None:
    assert {p.capability_id for p in PRIMITIVES} == MISSING_CAPABILITY_IDS
    assert len(PRIMITIVES) == 10
    assert len({p.primitive_id for p in PRIMITIVES}) == 10


def test_every_primitive_has_all_required_fields() -> None:
    roots = {p.primitive_id for p in PRIMITIVES if not p.derived_dependencies}
    for spec in PRIMITIVES:
        for field_name in REQUIRED_SPEC_FIELDS:
            value = getattr(spec, field_name)
            if field_name == "dependencies" and spec.primitive_id in roots:
                continue  # roots legitimately declare no primitive dependencies
            assert value, f"{spec.primitive_id}.{field_name} is empty"
        assert spec.type_signature, f"{spec.primitive_id} lacks a type signature"
        assert spec.semantic_meaning.endswith("."), f"{spec.primitive_id} meaning not a sentence"


def test_every_primitive_specifies_a_technology_neutral_projection() -> None:
    for spec in PRIMITIVES:
        for projection in spec.compiler_projection:
            lowered = projection.lower()
            assert "python" not in lowered and "go " not in lowered and "docker" not in lowered


# -- 2. technology-agnostic lint (Refinement 2) ------------------------------------

def test_technology_lint_passes_for_all_primitives() -> None:
    for spec in PRIMITIVES:
        assert_technology_agnostic(spec)


def test_technology_lint_rejects_coupling() -> None:
    class _Bad:
        primitive_id = "bad_primitive"
        semantic_meaning = "X."
        ownership = "system"
        constraints = ()
        mutation_surface = ()
        validation_surface = ()
        compiler_projection = ()
        evidence_projection = ()
        lineage_requirements = ()
        type_signature = {"postgresql_config": "object"}

    try:
        assert_technology_agnostic(_Bad())  # type: ignore[arg-type]
    except TechnologyCouplingError as exc:
        assert "postgresql" in str(exc)
    else:
        raise AssertionError("postgresql_config should be rejected by the lint")


# -- 3. dependency graph (mechanical derivation, Refinement 1) -----------------------

def test_dependency_graph_derived_mechanically() -> None:
    graph = derive_dependency_graph()
    for spec in PRIMITIVES:
        assert graph[spec.primitive_id] == spec.derived_dependencies
        for dep in graph[spec.primitive_id]:
            assert dep in {p.primitive_id for p in PRIMITIVES}


def test_dependency_graph_is_acyclic_and_topologically_ordered() -> None:
    graph = derive_dependency_graph()
    order = derived_implementation_order(graph)
    assert len(order) == len(PRIMITIVES)
    position = {pid: i for i, pid in enumerate(order)}
    for node, deps in graph.items():
        for dep in deps:
            assert position[dep] < position[node], f"{node} ordered before dependency {dep}"


def test_derived_order_matches_expected_cluster() -> None:
    graph = derive_dependency_graph()
    order = derived_implementation_order(graph)
    position = {pid: i for i, pid in enumerate(order)}
    # requirements -> capabilities -> boundaries -> evolution constraints cluster
    assert position["business_capabilities"] < position["requirements_acceptance_traceability"]
    assert position["business_capabilities"] < position["architecture_boundaries"]
    assert position["requirements_acceptance_traceability"] < position["testing_anchoring"]
    # reliability depends on temporal semantics
    assert position["behavior_temporal_semantics"] < position["reliability_resilience"]
    # rollout depends on data migrations + reliability
    assert position["data_migrations"] < position["deployment_rollout_rollback"]
    assert position["reliability_resilience"] < position["deployment_rollout_rollback"]
    # documentation derives from nearly everything; objectives/protected regions last
    assert position["deployment_rollout_rollback"] < position["documentation"]
    assert position["documentation"] < position["evolution_objectives_protected_regions"]
    assert order[-1] == "evolution_objectives_protected_regions"
    # roots (no incoming edges) may be implemented first
    assert "business_capabilities" in order[:4]


def test_unknown_dependency_rejected() -> None:
    spec = dataclasses.replace(PRIMITIVES[0], dependencies=("not_a_primitive",))
    try:
        derive_dependency_graph([spec])
    except ValueError as exc:
        assert "not_a_primitive" in str(exc)
    else:
        raise AssertionError("unknown dependency should be rejected")


# -- 4. extension contract ------------------------------------------------------------

def test_extension_contract_rules_present() -> None:
    rules = "\n".join(EXTENSION_CONTRACT)
    for rule in ("projection rule", "probe rule", "locality rule", "tech-agnostic rule",
                 "compatibility rule", "readiness rule"):
        assert rule in rules


# -- 5. evolution-readiness matrix (Refinement 3) ---------------------------------------

def test_readiness_matrix_complete_per_primitive() -> None:
    assert_readiness_complete()
    matrix = readiness_matrix()
    assert set(matrix) == {p.primitive_id for p in PRIMITIVES}
    for primitive_id, targets in matrix.items():
        assert set(targets) == set(READINESS_ORDER) - {ReadinessStage.MISSING}


def test_expressured_stage_requires_locality_proof() -> None:
    for spec in PRIMITIVES:
        assert spec.locality_required is True
        expressed = spec.readiness_targets[ReadinessStage.EXPRESSED]
        assert any("locality" in target for target in expressed), spec.primitive_id


def test_readiness_progression_order_is_strict() -> None:
    stages = [s.value for s in READINESS_ORDER]
    assert stages == [
        "missing", "represented", "validated", "mutatable",
        "compilable", "observable", "lineage_tracked", "expressed",
    ]


# -- 6. Option A projection migration gates ---------------------------------------------

def test_migration_omit_empty_is_hash_neutral_for_extensions() -> None:
    assert canonicalize({"a": 1, "b": "", "c": [], "d": None, "e": {}}) == canonicalize({"a": 1})
    empty_extension = ISR(system=System(
        id="s", name="S", modules=(Module(id="m", name="M"),), description="",
    ))
    absent_extension = ISR(system=System(
        id="s", name="S", modules=(Module(id="m", name="M"),),
    ))
    assert empty_extension.content_hash == absent_extension.content_hash


def test_migration_semantic_hash_stable_across_recompute() -> None:
    assert semantic_content_hash(RECIPE) == semantic_content_hash(RECIPE)
    assert RECIPE.content_hash == semantic_content_hash(RECIPE)


def test_migration_change_detection_preserved() -> None:
    module = RECIPE.system.modules[0]
    entity = module.entities[0]
    from constitutional_architecture.isr.model import Field, FieldType
    edited = dataclasses.replace(
        entity, fields=entity.fields + (Field(name="extra", field_type=FieldType.TEXT),)
    )
    module_edited = dataclasses.replace(module, entities=module.entities[:1] + (edited,) + module.entities[1:])
    mutated = RECIPE.with_system(dataclasses.replace(RECIPE.system, modules=(module_edited,) + RECIPE.system.modules[1:]))
    assert mutated.content_hash != RECIPE.content_hash


def test_migration_provenance_isolation_preserved() -> None:
    assert RECIPE.content_hash == RECIPE.with_system(RECIPE.system).content_hash


def test_migration_r2_10_1_matrix_re_attested() -> None:
    result = ISRCapabilityAudit().run(RECIPE)
    assert result.integrity is True
    assert result.isr_hash == RECIPE.content_hash
    # R2.10.3-A..G landed (behavior_temporal_semantics, business_capabilities,
    # data_migrations, reliability_resilience, architecture_boundaries,
    # requirements_acceptance_traceability, deployment_rollout_rollback):
    # MISSING -> EXPRESSED
    assert result.summary()["expressed"] == 9
    assert result.summary()["missing"] == 3


# -- 7. compatibility contract (old ISR unchanged) ---------------------------------------

def _fsm_isr() -> ISR:
    awaited = WorkflowState(
        id="await", name="awaiting", state_type=StateType.INTERMEDIATE,
        metadata={"awaits": "op0"},
    )
    final = WorkflowState(id="final", name="final", state_type=StateType.FINAL)
    return ISR(system=System(
        id="sys", name="OrderSystem",
        modules=(Module(
            id="m", name="M",
            workflows=(Workflow(
                id="wf0", name="wf0",
                states=(awaited, final),
                transitions=(WorkflowTransition(
                    id="resolve-op0", name="resolve", from_state_id="await",
                    to_state_id="final", trigger="op0",
                ),),
            ),),
        ),),
    ))


def test_compatibility_old_isr_identity_contract_holds() -> None:
    old = _fsm_isr()
    assert old.content_hash == semantic_content_hash(old)
    assert old.content_hash == old.content_hash  # stable
    assert old.with_system(old.system).content_hash == old.content_hash  # provenance-neutral


def test_compatibility_evolution_behavior_unchanged() -> None:
    old = _fsm_isr()
    stripped = _with_awaits(old, "await", "")
    invariant = AwaitingSurfaceIntactInvariant()
    ctx = GateContext(
        candidate_isr=stripped, candidate_artifact=None, candidate_run=None,
        baseline_artifact=None, baseline_run=None, observation=None,
        mutation=None, parent_isr=old,
    )
    assert invariant.holds(ctx) is False  # await-stripping still rejected pre-execution
    added = _with_awaits(old, "final", "notify")
    ctx_add = GateContext(
        candidate_isr=added, candidate_artifact=None, candidate_run=None,
        baseline_artifact=None, baseline_run=None, observation=None,
        mutation=None, parent_isr=old,
    )
    assert invariant.holds(ctx_add) is True  # await-add still allowed


def test_compatibility_compiler_artifact_unchanged() -> None:
    from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend

    backend = FastAPIHexagonalBackend()
    old = _fsm_isr()
    text1 = backend.async_resolution_module(old.system.modules[0].workflows)
    text2 = backend.async_resolution_module(old.system.modules[0].workflows)
    assert text1 == text2
    assert "async def op0():" in text1
    assert "    await op0()" in text1


# -- 8. contract ledger attestation ---------------------------------------------------------

def test_contract_chain_anchored(tmp_path: Path) -> None:
    from tiannara.application.evolution.primitive_contract import PrimitiveContract

    ledger = EvolutionLedger(root=str(tmp_path))
    contract = PrimitiveContract()
    contract.validate()
    event_id = contract.record(ledger)
    assert ledger.verify_event_chain() is True
    events = ledger.events()
    assert len(events) == 1
    event = events[0]
    assert event.event_type is EventType.PRIMITIVE_CONTRACT
    assert event.subject_id == contract.content_hash()[:32]
    assert event.payload["contract_content_hash"] == contract.content_hash()
    assert event.payload["implementation_order"][-1] == "evolution_objectives_protected_regions"
    assert event.payload["dependency_acyclic"] is True
    assert event.payload["technology_lint_passed"] is True
    assert event.payload["readiness_rows"] == 10 * (len(READINESS_ORDER) - 1)

    tampered = event.model_copy(update={"payload": {**event.payload, "readiness_rows": 1}})
    assert tampered.computed_hash() != event.event_hash
    assert tampered.is_intact() is False
    tampered_ledger = EvolutionLedger()
    tampered_ledger._events.append(tampered)
    assert tampered_ledger.verify_event_chain() is False


def test_contract_deterministic() -> None:
    from tiannara.application.evolution.primitive_contract import PrimitiveContract

    c1 = PrimitiveContract()
    c2 = PrimitiveContract()
    assert c1.content_hash() == c2.content_hash()
    assert c1.implementation_order == c2.implementation_order
    assert c1.dependency_graph == c2.dependency_graph