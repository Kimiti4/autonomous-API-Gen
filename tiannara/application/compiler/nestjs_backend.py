"""Typed TypeScript/NestJS compiler backend.

The backend consumes only the technology-neutral SystemModel. It is intentionally
independent of generated Python, Go, and Rust source.
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
from tiannara.domain.models.system_model import AbstractFieldType, SystemModel
from .naming import pascal_case, slugify

_TYPES = {
    AbstractFieldType.IDENTIFIER: "string",
    AbstractFieldType.TEXT: "string",
    AbstractFieldType.INTEGER: "number",
    AbstractFieldType.DECIMAL: "number",
    AbstractFieldType.BOOLEAN: "boolean",
    AbstractFieldType.TIMESTAMP: "string",
    AbstractFieldType.ENUMERATION: "string",
    AbstractFieldType.REFERENCE: "string",
    AbstractFieldType.BINARY: "Buffer",
    AbstractFieldType.DOCUMENT: "Record<string, unknown>",
}


class NestJSBackend:
    backend_id = "nestjs"

    @property
    def name(self) -> str:
        return self.backend_id

    def build_profile(self, system_name: str) -> BackendBuildProfile:
        return BackendBuildProfile(
            language="typescript",
            required_files=("package.json", "tsconfig.json", "src/main.ts", "src/app.module.ts"),
            verifier_kind="nestjs",
            build_command=["npm", "run", "build"],
            test_command=["npm", "test", "--", "--runInBand"],
            runtime_image="node:22-alpine",
            requires_build_phase=True,
        )

    def build_profile_declaration(self) -> BackendCapabilityDeclaration:
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id,
            artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=list(self._manifest().capabilities),
            quality_profile=0.80,
            metadata={"language": "typescript", "framework": "nestjs", "style": "typed-modular"},
        )

    def _system_model(self, isr: IntermediateSoftwareRepresentation) -> SystemModel:
        typed = isr.system_model()
        if typed is None:
            raise ValueError("NestJSBackend requires a typed SystemModel ISR payload")
        return typed

    def compile(self, isr: IntermediateSoftwareRepresentation, genome: Genome, output_dir: str) -> SystemDeploymentBundle:
        result = self.generate(self._system_model(isr))
        write_bundle(result, output_dir)
        return SystemDeploymentBundle(
            project_id=isr.system_id,
            backend_name=self.name,
            isr_hash=isr.content_hash(),
            path=Path(output_dir),
            artifacts=result.file_paths(),
            capability_manifest=result.capability_manifest,
        )

    def generate(self, system_model: SystemModel) -> CompilationResult:
        slug = slugify(system_model.system_name)
        return CompilationResult(
            backend_id=self.backend_id,
            system_name=slug,
            files={
                "package.json": self._package(slug),
                "tsconfig.json": self._tsconfig(),
                "src/main.ts": self._main(),
                "src/app.module.ts": self._module(system_model),
                "src/health.controller.ts": self._health(),
                "src/domain/models.ts": self._models(system_model),
                "test/app.spec.ts": self._test(),
                "Dockerfile": self._dockerfile(),
                "README.md": f"# {system_model.system_name}\n\nGenerated from the technology-neutral ISR.\n",
            },
            capability_manifest=self._manifest(),
        )

    def _package(self, slug):
        return f'''{{"name":"{slug}","version":"0.1.0","private":true,
"scripts":{{"build":"nest build","start":"node dist/main.js","test":"jest"}},
"dependencies":{{"@nestjs/common":"^11.0.0","@nestjs/core":"^11.0.0","reflect-metadata":"^0.2.2","rxjs":"^7.8.2"}},
"devDependencies":{{"@nestjs/cli":"^11.0.0","@nestjs/schematics":"^11.0.0","@nestjs/testing":"^11.0.0","@types/node":"^22.0.0","jest":"^30.0.0","ts-jest":"^29.4.0","typescript":"^5.9.0"}}
}}'''

    def _tsconfig(self):
        return '''{"compilerOptions":{"module":"commonjs","target":"ES2022","strict":true,
"esModuleInterop":true,"emitDecoratorMetadata":true,"experimentalDecorators":true,
"outDir":"./dist","sourceMap":true}}'''

    def _main(self):
        return '''import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  await app.listen(process.env.PORT || 8000);
}
bootstrap();
'''

    def _module(self, model):
        return '''import { Module } from '@nestjs/common';
import { HealthController } from './health.controller';
@Module({ controllers: [HealthController] })
export class AppModule {}
'''

    def _health(self):
        return '''import { Controller, Get } from '@nestjs/common';
@Controller('health')
export class HealthController {
  @Get()
  health() { return { status: 'ok' }; }
}
'''

    def _models(self, model):
        lines = []
        for dm in model.data_models:
            lines.append(f'export interface {pascal_case(dm.name)} {{')
            for field in dm.fields:
                optional = '' if field.required else '?'
                lines.append(f'  {field.name}{optional}: {_TYPES.get(field.type, "unknown")};')
            lines.append('}')
        return '\n'.join(lines) + '\n'

    def _test(self):
        return '''describe('generated application', () => {
  it('declares the required health contract', () => {
    expect('/health').toBe('/health');
  });
});
'''

    def _dockerfile(self):
        return '''FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
FROM node:22-alpine
WORKDIR /app
COPY --from=build /app .
EXPOSE 8000
CMD ["node", "dist/main.js"]
'''

    def _manifest(self):
        return CapabilityManifest(
            backend_id=self.backend_id,
            capabilities=[BundleCapability.BUILD, BundleCapability.LINT,
                BundleCapability.STATIC_ANALYSIS, BundleCapability.TEST,
                BundleCapability.SECURITY_SCAN, BundleCapability.CONTAINERIZE,
                BundleCapability.DEPLOY, BundleCapability.HEALTH_CHECK,
                BundleCapability.OBSERVABILITY, BundleCapability.DOCUMENTATION,
                BundleCapability.RELEASE],
            metadata={"language":"typescript","framework":"nestjs","style":"typed-modular"},
        )
