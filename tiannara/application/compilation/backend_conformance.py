"""R2.10.7 — real-backend conformance audit behind the frozen R2.10.6 contract.

R2.10.6 fixed the consumption contract and the eight-gate certifier; R2.10.7
is the first time the contract meets backends that were built BEFORE it
existed (the Phase 8-22 compilers under ``constitutional_architecture/
compilers/``). Governing principle, locked before implementation:

    Conform the backends to the contract. NEVER weaken the contract to
    fit a backend.

A failing gate is a FINDING to remediate, never a gate to weaken: the
evaluator has no gate-weakening surface, applies the eight gates unchanged,
and records every finding in the durable conformance report.

Audit finding (pre-implementation, recorded): all seven real backends
consume the pre-contract input surface (``UniversalISR`` object graph +
``ArchitectureGenome`` genes) — none has a model-consumption seam. The
``BackendConformanceAdapter`` is the remediation: it routes the compilation
through the ``BackendSemanticModel`` projection (never the semantic ISR
object graph), translates the projection deterministically into the real
backend's native inputs, and wraps the real backend's ``CompilationBundle``
in a provenance-bound artifact. The real backend's generation logic is
invoked read-only; the adapter gives it no ISR-mutation surface.

The deliverable is the ``BackendConformanceReport``: the platform's first
evidence-based map of what each real backend realizes (capability coverage),
which contract gates it satisfies, and what remains to remediate.
"""
from __future__ import annotations

import dataclasses
import inspect
import pathlib
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from constitutional_architecture.core.models.bundle import CompilationBundle
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.isr import (
    ISRNode,
    NodeType,
    UniversalISR,
)
from constitutional_architecture.isr.semantics.projection import (
    canonical_form,
    semantic_content_hash,
)

from .consumption_contract import (
    BackendSemanticModel,
    CapabilityCoverage,
    CapabilitySupport,
    CompilationProvenance,
    CompilationResult,
    CompilationTarget,
    CompilerBackend,
    ContaminationGuard,
    derive_backend_semantic_model,
    enumerate_isr_semantics,
)
from .integrity_gate import CompilationIntegrityGate


# -- the explicit capability declaration ---------------------------------------

@dataclass(frozen=True)
class BackendCapabilityDeclaration:
    """A backend's EXPLICIT declaration of which ISR semantics it realizes.

    SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED — silent omission is
    impossible because Gate D checks the declared coverage against the full
    semantic enumeration of the ISR. An undeclared semantic defaults to
    UNSUPPORTED (honest by default, never silently skipped).

    Two vocabularies are supported:

    - the 14 carrier ids (the gate-level enumeration, e.g. ``behavior``,
      ``requirement``) — the R2.10.7 original shape; and
    - the 12 capability ids (the user's R2.10.7-expansion vocabulary, e.g.
      ``behavior_transitions``, ``requirements_acceptance_traceability``),
      each grouping one or more carriers via ``CAPABILITY_TO_CARRIERS``.
      The adapter expands the 12 onto the 14 for the gate-level coverage.
    """

    backend_id: str
    declarations: Mapping[str, CapabilitySupport]

    def support_for(self, semantic_id: str) -> CapabilitySupport:
        return self.declarations.get(semantic_id, CapabilitySupport.UNSUPPORTED)


# The 12 capability ids -> the 14 gate-level carriers they group.
CAPABILITY_TO_CARRIERS: Mapping[str, tuple[str, ...]] = {
    "behavior_transitions": ("behavior",),
    "behavior_await_surface": ("behavior",),
    "temporal_semantics": ("temporal",),
    "business_capabilities": ("capability",),
    "data_migrations": ("migration",),
    "reliability_resilience": ("reliability",),
    "architecture_boundaries": ("boundary",),
    "requirements_acceptance_traceability": ("requirement", "acceptance_criterion"),
    "deployment_rollout_rollback": ("deployment",),
    "testing_anchoring": ("testing_anchor",),
    "documentation": ("documentation",),
    "evolution_objectives_protected_regions": (
        "evolution_objective",
        "protected_region",
        "evolution_policy",
    ),
}

