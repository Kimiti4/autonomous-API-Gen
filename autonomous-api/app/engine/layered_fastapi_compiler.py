"""CAP-003 layered Python/FastAPI lowering.

Generates separate API, schema, service and repository boundaries from the
technology-neutral Backend IR. Persistence implementation is intentionally
left behind the repository interface.
"""
from __future__ import annotations
import re
from .backend_ir import BackendProjectIR
from .backend_compiler import BackendCompilation, GeneratedArtifact
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

        operations = "
".join(
            f"    async def {_name(e.operation)}(self, payload=None):
"
            f"        return await self.repository.{_name(e.operation)}(payload)
"
            for e in ir.endpoints
        ) or "    pass
"

        schemas = "
".join(
            f"class {_name(e.operation).title().replace('_', '')}Request(BaseModel):
"
            "    pass
"
            for e in ir.endpoints
        ) or "class EmptyRequest(BaseModel):
    pass
"

        repository = "
".join(
            f"    async def {_name(e.operation)}(self, payload=None):
"
            "        raise NotImplementedError
"
            for e in ir.endpoints
        ) or "    pass
"

        artifacts = list(base.artifacts)
        artifacts.extend([
            GeneratedArtifact(
                "app/schemas.py",
                "from pydantic import BaseModel

" + schemas + "
",
                "schema",
            ),
            GeneratedArtifact(
                "app/repository.py",
                "class Repository:
" + repository + "
",
                "repository",
            ),
            GeneratedArtifact(
                "app/service.py",
                "from .repository import Repository

"
                "class Service:
"
                "    def __init__(self, repository: Repository):
"
                "        self.repository = repository

"
                + operations + "
",
                "service",
            ),
        ])
        return BackendCompilation(
            self.target, ir.schema_version, tuple(artifacts), ()
        )
