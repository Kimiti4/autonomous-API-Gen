"""R2.10.8 — artifact verification & provenance.

R2.10.7 proved the backend consumed the ISR correctly. R2.10.8 proves the
resulting artifact can INDEPENDENTLY demonstrate where it came from and
what semantic source it represents — judged by a verifier that trusts
nothing. The acceptance evidence:

  1.  a claim assembled from a real compilation + its real ledger event +
      its registered conformance report verifies in full;
  2.  forged claims fail loudly: modified artifact, wrong ISR, wrong
      backend, wrong target, missing compilation event;
  3.  silent omission stays fatal (a lie about coverage), while an explicit
      UNSUPPORTED boundary is permitted;
  4.  the cross-backend campaign's seven DIVERGENT realizations resolve to
      ONE semantic source — artifact equality is never required;
  5.  the verdict itself is chain-anchored (recorded only when the chain is
      intact) and the verifier never mutates the ISR or the artifact;
  6.  artifact identity rejects the default-str fallback: unhandled types
      raise CanonicalizationError instead of silently hashing a str() lie;
  7.  Option A (sixteenth use) — no new carriers, no matrix movement.
"""
from __future__ import annotations

import copy
import dataclasses
import tempfile

import pytest

from constitutional_architecture.isr.semantics.projection import (
    CanonicalizationError,
    semantic_content_hash,
)
from tiannara.application.compilation.artifact_verification import (
    ArtifactProvenance,
    ArtifactVerifier,
    ConformanceEvidenceRegistry,
    compilation_event_ref_for,
    conformance_event_ref_for,
    hash_artifact_canonical,
    provenance_claim,
)
from tiannara.application.compilation.backend_capability_registry import (
    BackendRegistry,
)
from tiannara.application.compilation.backend_conformance import (
    BackendConformanceEvaluator,
    CapabilitySupport,
)
from tiannara.application.compilation.consumption_contract import (
    ContaminationGuard,
)
from tiannara.application.compilation.cross_backend_campaign import (
    CrossBackendConformanceCampaign,
)
from tiannara.application.compilation.integrity_gate import (
    CompilationIntegrityGate,
)
from tiannara.application.evolution.ledger import (
    EventType,
    EvolutionLedger,
)
from .test_r29_10_1_capability_audit import RECIPE
from .test_r29_10_4_semantic_evolution_gate import (
    SemanticEvolutionIntegrationHarness,
)
from .test_r29_10_7_backend_conformance_expansion import SEVEN

RECIPE_HASH = "317b62a84dc1c4c0ee4a0e43c732a8d2d8b2f7b3c6b0404712a0fc5d6bb74613"


