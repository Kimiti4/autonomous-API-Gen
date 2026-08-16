"""R2.10.1 — ISR capability / expressivity audit acceptance criteria.

The audit is diagnostic-only: it measures which constitutional capabilities
the ISR represents and which the evolution machinery can evolve end-to-end.
Acceptance criteria A–H:

  A. Coverage / integrity — every constitutional obligation has a probe, no
     probe is unclassified, status is always derived (never asserted).
  B. One mutation-locality test per EXPRESSED gene class.
  C. Mutation locality — mutating one gene changes no other gene's semantic
     hash (and always changes its target's).
  D. Round-trip — ISR -> compile -> artifact -> project preserves the mutated
     gene (await-surface / transition lowering), deterministically.
  E. Invalid mutations rejected pre-execution (structural + identity gates).
  F. Every non-MISSING assessment carries evidence.
  G. The signed capability matrix is chain-anchored in the ledger as an
     ISR_CAPABILITY_AUDIT event (tamper-evident).
  H. Determinism — same ISR + mutation + seed => same semantic candidate.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from constitutional_architecture.isr.model import (
    Constraint,
    ConstraintScope,
    ConstraintSeverity,
    Deployment,
    Endpoint,
    Entity,
    EnvironmentTier,
    Event,
    EventGuarantee,
    EventPattern,
    Field,
    FieldCardinality,
    FieldType,
    HttpMethod,
    Interface,
    InterfaceType,
    ISR,
    Module,
    MonitoringConfig,
    NetworkingConfig,
    Operation,
    OperationType,
    Permission,
    Policy,
    PolicyRule,
    PolicyType,
    Relationship,
    ScalingConfig,
    ScalingStrategy,
    SecretsConfig,
    Service,
    ServiceDependency,
    StateType,
    StorageConfig,
    System,
    SystemMetadata,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)
from constitutional_architecture.isr.semantics.projection import canonicalize
from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.evolution.candidate_gate import GateContext
from tiannara.application.evolution.isr_capability_audit import (
    CONSTITUTIONAL_CAPABILITIES,
    CapabilityAssessment,
    CapabilityStatus,
    ISRCapabilityAudit,
    ISRCapabilityAuditResult,
    MutationLocalityProbe,
    derive_status,
    gene_index,
)
from tiannara.application.evolution.ledger import EventType, EvolutionLedger
from tiannara.application.evolution.variation import (
    AwaitingSurfaceIntactInvariant,
    RandomFSMExploration,
)
from tiannara.domain.models.observation import (
    FailureCategory,
    FailureObservation,
    FailurePhase,
)


# -- full-carrier recipe ISR --------------------------------------------------

def _field(name: str, ftype: FieldType = FieldType.STRING) -> Field:
    return Field(name=name, field_type=ftype, is_primary_key=(name == "id"))


def _recipe_isr() -> ISR:
    m1 = Module(
        id="orders",
        name="Orders",
        description="Order fulfillment bounded context",
        entities=(
            Entity(
                id="order",
                name="Order",
                fields=(
                    _field("id", FieldType.UUID),
                    _field("customer", FieldType.TEXT),
                    _field("total", FieldType.DECIMAL),
                ),
                relationships=(
                    Relationship(target_entity_id="line", relationship_type="one_to_many"),
                ),
                constraints=(
                    Constraint(
                        id="c-order-total",
                        name="total non-negative",
                        scope=ConstraintScope.ENTITY,
                        severity=ConstraintSeverity.ERROR,
                        rule_type="non_negative",
                        parameters={"field": "total"},
                        target_node_ids=("order",),
                    ),
                ),
                is_aggregate_root=True,
            ),
            Entity(
                id="line",
                name="OrderLine",
                fields=(_field("id", FieldType.UUID), _field("sku", FieldType.TEXT)),
            ),
        ),
        services=(
            Service(
                id="order-svc",
                name="OrderService",
                operations=(
                    Operation(id="place", name="place_order", operation_type=OperationType.COMMAND),
                    Operation(id="get", name="get_order", operation_type=OperationType.QUERY),
                ),
                dependencies=(ServiceDependency(target_service_id="payment-svc"),),
                emitted_events=("order-placed",),
                consumed_events=("payment-settled",),
            ),
        ),
        workflows=(
            Workflow(
                id="wf-orders",
                name="Order lifecycle",
                states=(
                    WorkflowState(
                        id="await-payment",
                        name="awaiting payment",
                        state_type=StateType.INTERMEDIATE,
                        metadata={"awaits": "collect_payment"},
                    ),
                    WorkflowState(
                        id="placed",
                        name="placed",
                        state_type=StateType.FINAL,
                    ),
                    WorkflowState(
                        id="failed",
                        name="failed",
                        state_type=StateType.ERROR,
                    ),
                ),
                transitions=(
                    WorkflowTransition(
                        id="t-pay",
                        name="payment collected",
                        from_state_id="await-payment",
                        to_state_id="placed",
                        trigger="collect_payment",
                    ),
                ),
            ),
            Workflow(
                id="wf-refunds",
                name="Refund lifecycle",
                states=(
                    WorkflowState(
                        id="refund-start",
                        name="started",
                        state_type=StateType.INITIAL,
                        metadata={"awaits": "issue_refund"},
                    ),
                    WorkflowState(
                        id="refund-done",
                        name="done",
                        state_type=StateType.FINAL,
                    ),
                ),
                transitions=(),
            ),
        ),
        policies=(
            Policy(
                id="authz-order",
                name="order authorization",
                policy_type=PolicyType.AUTHORIZATION,
                roles=("admin", "support"),
                permissions=(
                    Permission(id="p-approve", name="approve", resource="order", actions=("approve",)),
                ),
            ),
            Policy(
                id="authn-api",
                name="api authentication",
                policy_type=PolicyType.AUTHENTICATION,
                strategy="token",
            ),
            Policy(
                id="ops-retention",
                name="retention",
                policy_type=PolicyType.DATA_RETENTION,
                rules=(PolicyRule(id="r-90", name="90 days", rule_type="retention", parameters={"days": 90}),),
            ),
        ),
        interfaces=(
            Interface(
                id="order-api",
                name="Order API",
                interface_type=InterfaceType.REST,
                endpoints=(
                    Endpoint(
                        id="ep-create",
                        name="create order",
                        path="/orders",
                        method=HttpMethod.POST,
                        required_permissions=("p-approve",),
                        is_public=False,
                    ),
                    Endpoint(
                        id="ep-list",
                        name="list orders",
                        path="/orders",
                        method=HttpMethod.GET,
                        is_public=True,
                        rate_limit=100,
                    ),
                ),
                secured_by_policy_id="authn-api",
            ),
        ),
        events=(
            Event(
                id="order-placed",
                name="order placed",
                schema=(_field("order_id", FieldType.UUID),),
                pattern=EventPattern.PUBLISH_SUBSCRIBE,
                guarantee=EventGuarantee.AT_LEAST_ONCE,
            ),
            Event(
                id="payment-settled",
                name="payment settled",
                schema=(_field("payment_id", FieldType.UUID),),
                pattern=EventPattern.REQUEST_REPLY,
                guarantee=EventGuarantee.EXACTLY_ONCE,
                ordering_required=True,
            ),
        ),
        dependencies=("payments",),
    )
    m2 = Module(
        id="payments",
        name="Payments",
        entities=(Entity(id="payment", name="Payment", fields=(_field("id", FieldType.UUID),)),),
    )
    return ISR(
        system=System(
            id="audit-sys",
            name="AuditSystem",
            description="R2.10.1 full-carrier audit recipe",
            modules=(m1, m2),
            deployment=Deployment(
                id="audit-dep",
                name="production",
                environment=EnvironmentTier.PRODUCTION,
                scaling=ScalingConfig(strategy=ScalingStrategy.HORIZONTAL, min_instances=2, max_instances=8),
                networking=NetworkingConfig(expose_publicly=True, tls_required=True),
                monitoring=MonitoringConfig(health_check_path="/health", metrics_enabled=True),
                storage=StorageConfig(persistent_storage_required=True, backup_enabled=True),
                secrets=SecretsConfig(secrets=("db-password",), rotation_policy_days=30),
            ),
            metadata=SystemMetadata(version="1.0", tags=("audit",)),
            global_policies=("no-backdoor",),
            constraints=(
                Constraint(
                    id="sys-bounded",
                    name="bounded contexts",
                    scope=ConstraintScope.SYSTEM,
                    rule_type="module_count",
                    parameters={"max": 4},
                ),
            ),
        )
    )


RECIPE = _recipe_isr()
OBS = FailureObservation(
    execution_id="exec-audit",
    backend_id="stub",
    phase=FailurePhase.TEST,
    category=FailureCategory.TEST_FAILURE,
    exit_code=1,
    command=["pytest", "-W", "error::RuntimeWarning", "-q"],
    diagnostics=("coroutine 'collect_payment' was never awaited",),
    evidence_hash="obs-audit",
    stderr_excerpt="RuntimeWarning: coroutine 'collect_payment' was never awaited",
)


def _with_transition(isr: ISR, workflow_id: str, transition: WorkflowTransition) -> ISR:
    """Immutable gene-level mutation: append a transition to a workflow."""
    modules = []
    for module in isr.system.modules:
        workflows = []
        for wf in module.workflows:
            if wf.id == workflow_id:
                wf = dataclasses.replace(wf, transitions=wf.transitions + (transition,))
            workflows.append(wf)
        modules.append(dataclasses.replace(module, workflows=tuple(workflows)))
    return isr.with_system(dataclasses.replace(isr.system, modules=tuple(modules)))


def _with_awaits(isr: ISR, state_id: str, coroutine: str) -> ISR:
    """Immutable gene-level mutation: (re)declare a state's awaiting surface."""
    modules = []
    for module in isr.system.modules:
        workflows = []
        for wf in module.workflows:
            states = []
            for state in wf.states:
                if state.id == state_id:
                    state = dataclasses.replace(
                        state, metadata={**state.metadata, "awaits": coroutine}
                    )
                states.append(state)
            workflows.append(dataclasses.replace(wf, states=tuple(states)))
        modules.append(dataclasses.replace(module, workflows=tuple(workflows)))
    return isr.with_system(dataclasses.replace(isr.system, modules=tuple(modules)))


