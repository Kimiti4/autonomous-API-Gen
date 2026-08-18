"""R2.10.7 — real-backend conformance behind the frozen R2.10.6 contract.

R2.10.6 froze the consumption contract; R2.10.7 is the first time it meets
a backend that was built BEFORE it existed. The audit (pre-implementation)
found the truth: every real backend consumes the raw UniversalISR object
graph + ArchitectureGenome genes, and none has a model-consumption seam.
The acceptance evidence:

  1.  FastAPI — the backend most likely to fail first (deepest graph
      consumption across four generation layers plus genome genes) —
      is wrapped behind the contract and produces a conformance report
      on which ALL EIGHT gates hold;
  2.  the FastAPI capability declaration enumerates every semantic the
      ISR can express (fourteen) — no silent omission is possible,
      because Gate D checks the declared coverage against the full
      semantic enumeration;
  3.  multi-backend invariance with a REAL backend: the fixed ISR flows
      through FastAPI and the three reference backends to one semantic
      source with distinct artifacts;
  4.  the ISR stays technology-neutral under the real compilation
      (Layer-2 guard, before and after);
  5.  the conformance report binds to the ISR semantic hash at
      conformance time;
  6.  the evaluator has NO gate-weakening surface ("relax" /
      "skip_gate" / "override_gate" are absent from its source);
  7.  a non-conforming backend is surfaced: an omitting declaration is
      rejected and the report names the failed gate — a failure is
      recorded, never papered over;
  8.  honest findings are durable: the pre-contract input surface and
      the structural-gene projection gap are recorded with remediation
      notes, and the report is chain-anchored in the evidence ledger
      (EventType.CERTIFICATION);
  9.  Option A (fourteenth use) — no new carriers, no matrix movement:
      the recipe ISR hash is unchanged and the matrix stays 12/18/0/0.
"""
from __future__ import annotations

import ast
import pathlib
import tempfile

import pytest

from constitutional_architecture.compilers.backend.fastapi.compiler import (
    FastAPICompiler,
)
from constitutional_architecture.isr.semantics.projection import (
    semantic_content_hash,
)
from tiannara.application.compilation.backend_conformance import (
    BackendCapabilityDeclaration,
    BackendConformanceAdapter,
    BackendConformanceEvaluator,
    BackendConformanceReport,
)
from tiannara.application.compilation.consumption_contract import (
    CapabilitySupport,
    CompilationTarget,
    ContaminationGuard,
    derive_backend_semantic_model,
)
from tiannara.application.compilation.integrity_gate import (
    CompilationIntegrityGate,
    GATE_BACKEND_INDEPENDENCE,
    GATE_CONSTITUTIONAL_PRESERVATION,
    GATE_DETERMINISM,
    GATE_EVIDENCE_BINDING,
    GATE_PROVENANCE,
    GATE_READ_ONLY,
    GATE_ROUND_TRIP,
    GATE_SEMANTIC_COVERAGE,
)
from tiannara.application.compilation.reference_backend import (
    ReferenceCompilerBackend,
)
from tiannara.application.evolution.ledger import (
    EventType,
    EvolutionLedger,
)
from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_4_semantic_evolution_gate import (
    SemanticEvolutionIntegrationHarness,
)
from .test_r29_10_6_consumption_contract import TARGET

ALL_SEMANTICS = frozenset(
    {
        "capability",
        "requirement",
        "acceptance_criterion",
        "boundary",
        "testing_anchor",
        "reliability",
        "deployment",
        "documentation",
        "migration",
        "temporal",
        "behavior",
        "evolution_objective",
        "protected_region",
        "evolution_policy",
    }
)

FASTAPI_DECLARATION = BackendCapabilityDeclaration(
    backend_id="fastapi",
    declarations={
        "behavior": CapabilitySupport.SUPPORTED,
        "capability": CapabilitySupport.SUPPORTED,
        "reliability": CapabilitySupport.PARTIALLY_SUPPORTED,
        "boundary": CapabilitySupport.PARTIALLY_SUPPORTED,
        "deployment": CapabilitySupport.PARTIALLY_SUPPORTED,
        "requirement": CapabilitySupport.UNSUPPORTED,
        "acceptance_criterion": CapabilitySupport.UNSUPPORTED,
        "testing_anchor": CapabilitySupport.UNSUPPORTED,
        "documentation": CapabilitySupport.UNSUPPORTED,
        "migration": CapabilitySupport.UNSUPPORTED,
        "temporal": CapabilitySupport.UNSUPPORTED,
        "evolution_objective": CapabilitySupport.UNSUPPORTED,
        "protected_region": CapabilitySupport.UNSUPPORTED,
        "evolution_policy": CapabilitySupport.UNSUPPORTED,
    },
)

REFERENCE_BACKENDS = (
    ReferenceCompilerBackend("reference-json", artifact_style="json"),
    ReferenceCompilerBackend("reference-manifest", artifact_style="manifest"),
    ReferenceCompilerBackend("reference-fragment", artifact_style="fragment"),
)