class VerificationHarness:
    """The R2.10.7 campaign wired to the R2.10.8 verifier + evidence index."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger = EvolutionLedger(root=self._tmp.name)
        self.gate = CompilationIntegrityGate(ledger=self.ledger)
        self.guard = ContaminationGuard()
        self.conformance_registry = ConformanceEvidenceRegistry()
        self.evaluator = BackendConformanceEvaluator(
            integrity_gate=self.gate,
            contamination_guard=self.guard,
            ledger=self.ledger,
            conformance_registry=self.conformance_registry,
        )
        self.registry = BackendRegistry()
        self.verifier = ArtifactVerifier(
            ledger=self.ledger,
            conformance_registry=self.conformance_registry,
        )
        self._base = SemanticEvolutionIntegrationHarness()
        self._campaign = CrossBackendConformanceCampaign()

    def fixed_isr(self):
        return self._base.parent_isr()

    def different_isr(self):
        """A different ISR — semantically distinct from the fixed one."""
        return RECIPE

    def _conform_one(self, backend_id: str, isr):
        adapter = self.registry.adapter(backend_id)
        target = self.registry.target(backend_id)
        report = self.evaluator.conform(adapter, isr, target)
        self.evaluator.record_report(report)
        return adapter, target, report

    def valid_setup(self, backend_id: str = "fastapi"):
        """One conformed backend -> (artifact, provenance, isr)."""
        isr = self.fixed_isr()
        adapter, target, report = self._conform_one(backend_id, isr)
        result = adapter.compile(isr, target)
        claim = provenance_claim(
            result,
            compilation_event_ref_for(result),
            conformance_event_ref_for(report),
        )
        return result.artifact, claim, isr

    def setup_with_silent_omission(self, backend_id: str = "fastapi"):
        """The claim lies about coverage: one expressed carrier is dropped
        instead of being declared UNSUPPORTED."""
        artifact, claim, isr = self.valid_setup(backend_id)
        covered = tuple(
            item for item in claim.capability_coverage
            if item.capability_id != "behavior"
        )
        lying = dataclasses.replace(claim, capability_coverage=covered)
        return artifact, lying, isr

    def setup_with_explicit_unsupported(self, backend_id: str = "fastapi"):
        """The honest boundary: coverage declares an UNSUPPORTED semantic —
        never a silent omission."""
        artifact, claim, isr = self.valid_setup(backend_id)
        assert any(
            item.support is CapabilitySupport.UNSUPPORTED
            for item in claim.capability_coverage
        )
        return artifact, claim, isr

    def setup_with_missing_event_ref(self, backend_id: str = "fastapi"):
        """The claim references a compilation event that was never recorded."""
        artifact, claim, isr = self.valid_setup(backend_id)
        missing = dataclasses.replace(
            claim, compilation_event_ref="compilation-never-recorded"
        )
        return artifact, missing, isr

    def modify_artifact(self, artifact):
        """Tamper with the realization (deep copy — the original is never
        touched)."""
        modified = copy.deepcopy(artifact)
        bundle = modified["bundle"]
        if bundle.get("manifests"):
            manifest = bundle["manifests"][0]
            if manifest.get("files"):
                first_key = next(iter(manifest["files"]))
                manifest["files"][first_key] += "\n# tampered after compile"
            else:
                manifest["files"] = {"tampered.txt": "tampered"}
        elif "project_name" in bundle:
            bundle["project_name"] += "-tampered"
        else:
            bundle["__tampered__"] = True
        return modified

    def artifact_with_unhandled_type(self):
        """An artifact whose identity cannot be canonicalized — no default
        str() fallback is allowed to manufacture an identity."""
        return {"bundle": object()}

    def seven_artifacts(self, isr):
        """The cross-backend campaign's fixtures: seven realizations, each
        with a claim assembled from its own ledger event + registered
        conformance report."""
        adapters = {
            backend_id: self.registry.adapter(backend_id)
            for backend_id in SEVEN
        }
        targets = {
            backend_id: self.registry.target(backend_id)
            for backend_id in SEVEN
        }
        campaign = self._campaign.run(isr, adapters, self.evaluator, targets)
        assert campaign.all_conform
        assert campaign.semantic_invariance_held
        artifacts: dict[str, tuple[dict, ArtifactProvenance]] = {}
        for backend_id in SEVEN:
            result = adapters[backend_id].compile(isr, targets[backend_id])
            report = campaign.per_backend[backend_id]
            claim = provenance_claim(
                result,
                compilation_event_ref_for(result),
                conformance_event_ref_for(report),
            )
            artifacts[backend_id] = (result.artifact, claim)
        return artifacts, campaign

    def matrix_summary(self):
        from tiannara.application.evolution.isr_capability_audit import (
            ISRCapabilityAudit,
        )

        result = ISRCapabilityAudit().run(RECIPE)
        summary = result.summary()
        return (summary["expressed"], summary["partial"], summary["missing"])

    def recipe_isr_hash(self):
        return RECIPE.content_hash


@pytest.fixture
def verification_harness() -> VerificationHarness:
    return VerificationHarness()


def test_valid_provenance_verifies(verification_harness):
    artifact, claim, isr = verification_harness.valid_setup()
    result = verification_harness.verifier.verify(artifact, claim, isr)
    assert result.verified
    assert result.failures == ()
    assert result.artifact_integrity_verified
    assert result.isr_binding_verified
    assert result.target_binding_verified
    assert result.backend_binding_verified
    assert result.semantic_coverage_verified
    assert result.ledger_chain_verified
    assert result.artifact_hash == claim.artifact_hash


def test_forged_provenance_fails(verification_harness):
    artifact, claim, isr = verification_harness.valid_setup()
    forged = dataclasses.replace(claim, isr_hash="forged")
    result = verification_harness.verifier.verify(artifact, forged, isr)
    assert not result.verified
    assert "isr_mismatch" in result.failures


def test_modified_artifact_fails(verification_harness):
    artifact, claim, isr = verification_harness.valid_setup()
    tampered = verification_harness.modify_artifact(artifact)
    result = verification_harness.verifier.verify(tampered, claim, isr)
    assert not result.verified
    assert "artifact_modified" in result.failures
    assert result.artifact_integrity_verified is False


def test_mismatched_isr_fails(verification_harness):
    artifact, claim, _ = verification_harness.valid_setup()
    other = verification_harness.different_isr()
    result = verification_harness.verifier.verify(artifact, claim, other)
    assert not result.verified
    assert "isr_mismatch" in result.failures


def test_mismatched_backend_fails(verification_harness):
    artifact, claim, isr = verification_harness.valid_setup()
    wrong = dataclasses.replace(claim, backend_id="wrong_backend")
    result = verification_harness.verifier.verify(artifact, wrong, isr)
    assert not result.verified
    assert "backend_mismatch" in result.failures


def test_mismatched_target_fails(verification_harness):
    artifact, claim, isr = verification_harness.valid_setup()
    wrong = dataclasses.replace(claim, target_id="wrong_target")
    result = verification_harness.verifier.verify(artifact, wrong, isr)
    assert not result.verified
    assert "target_mismatch" in result.failures


def test_silent_omission_remains_fatal(verification_harness):
    artifact, claim, isr = verification_harness.setup_with_silent_omission()
    result = verification_harness.verifier.verify(artifact, claim, isr)
    assert not result.verified
    assert result.semantic_coverage_verified is False
    assert any(
        f.startswith("silently_discarded:") for f in result.failures
    )


def test_explicit_unsupported_is_permitted(verification_harness):
    artifact, claim, isr = verification_harness.setup_with_explicit_unsupported()
    result = verification_harness.verifier.verify(artifact, claim, isr)
    assert result.verified
    assert result.semantic_coverage_verified
    assert not any(
        f.startswith("silently_discarded:") for f in result.failures
    )


def test_cross_backend_same_source_divergent_artifacts(verification_harness):
    isr = verification_harness.fixed_isr()
    artifacts, campaign = verification_harness.seven_artifacts(isr)
    assert len(artifacts) == 7
    assert campaign.artifact_divergence_count == 7
    result = verification_harness.verifier.verify_cross_backend(
        artifacts, isr
    )
    assert result.verified
    assert len(result.per_backend) == 7
    assert all(r.verified for r in result.per_backend.values())
    assert result.semantic_sources_resolved == (semantic_content_hash(isr),)
    assert result.artifact_equality_required is False


def test_verification_result_enters_ledger(verification_harness):
    artifact, claim, isr = verification_harness.valid_setup()
    result = verification_harness.verifier.verify(artifact, claim, isr)
    assert result.verification_event_ref is not None
    event = verification_harness.ledger.event_by_ref(
        result.verification_event_ref
    )
    assert event is not None
    assert event.event_type is EventType.VERIFICATION
    assert event.payload["verified"] is True
    assert event.payload["artifact_hash"] == result.artifact_hash
    assert verification_harness.ledger.verify_event_chain()


def test_missing_compilation_event_fails(verification_harness):
    artifact, claim, isr = verification_harness.setup_with_missing_event_ref()
    result = verification_harness.verifier.verify(artifact, claim, isr)
    assert not result.verified
    assert "compilation_event_not_found" in result.failures
    assert result.verification_event_ref is None


def test_artifact_identity_rejects_default_str(verification_harness):
    artifact = verification_harness.artifact_with_unhandled_type()
    with pytest.raises(CanonicalizationError):
        hash_artifact_canonical(artifact)


def test_verifier_never_mutates_isr_or_artifact(verification_harness):
    artifact, claim, isr = verification_harness.valid_setup()
    isr_hash_before = semantic_content_hash(isr)
    artifact_hash_before = hash_artifact_canonical(artifact)
    result = verification_harness.verifier.verify(artifact, claim, isr)
    assert result.verified
    assert semantic_content_hash(isr) == isr_hash_before
    assert hash_artifact_canonical(artifact) == artifact_hash_before
    assert claim.artifact_hash == artifact_hash_before


def test_matrix_and_recipe_identity_unchanged(verification_harness):
    assert verification_harness.matrix_summary() == (12, 18, 0)
    assert (
        verification_harness.recipe_isr_hash()
        == RECIPE_HASH
    )