def _project_async_resolution(module_text: str) -> tuple[set[str], set[str]]:
    """Project the generated artifact back to its gene-level lowering:
    (coroutines, awaited-triggers)."""
    coroutines = set()
    awaited = set()
    for line in module_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("async def ") and stripped.endswith("():"):
            coroutines.add(stripped[len("async def "):-3])
        elif stripped.startswith("await "):
            awaited.add(stripped[len("await "):-2])
    return coroutines, awaited


# -- status derivation ----------------------------------------------------------

def test_status_is_always_derived_never_asserted() -> None:
    full = CapabilityAssessment(
        capability_id="x", represented=True,
        independently_mutatable=True, independently_validatable=True,
        compilable=True, observable=True, lineage_tracked=True,
    )
    partial = CapabilityAssessment(
        capability_id="x", represented=True,
        independently_mutatable=True, independently_validatable=True,
        compilable=False, observable=True, lineage_tracked=True,
    )
    projected = CapabilityAssessment(
        capability_id="x", represented=False, independently_mutatable=False,
        independently_validatable=False, compilable=False, observable=False,
        lineage_tracked=False, projected_via=("system.constraints",),
    )
    missing = CapabilityAssessment(
        capability_id="x", represented=False, independently_mutatable=False,
        independently_validatable=False, compilable=False, observable=False,
        lineage_tracked=False,
    )
    assert derive_status(full) is CapabilityStatus.EXPRESSED
    assert derive_status(partial) is CapabilityStatus.PARTIAL
    assert derive_status(projected) is CapabilityStatus.PROJECTED
    assert derive_status(missing) is CapabilityStatus.MISSING

    audit = ISRCapabilityAudit()
    result = audit.run(RECIPE)
    for capability in result.capabilities:
        assert capability.status is derive_status(capability.assessment)


