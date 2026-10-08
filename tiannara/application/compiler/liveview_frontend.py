"""Phoenix LiveView frontend compiler target.

This target models a server-reactive UI: browser interaction is represented by
LiveView events while state and rendering remain on the BEAM side.
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

class LiveViewFrontend:
    backend_id="phoenix_liveview"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="elixir",required_files=("mix.exs","lib/app_web/live/page_live.ex"),verifier_kind="phoenix_liveview",build_command=["mix","compile"],test_command=["mix","test"],runtime_image="elixir:1.18",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.FRONTEND_APP],capabilities=list(self._manifest().capabilities),quality_profile=0.80,metadata={"language":"elixir","framework":"phoenix_live_view","runtime_model":"server_reactive"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("LiveViewFrontend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        name=slugify(model.system_name)
        return CompilationResult(backend_id=self.backend_id,system_name=name,files={
          "mix.exs":'defmodule EsapApp.MixProject do\n  use Mix.Project\n  def project, do: [app: :esap_app, version: "0.1.0", elixir: "~> 1.18"]\n  def application, do: [extra_applications: [:logger]]\nend\n',
          "lib/esap_app_web.ex":'defmodule EsapAppWeb do\n  def live_view, do: quote do: use Phoenix.LiveView\nend\n',
          "lib/esap_app_web/live/page_live.ex":f'defmodule EsapAppWeb.PageLive do\n  use Phoenix.LiveView\n  def mount(_params, _session, socket), do: {{:ok, assign(socket, :title, "{model.system_name}")}}\n  def render(assigns), do: ~H"""<main><h1>{{@title}}</h1><p>Generated application</p></main>"""\nend\n',
          "test/page_live_test.exs":'defmodule EsapAppWeb.PageLiveTest do\n  use ExUnit.Case\n  test "generated LiveView module exists", do: assert Code.ensure_loaded?(EsapAppWeb.PageLive)\nend\n',
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n'
        },capability_manifest=self._manifest())
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],metadata={"language":"elixir","framework":"phoenix_live_view","runtime_model":"server_reactive"})
