"""Compilation contracts — the output of a compiler backend.

A CompilationResult is the in-memory product of a backend compile: a set of
files plus the capability manifest. It is deliberately decoupled from any
repository/git shape (see SystemDeploymentBundle, which carries the materialized
path) so Phase 17 (Repository Materializer) can consume it without the
compiler knowing about git. The backend writes no files itself during
``generate``; materialization is the writer's job, keeping compile pure.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .capability_manifest import CapabilityManifest


class CompilationResult(BaseModel):
    backend_id: str = Field(min_length=1)
    system_name: str = Field(min_length=1)
    files: dict[str, str] = Field(default_factory=dict)
    capability_manifest: CapabilityManifest

    def file_paths(self) -> list[str]:
        return sorted(self.files.keys())

    def read(self, path: str) -> str:
        return self.files[path]
