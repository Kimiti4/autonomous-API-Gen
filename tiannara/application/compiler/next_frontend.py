"""Next.js + TypeScript frontend compiler target."""
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

class NextFrontend:
    backend_id="next_ts"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="typescript",required_files=("package.json","tsconfig.json","vite.config.ts","app/page.tsx","app/page.test.tsx"),
          verifier_kind="next",build_command=["npm","run","build"],test_command=["npm","test"],runtime_image="node:22-alpine",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.FRONTEND_APPLICATION],capabilities=list(self._manifest().capabilities),quality_profile=0.80,metadata={"language":"typescript","framework":"next"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("NextFrontend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "package.json":self._package(),
          "tsconfig.json":'{"compilerOptions":{"target":"ES2022","lib":["dom","es2022"],"strict":true,"jsx":"preserve","module":"esnext","moduleResolution":"bundler","noEmit":true,"skipLibCheck":true}}',
          "vite.config.ts":self._vite_config(),
          "app/page.test.tsx":self._test(),
          "app/page.tsx":f'const title = {json.dumps(model.system_name, ensure_ascii=True)};\nexport default function Page() {{ return <main><h1>{{title}}</h1><p>Generated application</p></main>; }}',
          "app/layout.tsx":'import type { ReactNode } from "react"; export default function RootLayout({children}:{children:ReactNode}){return <html><body>{children}</body></html}',
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _package(self):
        return '{"name":"esap-next-app","private":true,"version":"0.1.0","scripts":{"build":"next build","test":"vitest run"},"dependencies":{"next":"^15.5.0","react":"^19.1.0","react-dom":"^19.1.0"},"devDependencies":{"@types/react":"^19.1.0","@types/react-dom":"^19.1.0","@types/node":"^22.0.0","@vitejs/plugin-react":"^5.0.0","typescript":"^5.9.0","vitest":"^3.2.4"}}'
    def _vite_config(self):
        return 'import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\nexport default defineConfig({ plugins: [react()] });\n'
    def _test(self):
        return 'import { describe, it, expect } from "vitest";\nimport { renderToStaticMarkup } from "react-dom/server";\nimport Page from "./page";\ndescribe("generated Next page",()=>{it("renders page content",()=>{const markup=renderToStaticMarkup(<Page />);expect(markup).toContain("<h1>");expect(markup).toContain("Generated application");});});\n'
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],metadata={"language":"typescript","framework":"next"})
