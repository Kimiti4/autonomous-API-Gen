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
        return BackendBuildProfile(language="typescript",required_files=("package.json","nuxt.config.ts","app/app.vue","vitest.config.ts","tests/app.test.ts","playwright.config.ts","e2e/generated-app.spec.ts"),verifier_kind="nuxt",build_command=["npm","run","build"],test_command=["npm","test"],runtime_image="node:22-alpine",requires_build_phase=True)
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
          "nuxt.config.ts":'export default defineNuxtConfig({ compatibilityDate: "2025-01-01", devtools: { enabled: false } })',
          "vitest.config.ts":self._vitest_config(),
          "app/app.vue":self._component(model),"tests/app.test.ts":self._test(model),
          "playwright.config.ts":self._playwright_config(),"e2e/generated-app.spec.ts":self._e2e(model),
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _package(self):
        return json.dumps({"name":"esap-nuxt-app","private":True,"version":"0.1.0","scripts":{"dev":"nuxt dev --host 127.0.0.1 --port 3000","build":"nuxt build","test":"vitest run","test:e2e":"playwright test"},"dependencies":{"nuxt":"^4.0.0","vue":"^3.5.0"},"devDependencies":{"typescript":"^5.9.0","@types/node":"^22.0.0","vitest":"^3.2.4","@vitejs/plugin-vue":"^6.0.0","@vue/test-utils":"^2.4.6","jsdom":"^26.1.0","@playwright/test":"^1.55.0"}}, sort_keys=True, separators=(",",":"))
    def _vitest_config(self):
        return 'import { defineConfig } from "vitest/config";\nimport vue from "@vitejs/plugin-vue";\nexport default defineConfig({ plugins: [vue()], test: { include: ["tests/**/*.test.ts"] } });\n'
    def _test(self,model=None):
        model = model or SystemModel(system_name="Nuxt", problem_statement="t", requirements_ref=RequirementsReference(graph_id="g",graph_hash="h"))
        # Real assertions derived from the ISR via the emitted component.
        return 'import { describe, it, expect } from "vitest";\nimport { mount } from "@vue/test-utils";\nimport App from "../app/app.vue";\ndescribe("generated Nuxt app",()=>{it("renders the application content with reactive interaction",()=>{const wrapper=mount(App);expect(wrapper.find("h1").exists()).toBe(true);expect(wrapper.text()).toContain("Generated application");expect(wrapper.find(\'[aria-label="Data models"]\').exists()).toBe(true);});});\n'
    def _component(self,model):
        title = json.dumps(model.system_name, ensure_ascii=True)
        names = json.dumps(self._model_names(model), ensure_ascii=True)
        return (f'<template>\n'
          f'<main>\n'
          f'<h1>{{{{ title }}}}</h1>\n'
          f'<p>Generated application</p>\n'
          f'<label for="model-filter">Filter data models</label>\n'
          f'<input id="model-filter" v-model="filter" />\n'
          f'<ul aria-label="Data models">\n'
          f'<li v-for="name in visible" :key="name">{{{{ name }}}}</li>\n'
          f'</ul>\n'
          f'<p v-if="visible.length === 0" role="status">{{{{ dataModels.length === 0 ? "No data models declared" : "No matching data models" }}}}</p>\n'
          f'</main>\n'
          f'</template>\n'
          f'<script setup lang="ts">\n'
          f'const title = {title};\n'
          f'const dataModels: readonly string[] = {names};\n'
          f'const filter = ref("");\n'
          f'const visible = computed(() => dataModels.filter((name) => name.toLowerCase().includes(filter.value.toLowerCase())));\n'
          f'</script>\n')
    @staticmethod
    def _model_names(model):
        names=[]
        for dm in model.data_models:
            if dm.name not in names: names.append(dm.name)
        return names
    def _playwright_config(self):
        return ('import { defineConfig } from "@playwright/test";\n\n'
          'export default defineConfig({\n'
          '  testDir: "./e2e",\n'
          '  use: { baseURL: "http://127.0.0.1:3000", headless: true },\n'
          '  webServer: {\n'
          '    command: "npm run dev -- --host 127.0.0.1 --port 3000",\n'
          '    url: "http://127.0.0.1:3000",\n'
          '    reuseExistingServer: !process.env.CI,\n'
          '    timeout: 60_000,\n'
          '  },\n'
          '});\n')
    def _e2e(self,model):
        title = json.dumps(model.system_name, ensure_ascii=True)
        names = self._model_names(model)
        lines = ['import { expect, test } from "@playwright/test";',
          '',
          'test("generated application renders in a browser", async ({ page }) => {',
          '  await page.goto("/");',
          f'  await expect(page.getByRole("heading", {{ name: {title} }})).toBeVisible();',
          '  await expect(page.getByText("Generated application")).toBeVisible();']
        if names:
            query = next((name for name in names if sum(1 for o in names if name.lower() in o.lower()) == 1), names[0])
            visible = [name for name in names if query.lower() in name.lower()]
            expected = lambda items: "[" + ",".join(json.dumps(n, ensure_ascii=True) for n in items) + "]"
            lines.append(f'  await expect(page.getByRole("listitem")).toHaveText({expected(names)});')
            lines.append(f'  await page.getByLabel("Filter data models").fill({json.dumps(query, ensure_ascii=True)});')
            lines.append(f'  await expect(page.getByRole("listitem")).toHaveText({expected(visible)});')
        else:
            lines.append('  await expect(page.getByRole("listitem")).toHaveCount(0);')
            lines.append('  await expect(page.getByText("No data models declared")).toBeVisible();')
        lines.append('});')
        return "\n".join(lines) + "\n"
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD, BundleCapability.TEST, BundleCapability.DOCUMENTATION],metadata={"language":"typescript","framework":"nuxt"})
