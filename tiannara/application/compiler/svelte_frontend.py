"""Svelte 5 + TypeScript frontend compiler target."""
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

def _js_string(value):
    # json.dumps gives a JS string literal; "</" is escaped so an ISR value can
    # never terminate the surrounding <script> element in the .svelte file.
    return json.dumps(value, ensure_ascii=True).replace("</", "<\\/")

class SvelteFrontend:
    backend_id="svelte_ts"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="typescript",required_files=("package.json","index.html","svelte.config.js","vite.config.ts","tsconfig.json","src/main.ts","src/App.svelte","src/App.test.ts","playwright.config.ts","e2e/generated-app.spec.ts"),verifier_kind="svelte",build_command=["npm","run","build"],test_command=["npm","test"],runtime_image="node:22-alpine",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.FRONTEND_APPLICATION],capabilities=list(self._manifest().capabilities),quality_profile=0.80,metadata={"language":"typescript","framework":"svelte"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("SvelteFrontend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    @staticmethod
    def _model_names(model):
        # Duplicate names would collide as keyed #each entries; keep first occurrence order.
        names=[]
        for dm in model.data_models:
            if dm.name not in names: names.append(dm.name)
        return names
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "package.json":self._package(),
          "index.html":'<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Generated application</title></head><body><div id="app"></div><script type="module" src="/src/main.ts"></script></body></html>',
          "svelte.config.js":'import { vitePreprocess } from "@sveltejs/vite-plugin-svelte"; export default { preprocess: vitePreprocess() };',
          "vite.config.ts":self._vite_config(),
          "tsconfig.json":self._tsconfig(),
          "src/main.ts":'import { mount } from "svelte"; import App from "./App.svelte"; mount(App, { target: document.body });',
          "src/App.svelte":self._app(model),
          "src/App.test.ts":self._test(model),
          "playwright.config.ts":self._playwright_config(),
          "e2e/generated-app.spec.ts":self._e2e(model),
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _package(self):
        return json.dumps({
          "name":"esap-svelte-app","private":True,"version":"0.1.0",
          "scripts":{"dev":"vite","build":"svelte-check --tsconfig ./tsconfig.json && vite build","test":"vitest run","test:e2e":"playwright test"},
          "devDependencies":{"@sveltejs/vite-plugin-svelte":"^6.0.0","svelte":"^5.0.0","svelte-check":"^4.0.0","vite":"^7.0.0",
            "typescript":"^5.9.0","@types/node":"^22.0.0","vitest":"^3.2.4","@testing-library/svelte":"^5.2.8","jsdom":"^26.1.0",
            "@playwright/test":"^1.55.0"},
        }, sort_keys=True, separators=(",",":"))
    def _vite_config(self):
        return ('import { defineConfig } from "vitest/config"; import { svelte } from "@sveltejs/vite-plugin-svelte";\n'
          'export default defineConfig({ plugins: [svelte()], resolve: { conditions: ["browser"] }, '
          # Vitest's default glob also matches .spec.ts, so the Playwright spec must be excluded.
          'test: { include: ["src/**/*.test.ts"], environment: "jsdom", environmentOptions: { jsdom: { url: "http://localhost/" } } } });\n')
    def _tsconfig(self):
        return json.dumps({
          "compilerOptions":{"target":"ES2022","module":"ESNext","moduleResolution":"bundler",
            "lib":["ES2022","DOM","DOM.Iterable"],"strict":True,"noEmit":True,"skipLibCheck":True,
            "allowJs":True,"checkJs":False,"isolatedModules":True,"verbatimModuleSyntax":True,
            "types":["vite/client"]},
          "include":["src/**/*.ts","src/**/*.svelte","e2e/**/*.ts","playwright.config.ts","vite.config.ts"],
        }, indent=2, sort_keys=True) + "\n"
    def _app(self,model):
        # Svelte interpolation renders ISR values as text, never as executable markup.
        title = _js_string(model.system_name)
        models = _js_string(self._model_names(model))
        return "\n".join([
          '<script lang="ts">',
          f'  const title = {title};',
          f'  const dataModels: readonly string[] = {models};',
          '  let filter = $state("");',
          '  const visible = $derived(dataModels.filter((name) => name.toLowerCase().includes(filter.toLowerCase())));',
          '</script>',
          '',
          '<main>',
          '  <h1>{title}</h1>',
          '  <p>Generated application</p>',
          '  <label for="model-filter">Filter data models</label>',
          '  <input id="model-filter" bind:value={filter} />',
          '  <ul aria-label="Data models">',
          '    {#each visible as name (name)}',
          '      <li>{name}</li>',
          '    {/each}',
          '  </ul>',
          '  {#if visible.length === 0}',
          '    <p role="status">{dataModels.length === 0 ? "No data models declared" : "No matching data models"}</p>',
          '  {/if}',
          '</main>',
          '',
        ])
    def _test(self,model):
        names = self._model_names(model)
        name_assertions = "".join(f'expect(container.textContent).toContain({_js_string(name)});' for name in names)
        empty_assertion = 'expect(container.textContent).toContain("No data models declared");' if not names else ""
        return ('// @vitest-environment jsdom\n'
          'import { describe, it, expect } from "vitest";\n'
          'import { render } from "@testing-library/svelte";\n'
          'import App from "./App.svelte";\n'
          'describe("generated Svelte application",()=>{it("renders the title and application content",()=>{'
          'const {container}=render(App);'
          'expect(container.querySelector("h1")?.textContent).toBe(' + _js_string(model.system_name) + ');'
          'expect(container.textContent).toContain("Generated application");'
          'expect(container.querySelector(\'[aria-label="Data models"]\')).not.toBeNull();'
          + name_assertions + empty_assertion + '});});\n')
    def _e2e(self,model):
        title = _js_string(model.system_name)
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
            expected = lambda items: "[" + ",".join(_js_string(name) for name in items) + "]"
            lines.append(f'  await expect(page.getByRole("listitem")).toHaveText({expected(names)});')
            lines.append(f'  await page.getByLabel("Filter data models").fill({_js_string(query)});')
            # Exact text content, so a shorter name cannot be satisfied by a longer one.
            lines.append(f'  await expect(page.getByRole("listitem")).toHaveText({expected(visible)});')
        else:
            lines.append('  await expect(page.getByRole("listitem")).toHaveCount(0);')
            lines.append('  await expect(page.getByText("No data models declared")).toBeVisible();')
        lines.append('});')
        return "\n".join(lines) + "\n"
    def _playwright_config(self):
        return ('import { defineConfig } from "@playwright/test";\n\n'
          'export default defineConfig({\n'
          '  testDir: "./e2e",\n'
          '  use: { baseURL: "http://127.0.0.1:5173", headless: true },\n'
          '  webServer: {\n'
          '    command: "npm run dev -- --host 127.0.0.1 --port 5173",\n'
          '    url: "http://127.0.0.1:5173",\n'
          '    reuseExistingServer: !process.env.CI,\n'
          '    timeout: 30_000,\n'
          '  },\n'
          '});\n')
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD, BundleCapability.TEST, BundleCapability.DOCUMENTATION],metadata={"language":"typescript","framework":"svelte"})
