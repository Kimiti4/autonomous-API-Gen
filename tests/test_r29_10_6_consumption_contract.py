"""R2.10.6 — the ISR -> Compiler Backend consumption contract.

R2.10.4/5 proved universal ISR evolution under one gate; R2.10.6 proves the
DOWNSTREAM contract: a compiler backend consumes the ISR without ever
participating in it. The acceptance evidence:

  1.  all eight gates (A read-only, B determinism, C provenance,
      D semantic coverage, E backend independence, F round-trip,
      G constitutional preservation, H evidence binding) hold for a
      conformance reference backend;
  2.  a backend that SILENTLY OMITS a semantic is rejected — Gate D names
      the discarded semantics ("silently discarded: [...]");
  3.  an explicit UNSUPPORTED declaration is NOT silent: coverage carries
      it and Gate D still holds;
  4.  the semantic source is invariant across backends (three reference
      artifact styles -> one semantic source, distinct artifacts);
  5.  the three-layer ContaminationGuard holds: the backend module is
      structurally read-only (AST), the ISR stays technology-neutral under
      compilation, and no reverse contamination flows artifact -> ISR;
  6.  the CompilationTarget is a realization selection — carried in the
      ARTIFACT, never embedded in the ISR;
  7.  the projection boundary is deterministic and faithful (stable
      model_hash, bound source_isr_hash, constitutional surface carried);
  8.  every certified compilation is chain-anchored in the evidence ledger
      (EventType.COMPILATION, payload binds ISR/backend/artifact/coverage);
  9.  Option A (thirteenth use) — no new carriers, no matrix movement:
      the recipe ISR hash is unchanged and the matrix stays 12/18/0/0.
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import pathlib
import tempfile

import pytest

from constitutional_architecture.isr.model import BusinessCapability
from constitutional_architecture.isr.semantics.projection import (
    canonical_form,
    canonicalize,
    semantic_content_hash,
)
from tiannara.application.compilation.consumption_contract import (
    BackendSemanticModel,
    CapabilitySupport,
    CompilationTarget,
    ContaminationGuard,
    constitutional_surface_intact,
    derive_backend_semantic_model,
    enumerate_isr_semantics,
    isr_has_no_target_genes,
    reconstruct_semantic_source,
)
from tiannara.application.compilation.integrity_gate import (
    CompilationIntegrityGate,
    CompilationIntegrityVerdict,
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
    stable_isr_hash,
)
from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_4_semantic_evolution_gate import (
    SemanticEvolutionIntegrationHarness,
)


# =============================================================================
# The harness: the R2.10.4 composition parent + the contract seams
# =============================================================================

# The realization selection under test: never embedded in the ISR (the
# target IS a realization choice; the ISR stays neutral).
TARGET = CompilationTarget(
    target_id="target-fastapi-hexagonal",
    language="python",
    runtime="python3.14",
    framework="fastapi",
    capabilities=frozenset({"http-api", "sql-persistence"}),
    version="1.0.0",
)

REFERENCE_BACKENDS = (
    ReferenceCompilerBackend("reference-json", artifact_style="json"),
    ReferenceCompilerBackend("reference-manifest", artifact_style="manifest"),
    ReferenceCompilerBackend("reference-fragment", artifact_style="fragment"),
)


class CompilationContractHarness:
    """Fixed ISR (all fourteen semantic carriers present), fresh evidence
    ledger, the eight-gate certifier, and the three reference backends."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger = EvolutionLedger(root=self._tmp.name)
        self.gate = CompilationIntegrityGate(ledger=self.ledger)
        self.guard = ContaminationGuard()
        self.backends = {
            "json": REFERENCE_BACKENDS[0],
            "manifest": REFERENCE_BACKENDS[1],
            "fragment": REFERENCE_BACKENDS[2],
        }
        self._base = SemanticEvolutionIntegrationHarness()

    def fixed_isr(self):
        return self._base.parent_isr()

    def run(self, backend=None):
        return self.gate.verify(
            self.fixed_isr(),
            TARGET,
            backend or self.backends["json"],
        )