# -- A: coverage / integrity -----------------------------------------------------

def test_a_integrity_and_coverage() -> None:
    audit = ISRCapabilityAudit()
    result = audit.run(RECIPE)
    assert isinstance(result, ISRCapabilityAuditResult)
    assert result.integrity is True
    assert result.unclassified == ()
    covered = {cid for c in result.capabilities for cid in c.constitutional_ids}
    for obligation in CONSTITUTIONAL_CAPABILITIES:
        assert obligation.id in covered, f"constitutional obligation {obligation.id} uncovered"
    for capability in result.capabilities:
        assert capability.constitutional_ids or capability.machinery, (
            f"probe {capability.capability_id} is an orphan (no constitutional id, not machinery)"
        )
    assert result.isr_hash == RECIPE.content_hash
    assert result.summary()["expressed"] >= 2
    assert result.summary()["missing"] >= 6


def test_a_expected_matrix() -> None:
    audit = ISRCapabilityAudit()
    result = audit.run(RECIPE)
    by_id = {c.capability_id: c.status for c in result.capabilities}
    assert by_id["behavior_transitions"] is CapabilityStatus.EXPRESSED
    assert by_id["behavior_await_surface"] is CapabilityStatus.EXPRESSED
    assert by_id["behavior_temporal_semantics"] is CapabilityStatus.EXPRESSED  # R2.10.3-A
    assert by_id["business_capabilities"] is CapabilityStatus.EXPRESSED  # R2.10.3-B
    assert by_id["data_migrations"] is CapabilityStatus.EXPRESSED  # R2.10.3-C
    assert by_id["reliability_resilience"] is CapabilityStatus.EXPRESSED  # R2.10.3-D
    for partial_id in (
        "behavior_guards_actions", "behavior_state_semantics",
        "behavior_events_triggers", "behavior_error_states",
        "architecture_modules", "architecture_components",
        "architecture_interfaces_apis", "architecture_dependencies",
        "deployment_topology", "data_entities_schema",
        "data_persistence_consistency", "security_authorization",
        "security_authentication_trust", "requirements_constraints",
        "performance_scalability", "observability",
        "operational_policies", "evolution_lineage_provenance",
    ):
        assert by_id[partial_id] is CapabilityStatus.PARTIAL, partial_id
    for missing_id in (
        "architecture_boundaries",
        "deployment_rollout_rollback",
        "requirements_acceptance_traceability",
        "documentation", "testing_anchoring",
        "evolution_objectives_protected_regions",
    ):
        assert by_id[missing_id] is CapabilityStatus.MISSING, missing_id
    assert CapabilityStatus.PROJECTED not in by_id.values()


