"""Typed Ruby/Rails compiler backend.

Consumes only the technology-neutral SystemModel and emits a Rails-oriented
Ruby application skeleton. It intentionally does not reuse Laravel or Node
implementation templates.
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
from .naming import pascal_case, slugify

class RailsBackend:
    backend_id="rails"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="ruby",required_files=("Gemfile","config/routes.rb","app/models/generated_models.rb"),
          verifier_kind="rails",build_command=["bundle","exec","rails","about"],test_command=["bundle","exec","rails","test"],
          runtime_image="ruby:3.3",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
          capabilities=list(self._manifest().capabilities),quality_profile=0.80,
          metadata={"language":"ruby","framework":"rails","style":"convention-over-configuration"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("RailsBackend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),
          path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "Gemfile":self._gemfile(),"config/routes.rb":'Rails.application.routes.draw do\n  get "/health", to: "health#show"\nend\n',
          "app/controllers/health_controller.rb":'class HealthController < ApplicationController\n  def show\n    render json: { status: "ok" }\n  end\nend\n',
          "app/models/generated_models.rb":self._models(model),
          "test/controllers/health_controller_test.rb":self._test(),
          "Dockerfile":self._docker(),
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _gemfile(self):
        return '''source "https://rubygems.org"
gem "rails", "~> 8.0"
'''
    def _models(self,model):
        lines=[]
        for dm in model.data_models:
            lines.append(f"class {pascal_case(dm.name)} < ApplicationRecord")
            lines.append("end")
            lines.append("")
        return "\n".join(lines)
    def _test(self):
        return '''require "test_helper"
class HealthControllerTest < ActionDispatch::IntegrationTest
  test "health endpoint exists" do
    get "/health"
    assert_response :success
  end
end
'''
    def _docker(self):
        return '''FROM ruby:3.3
WORKDIR /app
COPY . .
RUN bundle install
CMD ["bundle","exec","rails","server","-b","0.0.0.0"]
'''
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[
          BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,
          BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.CONTAINERIZE,
          BundleCapability.DEPLOY,BundleCapability.HEALTH_CHECK,BundleCapability.OBSERVABILITY,
          BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],
          metadata={"language":"ruby","framework":"rails","style":"convention-oriented"})
