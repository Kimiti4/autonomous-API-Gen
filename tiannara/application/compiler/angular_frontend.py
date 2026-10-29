"""Angular + TypeScript frontend compiler.

The compiler consumes only the technology-neutral SystemModel and emits an
Angular-specific standalone application skeleton. Framework-specific behavior
is verified independently rather than copied from another frontend target.
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

class AngularFrontend:
    backend_id="angular_ts"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="typescript",required_files=("package.json","angular.json","tsconfig.json","tsconfig.spec.json","src/index.html","src/main.ts","src/app/app.component.spec.ts","playwright.config.ts","e2e/generated-app.spec.ts"),
          verifier_kind="angular",build_command=["npm","run","build"],test_command=["npm","test"],
          runtime_image="node:22-alpine",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.FRONTEND_APPLICATION],
          capabilities=list(self._manifest().capabilities),quality_profile=0.80,
          metadata={"language":"typescript","framework":"angular","style":"standalone-components"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("AngularFrontend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),
          path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "package.json":self._package(),"angular.json":self._angular_json(),"tsconfig.json":self._tsconfig(),"tsconfig.spec.json":self._tsconfig_spec(),
          "src/index.html":self._index(model),"src/main.ts":self._main(),"src/app/app.component.ts":self._component(model),
          "src/app/app.component.html":self._template(model),"src/app/app.component.spec.ts":self._test(model),
          "playwright.config.ts":self._playwright_config(),"e2e/generated-app.spec.ts":self._e2e(model),
          "src/domain.ts":self._domain(model),"README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _package(self):
        scripts = {"build":"ng build","test":"ng test","test:e2e":"playwright test","start":"ng serve"}
        deps = {"@angular/common":"^20.0.0","@angular/core":"^20.0.0","@angular/platform-browser":"^20.0.0","rxjs":"^7.8.0","zone.js":"^0.15.0"}
        dev = {"@angular/build":"^20.0.0","@angular/cli":"^20.0.0","@angular/compiler-cli":"^20.0.0","typescript":"^5.9.0","vitest":"^3.2.4","jsdom":"^26.1.0","@playwright/test":"^1.55.0"}
        return json.dumps({"name":"esap-angular-app","private":True,"version":"0.1.0",
          "scripts":scripts,"dependencies":deps,"devDependencies":dev}, sort_keys=True, separators=(",",":"))
    def _angular_json(self):
        return '{"$schema":"./node_modules/@angular/cli/lib/config/schema.json","version":1,"projects":{"app":{"projectType":"application","root":"","sourceRoot":"src","architect":{"build":{"builder":"@angular/build:application","options":{"browser":"src/main.ts","index":"src/index.html","tsConfig":"tsconfig.json"}},"test":{"builder":"@angular/build:unit-test","options":{"runner":"vitest","buildTarget":"app:build","tsConfig":"tsconfig.spec.json"}}}}}}'
    def _tsconfig(self):
        return '{"compilerOptions":{"target":"ES2022","module":"ES2022","moduleResolution":"bundler","strict":true,"experimentalDecorators":true,"skipLibCheck":true},"angularCompilerOptions":{"strictTemplates":true}}'
    def _index(self,model):
        return '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Generated application</title><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><app-root></app-root></body></html>'
    def _tsconfig_spec(self):
        return '{"extends":"./tsconfig.json","compilerOptions":{"types":["vitest/globals"]},"include":["src/**/*.spec.ts","e2e/**/*.spec.ts"]}'
    def _main(self):
        return 'import { bootstrapApplication } from "@angular/platform-browser";\nimport { AppComponent } from "./app/app.component";\nbootstrapApplication(AppComponent).catch(err => console.error(err));\n'
    def _component(self,model):
        title = json.dumps(model.system_name, ensure_ascii=True)
        names = json.dumps([dm.name for dm in model.data_models], ensure_ascii=True)
        return (f'import {{ Component }} from "@angular/core";\n'
          f'import {{ FormsModule }} from "@angular/forms";\n\n'
          f'@Component({{selector:"app-root",standalone:true,imports:[FormsModule],templateUrl:"./app.component.html"}})\n'
          f'export class AppComponent {{\n'
          f'  title = {title};\n'
          f'  dataModels = {names};\n'
          f'  filter = "";\n'
          f'  get visible() {{ return this.dataModels.filter((n) => n.toLowerCase().includes(this.filter.toLowerCase())); }}\n'
          f'}}\n')
    def _template(self,model):
        return ('<main>\n'
          '  <h1>{{ title }}</h1>\n'
          '  <p>Generated application</p>\n'
          '  <label for="model-filter">Filter data models</label>\n'
          '  <input id="model-filter" type="text" [(ngModel)]="filter" />\n'
          '  <ul aria-label="Data models">\n'
          '    <li *ngFor="let name of visible">{{ name }}</li>\n'
          '  </ul>\n'
          '  <p *ngIf="visible.length === 0" role="status">{{ dataModels.length === 0 ? "No data models declared" : "No matching data models" }}</p>\n'
          '</main>\n')
    def _test(self,model):
        title = json.dumps(model.system_name, ensure_ascii=True)
        names = [dm.name for dm in model.data_models]
        names_json = json.dumps(names, ensure_ascii=True)
        return (f'import "zone.js";\n'
          f'import {{ TestBed }} from "@angular/core/testing";\n'
          f'import {{ describe, it, expect }} from "vitest";\n'
          f'import {{ FormsModule }} from "@angular/forms";\n'
          f'import {{ AppComponent }} from "./app.component";\n'
          f'describe("AppComponent",()=>{{\n'
          f'  it("renders the application content with ISR-derived data",async()=>{{\n'
          f'    await TestBed.configureTestingModule({{imports:[AppComponent,FormsModule]}}).compileComponents();\n'
          f'    const fixture=TestBed.createComponent(AppComponent);\n'
          f'    fixture.detectChanges();\n'
          f'    expect(fixture.nativeElement.querySelector("h1")?.textContent).toContain({title});\n'
          f'    expect(fixture.nativeElement.textContent).toContain("Generated application");\n'
          f'  }});\n'
          f'  it("isolates overlapping model names",()=>{{\n'
          f'    const comp=AppComponent;\n'
          f'    const instance=new comp();\n'
          f'    instance.dataModels=["Payment","Pay","Invoice"];\n'
          f'    instance.filter="Pay";\n'
          f'    expect(instance.visible).toEqual(["Pay","Payment"]);\n'
          f'  }});\n'
          f'}});\n')
    def _domain(self,model):
        return "\n".join(f"export interface {pascal_case(dm.name)} {{\n"+"".join(f"  {f.name}{'' if f.required else '?'}: unknown;\n" for f in dm.fields)+"}\n" for dm in model.data_models)
    def _playwright_config(self):
        return ('import { defineConfig } from "@playwright/test";\n\n'
          'export default defineConfig({\n'
          '  testDir: "./e2e",\n'
          '  use: { baseURL: "http://127.0.0.1:4200", headless: true },\n'
          '  webServer: {\n'
          '    command: "npm run start -- --host 127.0.0.1 --port 4200",\n'
          '    url: "http://127.0.0.1:4200",\n'
          '    reuseExistingServer: !process.env.CI,\n'
          '    timeout: 60_000,\n'
          '  },\n'
          '});\n')
    def _e2e(self,model):
        title = json.dumps(model.system_name, ensure_ascii=True)
        lines = ['import { expect, test } from "@playwright/test";',
          '',
          'test("generated application renders in a browser", async ({ page }) => {',
          '  await page.goto("/");',
          f'  await expect(page.getByRole("heading", {{ name: {title} }})).toBeVisible();',
          '  await expect(page.getByText("Generated application")).toBeVisible();',
          '  await expect(page.locator("main")).toBeVisible();',
          '});',
          '']
        return "\n".join(lines)
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD, BundleCapability.TEST, BundleCapability.DOCUMENTATION],metadata={"language":"typescript","framework":"angular","style":"standalone-components"})
