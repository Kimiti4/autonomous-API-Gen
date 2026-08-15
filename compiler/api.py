"""
Universal Compiler API.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .backends.production.register import register_production_backends
from .backends.reference_backend import ReferenceBackend
from .errors import (
    BackendNotFoundError,
    CompilationOutputValidationError,
    CompilerError,
    ISRValidationError,
)
from .kernel import UniversalCompiler
from .models import CapabilityQuery, CompilationRequest
from .registry import BackendRegistry
from .sdk.routes import enable_compiler_sdk


def create_default_compiler(output_root: str | Path) -> UniversalCompiler:
    """Create the default compiler with reference backend."""

    registry = BackendRegistry()
    registry.register_backend(ReferenceBackend())
    register_production_backends(registry)

    return UniversalCompiler(
        registry=registry,
        output_root=output_root,
    )


def create_app(output_root: str | Path = ".var/compiler/artifacts") -> FastAPI:
    """Create the compiler API application."""

    app = FastAPI(
        title="Universal Software Compiler",
        version="0.1.0",
        description=(
            "Phase 25 Universal Software Compiler. "
            "Compiles ISR into target artifacts through replaceable backends."
        ),
    )

    compiler = create_default_compiler(output_root)

    app.state.compiler = compiler

    enable_compiler_sdk(app, compiler)

    @app.exception_handler(ISRValidationError)
    async def isr_validation_handler(
        request: Request,
        exc: ISRValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "message": str(exc),
                "report": exc.report.model_dump(mode="json"),
            },
        )

    @app.exception_handler(CompilationOutputValidationError)
    async def output_validation_handler(
        request: Request,
        exc: CompilationOutputValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "message": str(exc),
                "report": exc.report.model_dump(mode="json"),
            },
        )

    @app.exception_handler(BackendNotFoundError)
    async def backend_not_found_handler(
        request: Request,
        exc: BackendNotFoundError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "message": str(exc),
            },
        )

    @app.exception_handler(CompilerError)
    async def compiler_error_handler(
        request: Request,
        exc: CompilerError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "message": str(exc),
            },
        )

    @app.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def health_ready() -> dict[str, str]:
        return {"status": "ready"}

    @app.get("/v1/compiler/backends")
    def list_backends():
        return compiler.registry.list_manifests()

    @app.post("/v1/compiler/backends/discover")
    def discover_backends(query: CapabilityQuery):
        return compiler.registry.find_backends(query)

    @app.post("/v1/compiler/validate")
    def validate_compilation_request(payload: CompilationRequest):
        from .validation import validate_isr_payload

        report = validate_isr_payload(payload.isr)

        try:
            compiler.registry.get_backend(
                payload.target.backend_id,
                payload.target.backend_version,
            )

            backend_available = True
            backend_error = None

        except BackendNotFoundError as exc:
            backend_available = False
            backend_error = str(exc)

        return {
            "isr_validation": report,
            "backend_available": backend_available,
            "backend_error": backend_error,
        }

    @app.post("/v1/compiler/compile")
    def compile_isr(payload: CompilationRequest):
        return compiler.compile(payload)

    @app.get("/v1/compiler/jobs/{job_id}")
    def get_compilation_job(job_id: str):
        job = compiler.get_job(job_id)

        if not job:
            return JSONResponse(
                status_code=404,
                content={
                    "message": f"Compilation job not found: {job_id}",
                },
            )

        return job

    return app


app = create_app()