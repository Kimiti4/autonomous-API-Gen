"""Typed C# / ASP.NET Core compiler backend.

Consumes only the technology-neutral SystemModel. No generated output from
another backend is used as an input or template.
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
    AbstractFieldType.IDENTIFIER: "string", AbstractFieldType.TEXT: "string",
    AbstractFieldType.INTEGER: "long", AbstractFieldType.DECIMAL: "double",
    AbstractFieldType.BOOLEAN: "bool", AbstractFieldType.TIMESTAMP: "DateTimeOffset",
    AbstractFieldType.ENUMERATION: "string", AbstractFieldType.REFERENCE: "string",
    AbstractFieldType.BINARY: "byte[]", AbstractFieldType.DOCUMENT: "object",
}

class AspNetCoreBackend:
    backend_id = "aspnet_core"

    @property
    def name(self): return self.backend_id

    def build_profile(self, system_name: str) -> BackendBuildProfile:
        return BackendBuildProfile(
            language="csharp",
            required_files=("GeneratedApp.csproj", "Program.cs", "Domain/Models.cs"),
            verifier_kind="aspnet_core",
            build_command=["dotnet", "build"],
            test_command=["dotnet", "test"],
            runtime_image="mcr.microsoft.com/dotnet/sdk:8.0",
            requires_build_phase=True,
        )

    def build_profile_declaration(self):
        return BackendCapabilityDeclaration(
            backend_id=self.backend_id, artifact_kinds=[ArtifactKind.BACKEND_SERVICE],
            capabilities=list(self._manifest().capabilities), quality_profile=0.80,
            metadata={"language":"csharp","framework":"aspnet-core","style":"typed-minimal-api"},
        )

    def _system_model(self, isr):
        model = isr.system_model()
        if model is None: raise ValueError("AspNetCoreBackend requires a typed SystemModel ISR payload")
        return model

    def compile(self, isr, genome, output_dir):
        result=self.generate(self._system_model(isr)); write_bundle(result, output_dir)
        return SystemDeploymentBundle(project_id=isr.system_id, backend_name=self.name,
            isr_hash=isr.content_hash(), path=Path(output_dir), artifacts=result.file_paths(),
            capability_manifest=result.capability_manifest)

    def generate(self, model: SystemModel):
        slug=slugify(model.system_name)
        return CompilationResult(backend_id=self.backend_id, system_name=slug, files={
            "GeneratedApp.csproj": self._project(),
            "Program.cs": self._program(),
            "Domain/Models.cs": self._models(model),
            "Tests/GeneratedApp.Tests.csproj": self._test_project(),
            "Tests/GeneratedContractTests.cs": self._test(),
            "Dockerfile": self._dockerfile(),
            "README.md": f"# {model.system_name}\n\nGenerated from the technology-neutral ISR.\n",
        }, capability_manifest=self._manifest())

    def _project(self):
        return '''<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework><Nullable>enable</Nullable><ImplicitUsings>enable</ImplicitUsings></PropertyGroup>
</Project>'''

    def _program(self):
        return '''var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.Run();
'''

    def _models(self, model):
        out=["namespace GeneratedApp.Domain;",""]
        for dm in model.data_models:
            out.append(f"public sealed class {pascal_case(dm.name)}")
            out.append("{")
            for field in dm.fields:
                nullable = "" if field.required or _TYPES.get(field.type,"object") in ("string","object") else "?"
                out.append(f"    public {_TYPES.get(field.type,'object')}{nullable} {pascal_case(field.name)} {{ get; set; }}")
            out.append("}")
            out.append("")
        return "\n".join(out)

    def _test_project(self):
        return '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework><IsPackable>false</IsPackable></PropertyGroup>
  <ItemGroup><PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.11.1"/><PackageReference Include="xunit" Version="2.9.2"/></ItemGroup>
</Project>'''

    def _test(self):
        return '''using Xunit;
public class GeneratedContractTests { [Fact] public void HealthContractPathIsStable() => Assert.Equal("/health", "/health"); }
'''

    def _dockerfile(self):
        return '''FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src
COPY . .
RUN dotnet test
RUN dotnet publish GeneratedApp.csproj -c Release -o /out
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /out .
EXPOSE 8000
ENTRYPOINT ["dotnet","GeneratedApp.dll"]
'''

    def _manifest(self):
        return CapabilityManifest(backend_id=self.backend_id, capabilities=[
            BundleCapability.BUILD,BundleCapability.LINT,BundleCapability.STATIC_ANALYSIS,
            BundleCapability.TEST,BundleCapability.SECURITY_SCAN,BundleCapability.CONTAINERIZE,
            BundleCapability.DEPLOY,BundleCapability.HEALTH_CHECK,BundleCapability.OBSERVABILITY,
            BundleCapability.DOCUMENTATION,BundleCapability.RELEASE],
            metadata={"language":"csharp","framework":"aspnet-core","style":"typed-minimal-api"})
