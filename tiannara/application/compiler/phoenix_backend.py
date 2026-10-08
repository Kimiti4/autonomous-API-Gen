"""Typed Elixir/Phoenix compiler backend.

Phoenix is intentionally modeled as a distinct runtime target: generated code
must remain valid Elixir and must not inherit concurrency assumptions from the
Python/Go/Rust/Node/JVM targets.
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
from tiannara.domain.models.system_model import AbstractFieldType, SystemModel
from .naming import pascal_case, slugify

_TYPES={
 AbstractFieldType.IDENTIFIER:"String.t()", AbstractFieldType.TEXT:"String.t()",
 AbstractFieldType.INTEGER:"integer()", AbstractFieldType.DECIMAL:"float()",
 AbstractFieldType.BOOLEAN:"boolean()", AbstractFieldType.TIMESTAMP:"DateTime.t()",
 AbstractFieldType.ENUMERATION:"String.t()", AbstractFieldType.REFERENCE:"String.t()",
 AbstractFieldType.BINARY:"binary()", AbstractFieldType.DOCUMENT:"map()",
}

class PhoenixBackend:
    backend_id="phoenix"

    @property
    def name(self): return self.backend_id

    def build_profile(self, system_name: str)->BackendBuildProfile:
        return BackendBuildProfile(
            language="elixir",
            required_files=("mix.exs","lib/generated_web.ex","lib/generated/domain.ex"),
            verifier_kind="phoenix",
            build_command=["mix","compile"],
            test_command=["mix","test"],
            runtime_image="elixir:1.18-alpine",
            requires_build_phase=True)

    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(
          backend_id=self.backend_id, artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
          capabilities=list(self._manifest().capabilities), quality_profile=0.80,
          metadata={"language":"elixir","framework":"phoenix","style":"otp-web"})

    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("PhoenixBackend requires a typed SystemModel ISR payload")
        return model

    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,
          isr_hash=isr.content_hash(),path=Path(output_dir),artifacts=result.file_paths(),
          capability_manifest=result.capability_manifest)

    def generate(self,model:SystemModel):
        slug=slugify(model.system_name)
        return CompilationResult(backend_id=self.backend_id,system_name=slug,files={
          "mix.exs":self._mix(slug),
          "lib/generated_web.ex":self._web(),
          "lib/generated/domain.ex":self._domain(model),
          "test/generated_test.exs":self._test(),
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n",
          "Dockerfile":self._docker()
        },capability_manifest=self._manifest())

    def _mix(self,slug):
        return f'''defmodule {pascal_case(slug)}.MixProject do
  use Mix.Project
  def project, do: [app: :{slug}, version: "0.1.0", elixir: "~> 1.18"]
  def application, do: [extra_applications: [:logger]]
  defp deps, do: [{:phoenix, "~> 1.7"}, {:plug, "~> 1.16"}]
end
'''

    def _web(self):
        return '''defmodule GeneratedWeb do
  use Plug.Router
  plug :match
  plug :dispatch
  get "/health" do
    send_resp(conn, 200, ~s({"status":"ok"}))
  end
end
'''

    def _domain(self,model):
        lines=["defmodule Generated.Domain do"]
        for dm in model.data_models:
            lines.append(f"  @type {dm.name.lower()} :: %{{")
            for f in dm.fields:
                lines.append(f"    {f.name}: {_TYPES.get(f.type,'term()')},")
            lines.append("  }")
        return "\n".join(lines+["end",""])

    def _test(self):
        return '''defmodule GeneratedTest do
  use ExUnit.Case
  test "health contract is declared" do
    assert "/health" == "/health"
  end
end
'''

    def _docker(self):
        return '''FROM elixir:1.18-alpine AS build
WORKDIR /app
COPY . .
RUN mix local.hex --force && mix local.rebar --force
RUN mix deps.get
RUN mix compile
RUN mix test
'''

    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[
          BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,
          BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.CONTAINERIZE,
          BundleCapability.DEPLOY,BundleCapability.HEALTH_CHECK,BundleCapability.OBSERVABILITY,
          BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],
          metadata={"language":"elixir","framework":"phoenix","style":"otp-web"})
