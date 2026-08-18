"""R2.10.6 — ReferenceCompilerBackend: the conformance reference.

R2.10.6 proves the consumption contract WITHOUT touching any real compiler
backend (that is R2.10.7). The reference backend implements the
``CompilerBackend`` protocol over the projection boundary only: it derives
the semantic model, declares coverage per capability, and emits an artifact
that embeds its semantic source + the full projection + the target.

Variants (all three artifact styles embed the same ``semantic_source`` so
Gate F round-trips identically while artifact hashes differ):

  * artifact_style "json"      — one JSON-shaped realization document
  * artifact_style "manifest"  — a service-manifest-shaped realization
  * artifact_style "fragment"  — a generated-fragments-shaped realization

Conformance variants:

  * ``declared_unsupported`` — capability ids the backend DECLARES it cannot
    realize (coverage marks them UNSUPPORTED — explicit, never silent; Gate D
    still holds).
  * ``omitted`` — capability ids the backend silently DROPS from its model
    and coverage (the negative conformance: Gate D must fail with
    "silently discarded").

The backend never touches the ISR: compile is a pure function of
(isr, target) and the ISR object is never mutated.
"""
from __future__ import annotations

import hashlib
from typing import Any

from constitutional_architecture.isr.semantics.projection import canonical_form, canonicalize

from .consumption_contract import (
    BackendSemanticModel,
    CapabilityCoverage,
    CapabilitySupport,
    CompilationProvenance,
    CompilationResult,
    CompilationTarget,
    CompilerBackend,
    derive_backend_semantic_model,
)


class ReferenceCompilerBackend(CompilerBackend):
    """A minimal, deterministic backend implementing the consumption
    contract. Read-only by construction: no mutation of the ISR, no
    import of evolution machinery, pure (isr, target) -> artifact."""

    def __init__(
        self,
        backend_id: str,
        backend_version: str = "1.0.0",
        artifact_style: str = "json",
        *,
        declared_unsupported: frozenset[str] = frozenset(),
        omitted: frozenset[str] = frozenset(),
    ) -> None:
        if artifact_style not in ("json", "manifest", "fragment"):
            raise ValueError(
                f"unknown artifact_style '{artifact_style}' "
                "(json / manifest / fragment)"
            )
        self.backend_id = backend_id
        self.backend_version = backend_version
        self._artifact_style = artifact_style
        self._declared_unsupported = frozenset(declared_unsupported)
        self._omitted = frozenset(omitted)

    # -- the projection boundary ------------------------------------------------

    def semantic_projection(self, isr: Any) -> BackendSemanticModel:
        model = derive_backend_semantic_model(isr)
        if not self._omitted:
            return model
        capabilities = model.capabilities - self._omitted
        constraints = tuple(
            (kind, form)
            for (kind, form) in model.constraints
            if kind not in self._omitted
        )
        regions = (
            ()
            if "protected_region" in self._omitted
            else model.protected_regions
        )
        return BackendSemanticModel(
            model_hash=hashlib.sha256(
                canonicalize(
                    {
                        "capabilities": sorted(capabilities),
                        "constraints": constraints,
                        "protected_regions": regions,
                    }
                ).encode("utf-8")
            ).hexdigest(),
            source_isr_hash=model.source_isr_hash,
            capabilities=frozenset(capabilities),
            constraints=constraints,
            protected_regions=regions,
        )

    # -- the compile (pure: never mutates the ISR) -------------------------------

    def compile(
        self, isr: Any, target: CompilationTarget
    ) -> CompilationResult:
        model = self.semantic_projection(isr)
        coverage = tuple(
            CapabilityCoverage(
                capability_id=capability_id,
                support=(
                    CapabilitySupport.UNSUPPORTED
                    if capability_id in self._declared_unsupported
                    else CapabilitySupport.SUPPORTED
                ),
                note=(
                    "explicitly unsupported: this backend cannot realize "
                    "the semantic without weakening it"
                    if capability_id in self._declared_unsupported
                    else "semantics carried into the realization"
                ),
            )
            for capability_id in sorted(model.capabilities)
        )
        artifact = self._build_artifact(isr, model, target, coverage)
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

    # -- artifact construction (all styles embed semantic_source) ---------------

    def _build_artifact(
        self,
        isr: Any,
        model: BackendSemanticModel,
        target: CompilationTarget,
        coverage: tuple[CapabilityCoverage, ...],
    ) -> dict:
        semantic_source = {
            "isr_hash": model.source_isr_hash,
            "model_hash": model.model_hash,
        }
        projection = {
            "capabilities": sorted(model.capabilities),
            "constraints": [
                {"kind": kind, "content": form}
                for (kind, form) in model.constraints
            ],
            "protected_regions": list(model.protected_regions),
        }
        artifact: dict = {
            "semantic_source": semantic_source,
            "projection": projection,
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
        if self._artifact_style == "json":
            artifact["style"] = "json"
        elif self._artifact_style == "manifest":
            system = isr.system
            artifact["style"] = "manifest"
            artifact["manifest"] = {
                "modules": [
                    {"id": module.id, "name": module.name}
                    for module in system.modules
                ],
                "capabilities": [
                    capability.capability_id
                    for capability in system.business_capabilities
                ],
            }
        else:  # fragment
            system = isr.system
            artifact["style"] = "fragment"
            artifact["fragments"] = {
                "architecture_summary": (
                    "modules: "
                    + ", ".join(module.name for module in system.modules)
                    + "; capabilities: "
                    + ", ".join(
                        capability.capability_id
                        for capability in system.business_capabilities
                    )
                ),
                "lifecycle_summary": (
                    "deployment intents: "
                    + ", ".join(
                        intent.deployment_id
                        for intent in system.deployment_intents
                    )
                ),
            }
        return artifact