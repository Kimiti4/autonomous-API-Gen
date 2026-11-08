"""Unified full-stack orchestration authority (Checkpoint 055)."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from certification.orchestration.boundaries import assert_governed_request_kind
from certification.orchestration.contract import (
    FullStackOrchestrationRequest,
    IsrProvenance,
    OrchestrationLifecycleState,
    RequestKind,
)
from certification.orchestration.store import OrchestrationRunRecord, OrchestrationRunStore, new_run_id
from certification.orchestration.workload_registry import WorkloadSpec, get_workload_spec
from certification.product.evidence_manifest import build_candidate_evidence_manifest
from certification.product.evidence_registration import (
    populate_dimension_evidence,
    register_product_evidence_bundle,
)
from certification.product.product_acceptance import (
    ProductAcceptanceDecision,
    ProductAcceptanceReport,
    evaluate_independent_product_acceptance,
)
from compiler.core.canonical_api_contract import build_canonical_api_contract, contract_digest
from compiler.core.lowering import isr_to_plan
from constitutional_architecture.governance.candidate_promotion_lifecycle import (
    GovernedCandidatePromotionService,
    GovernanceCandidateStore,
)
from constitutional_architecture.governance.trusted_evidence_registry import TrustedEvidenceRegistry
from constitutional_architecture.governance.trusted_evidence_resolution import GovernedTrustedEvidenceService
from tiannara.application.engineering.senior_engineering_gate import (
    SeniorEngineeringVerdict,
    evaluate_senior_engineering_acceptance,
)


@dataclass(frozen=True)
class OrchestrationRunReport:
    run_id: str
    workload_id: str
    candidate_id: str
    state: OrchestrationLifecycleState
    isr_provenance: IsrProvenance
    revision_id: str
    artifact_sha256: str
    canonical_contract_digest: str
    full_stack_passed: bool
    full_stack_findings: tuple[str, ...]
    senior_verdict: SeniorEngineeringVerdict
    senior_blockers: tuple[str, ...]
    product_acceptance: ProductAcceptanceDecision
    governance_lifecycle_state: str | None
    evidence_ids: tuple[str, ...]
    transition_history: tuple[str, ...]
    blockers: tuple[str, ...]
    limitations: tuple[str, ...] = field(default_factory=tuple)
    isr_source_mode: str = "human_baseline"
    isr_content_hash_consumed: str = ""
    synthesis_binding_digest: str = ""
    plan_binding_digest: str = ""


class _CompileAdapter:
    def __init__(self, norm) -> None:
        self.candidate_id = norm.candidate_id
        self.artifact_sha256 = norm.artifact_sha256
        self.artifact_manifest_digest = norm.artifact_manifest_digest
        self.revision_id = norm.revision_id
        self.backend_compile_error = None if norm.backend_present else "backend-missing"
        self.frontend = norm.frontend
        self.backend = norm.backend


class FullStackOrchestrationAuthority:
    """Single mandatory coordinator for governed full-stack product generation."""

    AUTHORITY_ID = "tiannara.orchestration.full_stack.v1"

    def __init__(
        self,
        *,
        run_store: OrchestrationRunStore | None = None,
        evidence_registry_path: str | None = None,
        governance_store_path: str | None = None,
    ) -> None:
        self._store = run_store
        self._evidence_path = evidence_registry_path
        self._governance_path = governance_store_path

    def run(self, request: FullStackOrchestrationRequest) -> OrchestrationRunReport:
        assert_governed_request_kind(request.request_kind)
        from certification.orchestration.implir_ingress_guard import (
            assert_trusted_orchestration_ingress,
        )

        assert_trusted_orchestration_ingress(
            request.isr_ingress_authority,
            governed_lineage_ref=request.governed_lineage_ref,
        )
        spec = get_workload_spec(request.workload_id)
        run_id = request.run_id or new_run_id()
        record = OrchestrationRunRecord(
            run_id=run_id,
            workload_id=spec.workload_id,
            candidate_id="",
            state=OrchestrationLifecycleState.REQUEST_RECEIVED,
            revision_id="",
            artifact_sha256="",
            isr_provenance=spec.isr_provenance.value,
            created_at=_now(),
            updated_at=_now(),
        )
        from certification.orchestration.isr_source import IsrSourceMode

        limitations: list[str] = []
        isr_source = IsrSourceMode(request.isr_source_mode)
        synthesis_provenance = None
        consumed_provenance = spec.isr_provenance
        try:
            record.transition(OrchestrationLifecycleState.REQUIREMENTS_PENDING)
            requirements = spec.requirements_fn()
            if not requirements.nodes:
                raise ValueError("orchestration-requirements-empty")
            record.transition(OrchestrationLifecycleState.REQUIREMENTS_APPROVED)

            record.transition(OrchestrationLifecycleState.ISR_PENDING)
            consumed_provenance = spec.isr_provenance
            if isr_source is IsrSourceMode.HUMAN_BASELINE:
                revision = spec.revision_fn()
                limitations.append(f"ISR provenance: {spec.isr_provenance.value}")
            else:
                from certification.synthesis.pipeline import (
                    assert_gate_for_orchestration,
                    synthesize_for_workload,
                )
                from reqgraph.synthesis.provenance import SynthesisProvenanceClass

                pclass = (
                    SynthesisProvenanceClass.HUMAN_APPROVED_SYNTHESIZED
                    if isr_source is IsrSourceMode.HUMAN_APPROVED_SYNTHESIZED
                    else SynthesisProvenanceClass.AUTO_SYNTHESIZED
                )
                requirements, revision, synthesis_provenance = synthesize_for_workload(
                    spec.workload_id,
                    provenance_class=pclass,
                    human_approval_ref=request.lineage.get("human_approval_ref", ""),
                )
                binding = request.synthesis_binding_digest or synthesis_provenance.binding_digest()
                if (
                    request.synthesis_binding_digest
                    and binding != synthesis_provenance.binding_digest()
                ):
                    raise ValueError("orchestration-synthesis-binding-mismatch")
                assert_gate_for_orchestration(
                    requirements,
                    synthesis_provenance,
                    binding_digest=binding,
                )
                if revision.content_hash != synthesis_provenance.isr_content_hash:
                    raise ValueError("orchestration-isr-digest-mismatch")
                consumed_provenance = (
                    IsrProvenance.HUMAN_APPROVED_SYNTHESIZED
                    if pclass is SynthesisProvenanceClass.HUMAN_APPROVED_SYNTHESIZED
                    else IsrProvenance.AUTO_SYNTHESIZED
                )
                record.isr_provenance = consumed_provenance.value
                limitations.append(f"ISR consumed digest: {revision.content_hash[:16]}…")
                limitations.append(f"Synthesis run: {synthesis_provenance.synthesis_run_id}")
            from isr.core.digest_verification import assert_certification_digest_envelope
            from isr.core.revision_integrity import assert_revision_integrity_at_boundary

            assert_revision_integrity_at_boundary(revision)
            _ = assert_certification_digest_envelope(revision)
            record.transition(OrchestrationLifecycleState.ISR_VALIDATED)
            record.revision_id = revision.revision_id

            plan = isr_to_plan(revision)
            from certification.orchestration.plan_binding_gate import (
                assert_plan_binding_before_compile,
            )

            plan_binding = assert_plan_binding_before_compile(
                revision,
                plan,
                expected_plan_digest=request.plan_binding_digest,
                backend_id=request.frontend_backend_id,
            )
            limitations.append(f"Plan binding digest: {plan_binding.plan_digest[:16]}…")
            _ = build_canonical_api_contract(plan)
            record.transition(OrchestrationLifecycleState.PLAN_APPROVED)

            record.transition(OrchestrationLifecycleState.COMPILING)
            if isr_source is not IsrSourceMode.HUMAN_BASELINE:
                from certification.synthesis.compile_bridge import compile_workload_with_revision

                compiled = compile_workload_with_revision(spec.workload_id, revision)
            else:
                compiled = spec.compile_fn()
            record.candidate_id = compiled.candidate_id
            if not compiled.backend_present:
                raise ValueError("orchestration-backend-compile-failed")
            record.artifact_sha256 = compiled.artifact_sha256
            record.transition(OrchestrationLifecycleState.ARTIFACTS_GENERATED)

            record.transition(OrchestrationLifecycleState.INTEGRATION_VERIFYING)
            verify = spec.verify_fn(compiled.plan)
            record.transition(OrchestrationLifecycleState.BEHAVIOR_VERIFYING)
            if any(f.startswith("mandatory:") for f in verify.findings):
                record.transition(
                    OrchestrationLifecycleState.REJECTED,
                    reason="mandatory-full-stack-finding",
                )
                return self._fail_report(record, verify, limitations, request)

            record.transition(OrchestrationLifecycleState.SENIOR_REVIEW_PENDING)
            frontend_evidence: dict[str, str] = {}
            backend_evidence: dict[str, str] = {}
            if (
                request.populate_senior_dimensions
                and self._evidence_path
            ):
                reg = TrustedEvidenceRegistry(self._evidence_path)
                svc = GovernedTrustedEvidenceService(reg)
                frontend_evidence, backend_evidence = populate_dimension_evidence(
                    svc,
                    candidate_id=compiled.candidate_id,
                    artifact_sha256=compiled.artifact_sha256,
                    revision_id=compiled.revision_id,
                )

            engineering = evaluate_senior_engineering_acceptance(
                generator_id=request.generator_id,
                reviewer_id=request.reviewer_id,
                verifier_id=request.verifier_id,
                frontend_evidence=frontend_evidence,
                backend_evidence=backend_evidence,
                frontend_operations=compiled.frontend_operations,
                backend_operations=compiled.backend_operations,
                persistence_entities=compiled.persistence_entities,
                backend_persisted_entities=compiled.persistence_entities
                if compiled.backend_present
                else (),
                shared_auth_models=compiled.shared_auth_models,
                external_coherence_findings=verify.findings,
                evidence_service=(
                    GovernedTrustedEvidenceService(TrustedEvidenceRegistry(self._evidence_path))
                    if self._evidence_path
                    else None
                ),
                candidate_id=compiled.candidate_id,
                artifact_sha256=compiled.artifact_sha256,
            )
            senior_verdict = engineering.verdict
            senior_blockers = engineering.blockers

            evidence_ids: tuple[str, ...] = ()
            governance_state: str | None = None
            blockers = list(senior_blockers)
            if senior_verdict is SeniorEngineeringVerdict.ACCEPTANCE_BLOCKED:
                blockers.append("senior-engineering-blocked")

            if self._evidence_path and self._governance_path:
                record.transition(OrchestrationLifecycleState.EVIDENCE_REGISTERING)
                manifest = build_candidate_evidence_manifest(
                    candidate_id=compiled.candidate_id,
                    domain=spec.workload_id,
                    source_revision=compiled.revision_id,
                    artifact_sha256=compiled.artifact_sha256,
                    artifact_manifest_digest=compiled.artifact_manifest_digest,
                    plan=compiled.plan,
                )
                svc = GovernedTrustedEvidenceService(
                    TrustedEvidenceRegistry(self._evidence_path)
                )
                bundle = register_product_evidence_bundle(
                    svc,
                    compile_result=_CompileAdapter(compiled),
                    manifest=manifest,
                    domain=spec.workload_id,
                    full_stack_summary=";".join(verify.findings[:8]) or "ok",
                    domain_evidence_label=f"orchestration:{spec.workload_id}",
                    domain_provenance={
                        "authority_id": self.AUTHORITY_ID,
                        "run_id": run_id,
                    },
                )
                promo = GovernedCandidatePromotionService(
                    GovernanceCandidateStore(self._governance_path),
                    svc,
                )
                gov_rec = promo.evaluate_and_stage(
                    candidate_id=compiled.candidate_id,
                    artifact_bytes=compiled.artifact_bytes,
                    artifact_manifest_digest=compiled.artifact_manifest_digest,
                    source_revision=compiled.revision_id,
                    evidence_ids=bundle.primary_ids + (bundle.domain_evidence_id,),
                )
                governance_state = gov_rec.state.value
                evidence_ids = bundle.primary_ids + (bundle.domain_evidence_id,)
                record.transition(OrchestrationLifecycleState.PRODUCT_ACCEPTANCE_PENDING)
                acceptance = evaluate_independent_product_acceptance(
                    senior_verdict=senior_verdict,
                    senior_blockers=senior_blockers,
                    governance_eligible=False,
                    governance_blockers=(
                        f"{spec.workload_id}-candidate-not-certified:{governance_state}",
                    ),
                    statutory_satisfied=spec.workload_id != "payroll"
                    or senior_verdict is not SeniorEngineeringVerdict.ACCEPTANCE_BLOCKED,
                    runtime_evidence_registered=True,
                    manifest_evidence_registered=True,
                    durable_evidence_registered=True,
                    candidate_certified=False,
                    lifecycle_awaiting_governance=True,
                )
                record.transition(OrchestrationLifecycleState.AWAITING_GOVERNANCE)
                product_decision = acceptance.decision
                blockers.extend(acceptance.blockers)
            else:
                product_decision = ProductAcceptanceDecision.ACCEPTANCE_BLOCKED
                blockers.append("orchestration-governance-path-unconfigured")

            contract = build_canonical_api_contract(compiled.plan)
            binding_digest = ""
            if synthesis_provenance is not None:
                binding_digest = synthesis_provenance.binding_digest()
            report = OrchestrationRunReport(
                run_id=run_id,
                workload_id=spec.workload_id,
                candidate_id=compiled.candidate_id,
                state=record.state,
                isr_provenance=consumed_provenance,
                revision_id=compiled.revision_id,
                artifact_sha256=compiled.artifact_sha256,
                canonical_contract_digest=contract_digest(contract),
                full_stack_passed=verify.passed,
                full_stack_findings=verify.findings,
                senior_verdict=senior_verdict,
                senior_blockers=senior_blockers,
                product_acceptance=product_decision,
                governance_lifecycle_state=governance_state,
                evidence_ids=evidence_ids,
                transition_history=record.transition_history,
                blockers=tuple(dict.fromkeys(blockers)),
                limitations=tuple(dict.fromkeys(limitations)),
                isr_source_mode=isr_source.value,
                isr_content_hash_consumed=revision.content_hash,
                synthesis_binding_digest=binding_digest,
                plan_binding_digest=plan_binding.plan_digest,
            )
            if self._store:
                self._store.save(record)
            return report
        except ValueError as exc:
            record.transition(OrchestrationLifecycleState.FAILED, reason=str(exc))
            if self._store:
                self._store.save(record)
            raise

    def recover_run(self, run_id: str) -> OrchestrationRunRecord | None:
        if self._store is None:
            return None
        return self._store.load(run_id)

    def assert_artifact_lineage(
        self,
        run_id: str,
        *,
        candidate_id: str,
        artifact_sha256: str,
    ) -> OrchestrationRunRecord:
        rec = self.recover_run(run_id)
        if rec is None:
            raise ValueError("orchestration-run-unknown")
        if rec.candidate_id != candidate_id:
            raise ValueError("orchestration-candidate-mismatch")
        if rec.artifact_sha256 != artifact_sha256:
            raise ValueError("orchestration-artifact-digest-mismatch")
        return rec

    def _fail_report(
        self,
        record: OrchestrationRunRecord,
        verify,
        limitations: tuple[str, ...],
        request: FullStackOrchestrationRequest,
    ) -> OrchestrationRunReport:
        if self._store:
            self._store.save(record)
        return OrchestrationRunReport(
            run_id=record.run_id,
            workload_id=record.workload_id,
            candidate_id=record.candidate_id,
            state=record.state,
            isr_provenance=IsrProvenance.HUMAN_AUTHORED_IMPORTED,
            revision_id=record.revision_id,
            artifact_sha256=record.artifact_sha256,
            canonical_contract_digest="",
            full_stack_passed=False,
            full_stack_findings=verify.findings,
            senior_verdict=SeniorEngineeringVerdict.ACCEPTANCE_BLOCKED,
            senior_blockers=(),
            product_acceptance=ProductAcceptanceDecision.ACCEPTANCE_BLOCKED,
            governance_lifecycle_state=None,
            evidence_ids=(),
            transition_history=record.transition_history,
            blockers=verify.findings,
            limitations=limitations,
        )


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def isr_revision_digest(revision) -> str:
    payload = json.dumps(
        revision.revision_id,
        sort_keys=True,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def run_canonical_full_stack(
    workload_id: str,
    *,
    evidence_registry_path: str | None = None,
    governance_store_path: str | None = None,
    orchestration_store_path: str | None = None,
    populate_senior_dimensions: bool = False,
    isr_source_mode: str = "human_baseline",
    synthesis_binding_digest: str = "",
    isr_ingress_authority: str = "isr.core.revision",
    governed_lineage_ref: str = "",
    plan_binding_digest: str = "",
) -> OrchestrationRunReport:
    """Composition root for all governed full-stack workloads."""
    store = (
        OrchestrationRunStore(orchestration_store_path)
        if orchestration_store_path
        else None
    )
    auth = FullStackOrchestrationAuthority(
        run_store=store,
        evidence_registry_path=evidence_registry_path,
        governance_store_path=governance_store_path,
    )
    return auth.run(
        FullStackOrchestrationRequest(
            workload_id=workload_id,
            request_kind=RequestKind.FULL_STACK_PRODUCT,
            populate_senior_dimensions=populate_senior_dimensions,
            isr_source_mode=isr_source_mode,
            synthesis_binding_digest=synthesis_binding_digest,
            isr_ingress_authority=isr_ingress_authority,
            governed_lineage_ref=governed_lineage_ref,
            plan_binding_digest=plan_binding_digest,
        )
    )
