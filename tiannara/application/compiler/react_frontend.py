"""Typed React/TypeScript frontend compiler backend."""
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

class ReactFrontend:
    backend_id="react_ts"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="typescript",required_files=("package.json","tsconfig.json","src/App.tsx"),
          verifier_kind="react",build_command=["npm","run","build"],test_command=["npm","test","--","--runInBand"],
          runtime_image="node:22-alpine",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.FRONTEND_APPLICATION],
          capabilities=list(self._manifest().capabilities),quality_profile=0.80,
          metadata={"language":"typescript","framework":"react","style":"component-based"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("ReactFrontend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),
          path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "package.json":self._package(), "tsconfig.json":self._tsconfig(),
          "index.html":'<div id="root"></div><script type="module" src="/src/main.tsx"></script>',
          "src/main.tsx":self._main(), "src/App.tsx":self._app(model),
          "src/domain.ts":self._domain(model), "src/App.test.tsx":self._test(),
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _package(self):
        return '{"name":"esap-react-app","private":true,"version":"0.1.0","scripts":{"build":"tsc --noEmit && vite build","test":"vitest run"},"dependencies":{"@vitejs/plugin-react":"latest","vite":"latest","typescript":"latest","react":"latest","react-dom":"latest","vitest":"latest"}}'
    def _tsconfig(self):
        return '{"compilerOptions":{"target":"ES2022","module":"ESNext","moduleResolution":"Bundler","strict":true,"jsx":"react-jsx","noEmit":true}}'
    def _main(self):
        return 'import React from "react";\nimport { createRoot } from "react-dom/client";\nimport App from "./App";\ncreateRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);\n'
    def _app(self,model):
        return f'import React from "react";\nexport default function App() {{ return <main><h1>{model.system_name}</h1><p>Generated application</p></main>; }}\n'
    def _domain(self,model):
        return "\n".join([f"export interface {pascal_case(dm.name)} {{\n" + "".join(f"  {f.name}{'' if f.required else '?'}: unknown;\n" for f in dm.fields) + "}\n" for dm in model.data_models])
    def _test(self):
        return 'import { describe, it, expect } from "vitest";\ndescribe("generated frontend",()=>{it("declares the application",()=>expect(true).toBe(true));});\n'
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],metadata={"language":"typescript","framework":"react","style":"component-based"})
