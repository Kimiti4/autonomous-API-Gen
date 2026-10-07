"""Typed compiler adapter for the existing Rust/Axum emitter.

The legacy emitter remains the source implementation until its output is fully
brought under the typed SystemModel/evidence contract. This adapter deliberately
does not register the backend as production-ready yet.
"""
from __future__ import annotations

from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.domain.models.backend_declaration import ArtifactKind, BackendCapabilityDeclaration
from tiannara.domain.models.capability_manifest import BundleCapability
from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.domain.models.genome import Genome
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.compilation import CompilationResult
from tiannara.application.compiler.writer import write_bundle
from .naming import slugify


class RustAxumTypedAdapter:
    backend_id = "rust_axum"

    def build_profile(self, system_name: str) -> BackendBuildProfile:
        slug = slugify(system_name)
        return BackendBuildProfile(
            language="rust",
            required_files=("Cargo.toml", "src/main.rs", "Dockerfile"),
            verifier_kind="required_files",
            build_command=["cargo", "build", "--locked"],
            test_command=["cargo", "test", "--locked"],
            runtime_image="rust:1.78-slim",
            requires_build_phase=False,
        )

    def declaration(self) -> BackendCapabilityDeclaration:
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=[
                BundleCapability.BUILD,
                BundleCapability.TEST,
                BundleCapability.CONTAINERIZE,
                BundleCapability.HEALTH_CHECK,
                BundleCapability.DOCUMENTATION,
            ],
            quality_profile=0.40,
            metadata={"language":"rust","framework":"axum","status":"adapter-pending-certification"},
        )

    def compile(self, isr: IntermediateSoftwareRepresentation, genome: Genome, output_dir: str) -> SystemDeploymentBundle:
        raise RuntimeError(
            "rust_axum is not production-registered: typed SystemModel lowering and "
            "independent runtime verification must be completed before generation."
        )

    def generate(self, system_model) -> CompilationResult:
        raise RuntimeError(
            "rust_axum is not production-registered: complete the typed adapter before use."
        )