@pytest.fixture
def harness() -> CompilationContractHarness:
    return CompilationContractHarness()


def gate_by_id(verdict: CompilationIntegrityVerdict, gate_id: str):
    return next(gate for gate in verdict.gates if gate.gate_id == gate_id)


# =============================================================================
# 1.  All eight gates hold
# =============================================================================

def test_all_eight_gates_hold(harness):
    """A conformance reference backend is certified: every gate holds and
    the primary compilation is returned with its evidence binding."""
    verdict = harness.run()
    assert verdict.held is True
    assert [gate.gate_id for gate in verdict.gates] == [
        GATE_READ_ONLY,
        GATE_DETERMINISM,
        GATE_PROVENANCE,
        GATE_SEMANTIC_COVERAGE,
        GATE_BACKEND_INDEPENDENCE,
        GATE_ROUND_TRIP,
        GATE_CONSTITUTIONAL_PRESERVATION,
        GATE_EVIDENCE_BINDING,
    ]
    assert all(gate.held for gate in verdict.gates)
    assert verdict.result is not None
    assert verdict.ledger_event_range is not None
    assert len(verdict.result.artifact_hash) == 64


# =============================================================================
# 2.  Gate A — the backend is a consumer, never a participant
# =============================================================================

def test_gate_a_backend_is_read_only(harness):
    """Compiling must leave the ISR byte-identical (semantic hash stable)."""
    isr = harness.fixed_isr()
    before = semantic_content_hash(isr)
    verdict = harness.run()
    assert gate_by_id(verdict, GATE_READ_ONLY).held is True
    assert semantic_content_hash(isr) == before


# =============================================================================
# 3.  Gate B — determinism
# =============================================================================

def test_gate_b_determinism(harness):
    """Same ISR + same target -> same artifact hash, same isr hash."""
    verdict = harness.run()
    assert gate_by_id(verdict, GATE_DETERMINISM).held is True
    first = harness.backends["json"].compile(harness.fixed_isr(), TARGET)
    second = harness.backends["json"].compile(harness.fixed_isr(), TARGET)
    assert first.artifact_hash == second.artifact_hash
    assert first.isr_hash == second.isr_hash


# =============================================================================
# 4.  Gate C — provenance binding
# =============================================================================

def test_gate_c_provenance_binding(harness):
    """The result binds isr_hash / target / backend / version, and the
    artifact_hash is the artifact's own content hash."""
    verdict = harness.run()
    assert gate_by_id(verdict, GATE_PROVENANCE).held is True
    result = verdict.result
    provenance = result.provenance
    assert provenance.isr_hash == result.isr_hash == semantic_content_hash(
        harness.fixed_isr()
    )
    assert provenance.target_id == TARGET.target_id
    assert provenance.backend_id == result.backend_id == "reference-json"
    assert provenance.backend_version == result.backend_version == "1.0.0"
    expected = hashlib.sha256(
        canonicalize(result.artifact).encode("utf-8")
    ).hexdigest()
    assert result.artifact_hash == expected


# =============================================================================
# 5.  Gate D — never a silent omission
# =============================================================================

def test_gate_d_silent_omission_impossible(harness):
    """A backend that silently drops a semantic from its model AND coverage
    is rejected: Gate D names exactly what was discarded."""
    omitting = ReferenceCompilerBackend(
        "reference-omitting", artifact_style="json", omitted=frozenset({"reliability"})
    )
    verdict = harness.run(backend=omitting)
    assert verdict.held is False
    gate = gate_by_id(verdict, GATE_SEMANTIC_COVERAGE)
    assert gate.held is False
    assert "silently discarded" in gate.evidence
    assert "reliability" in gate.evidence