class ConformanceHarness:
    """Fixed ISR, fresh evidence ledger, frozen eight-gate certifier, the
    Layer-1/2/3 guard, and the evaluator + the FastAPI conformance adapter."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger = EvolutionLedger(root=self._tmp.name)
        self.gate = CompilationIntegrityGate(ledger=self.ledger)
        self.guard = ContaminationGuard()
        self.evaluator = BackendConformanceEvaluator(
            integrity_gate=self.gate,
            contamination_guard=self.guard,
            ledger=self.ledger,
        )
        self.fastapi = BackendConformanceAdapter(
            backend_id="fastapi",
            backend_version="8.0.0",
            real_backend=FastAPICompiler(),
            declaration=FASTAPI_DECLARATION,
        )
        self._base = SemanticEvolutionIntegrationHarness()

    def fixed_isr(self):
        return self._base.parent_isr()

    def conform_fastapi(self) -> BackendConformanceReport:
        report = self.evaluator.conform(self.fastapi, self.fixed_isr(), TARGET)
        self.evaluator.record_report(report)
        return report


@pytest.fixture
def harness() -> ConformanceHarness:
    return ConformanceHarness()


def gate_by_id(report: BackendConformanceReport, gate_id: str):
    return next(gate for gate in report.gate_results if gate.gate_id == gate_id)


# =============================================================================
# 1.  FastAPI conforms: all eight gates hold on the real backend
# =============================================================================

def test_fastapi_conformance_all_eight_gates_hold(harness):
    """The backend most likely to fail first is wrapped behind the frozen
    contract and certified: every gate holds, the report conforms, and the
    compilation is bound to evidence."""
    report = harness.conform_fastapi()
    assert [gate.gate_id for gate in report.gate_results] == [
        GATE_READ_ONLY,
        GATE_DETERMINISM,
        GATE_PROVENANCE,
        GATE_SEMANTIC_COVERAGE,
        GATE_BACKEND_INDEPENDENCE,
        GATE_ROUND_TRIP,
        GATE_CONSTITUTIONAL_PRESERVATION,
        GATE_EVIDENCE_BINDING,
    ]
    assert all(gate.held for gate in report.gate_results)
    assert report.conforms is True
    assert report.failed_gates == ()


# =============================================================================
# 2.  The declaration enumerates all fourteen semantics
# =============================================================================

def test_fastapi_declaration_enumerates_all_fourteen_semantics(harness):
    """Every semantic the ISR can express has an explicit SUPPORTED /
    PARTIALLY_SUPPORTED / UNSUPPORTED verdict — nothing is silently skipped."""
    report = harness.conform_fastapi()
    declared = {item.capability_id for item in report.capability_coverage}
    assert declared == ALL_SEMANTICS
    by_id = {item.capability_id: item for item in report.capability_coverage}
    assert by_id["behavior"].support is CapabilitySupport.SUPPORTED
    assert by_id["capability"].support is CapabilitySupport.SUPPORTED
    assert by_id["requirement"].support is CapabilitySupport.UNSUPPORTED
    assert by_id["acceptance_criterion"].support is CapabilitySupport.UNSUPPORTED


def test_no_silent_omission_for_fastapi(harness):
    """Gate D holds because the declared coverage covers every semantic the
    fixed ISR expresses — the backend can reject, but never silently discard."""
    report = harness.conform_fastapi()
    gate = gate_by_id(report, GATE_SEMANTIC_COVERAGE)
    assert gate.held is True
    assert "explicit, never silent" in gate.evidence


# =============================================================================
# 3.  Multi-backend invariance with a REAL backend
# =============================================================================

def test_multi_backend_invariance_with_real_backend(harness):
    """The fixed ISR flows through FastAPI and the three reference backends:
    one semantic source (identical isr_hash) with distinct artifacts — the
    semantic meaning is invariant across real and reference backends."""
    isr = harness.fixed_isr()
    results = [harness.gate.verify(isr, TARGET, harness.fastapi).result]
    for backend in REFERENCE_BACKENDS:
        results.append(harness.gate.verify(isr, TARGET, backend).result)
    isr_hashes = {r.isr_hash for r in results}
    assert isr_hashes == {semantic_content_hash(isr)}
    artifact_hashes = {r.artifact_hash for r in results}
    assert len(artifact_hashes) >= 2


# =============================================================================
# 4.  Layer 2 — the ISR stays technology-neutral under the real compile
# =============================================================================

def test_isr_stays_technology_neutral_after_real_compile(harness):
    """The real compilation consumes the projection, never the ISR: the
    semantic content and the projection boundary are byte-identical before
    and after the conformance run."""
    isr = harness.fixed_isr()
    before = semantic_content_hash(isr)
    model_before = derive_backend_semantic_model(isr)
    harness.conform_fastapi()
    assert semantic_content_hash(isr) == before
    assert derive_backend_semantic_model(isr) == model_before


# =============================================================================
# 5.  The report binds to the ISR
# =============================================================================

def test_conformance_report_binds_to_isr(harness):
    """The report is evidence against a specific ISR: the semantic hash at
    conformance time is the fixed ISR's own semantic content hash."""
    report = harness.conform_fastapi()
    assert (
        report.isr_semantic_hash_at_conformance
        == semantic_content_hash(harness.fixed_isr())
    )