_SUPPORT_ORDER: Mapping[CapabilitySupport, int] = {
    CapabilitySupport.SUPPORTED: 3,
    CapabilitySupport.PARTIALLY_SUPPORTED: 2,
    CapabilitySupport.UNSUPPORTED: 1,
}


def _resolve_support(
    declaration: BackendCapabilityDeclaration, carrier_id: str
) -> CapabilitySupport:
    """Gate-level support for one carrier: a direct declaration wins; a
    12-capability declaration is expanded onto its carriers with the
    best-of-facets merge (a carrier with ANY supported facet is at least
    PARTIALLY_SUPPORTED — the degradation is carried, never hidden)."""
    if carrier_id in declaration.declarations:
        return declaration.support_for(carrier_id)
    facets = tuple(
        capability_id
        for capability_id, carriers in CAPABILITY_TO_CARRIERS.items()
        if carrier_id in carriers
    )
    if not facets:
        return CapabilitySupport.UNSUPPORTED
    return max(
        (declaration.support_for(facet) for facet in facets),
        key=_SUPPORT_ORDER.get,
    )


_SUPPORT_NOTES: Mapping[CapabilitySupport, str] = {
    CapabilitySupport.SUPPORTED: "declared: realized by this backend",
    CapabilitySupport.PARTIALLY_SUPPORTED: (
        "declared: partially realized (see conformance findings)"
    ),
    CapabilitySupport.UNSUPPORTED: "declared: not realized by this backend",
}


# -- projection-only translation to the real backend's native inputs -----------

@dataclass(frozen=True)
class UniversalInputs:
    """The universal input surface the real backends' native entrypoints
    consume: the translated graph (UniversalISR), the genome, the context
    dict, and — for meta-compilers — the deployment bundle."""

    universal_isr: UniversalISR
    genome: ArchitectureGenome
    context: dict
    system_bundle: Any = None


class ProjectionSeam:
    """Backend-specific translation: BackendSemanticModel -> UniversalInputs.
    Projection-only — the seam never reaches into the semantic ISR itself."""

    def translate(self, model: BackendSemanticModel) -> UniversalInputs:
        raise NotImplementedError


def translate_projection_to_universal_inputs(
    model: BackendSemanticModel,
) -> tuple[UniversalISR, ArchitectureGenome, dict]:
    """Deterministically translate the projection boundary into the real
    backends' native input surface (UniversalISR + ArchitectureGenome).

    PROJECTION-ONLY discipline: every node is derived from the model's
    canonical constraints — the real backend never receives the semantic ISR
    object graph. Behaviors (workflows) become SERVICE nodes; capabilities
    become CAPABILITY nodes. Structural genes (entities, interfaces, events)
    are NOT carried by the 14-semantic projection — the adapter records that
    as a conformance finding rather than inventing content.
    """
    nodes: dict[str, ISRNode] = {}
    for kind, form in model.constraints:
        if kind == "behavior":
            workflow_id = str(form.get("id") or "unknown")
            nodes[f"svc_{workflow_id}"] = ISRNode(
                id=f"svc_{workflow_id}",
                type=NodeType.SERVICE,
                semantic_attributes={
                    "capability": str(form.get("name") or workflow_id),
                    "behavior_id": workflow_id,
                },
            )
        elif kind == "capability":
            capability_id = str(form.get("capability_id") or "unknown")
            nodes[f"cap_{capability_id}"] = ISRNode(
                id=f"cap_{capability_id}",
                type=NodeType.CAPABILITY,
                semantic_attributes={
                    "capability": str(form.get("intent") or capability_id),
                },
            )
    universal = UniversalISR(nodes=nodes, edges=[])
    genome = ArchitectureGenome()
    return universal, genome, {}


class FastAPIProjectionSeam(ProjectionSeam):
    """The FastAPI seam (R2.10.7 original): behaviors -> SERVICE + CAPABILITY
    nodes. Kept as the default seam so the frozen R2.10.7 adapter behaves
    identically."""

    def translate(self, model: BackendSemanticModel) -> UniversalInputs:
        universal, genome, context = translate_projection_to_universal_inputs(
            model
        )
        return UniversalInputs(
            universal_isr=universal, genome=genome, context=context
        )


# -- the conformance adapter ----------------------------------------------------

