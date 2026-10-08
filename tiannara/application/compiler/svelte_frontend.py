"""Svelte + TypeScript frontend compiler target."""
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

class SvelteFrontend:
    backend_id="svelte_ts"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="typescript",required_files=("package.json","svelte.config.js","src/App.svelte"),verifier_kind="svelte",build_command=["npm","run","build"],test_command=["npm","test"],runtime_image="node:22-alpine",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.FRONTEND_APP],capabilities=list(self._manifest().capabilities),quality_profile=0.80,metadata={"language":"typescript","framework":"svelte"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("SvelteFrontend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "package.json":'{"name":"esap-svelte-app","private":true,"version":"0.1.0","scripts":{"build":"vite build","test":"vitest run"},"devDependencies":{"@sveltejs/vite-plugin-svelte":"^6.0.0","svelte":"^5.0.0","vite":"^7.0.0","typescript":"^5.9.0","vitest":"^3.0.0"}}',
          "svelte.config.js":'import { vitePreprocess } from "@sveltejs/vite-plugin-svelte"; export default { preprocess: vitePreprocess() };',
          "vite.config.ts":'import { defineConfig } from "vite"; import { svelte } from "@sveltejs/vite-plugin-svelte"; export default defineConfig({ plugins: [svelte()] });',
          "src/main.ts":'import App from "./App.svelte"; const app = new App({ target: document.body }); export default app;',
          "src/App.svelte":f'<script lang="ts">const title = "{model.system_name}";</script>\n<main><h1>{{title}}</h1><p>Generated application</p></main>\n',
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],metadata={"language":"typescript","framework":"svelte"})