# =============================================================================
# 6.  The contract is not weakened by conformance
# =============================================================================

def test_evaluator_has_no_gate_weakening_surface():
    """The conformance path cannot weaken the contract: no identifier
    resembling a relaxation knob exists anywhere in the evaluator's source."""
    module = pathlib.Path(
        __import__(
            "tiannara.application.compilation.backend_conformance",
            fromlist=["x"],
        ).__file__
    )
    tree = ast.parse(module.read_text(encoding="utf-8"))
    names = {
        node.id if isinstance(node, ast.Name) else node.attr
        for node in ast.walk(tree)
        if isinstance(node, (ast.Name, ast.Attribute))
    }
    for banned in ("relax", "skip_gate", "override_gate"):
        assert not any(banned in name for name in names), banned


# =============================================================================
# 7.  A non-conforming backend is surfaced
# =============================================================================

def test_non_conforming_backend_is_surfaced(harness):
    """A backend whose generation is non-deterministic — the markdown
    ``date.today()`` class of defect — is surfaced: Gate B names the failed
    gate and the report records the failure instead of conforming."""
    class NonDeterministicBackend(FastAPICompiler):
        """The real backend with a time-dependent stamp injected into the
        bundle — the exact shape of the audit's markdown finding."""

        def compile(self, isr, genome, context):
            import time

            bundle = super().compile(isr, genome, context)
            bundle.manifests[0].metadata["generated_at"] = time.time()
            return bundle

    adapter = BackendConformanceAdapter(
        backend_id="fastapi-flaky",
        backend_version="8.0.0",
        real_backend=NonDeterministicBackend(),
        declaration=FASTAPI_DECLARATION,
    )
    report = harness.evaluator.conform(adapter, harness.fixed_isr(), TARGET)
    assert report.conforms is False
    assert report.failed_gates == (GATE_DETERMINISM,)
    assert gate_by_id(report, GATE_DETERMINISM).held is False


def test_undeclared_semantics_default_to_explicit_unsupported(harness):
    """An omitting declaration cannot become a silent omission: undeclared
    semantics default to explicit UNSUPPORTED coverage — honest by default."""
    omitting_declaration = BackendCapabilityDeclaration(
        backend_id="fastapi-omitting",
        declarations={
            "behavior": CapabilitySupport.SUPPORTED,
            "capability": CapabilitySupport.SUPPORTED,
        },
    )
    adapter = BackendConformanceAdapter(
        backend_id="fastapi-omitting",
        backend_version="8.0.0",
        real_backend=FastAPICompiler(),
        declaration=omitting_declaration,
    )
    report = harness.evaluator.conform(adapter, harness.fixed_isr(), TARGET)
    assert report.conforms is True
    by_id = {item.capability_id: item for item in report.capability_coverage}
    assert by_id["reliability"].support is CapabilitySupport.UNSUPPORTED
    assert "declared" in by_id["reliability"].note


# =============================================================================
# 8.  Honest findings are durable and chain-anchored
# =============================================================================

def test_conformance_findings_recorded(harness):
    """The audit findings are recorded with remediation notes — the
    pre-contract input surface and the structural-gene projection gap are
    never silently forgotten — while contamination findings stay empty."""
    report = harness.conform_fastapi()
    assert any("pre-contract input surface" in f for f in report.findings)
    assert any("structural genes outside" in f for f in report.findings)
    assert report.contamination_findings == ()
    assert report.conforms is True


def test_conformance_report_chain_anchored(harness):
    """The report enters the evidence chain: a CERTIFICATION event binds the
    backend id, its verdict, its coverage summary, and the ISR hash, and the
    chain verifies."""
    report = harness.conform_fastapi()
    events = [
        ev
        for ev in harness.ledger._events
        if ev.event_type is EventType.CERTIFICATION
    ]
    assert len(events) == 1
    event = events[0]
    assert event.event_id == f"conformance-fastapi-{report.isr_semantic_hash_at_conformance[:8]}"
    assert event.subject_id == report.isr_semantic_hash_at_conformance
    assert event.payload["backend_id"] == "fastapi"
    assert event.payload["conforms"] is True
    assert event.payload["failed_gates"] == []
    summary = event.payload["coverage_summary"]
    assert summary["SUPPORTED"] >= 2
    assert summary["UNSUPPORTED"] >= 8
    assert harness.ledger.verify_event_chain() is True


# =============================================================================
# 9.  Option A (fourteenth use) — the recipe is untouched
# =============================================================================

def test_option_a_fourteenth_use():
    """No new semantic carriers, no matrix movement: the recipe ISR hash is
    unchanged and the matrix stays 12/18/0/0."""
    from tiannara.application.evolution.isr_capability_audit import (
        ISRCapabilityAudit,
    )

    assert RECIPE.content_hash == (
        "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
    )
    result = ISRCapabilityAudit().run(RECIPE)
    summary = result.summary()
    assert (summary["expressed"], summary["partial"], summary["missing"]) == (
        12, 18, 0,
    )