"""Vue 3 + TypeScript frontend compiler.

This target consumes the technology-neutral SystemModel and emits Vue-specific
artifacts. It intentionally shares no generated source with React.
"""
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
from .naming import pascal_case, slugify

class VueFrontend:
    backend_id="vue_ts"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="typescript",required_files=("package.json","tsconfig.json","vite.config.ts","index.html",
          "src/main.ts","src/App.vue","src/App.test.ts","playwright.config.ts","e2e/generated-app.spec.ts"),
          verifier_kind="vue",build_command=["npm","run","build"],test_command=["npm","test"],
          runtime_image="node:22-alpine",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.FRONTEND_APPLICATION],
          capabilities=list(self._manifest().capabilities),quality_profile=0.80,
          metadata={"language":"typescript","framework":"vue","style":"reactive-component"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("VueFrontend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),
          path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "package.json":self._package(),"tsconfig.json":self._tsconfig(),"vite.config.ts":self._vite_config(),"index.html":'<div id="app"></div><script type="module" src="/src/main.ts"></script>',
          "src/main.ts":self._main(),"src/App.vue":self._app(model),"src/domain.ts":self._domain(model),
          "src/App.test.ts":self._test(model),"playwright.config.ts":self._playwright_config(),
          "e2e/generated-app.spec.ts":self._e2e(model),
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _package(self):
        return json.dumps({
          "name":"esap-vue-app","private":True,"version":"0.1.0",
          "scripts":{"dev":"vite","build":"vue-tsc --noEmit && vite build","test":"vitest run","test:e2e":"playwright test"},
          "dependencies":{"vue":"^3.5.0","vite":"^7.0.0","typescript":"^5.9.0","vue-tsc":"^2.2.0","vitest":"^3.0.0",
            "@vitejs/plugin-vue":"^6.0.0","@types/node":"^22.0.0","@vue/test-utils":"^2.4.6","jsdom":"^26.1.0",
            "@playwright/test":"^1.55.0"},
        }, sort_keys=True, separators=(",",":"))
    def _vite_config(self):
        return ('import vue from "@vitejs/plugin-vue";\n'
          'import { defineConfig } from "vitest/config";\n'
          'export default defineConfig({ plugins: [vue()], test: { include: ["src/**/*.test.ts"] } });\n')
    def _tsconfig(self):
        return '{"compilerOptions":{"target":"ES2022","module":"ESNext","moduleResolution":"Bundler","strict":true,"noEmit":true,"skipLibCheck":true}}'
    def _main(self):
        return 'import { createApp } from "vue";\nimport App from "./App.vue";\ncreateApp(App).mount("#app");\n'
    @staticmethod
    def _model_names(model):
        # Duplicate names would collide as v-for keys; keep first occurrence order.
        names=[]
        for dm in model.data_models:
            if dm.name not in names: names.append(dm.name)
        return names
    def _app(self,model):
        # Vue interpolation renders ISR values as text, never as executable markup.
        title = json.dumps(model.system_name, ensure_ascii=True)
        models = json.dumps(self._model_names(model), ensure_ascii=True)
        return "\n".join([
          '<script setup lang="ts">',
          'import { computed, ref } from "vue";',
          f'const title = {title};',
          f'const dataModels: readonly string[] = {models};',
          'const filter = ref("");',
          'const visible = computed(() => dataModels.filter((name) => name.toLowerCase().includes(filter.value.toLowerCase())));',
          '</script>',
          '',
          '<template>',
          '  <main>',
          '    <h1>{{ title }}</h1>',
          '    <p>Generated application</p>',
          '    <label for="model-filter">Filter data models</label>',
          '    <input id="model-filter" v-model="filter" />',
          '    <ul aria-label="Data models">',
          '      <li v-for="name in visible" :key="name">{{ name }}</li>',
          '    </ul>',
          '    <p v-if="visible.length === 0" role="status">{{ dataModels.length === 0 ? "No data models declared" : "No matching data models" }}</p>',
          '  </main>',
          '</template>',
          '',
        ])
    def _domain(self,model):
        return "\n".join(f"export interface {pascal_case(dm.name)} {{\n"+"".join(f"  {f.name}{'' if f.required else '?'}: unknown;\n" for f in dm.fields)+"}\n" for dm in model.data_models)
    def _test(self,model):
        model_assertions = "".join(f'expect(wrapper.text()).toContain({json.dumps(name, ensure_ascii=True)});' for name in self._model_names(model))
        empty_assertion = 'expect(wrapper.text()).toContain("No data models declared");' if not self._model_names(model) else ""
        return ('// @vitest-environment jsdom\n'
          'import { describe, it, expect } from "vitest";\n'
          'import { mount } from "@vue/test-utils";\n'
          'import App from "./App.vue";\n'
          'describe("generated Vue application",()=>{it("renders the title and application content",()=>{'
          'const wrapper=mount(App);'
          'expect(wrapper.find("h1").exists()).toBe(true);'
          'expect(wrapper.text()).toContain("Generated application");'
          'expect(wrapper.find(\'[aria-label="Data models"]\').exists()).toBe(true);'
          + model_assertions + empty_assertion + '});});\n')
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
            # Choose a name that no other name contains, so filtering it isolates a known subset.
            query = next((name for name in names if sum(1 for other in names if name.lower() in other.lower()) == 1), names[0])
            visible = [name for name in names if query.lower() in name.lower()]
            expected = lambda items: "[" + ",".join(json.dumps(name, ensure_ascii=True) for name in items) + "]"
            lines.append(f'  await expect(page.getByRole("listitem")).toHaveText({expected(names)});')
            lines.append(f'  await page.getByLabel("Filter data models").fill({json.dumps(query, ensure_ascii=True)});')
            # Exact text content, so a shorter name cannot be satisfied by a longer one.
            lines.append(f'  await expect(page.getByRole("listitem")).toHaveText({expected(visible)});')
        else:
            lines.append('  await expect(page.getByText("No data models declared")).toBeVisible();')
        lines.append('});')
        return "\n".join(lines) + "\n"
    def _playwright_config(self):
        return ('import { defineConfig } from "@playwright/test";\n\n'
          'export default defineConfig({\n'
          '  testDir: "./e2e",\n'
          '  use: { baseURL: "http://127.0.0.1:5173", headless: true },\n'
          '  webServer: {\n'
          '    command: "npm run dev -- --host 127.0.0.1",\n'
          '    url: "http://127.0.0.1:5173",\n'
          '    reuseExistingServer: !process.env.CI,\n'
          '    timeout: 30_000,\n'
          '  },\n'
          '});\n')
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD, BundleCapability.TEST, BundleCapability.DOCUMENTATION],metadata={"language":"typescript","framework":"vue","style":"reactive-component"})