def test_gate_d_explicit_unsupported_is_not_silent(harness):
    """An explicit UNSUPPORTED declaration is honest: the coverage carries
    it with a note and Gate D still holds (no silent omission)."""
    partial = ReferenceCompilerBackend(
        "reference-partial",
        artifact_style="json",
        declared_unsupported=frozenset({"reliability"}),
    )
    verdict = harness.run(backend=partial)
    coverage = {c.capability_id: c for c in verdict.result.capability_coverage}
    assert coverage["reliability"].support is CapabilitySupport.UNSUPPORTED
    assert coverage["reliability"].note
    assert coverage["capability"].support is CapabilitySupport.SUPPORTED
    assert gate_by_id(verdict, GATE_SEMANTIC_COVERAGE).held is True
    assert verdict.held is True


# =============================================================================
# 6.  Gate E — backend independence
# =============================================================================

def test_gate_e_backend_independence(harness):
    """Compiling the same ISR under a DIFFERENT target must not change the
    ISR — realization selection is consumed, never authored."""
    verdict = harness.run()
    assert gate_by_id(verdict, GATE_BACKEND_INDEPENDENCE).held is True
    isr = harness.fixed_isr()
    before = stable_isr_hash(isr)
    alt_target = dataclasses.replace(TARGET, target_id="target-other-stack")
    harness.backends["json"].compile(isr, alt_target)
    assert stable_isr_hash(isr) == before


# =============================================================================
# 7.  Gate F — round-trip
# =============================================================================

def test_gate_f_round_trip(harness):
    """The artifact re-declares its semantic source; reading the hash back
    from the artifact matches the compiled ISR's identity."""
    verdict = harness.run()
    assert gate_by_id(verdict, GATE_ROUND_TRIP).held is True
    result = verdict.result
    assert reconstruct_semantic_source(result) == result.isr_hash
    assert result.isr_hash == semantic_content_hash(harness.fixed_isr())
    model = harness.backends["json"].semantic_projection(harness.fixed_isr())
    assert result.artifact["semantic_source"]["model_hash"] == model.model_hash


# =============================================================================
# 8.  Gate G — constitutional preservation
# =============================================================================

def test_gate_g_constitutional_preservation(harness):
    """The backend's projection carries the constitutional surface
    content-identically (the seven per-kind comparisons hold)."""
    verdict = harness.run()
    assert gate_by_id(verdict, GATE_CONSTITUTIONAL_PRESERVATION).held is True
    isr = harness.fixed_isr()
    model = harness.backends["json"].semantic_projection(isr)
    assert constitutional_surface_intact(isr, model) == ()


def test_gate_g_rejects_weakened_constitutional_surface(harness):
    """A projection that drops reliability (or any constitutional carrier)
    breaks Gate G — the surface comparison names the weakened kind."""
    isr = harness.fixed_isr()
    model = harness.backends["json"].semantic_projection(isr)
    tampered = BackendSemanticModel(
        model_hash=model.model_hash,
        source_isr_hash=model.source_isr_hash,
        capabilities=model.capabilities - frozenset({"reliability"}),
        constraints=tuple(
            (kind, form) for (kind, form) in model.constraints if kind != "reliability"
        ),
        protected_regions=model.protected_regions,
    )
    mismatches = constitutional_surface_intact(isr, tampered)
    assert mismatches
    assert any("reliability" in m for m in mismatches)

    omitting = ReferenceCompilerBackend(
        "reference-omitting", artifact_style="json", omitted=frozenset({"reliability"})
    )
    verdict = harness.run(backend=omitting)
    gate = gate_by_id(verdict, GATE_CONSTITUTIONAL_PRESERVATION)
    assert gate.held is False
    assert "reliability" in gate.evidence


# =============================================================================
# 9.  Gate H — evidence binding
# =============================================================================

def test_gate_h_evidence_binding(harness):
    """Every certified compilation is chain-anchored as a COMPILATION event;
    the payload binds ISR / target / backend / artifact / coverage."""
    verdict = harness.run()
    assert gate_by_id(verdict, GATE_EVIDENCE_BINDING).held is True
    assert harness.ledger.verify_event_chain() is True
    compilation_events = [
        ev
        for ev in harness.ledger.events()
        if ev.event_type is EventType.COMPILATION
    ]
    assert len(compilation_events) == 1
    event = compilation_events[0]
    assert event.payload["isr_hash"] == verdict.result.isr_hash
    assert event.payload["target_id"] == TARGET.target_id
    assert event.payload["backend_id"] == "reference-json"
    assert event.payload["artifact_hash"] == verdict.result.artifact_hash
    assert len(event.payload["coverage"]) == len(verdict.result.capability_coverage)
    assert event.event_id == f"compilation-reference-json-{verdict.result.artifact_hash[:8]}"
    assert event.is_intact() is True