# -- B + C: mutation locality per EXPRESSED gene class ----------------------------

def test_b_c_locality_for_transition_gene() -> None:
    probe = MutationLocalityProbe()
    gene_path = "system.modules[0].workflows[0].transitions[1]"
    added = WorkflowTransition(
        id="t-refund", name="refund triggered",
        from_state_id="placed", to_state_id="failed", trigger="issue_refund",
    )
    mutated = _with_transition(RECIPE, "wf-orders", added)
    assert mutated.content_hash != RECIPE.content_hash
    result = probe.probe(RECIPE, mutated, gene_path)
    assert result.target_gene_changed is True
    assert result.unintended_changes == ()
    assert result.locality_holds is True
    before = gene_index(RECIPE)
    after = gene_index(mutated)
    diff = {p for p in set(before) | set(after) if before.get(p) != after.get(p)}
    assert diff == {gene_path}


def test_b_c_locality_for_await_surface_gene() -> None:
    probe = MutationLocalityProbe()
    gene_path = "system.modules[0].workflows[0].states[1]"
    mutated = _with_awaits(RECIPE, "placed", "notify_shipped")
    assert mutated.content_hash != RECIPE.content_hash
    result = probe.probe(RECIPE, mutated, gene_path)
    assert result.target_gene_changed is True
    assert result.unintended_changes == ()
    assert result.locality_holds is True


