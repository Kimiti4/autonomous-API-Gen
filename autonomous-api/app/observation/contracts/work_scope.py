"""Persisted Observatory event for an ESAP work-scope declaration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WorkScopeDeclared(BaseModel):
    model_config = ConfigDict(frozen=True)
    projectIntent: str = Field(min_length=1)
    projectKind: str = Field(min_length=1)
    generationScope: str = Field(min_length=1)
    allowedSurfaces: list[str]
    preservedSurfaces: list[str]