def test_gate_h_requires_evidence_ledger():
    """The evidence substrate is the ONLY trust boundary: a compilation
    without a bound ledger is not certifiable (Gate H fails loudly)."""
    gate = CompilationIntegrityGate()
    harness = CompilationContractHarness()
    verdict = gate.verify(harness.fixed_isr(), TARGET, harness.backends["json"])
    assert verdict.held is False
    gate_h = gate_by_id(verdict, GATE_EVIDENCE_BINDING)
    assert gate_h.held is False
    assert "no evidence ledger bound" in gate_h.evidence


# =============================================================================
# 10.  Multi-backend invariance — one semantic source, distinct artifacts
# =============================================================================

def test_semantic_source_invariant_across_backends(harness):
    """Three reference artifact styles project the SAME semantic source
    (deterministic, faithful) yet produce distinct artifacts — the ISR's
    identity is backend-independent by construction."""
    isr = harness.fixed_isr()
    sources = set()
    artifacts: list[str] = []
    for backend in harness.backends.values():
        model = backend.semantic_projection(isr)
        sources.add(model.source_isr_hash)
        sources.add(model.model_hash)
        result = backend.compile(isr, TARGET)
        artifacts.append(result.artifact_hash)
        verdict = harness.gate.verify(isr, TARGET, backend)
        assert verdict.held is True
    assert len(sources) == 2  # one source_isr_hash + one model_hash
    assert len(set(artifacts)) >= 2


# =============================================================================
# 11.  Layer 1 — the backend module is structurally read-only
# =============================================================================

def test_backend_module_read_only_structurally(harness):
    """The reference backend's own source carries no mutation-shaped call
    site; a hypothetical mutating backend is rejected structurally."""
    module_path = (
        pathlib.Path(__file__).resolve().parent.parent
        / "tiannara"
        / "application"
        / "compilation"
        / "reference_backend.py"
    )
    assert module_path.exists()
    harness.guard.assert_backend_module_is_read_only(module_path)

    mutating = ast.parse(
        "def compile(isr, target):\n"
        "    replace_gene(isr, 'capability', 'c1', new_gene)\n"
        "    mutate(isr)\n"
        "    isr.set_governance('self-authored')\n"
    )
    with pytest.raises(AssertionError, match="NOT read-only"):
        harness.guard.assert_backend_module_is_read_only(mutating)


# =============================================================================
# 12.  Layer 2 — the ISR stays technology-neutral under compilation
# =============================================================================

def test_isr_technology_neutral_under_compilation(harness):
    """The fixed ISR passes the full Layer-2 scan before AND after a
    certified compile — compiling never injects technology concepts."""
    isr = harness.fixed_isr()
    harness.guard.assert_isr_technology_neutral(isr)
    harness.run()
    harness.guard.assert_isr_technology_neutral(isr)


def test_layer2_rejects_realization_leak(harness):
    """A capability intent that names a realization technology (react) is
    rejected by the realization-lexicon layer."""
    isr = harness.fixed_isr()
    contaminated = isr.with_system(
        dataclasses.replace(
            isr.system,
            business_capabilities=(
                BusinessCapability(
                    capability_id="capability_pay",
                    intent="expose a react dashboard",
                    behavior_refs=("w1",),
                    interface_refs=("i1",),
                ),
            ),
        )
    )
    with pytest.raises(AssertionError, match="react"):
        harness.guard.assert_isr_technology_neutral(contaminated)