def test_b_c_locality_across_workflows_and_modules() -> None:
    probe = MutationLocalityProbe()
    added = WorkflowTransition(
        id="t-pay2", name="payment collected (dup)",
        from_state_id="await-payment", to_state_id="placed", trigger="collect_payment",
    )
    mutated = _with_transition(RECIPE, "wf-orders", added)
    result = probe.probe(RECIPE, mutated, "system.modules[0].workflows[0].transitions[1]")
    assert result.locality_holds is True
    assert all("wf-refunds" not in u for u in result.unintended_changes)
    assert all("payments" not in u for u in result.unintended_changes)


def test_b_c_locality_false_when_target_unchanged() -> None:
    probe = MutationLocalityProbe()
    result = probe.probe(RECIPE, RECIPE, "system.modules[0].workflows[0].transitions[0]")
    assert result.target_gene_changed is False
    assert result.locality_holds is False


def test_b_c_locality_catches_unintended_change() -> None:
    probe = MutationLocalityProbe()
    mutated = _with_transition(RECIPE, "wf-orders", WorkflowTransition(
        id="t-x", name="x", from_state_id="await-payment", to_state_id="placed", trigger="collect_payment",
    ))
    mutated = _with_awaits(mutated, "placed", "collect_payment")
    result = probe.probe(RECIPE, mutated, "system.modules[0].workflows[0].transitions[1]")
    assert result.target_gene_changed is True
    assert result.unintended_changes != ()
    assert result.locality_holds is False


# -- D: round-trip per gene (compile -> artifact -> project) -----------------------

def test_d_round_trip_transition_gene() -> None:
    backend = FastAPIHexagonalBackend()
    before_text = backend.async_resolution_module(RECIPE.system.modules[0].workflows)
    coroutines_before, awaited_before = _project_async_resolution(before_text)
    assert "collect_payment" in coroutines_before
    assert "collect_payment" in awaited_before

    mutated = _with_transition(RECIPE, "wf-refunds", WorkflowTransition(
        id="t-refund", name="refund issued",
        from_state_id="refund-start", to_state_id="refund-done", trigger="issue_refund",
    ))
    after_text = backend.async_resolution_module(mutated.system.modules[0].workflows)
    coroutines_after, awaited_after = _project_async_resolution(after_text)
    assert "issue_refund" in coroutines_after
    assert "issue_refund" in awaited_after
    assert "issue_refund" not in awaited_before
    assert coroutines_before | awaited_before <= coroutines_after | awaited_after

    # compile determinism
    again = backend.async_resolution_module(mutated.system.modules[0].workflows)
    assert again == after_text


# -- E: invalid mutations rejected pre-execution ------------------------------------

def test_e_await_stripping_rejected_pre_execution() -> None:
    stripped = _with_awaits(RECIPE, "await-payment", "")
    invariant = AwaitingSurfaceIntactInvariant()
    ctx = GateContext(
        candidate_isr=stripped, candidate_artifact=None, candidate_run=None,
        baseline_artifact=None, baseline_run=None, observation=None,
        mutation=None, parent_isr=RECIPE,
    )
    assert invariant.holds(ctx) is False


def test_e_await_repoint_rejected_pre_execution() -> None:
    repointed = _with_awaits(RECIPE, "await-payment", "other_coroutine")
    invariant = AwaitingSurfaceIntactInvariant()
    ctx = GateContext(
        candidate_isr=repointed, candidate_artifact=None, candidate_run=None,
        baseline_artifact=None, baseline_run=None, observation=None,
        mutation=None, parent_isr=RECIPE,
    )
    assert invariant.holds(ctx) is False


