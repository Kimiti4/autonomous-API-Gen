"""Angular + TypeScript frontend compiler.

The compiler consumes only the technology-neutral SystemModel and emits an
Angular-specific standalone application skeleton. Framework-specific behavior
is verified independently rather than copied from another frontend target.
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

class AngularFrontend:
    backend_id="angular_ts"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="typescript",required_files=("package.json","tsconfig.json","src/main.ts"),
          verifier_kind="angular",build_command=["npm","run","build"],test_command=["npm","test","--","--watch=false"],
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
          "package.json":self._package(),"angular.json":self._angular_json(),"tsconfig.json":self._tsconfig(),
          "src/main.ts":self._main(),"src/app/app.component.ts":self._component(model),
          "src/app/app.component.html":self._template(model),"src/app/app.component.spec.ts":self._test(),
          "src/domain.ts":self._domain(model),"README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _package(self):
        return '{"name":"esap-angular-app","private":true,"version":"0.1.0","scripts":{"build":"ng build","test":"ng test --watch=false --browsers=ChromeHeadless"},"dependencies":{"@angular/common":"^20.0.0","@angular/core":"^20.0.0","@angular/platform-browser":"^20.0.0","rxjs":"^7.8.0","zone.js":"^0.15.0"},"devDependencies":{"@angular/cli":"^20.0.0","@angular/compiler-cli":"^20.0.0","typescript":"^5.8.0"}}'
    def _angular_json(self):
        return '{"$schema":"./node_modules/@angular/cli/lib/config/schema.json","version":1,"projects":{"app":{"projectType":"application","root":"","sourceRoot":"src","architect":{"build":{"builder":"@angular-devkit/build-angular:application","options":{"browser":"src/main.ts","tsConfig":"tsconfig.json"}},"test":{"builder":"@angular-devkit/build-angular:karma","options":{"tsConfig":"tsconfig.json"}}}}}}'
    def _tsconfig(self):
        return '{"compilerOptions":{"target":"ES2022","module":"ES2022","moduleResolution":"bundler","strict":true,"experimentalDecorators":true,"skipLibCheck":true},"angularCompilerOptions":{"strictTemplates":true}}'
    def _main(self):
        return 'import { bootstrapApplication } from "@angular/platform-browser";\nimport { AppComponent } from "./app/app.component";\nbootstrapApplication(AppComponent).catch(err => console.error(err));\n'
    def _component(self,model):
        return f'import {{ Component }} from "@angular/core";\n\n@Component({{selector:"app-root",standalone:true,templateUrl:"./app.component.html"}})\nexport class AppComponent {{ readonly title = "{model.system_name}"; }}\n'
    def _template(self,model):
        return '<main><h1>{{ title }}</h1><p>Generated application</p></main>\n'
    def _test(self):
        return 'import { TestBed } from "@angular/core/testing";\nimport { AppComponent } from "./app.component";\ndescribe("AppComponent",()=>{it("creates",async()=>{const fixture=TestBed.createComponent(AppComponent); expect(fixture.componentInstance).toBeTruthy();});});\n'
    def _domain(self,model):
        return "\n".join(f"export interface {pascal_case(dm.name)} {{\n"+"".join(f"  {f.name}{'' if f.required else '?'}: unknown;\n" for f in dm.fields)+"}\n" for dm in model.data_models)
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[
          BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,
          BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.DOCUMENTATION,
          BundleCapability.RELEASE],metadata={"language":"typescript","framework":"angular","style":"standalone-components"})
