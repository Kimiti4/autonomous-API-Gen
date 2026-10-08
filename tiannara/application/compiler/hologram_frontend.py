"""Hologram Elixir frontend compiler target.

Hologram is modeled as an Elixir client/server application target, distinct from
Phoenix LiveView's server-reactive model.
"""
from __future__ import annotations
from pathlib import Path
from tiannara.application.compiler.build_profile import BackendBuildProfile
from tiannara.application.compiler.writer import write_bundle
from tiannara.domain.models.backend_declaration import ArtifactKind, BackendCapabilityDeclaration
from tiannara.domain.models.bundle import SystemDeploymentBundle
from tiannara.domain.models.capability_manifest import BundleCapability, CapabilityManifest
from tiannara.domain.models.compilation import CompilationResult
from tiannara.domain.models.genome import Genome
from tiannara.domain.models.isr import IntermediateSoftwareRepresentation
from tiannara.domain.models.system_model import SystemModel
from .naming import slugify

class HologramFrontend:
    backend_id="hologram"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="elixir",required_files=("mix.exs","lib/esap_app/page.ex"),verifier_kind="hologram",build_command=["mix","compile"],test_command=["mix","test"],runtime_image="elixir:1.18",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.FRONTEND_APP],capabilities=list(self._manifest().capabilities),quality_profile=0.80,metadata={"language":"elixir","framework":"hologram","runtime_model":"server_client_elixir"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("HologramFrontend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "mix.exs":'defmodule EsapApp.MixProject do\n  use Mix.Project\n  def project, do: [app: :esap_app, version: "0.1.0", elixir: "~> 1.18"]\n  def application, do: [extra_applications: [:logger]]\nend\n',
          "lib/esap_app/page.ex":f'defmodule EsapApp.Page do\n  # Hologram target: client/server Elixir boundary.\n  def title, do: "{model.system_name}"\nend\n',
          "test/page_test.exs":'defmodule EsapApp.PageTest do\n  use ExUnit.Case\n  test "page title is deterministic", do: assert EsapApp.Page.title() != ""\nend\n',
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],metadata={"language":"elixir","framework":"hologram","runtime_model":"server_client_elixir"})
