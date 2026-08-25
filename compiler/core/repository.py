"""GeneratedRepository — the deterministic output container."""
from __future__ import annotations
import hashlib
import json
from pydantic import BaseModel, ConfigDict, Field


class GeneratedRepository(BaseModel):
    model_config = ConfigDict(frozen=True)
    files: dict[str, str] = Field(default_factory=dict)
    content_hash: str = ""


def build_repository(files: dict[str, str]) -> GeneratedRepository:
    """Build a deterministic GeneratedRepository, computing the content hash
    over sorted (path, content) pairs."""
    canonical = json.dumps(
        {k: v for k, v in sorted(files.items())},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return GeneratedRepository(files=files, content_hash=content_hash)
