"""Observatory backend settings (environment-driven, no secrets in code)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Tuple


@dataclass(frozen=True)
class Settings:
    db_path: str
    api_token: Optional[str]
    cors_origins: Tuple[str, ...]
    max_batch_size: int


@lru_cache
def get_settings() -> Settings:
    raw_origins = os.getenv("OBSERVATORY_CORS_ORIGINS", "")
    origins = tuple(origin.strip() for origin in raw_origins.split(",") if origin.strip())

    raw_max_batch_size = os.getenv("OBSERVATORY_MAX_BATCH_SIZE", "500")
    try:
        max_batch_size = int(raw_max_batch_size)
    except ValueError:
        max_batch_size = 500
    if max_batch_size <= 0:
        max_batch_size = 500

    return Settings(
        db_path=os.getenv("OBSERVATORY_DB_PATH", "observatory.sqlite3"),
        api_token=os.getenv("OBSERVATORY_API_TOKEN") or None,
        cors_origins=origins,
        max_batch_size=max_batch_size,
    )