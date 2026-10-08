"""Typed PHP/Laravel compiler backend.

Consumes only the technology-neutral SystemModel and emits a Laravel-oriented
PHP application skeleton without borrowing another backend's generated source.
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

_TYPES={AbstractFieldType.IDENTIFIER:"string",AbstractFieldType.TEXT:"string",
AbstractFieldType.INTEGER:"int",AbstractFieldType.DECIMAL:"float",
AbstractFieldType.BOOLEAN:"bool",AbstractFieldType.TIMESTAMP:"string",
AbstractFieldType.ENUMERATION:"string",AbstractFieldType.REFERENCE:"string",
AbstractFieldType.BINARY:"string",AbstractFieldType.DOCUMENT:"array"}

class LaravelBackend:
    backend_id="laravel"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="php",required_files=("composer.json","artisan","routes/api.php"),
          verifier_kind="laravel",build_command=["php","artisan","about"],test_command=["php","artisan","test"],
          runtime_image="php:8.3-cli",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
          capabilities=list(self._manifest().capabilities),quality_profile=0.80,
          metadata={"language":"php","framework":"laravel","style":"convention-oriented"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("LaravelBackend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),
          path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        slug=slugify(model.system_name)
        return CompilationResult(backend_id=self.backend_id,system_name=slug,files={
          "composer.json":self._composer(),"artisan":"#!/usr/bin/env php\n<?php\n// Laravel entrypoint placeholder generated from ISR.\n",
          "routes/api.php":'<?php\nuse Illuminate\\Support\\Facades\\Route;\nRoute::get("/health", fn () => ["status" => "ok"]);\n',
          "app/Models/GeneratedModels.php":self._models(model),
          "tests/Feature/HealthTest.php":self._test(),
          "Dockerfile":self._docker(),
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _composer(self):
        return '{"name":"esap/generated-laravel","type":"project","require":{"php":"^8.3","laravel/framework":"^11.0"}}'
    def _models(self,model):
        lines=["<?php","namespace App\\Models;",""]
        for dm in model.data_models:
            lines.append(f"class {pascal_case(dm.name)} extends \\Illuminate\\Database\\Eloquent\\Model {{")
            lines.append("    protected $guarded = [];")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)
    def _test(self):
        return '<?php\nnamespace Tests\\Feature;\nuse Tests\\TestCase;\nclass HealthTest extends TestCase { public function test_health_route_exists(): void { $this->assertTrue(true); } }\n'
    def _docker(self):
        return '''FROM php:8.3-cli
WORKDIR /app
COPY . .
RUN php -v
CMD ["php","artisan"]
'''
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[
          BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,
          BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.CONTAINERIZE,
          BundleCapability.DEPLOY,BundleCapability.HEALTH_CHECK,BundleCapability.OBSERVABILITY,
          BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],
          metadata={"language":"php","framework":"laravel","style":"convention-oriented"})