def test_e_await_add_is_allowed() -> None:
    added = _with_awaits(RECIPE, "placed", "notify_shipped")
    invariant = AwaitingSurfaceIntactInvariant()
    ctx = GateContext(
        candidate_isr=added, candidate_artifact=None, candidate_run=None,
        baseline_artifact=None, baseline_run=None, observation=None,
        mutation=None, parent_isr=RECIPE,
    )
    assert invariant.holds(ctx) is True


def test_e_structural_invalidity_rejected_pre_execution() -> None:
    empty = ISR(system=System(id="x", name="X", modules=()))
    assert empty.validate_structure() is False
    duplicate = ISR(system=System(id="x", name="X", modules=(RECIPE.system.modules[0], RECIPE.system.modules[0])))
    assert duplicate.validate_structure() is False
    assert RECIPE.validate_structure() is True


# -- F: evidence per assessment -------------------------------------------------------

def test_f_evidence_per_assessment() -> None:
    audit = ISRCapabilityAudit()
    result = audit.run(RECIPE)
    for capability in result.capabilities:
        if capability.status is not CapabilityStatus.MISSING:
            assert capability.assessment.evidence, (
                f"{capability.capability_id} ({capability.status.value}) has no evidence"
            )
    audit_result_hash = result.content_hash()
    assert canonicalize({}) != audit_result_hash


# -- G: ledger chain-anchoring --------------------------------------------------------

def test_g_audit_record_is_chain_anchored(tmp_path: Path) -> None:
    ledger = EvolutionLedger(root=str(tmp_path))
    audit = ISRCapabilityAudit()
    result = audit.run(RECIPE)
    event_id = audit.record(result, ledger)
    assert ledger.verify_event_chain() is True
    events = ledger.events()
    assert len(events) == 1
    event = events[0]
    assert event.event_type is EventType.ISR_CAPABILITY_AUDIT
    assert event.isr_hash == result.isr_hash
    assert event.subject_id == result.content_hash()[:32]
    assert event.payload["audit_content_hash"] == result.content_hash()
    assert event.payload["integrity"] is True
    assert event.payload["summary"]["expressed"] == 6  # R2.10.3-A + B + C + D landed

    # tamper-evidence: editing any assessment field breaks the chain
    tampered = event.model_copy(update={"payload": {**event.payload, "summary": {"expressed": 99}}})
    assert tampered.computed_hash() != event.event_hash
    tampered_ledger = EvolutionLedger()
    tampered_ledger._events.append(tampered)
    assert tampered_ledger.verify_event_chain() is False

    # a second record links to the first (parent chain)
    event_id2 = audit.record(result, ledger, evolution_id="r2.10.1-rerun")
    assert event_id2 != event_id
    assert ledger.verify_event_chain() is True
    assert ledger.events()[1].parent_event_id == events[0].event_hash


# -- H: determinism ----------------------------------------------------------------------

def test_h_deterministic_exploration() -> None:
    explorer = RandomFSMExploration(trigger_pool=("audit-op",), max_candidates=1)
    c1 = explorer.generate(RECIPE, OBS, 1, seed=4242)
    c2 = explorer.generate(RECIPE, OBS, 1, seed=4242)
    assert len(c1) == len(c2)
    assert c1[0].candidate_id == c2[0].candidate_id
    assert c1[0].candidate_isr.content_hash == c2[0].candidate_isr.content_hash
    assert c1[0].mutation_delta == c2[0].mutation_delta


def test_h_deterministic_audit_and_compile() -> None:
    audit = ISRCapabilityAudit()
    r1 = audit.run(RECIPE)
    r2 = audit.run(RECIPE)
    assert r1.content_hash() == r2.content_hash()
    assert r1.summary() == r2.summary()
    assert gene_index(RECIPE) == gene_index(RECIPE)

    backend = FastAPIHexagonalBackend()
    text1 = backend.async_resolution_module(RECIPE.system.modules[0].workflows)
    text2 = backend.async_resolution_module(RECIPE.system.modules[0].workflows)
    assert text1 == text2