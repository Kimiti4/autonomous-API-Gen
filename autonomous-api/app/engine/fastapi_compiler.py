"""CAP-003 Python/FastAPI backend target compiler.

This target owns framework-specific lowering. The input remains the neutral
BackendProjectIR and is never mutated.
"""
from __future__ import annotations
import json
import re
from .backend_ir import BackendProjectIR, BackendEndpoint, validate_backend_ir
from .backend_compiler import BackendCompilation, GeneratedArtifact


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]", "_", value).strip("_").lower()
    return value or "operation"


def _route(endpoint: BackendEndpoint) -> str:
    fn = _safe_name(endpoint.operation)
    return (
        f'@router.{endpoint.method.lower()}("{endpoint.path}")\n'
        f"async def {fn}():\n"
        f'    return {{"operation": "{endpoint.operation}"}}\n'
    )


class FastAPIBackendCompiler:
    target = "python-fastapi"

    def compile(self, ir: BackendProjectIR) -> BackendCompilation:
        findings = validate_backend_ir(ir)
        if findings:
            return BackendCompilation(self.target, ir.schema_version, (), findings)

        routes = "\n".join(_route(e) for e in ir.endpoints)
        main = (
            "from fastapi import FastAPI, APIRouter\n\n"
            "app = FastAPI()\nrouter = APIRouter()\n\n"
            f"{routes}\n"
            "app.include_router(router)\n\n"
            '@app.get("/health")\n'
            "async def health():\n"
            '    return {"status": "ok"}\n'
        )
        settings = (
            "from pydantic_settings import BaseSettings\n\n"
            "class Settings(BaseSettings):\n"
            + "".join(f"    {k}: str = \'\'\n" for k in ir.configuration_keys)
            + "\nsettings = Settings()\n"
        )
        requirements = "fastapi\nuvicorn[standard]\npydantic-settings\n"
        errors = json.dumps({
            "contract": ir.error_contract,
            "lifecycle": list(ir.lifecycle),
        }, sort_keys=True, indent=2) + "\n"

        artifacts = (
            GeneratedArtifact("app/main.py", main, "source"),
            GeneratedArtifact("app/settings.py", settings, "source"),
            GeneratedArtifact("requirements.txt", requirements, "dependency"),
            GeneratedArtifact("contracts/errors.json", errors, "contract"),
            GeneratedArtifact("tests/test_health.py",
                'from fastapi.testclient import TestClient\nfrom app.main import app\n\n'
                'def test_health():\n    assert TestClient(app).get("/health").status_code == 200\n',
                "test"),
        )
        return BackendCompilation(self.target, ir.schema_version, artifacts, ())