class BackendConformanceAdapter(CompilerBackend):
    """Wraps a pre-contract real backend behind the frozen CompilerBackend.

    The seam where an existing backend is brought into conformance: it
    consumes the BackendSemanticModel (never the raw semantic ISR object
    graph), derives the semantic projection deterministically, translates it
    into the real backend's native inputs through its projection seam, invokes
    the real generation logic READ-ONLY, and wraps the resulting bundle in a
    provenance-bound artifact that re-declares its semantic source (Gate F
    round-trips through it). Coverage comes from the backend's explicit
    declaration.

    A backend whose native entrypoint is ``compile_system(bundle, context)``
    (the CI/CD meta-compiler) is dispatched through the bundle seam — the
    adapter routes to the entrypoint the real backend actually implements.
    """

    def __init__(
        self,
        backend_id: str,
        backend_version: str,
        real_backend: Any,
        declaration: BackendCapabilityDeclaration,
        projection_seam: Any = None,
        findings: tuple[str, ...] = (),
    ) -> None:
        self.backend_id = backend_id
        self.backend_version = backend_version
        self._real_backend = real_backend
        self._declaration = declaration
        self._projection_seam = projection_seam or FastAPIProjectionSeam()
        self.findings = findings

    # -- the projection boundary -------------------------------------------------

    def semantic_projection(self, isr: Any) -> BackendSemanticModel:
        return derive_backend_semantic_model(isr)

    # -- declared coverage --------------------------------------------------------

    def coverage_for(self, isr: Any) -> tuple[CapabilityCoverage, ...]:
        semantics = enumerate_isr_semantics(isr)
        return tuple(
            CapabilityCoverage(
                capability_id=semantic_id,
                support=_resolve_support(self._declaration, semantic_id),
                note=_SUPPORT_NOTES[
                    _resolve_support(self._declaration, semantic_id)
                ],
            )
            for semantic_id in sorted(semantics)
        )

    # -- the read-only compile -----------------------------------------------------

    def compile(
        self, isr: Any, target: CompilationTarget
    ) -> CompilationResult:
        model = self.semantic_projection(isr)
        inputs = self._projection_seam.translate(model)
        if hasattr(self._real_backend, "compile_system"):
            bundle = self._real_backend.compile_system(
                inputs.system_bundle, inputs.context
            )
        else:
            bundle = self._real_backend.compile(
                inputs.universal_isr, inputs.genome, inputs.context
            )
        coverage = self.coverage_for(isr)
        artifact = {
            "semantic_source": {
                "isr_hash": model.source_isr_hash,
                "model_hash": model.model_hash,
            },
            "bundle": bundle.model_dump(mode="json"),
            "target": canonical_form(target),
            "coverage": [
                {
                    "capability_id": item.capability_id,
                    "support": item.support.value,
                    "note": item.note,
                }
                for item in coverage
            ],
        }
        from constitutional_architecture.isr.semantics.projection import canonicalize
        import hashlib

        artifact_hash = hashlib.sha256(
            canonicalize(artifact).encode("utf-8")
        ).hexdigest()
        return CompilationResult(
            artifact=artifact,
            isr_hash=model.source_isr_hash,
            target_id=target.target_id,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            artifact_hash=artifact_hash,
            provenance=CompilationProvenance(
                isr_hash=model.source_isr_hash,
                target_id=target.target_id,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                model_hash=model.model_hash,
            ),
            capability_coverage=coverage,
        )


# -- the durable conformance report ----------------------------------------------

@dataclass(frozen=True)
class BackendConformanceReport:
    """The durable conformance artifact for one backend — the evidence-based
    map of what the backend realizes and which contract gates it satisfies.

    A failure is recorded, never papered over: ``conforms`` requires every
    gate to hold AND zero contamination findings. ``findings`` carries
    remediation notes (projection gaps, pre-contract input surface) that do
    not by themselves block conformance but are recorded, never forgotten.
    """

    backend_id: str
    backend_version: str
    gate_results: tuple[Any, ...]
    capability_coverage: tuple[CapabilityCoverage, ...]
    contamination_findings: tuple[str, ...]
    findings: tuple[str, ...]
    isr_semantic_hash_at_conformance: str

    @property
    def conforms(self) -> bool:
        return (
            all(gate.held for gate in self.gate_results)
            and not self.contamination_findings
        )

    @property
    def failed_gates(self) -> tuple[str, ...]:
        return tuple(
            gate.gate_id for gate in self.gate_results if not gate.held
        )

    def coverage_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for item in self.capability_coverage:
            summary[item.support.value] = summary.get(item.support.value, 0) + 1
        return summary


