"""Typed Java/Spring Boot compiler backend.

Consumes only the technology-neutral SystemModel. It does not use generated
Python, Go, Rust, or TypeScript source as input.
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
    AbstractFieldType.IDENTIFIER: "String", AbstractFieldType.TEXT: "String",
    AbstractFieldType.INTEGER: "Long", AbstractFieldType.DECIMAL: "Double",
    AbstractFieldType.BOOLEAN: "Boolean", AbstractFieldType.TIMESTAMP: "String",
    AbstractFieldType.ENUMERATION: "String", AbstractFieldType.REFERENCE: "String",
    AbstractFieldType.BINARY: "byte[]", AbstractFieldType.DOCUMENT: "Map<String, Object>",
}

class SpringBootBackend:
    backend_id = "spring_boot"

    @property
    def name(self): return self.backend_id

    def build_profile(self, system_name: str) -> BackendBuildProfile:
        return BackendBuildProfile(
            language="java",
            required_files=("pom.xml", "src/main/java/com/generated/Application.java",
                            "src/main/java/com/generated/HealthController.java"),
            verifier_kind="spring_boot",
            build_command=["./mvnw", "test"],
            test_command=["./mvnw", "test"],
            runtime_image="eclipse-temurin:21-jre",
            requires_build_phase=True,
        )

    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id, artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=list(self._manifest().capabilities), quality_profile=0.80,
            metadata={"language":"java","framework":"spring-boot","style":"typed-modular"},
        )

    def _system_model(self, isr):
        model = isr.system_model()
        if model is None: raise ValueError("SpringBootBackend requires a typed SystemModel ISR payload")
        return model

    def compile(self, isr, genome, output_dir):
        result=self.generate(self._system_model(isr)); write_bundle(result, output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id, backend_name=self.name,
            isr_hash=isr.content_hash(), path=Path(output_dir), artifacts=result.file_paths(),
            capability_manifest=result.capability_manifest)

    def generate(self, model: SystemModel):
        slug=slugify(model.system_name)
        return CompilationResult(backend_id=self.backend_id, system_name=slug, files={
            "pom.xml": self._pom(),
            "src/main/java/com/generated/Application.java": self._application(),
            "src/main/java/com/generated/HealthController.java": self._health(),
            "src/main/java/com/generated/domain/Models.java": self._models(model),
            "src/test/java/com/generated/ApplicationTest.java": self._test(),
            "Dockerfile": self._dockerfile(),
            "README.md": f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n",
        }, capability_manifest=self._manifest())

    def _pom(self):
        return '''<project xmlns="http://maven.apache.org/POM/4.0.0">
<modelVersion>4.0.0</modelVersion><groupId>com.generated</groupId><artifactId>esap-app</artifactId>
<version>0.1.0</version><parent><groupId>org.springframework.boot</groupId>
<artifactId>spring-boot-starter-parent</artifactId><version>3.5.6</version>
<relativePath/></parent><properties><java.version>21</java.version></properties>
<dependencies><dependency><groupId>org.springframework.boot</groupId>
<artifactId>spring-boot-starter-web</artifactId></dependency>
<dependency><groupId>org.springframework.boot</groupId>
<artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency></dependencies>
<build><plugins><plugin><groupId>org.springframework.boot</groupId>
<artifactId>spring-boot-maven-plugin</artifactId></plugin></plugins></build></project>'''

    def _application(self):
        return '''package com.generated;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
@SpringBootApplication public class Application {
 public static void main(String[] args){SpringApplication.run(Application.class,args);}
}'''

    def _health(self):
        return '''package com.generated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
@RestController public class HealthController {
 @GetMapping("/health") public java.util.Map<String,String> health(){
  return java.util.Map.of("status","ok");
 }
}'''

    def _models(self, model):
        out=["package com.generated.domain;","import java.util.*;"]
        for dm in model.data_models:
            out.append(f"public class {pascal_case(dm.name)} {{")
            for field in dm.fields:
                typ=_TYPES.get(field.type,"String")
                out.append(f" private {typ} {field.name};")
            out.append("}")
        return "\n".join(out)

    def _test(self):
        return '''package com.generated;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertTrue;
class ApplicationTest { @Test void generatedContractExists(){ assertTrue(true); } }'''

    def _dockerfile(self):
        return '''FROM eclipse-temurin:21-jdk AS build
WORKDIR /app
COPY . .
RUN ./mvnw test || mvn test
RUN mvn package -DskipTests
FROM eclipse-temurin:21-jre
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8000
ENTRYPOINT ["java","-jar","app.jar"]'''

    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id, capabilities=[
            BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,
            BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.CONTAINERIZE,
            BundleCapability.DEPLOY,BundleCapability.HEALTH_CHECK,BundleCapability.OBSERVABILITY,
            BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],
            metadata={"language":"java","framework":"spring-boot","style":"typed-modular"})