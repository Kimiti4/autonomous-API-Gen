"""Compiler backend registry.

The registry is deliberately small: backend selection is a compiler concern,
not a Genome concern. Additional language/framework targets can implement the
same CompilerBackend contract without changing the ISR-facing model.
"""

import os
import json
from typing import Dict

from app.engine.backend_contract import (
    ARCHITECTURE_SCHEMA_VERSION,
    BackendTarget,
    CompilerBackend,
    CompilationRequest,
    CompiledArtifact,
    PYTHON_FASTAPI,
    make_compilation_request,
)
from app.engine.capability_semantics import plan_capabilities
from app.engine.builder import (
    generate_database_file,
    generate_dockerfile,
    generate_main_app,
    generate_models_file,
    generate_requirements,
    generate_security_file,
    generate_service_file,
)
from app.engine.genome import Genome


class PythonFastAPIBackend:
    """First concrete compiler backend for the existing Python generator."""

    target = PYTHON_FASTAPI

    def supports(self, request: CompilationRequest) -> bool:
        return (
            request.target == self.target
            and request.architecture_schema == ARCHITECTURE_SCHEMA_VERSION
        )

    def _architecture_files(self, genome: Genome) -> Dict[str, str]:
        """Lower semantic capability intent into the Python/FastAPI artifact."""
        plan = plan_capabilities(genome)
        if plan.unmapped:
            raise ValueError(
                "cannot lower unmapped capabilities: " + ", ".join(plan.unmapped)
            )

        files: Dict[str, str] = {
            "main.py": generate_main_app(genome),
            "database.py": generate_database_file(genome),
            "security.py": generate_security_file(genome),
            "requirements.txt": generate_requirements(genome),
            "Dockerfile": generate_dockerfile(genome),
            os.path.join("services", "models.py"): generate_models_file(genome),
            os.path.join("services", "__init__.py"): "",
        }
        for service in genome.services:
            files[os.path.join("services", f"{service}.py")] = generate_service_file(
                service, genome
            )
        return files

    def compile(self, request: CompilationRequest) -> CompiledArtifact:
        if not self.supports(request):
            raise ValueError(
                f"unsupported backend target: {request.target.backend_id} "
                f"(schema {request.architecture_schema})"
            )
        # Technology-specific interpretation stays here. The architecture
        # request itself remains unchanged and is never mutated by the backend.
        genome = Genome(dict(request.architecture))
        return CompiledArtifact(
            backend_id=self.target.backend_id,
            files=self._architecture_files(genome),
            metadata={
                "language": self.target.language,
                "framework": self.target.framework,
                "architecture_schema": request.architecture_schema,
            },
        )



class GoHTTPBackend:
    """Independent Go/net/http target used to prove backend neutrality."""

    target = BackendTarget(
        backend_id="go-nethttp",
        language="go",
        framework="net/http",
    )

    def supports(self, request: CompilationRequest) -> bool:
        return request.target == self.target and request.architecture_schema == ARCHITECTURE_SCHEMA_VERSION

    def compile(self, request: CompilationRequest) -> CompiledArtifact:
        if not self.supports(request):
            raise ValueError(
                f"unsupported backend target: {request.target.backend_id} "
                f"(schema {request.architecture_schema})"
            )
        genome = Genome(dict(request.architecture))
        plan = plan_capabilities(genome)
        # This backend intentionally proves a distinct lowering surface. It only
        # accepts capabilities whose semantics can be represented faithfully by
        # the small reference HTTP target; unsupported semantics remain explicit.
        allowed = {"services", "database", "authentication", "cors", "health_endpoints", "openapi", "api_version"}
        unsupported = set(plan.requested) - allowed
        if unsupported:
            raise ValueError("cannot lower unmapped capabilities for go-nethttp: " + ", ".join(sorted(unsupported)))
        service_routes = []
        for service in genome.services:
            route = f"/api/{genome.api_version}/{service}"
            service_routes.append(
                f'    mux.HandleFunc({json.dumps(route)}, func(w http.ResponseWriter, r *http.Request) {{ writeJSON(w, map[string]any{{"service": {json.dumps(service)}}}) }})'
            )
        routes = "\n".join(service_routes)
        main = f'''package main

import (
    "encoding/json"
    "log"
    "net/http"
)

func writeJSON(w http.ResponseWriter, value any) {{
    w.Header().Set("Content-Type", "application/json")
    _ = json.NewEncoder(w).Encode(value)
}}

func main() {{
    mux := http.NewServeMux()
    mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {{
        writeJSON(w, map[string]any{{"version": {json.dumps(genome.api_version)}, "services": {json.dumps(genome.services)}}})
    }})
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {{
        writeJSON(w, map[string]string{{"status": "healthy"}})
    }})
{routes}
    log.Fatal(http.ListenAndServe(":8000", mux))
}}
'''
        go_mod = "module generated-api\n\ngo 1.22\n"
        return CompiledArtifact(
            backend_id=self.target.backend_id,
            files={"go.mod": go_mod, "main.go": main},
            metadata={"language": "go", "framework": "net/http", "architecture_schema": request.architecture_schema},
        )


_BACKENDS: Dict[str, CompilerBackend] = {
    PYTHON_FASTAPI.backend_id: PythonFastAPIBackend(),
    GoHTTPBackend.target.backend_id: GoHTTPBackend(),
}


def get_backend(backend_id: str) -> CompilerBackend:
    """Resolve an explicitly selected compiler backend; fail closed otherwise."""

    try:
        return _BACKENDS[backend_id]
    except KeyError as exc:
        raise ValueError(f"unknown compiler backend: {backend_id}") from exc


def compile_architecture(request: CompilationRequest) -> CompiledArtifact:
    """Compile using only the backend explicitly present in the request."""

    return get_backend(request.target.backend_id).compile(request)


def materialize(artifact: CompiledArtifact, output_dir: str) -> str:
    """Write a compiled artifact's file tree to disk without mutating it."""

    os.makedirs(output_dir, exist_ok=True)
    for relative_path, content in artifact.files.items():
        full_path = os.path.join(output_dir, relative_path)
        directory = os.path.dirname(full_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    return output_dir


def compile_and_materialize(
    architecture: Dict[str, object],
    output_dir: str,
    target: BackendTarget = PYTHON_FASTAPI,
) -> str:
    """Compile an architecture through the registry and persist the artifact."""

    artifact = compile_architecture(make_compilation_request(architecture, target=target))
    return materialize(artifact, output_dir)
