"""Local inference topology — deployment configuration, not AIR core.

The AIR core never reads this file; the LocalModelProvider adapter does.
Transport is the OpenAI-compatible protocol family; the serving runtime
(Ollama, llama.cpp server, vLLM, ...) is a deployment choice named only
here, never in the AIR core.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class LocalEndpoint(BaseModel):
    base_url: str = Field(min_length=1)
    model_id: str = Field(min_length=1)


class LocalTopology(BaseModel):
    topology_version: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    provider_class: str = "local_model"
    transport: str = "openai_compatible"   # protocol family, not a vendor
    task_kinds: list[str] = Field(default_factory=list)
    endpoint: LocalEndpoint | None = None
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "LocalTopology":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.model_validate(yaml.safe_load(handle))
