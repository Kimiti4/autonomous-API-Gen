"""CAP-003 layered Python/FastAPI lowering."""
from __future__ import annotations

import re

from .backend_compiler import BackendCompilation, GeneratedArtifact
from .backend_ir import BackendProjectIR
from .fastapi_compiler import FastAPIBackendCompiler


def _name(value: str) -> str:
    x = re.sub(r"[^A-Za-z0-9_]", "_", value).strip("_").lower()
    return x or "operation"


class LayeredFastAPICompiler(FastAPIBackendCompiler):
    target = "python-fastapi-layered"

    def compile(self, ir: BackendProjectIR) -> BackendCompilation:
        base = super().compile(ir)
        if base.diagnostics:
            return base

        operations = "\n".join(
            f"""    async def {_name(e.operation)}(self, payload=None):
        return await self.repository.{_name(e.operation)}(payload)"""
            for e in ir.endpoints
        ) or "    pass\n"

        schemas = "\n".join(
            f"""class {_name(e.operation).title().replace('_', '')}Request(BaseModel):
    pass"""
            for e in ir.endpoints
        ) or "class EmptyRequest(BaseModel):\n    pass\n"

        repository = "\n".join(
            f"""    async def {_name(e.operation)}(self, payload=None):
        raise NotImplementedError"""
            for e in ir.endpoints
        ) or "    pass\n"

        artifacts = list(base.artifacts)
        artifacts.extend(
            [
                GeneratedArtifact(
                    "app/schemas.py",
                    "from pydantic import BaseModel\n\n" + schemas + "\n",
                    "schema",
                ),
                GeneratedArtifact(
                    "app/repository.py",
                    "class Repository:\n" + repository + "\n",
                    "repository",
                ),
                GeneratedArtifact(
                    "app/service.py",
                    "from .repository import Repository\n\n"
                    "class Service:\n"
                    "    def __init__(self, repository: Repository):\n"
                    "        self.repository = repository\n\n"
                    + operations
                    + "\n",
                    "service",
                ),
            ]
        )
        return BackendCompilation(self.target, ir.schema_version, tuple(artifacts), ())
