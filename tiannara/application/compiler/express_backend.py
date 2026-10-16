"""Typed Node.js/Express compiler backend.

Consumes only the technology-neutral SystemModel. Express deliberately provides
a less opinionated Node target than NestJS, testing whether ESAP can lower the
same semantics without relying on Nest conventions.
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
from tiannara.domain.models.system_model import SystemModel, AbstractFieldType
from .naming import pascal_case, slugify

class ExpressBackend:
    backend_id="express"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="typescript",required_files=("package.json","tsconfig.json","src/index.ts","src/app.ts","test/app.test.ts","Dockerfile"),
          verifier_kind="express",build_command=["npm","run","build"],test_command=["npm","test"],
          runtime_image="node:22-alpine",requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
          capabilities=list(self._manifest().capabilities),quality_profile=0.80,
          metadata={"language":"typescript","runtime":"node.js","framework":"express","style":"middleware"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("ExpressBackend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,isr_hash=isr.content_hash(),
          path=Path(output_dir),artifacts=result.file_paths(),capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        return CompilationResult(backend_id=self.backend_id,system_name=slugify(model.system_name),files={
          "package.json":self._package(),"tsconfig.json":self._tsconfig(),"src/index.ts":self._app_entry(),"src/app.ts":self._app(),"test/app.test.ts":self._test(),
          "src/domain.ts":self._domain(model),"Dockerfile":self._docker(),"README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"
        },capability_manifest=self._manifest())
    def _package(self):
        return '{"name":"esap-express-app","version":"0.1.0","private":true,"scripts":{"build":"tsc","start":"node dist/src/index.js","test":"vitest run"},"dependencies":{"express":"^5.1.0"},"devDependencies":{"@types/express":"^5.0.1","@types/node":"^22.0.0","typescript":"^5.9.0","vitest":"^3.2.4"}}'
    def _tsconfig(self):
        return '{"compilerOptions":{"target":"ES2022","module":"commonjs","moduleResolution":"node","strict":true,"esModuleInterop":true,"skipLibCheck":true,"outDir":"dist"}}'
    def _app(self):
        return '''import express from "express";
import type { Request, Response } from "express";

export function createApp() {
  const app = express();
  app.use(express.json());
  app.get("/health", (_req: Request, res: Response) => res.json({ status: "ok" }));
  return app;
}
'''
    def _app_entry(self):
        return 'import { createApp } from "./app";\nconst port = Number(process.env.PORT || 8000);\ncreateApp().listen(port, "0.0.0.0");\n'
    def _domain(self,model):
        return "\n".join(f"export interface {pascal_case(dm.name)} {{\n"+
          "".join(f"  {f.name}{'' if f.required else '?'}: unknown;\n" for f in dm.fields)+"}\n"
          for dm in model.data_models)
    def _test(self):
        return '''import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { Server } from "node:http";
import { createApp } from "../src/app";

let server: Server;
let baseUrl: string;

beforeAll(async () => {
  server = createApp().listen(0, "127.0.0.1");
  await new Promise<void>((resolve) => server.once("listening", resolve));
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("test server did not bind TCP port");
  baseUrl = "http://127.0.0.1:" + address.port;
});

afterAll(async () => {
  await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
});

describe("generated Express HTTP behavior", () => {
  it("returns a healthy JSON response", async () => {
    const response = await fetch(baseUrl + "/health");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ status: "ok" });
  });
  it("returns 404 for an unknown route", async () => {
    const response = await fetch(baseUrl + "/not-a-route");
    expect(response.status).toBe(404);
  });
});
'''
    def _docker(self):
        return '''FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build && npm test && npm prune --omit=dev
FROM node:22-alpine
WORKDIR /app
COPY --from=build /app .
EXPOSE 8000
CMD ["node","dist/src/index.js"]
'''
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[
          BundleCapability.BUILD, BundleCapability.TEST, BundleCapability.CONTAINERIZE,
          BundleCapability.HEALTH_CHECK, BundleCapability.DOCUMENTATION],
          metadata={"language":"typescript","runtime":"node.js","framework":"express","style":"middleware"})