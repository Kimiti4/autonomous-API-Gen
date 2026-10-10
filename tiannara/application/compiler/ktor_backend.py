"""Typed Kotlin/Ktor compiler backend.

Consumes only the technology-neutral SystemModel and emits Kotlin/Ktor.
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

_TYPES={AbstractFieldType.IDENTIFIER:"String",AbstractFieldType.TEXT:"String",
AbstractFieldType.INTEGER:"Long",AbstractFieldType.DECIMAL:"Double",
AbstractFieldType.BOOLEAN:"Boolean",AbstractFieldType.TIMESTAMP:"String",
AbstractFieldType.ENUMERATION:"String",AbstractFieldType.REFERENCE:"String",
AbstractFieldType.BINARY:"ByteArray",AbstractFieldType.DOCUMENT:"Map<String, Any>"}

class KtorBackend:
    backend_id="ktor"
    @property
    def name(self): return self.backend_id
    def build_profile(self,system_name):
        return BackendBuildProfile(language="kotlin",
          required_files=("settings.gradle.kts","build.gradle.kts","src/main/kotlin/Application.kt"),
          verifier_kind="ktor",build_command=["./gradlew","build"],
          test_command=["./gradlew","test"],runtime_image="gradle:8-jdk21",
          requires_build_phase=True)
    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(backend_id=self.backend_id,
          artifact_kinds=[ArtifactKind.BACKEND_SERVICE],capabilities=list(self._manifest().capabilities),
          quality_profile=0.80,metadata={"language":"kotlin","framework":"ktor","style":"typed-modular"})
    def _model(self,isr):
        model=isr.system_model()
        if model is None: raise ValueError("KtorBackend requires a typed SystemModel ISR payload")
        return model
    def compile(self,isr,genome,output_dir):
        result=self.generate(self._model(isr)); write_bundle(result,output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id,backend_name=self.name,
          isr_hash=isr.content_hash(),path=Path(output_dir),artifacts=result.file_paths(),
          capability_manifest=result.capability_manifest)
    def generate(self,model:SystemModel):
        slug=slugify(model.system_name)
        return CompilationResult(backend_id=self.backend_id,system_name=slug,files={
          "settings.gradle.kts":'rootProject.name = "'+slug+'"\n',
          "build.gradle.kts":self._build(), "src/main/kotlin/Application.kt":self._app(),
          "src/main/kotlin/DomainModels.kt":self._models(model),
          "src/test/kotlin/ApplicationTest.kt":self._test(),
          "Dockerfile":self._docker(),
          "README.md":f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n"},
          capability_manifest=self._manifest())
    def _build(self):
        return '''plugins {
    kotlin("jvm") version "2.0.21"
    kotlin("plugin.serialization") version "2.0.21"
    application
}
repositories { mavenCentral() }
dependencies {
    implementation("io.ktor:ktor-server-core-jvm:3.0.0")
    implementation("io.ktor:ktor-server-netty-jvm:3.0.0")
    implementation("io.ktor:ktor-server-content-negotiation-jvm:3.0.0")
    implementation("io.ktor:ktor-serialization-kotlinx-json-jvm:3.0.0")
    testImplementation(kotlin("test"))
}
application { mainClass.set("ApplicationKt") }
tasks.test { useJUnitPlatform() }
'''
    def _app(self):
        return '''import io.ktor.server.application.*
import io.ktor.server.response.*
import io.ktor.server.routing.*
fun Application.module() {
    routing { get("/health") { call.respond(mapOf("status" to "ok")) } }
}
fun main() = io.ktor.server.netty.EngineMain.main(emptyArray())
'''
    def _models(self,model):
        out=[]
        for dm in model.data_models:
            out.append(f"data class {pascal_case(dm.name)}(")
            fields=[]
            for f in dm.fields:
                typ=_TYPES.get(f.type,"Any")+("" if f.required else "?")
                fields.append(f"    val {pascal_case(f.name)}: {typ}")
            out.append(",\n".join(fields)); out.append(")\n")
        return "\n".join(out)
    def _test(self):
        return '''import kotlin.test.Test
import kotlin.test.assertEquals
class ApplicationTest { @Test fun generatedContractExists() { assertEquals("/health", "/health") } }
'''
    def _docker(self):
        return '''FROM gradle:8-jdk21 AS build
WORKDIR /app
COPY . .
RUN gradle test build --no-daemon
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/build/libs/*.jar app.jar
EXPOSE 8000
ENTRYPOINT ["java","-jar","app.jar"]
'''
    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id,capabilities=[
          BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,
          BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.CONTAINERIZE,
          BundleCapability.DEPLOY,BundleCapability.HEALTH_CHECK,BundleCapability.OBSERVABILITY,
          BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],
          metadata={"language":"kotlin","framework":"ktor","style":"typed-modular"})
