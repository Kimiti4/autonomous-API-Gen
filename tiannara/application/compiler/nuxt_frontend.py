"""Nuxt + Vue TypeScript frontend compiler target."""
from __future__ import annotations
from pathlib import Path
import json
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

class NuxtFrontend:
    backend_id="nuxt_ts"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="typescript",required_files=("package.json","nuxt.config.ts","app/app.vue","vitest.config.ts","tests/app.test.ts"),verifier_kind="nuxt",build_command=["npm","run","build"],test_command=["npm","test"],runtime_image="node:22-alpine",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.FRONTEND_APPLICATION],capabilities=list(self._manifest().capabilities),quality_profile=0.80,metadata={"language":"typescript","framework":"nuxt"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("NuxtFrontend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "package.json":self._package(),
          "nuxt.config.ts":'export default defineNuxtConfig({ compatibilityDate: "2025-01-01", compatibilityVersion: 4, devtools: { enabled: false } })',
          "vitest.config.ts":self._vitest_config(),
          "app/app.vue":f'<template><main><h1>{{{{ title }}}}</h1><p>Generated application</p></main></template>\n<script setup lang="ts">const title = {json.dumps(model.system_name, ensure_ascii=True)}</script>\n',
          "tests/app.test.ts":self._test(),
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _package(self):
        return '{"name":"esap-nuxt-app","private":true,"version":"0.1.0","scripts":{"build":"nuxt build","test":"vitest run"},"dependencies":{"nuxt":"^4.0.0","vue":"^3.5.0"},"devDependencies":{"typescript":"^5.9.0","vitest":"^3.2.4","@vitejs/plugin-vue":"^6.0.0","@vue/test-utils":"^2.4.6","jsdom":"^26.1.0"}}'
    def _vitest_config(self):
        return 'import { defineConfig } from "vitest/config";\nimport vue from "@vitejs/plugin-vue";\nexport default defineConfig({ plugins: [vue()], test: { environment: "jsdom" } });\n'
    def _test(self):
        return 'import { describe, it, expect } from "vitest";\nimport { mount } from "@vue/test-utils";\nimport App from "../app/app.vue";\ndescribe("generated Nuxt app",()=>{it("renders the application content",()=>{const wrapper=mount(App);expect(wrapper.find("h1").exists()).toBe(true);expect(wrapper.text()).toContain("Generated application");});});\n'
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],metadata={"language":"typescript","framework":"nuxt"})