# -- the evaluator ---------------------------------------------------------------

def _projection_gap_findings(isr: Any) -> tuple[str, ...]:
    """Structural genes the 14-semantic projection does not carry: entities,
    interfaces, events live inside Module but are not part of the semantic
    enumeration, so no backend can realize them through the contract alone."""
    findings: list[str] = []
    entity_count = sum(
        len(module.entities) for module in isr.system.modules
    )
    interface_count = sum(
        len(module.interfaces) for module in isr.system.modules
    )
    event_count = sum(len(module.events) for module in isr.system.modules)
    if entity_count or interface_count or event_count:
        findings.append(
            "structural genes outside the 14-semantic projection: "
            f"{entity_count} entities, {interface_count} interfaces, "
            f"{event_count} events are not carried by BackendSemanticModel — "
            "the backend cannot realize them through the contract; declared "
            "coverage governs (remediation: extend the projection surface)"
        )
    return tuple(findings)


class BackendConformanceEvaluator:
    """Conforms real backends to the FROZEN R2.10.6 contract.

    The eight gates are applied unchanged through the integrity gate; the
    three-layer contamination guard adds its findings; every finding lands
    in the durable report. This evaluator has no gate-weakening surface.
    """

    def __init__(
        self,
        integrity_gate: CompilationIntegrityGate,
        contamination_guard: ContaminationGuard,
        ledger: Any = None,
    ) -> None:
        self._integrity_gate = integrity_gate
        self._contamination_guard = contamination_guard
        self._ledger = ledger

    def conform(
        self,
        adapter: BackendConformanceAdapter,
        isr: Any,
        target: CompilationTarget,
    ) -> BackendConformanceReport:
        verdict = self._integrity_gate.verify(
            isr, target, adapter, ledger=self._ledger
        )
        coverage = adapter.coverage_for(isr)
        contamination: list[str] = []
        findings: list[str] = []

        # Layer 1 — the real backend's module is structurally read-only.
        try:
            module_file = pathlib.Path(
                inspect.getsourcefile(adapter._real_backend.__class__)
            )
            self._contamination_guard.assert_backend_module_is_read_only(
                module_file
            )
        except (AssertionError, TypeError) as exc:
            contamination.append(str(exc))

        # Layer 2 — the ISR stays technology-neutral under the real compile.
        try:
            self._contamination_guard.assert_isr_technology_neutral(isr)
        except AssertionError as exc:
            contamination.append(str(exc))

        # The real compile (read-only; the ISR is never touched).
        result = adapter.compile(isr, target)

        # Layer 3 — no reverse contamination flows artifact -> ISR.
        try:
            self._contamination_guard.assert_no_reverse_contamination(result)
        except AssertionError as exc:
            contamination.append(str(exc))

        findings.extend(adapter.findings)
        findings.extend(_projection_gap_findings(isr))
        findings.append(
            "pre-contract input surface: the real backend consumes its "
            "native input model; the adapter routes the compilation through "
            "BackendSemanticModel (conformance remediation)"
        )

        return BackendConformanceReport(
            backend_id=adapter.backend_id,
            backend_version=adapter.backend_version,
            gate_results=verdict.gates,
            capability_coverage=coverage,
            contamination_findings=tuple(contamination),
            findings=tuple(findings),
            isr_semantic_hash_at_conformance=semantic_content_hash(isr),
        )

    def record_report(self, report: BackendConformanceReport) -> str:
        """Chain-anchor the durable report alongside the COMPILATION events
        (the evidence substrate is the only trust boundary)."""
        if self._ledger is None:
            raise ValueError(
                "no evidence ledger bound — a conformance report without "
                "chain-anchored evidence cannot be certified"
            )
        return self._ledger.record_conformance(report)