def test_layer2_rejects_mechanism_leak(harness):
    """A capability intent that names a test mechanism (pytest) is rejected
    by the mechanism-lint layer."""
    isr = harness.fixed_isr()
    contaminated = isr.with_system(
        dataclasses.replace(
            isr.system,
            business_capabilities=(
                BusinessCapability(
                    capability_id="capability_pay",
                    intent="run pytest over the payment flows",
                    behavior_refs=("w1",),
                    interface_refs=("i1",),
                ),
            ),
        )
    )
    with pytest.raises(AssertionError, match="pytest"):
        harness.guard.assert_isr_technology_neutral(contaminated)


# =============================================================================
# 13.  Layer 3 — no reverse contamination
# =============================================================================

def test_no_reverse_contamination(harness):
    """The artifact's declared source ISR identity, the provenance's, and
    the result's all agree; a forged provenance is rejected."""
    verdict = harness.run()
    harness.guard.assert_no_reverse_contamination(verdict.result)

    forged = dataclasses.replace(
        verdict.result,
        provenance=dataclasses.replace(
            verdict.result.provenance, isr_hash="forged-source"
        ),
    )
    with pytest.raises(AssertionError, match="reverse contamination"):
        harness.guard.assert_no_reverse_contamination(forged)


# =============================================================================
# 14.  The target is a realization selection — never embedded in the ISR
# =============================================================================

def test_target_never_embedded_in_the_isr(harness):
    """The ISR carries no target genes before or after compilation; the
    target lives in the ARTIFACT, where realization belongs."""
    isr = harness.fixed_isr()
    assert isr_has_no_target_genes(isr) is True
    harness.run()
    assert isr_has_no_target_genes(isr) is True
    verdict = harness.run()
    assert verdict.result.artifact["target"]["target_id"] == TARGET.target_id
    assert isr_has_no_target_genes(isr) is True


# =============================================================================
# 15.  The projection boundary is deterministic and faithful
# =============================================================================

def test_model_deterministic_and_faithful(harness):
    """Two derivations give the same model_hash; the model binds its source
    ISR, enumerates exactly the expressed semantics, and carries the
    constitutional protected-region declaration."""
    isr = harness.fixed_isr()
    first = derive_backend_semantic_model(isr)
    second = derive_backend_semantic_model(isr)
    assert first.model_hash == second.model_hash
    assert first.source_isr_hash == semantic_content_hash(isr)
    assert first.capabilities == enumerate_isr_semantics(isr)
    assert len(first.capabilities) == 14
    assert first.protected_regions == (
        canonical_form(isr.system.protected_regions[0]),
    )
    assert stable_isr_hash(isr) == first.source_isr_hash
    kinds = {kind for (kind, _) in first.constraints}
    assert "requirement" in kinds and "temporal" in kinds and "behavior" in kinds
    assert "protected_region" not in kinds  # travels in its own field


# =============================================================================
# 16.  Option A — the thirteenth use: no new carriers, no matrix movement
# =============================================================================

def test_option_a_holds_under_the_consumption_contract(harness):
    """R2.10.6 adds no carriers and moves no matrix row: the recipe ISR is
    byte-identical (the thirteenth Option A use), the matrix stays 12/18/0/0,
    and the consumption contract leaves the J carriers' cardinality intact."""
    assert RECIPE.content_hash == (
        "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"
    )
    from tiannara.application.evolution.isr_capability_audit import (
        CapabilityStatus,
        ISRCapabilityAudit,
    )

    result = ISRCapabilityAudit().run(RECIPE)
    assert result.integrity is True
    assert result.isr_hash == RECIPE.content_hash
    summary = result.summary()
    assert (summary["expressed"], summary["partial"], summary["missing"]) == (
        12, 18, 0,
    )
    by_id = {c.capability_id: c.status for c in result.capabilities}
    assert CapabilityStatus.PROJECTED not in by_id.values()

    verdict = harness.run()
    assert verdict.held is True
    final = harness.fixed_isr()
    assert len(final.system.evolution_objectives) == 1
    assert len(final.system.protected_regions) == 1
    assert len(final.system.evolution_policies) == 1
    assert isr_has_no_target_genes(final) is True
