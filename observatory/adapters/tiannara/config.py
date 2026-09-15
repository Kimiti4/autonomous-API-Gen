"""Tiannara adapter settings (environment-driven, no secrets in code)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class TiannaraAdapterSettings:
    observatory_base_url: str
    api_token: Optional[str]
    source: str
    environment: str
    actor_id: str
    actor_role: str
    timeout_seconds: float
    queue_size: int
    max_retries: int
    initial_retry_delay_seconds: float
    max_retry_delay_seconds: float
    redaction_enabled: bool
    failure_log_path: Optional[str]
    batch_size: int
    flush_interval_seconds: float


@lru_cache
def get_adapter_settings() -> TiannaraAdapterSettings:
    return TiannaraAdapterSettings(
        observatory_base_url=os.getenv(
            "OBSERVATORY_BASE_URL", "http://127.0.0.1:8000"),
        api_token=os.getenv("OBSERVATORY_API_TOKEN") or None,
        source=os.getenv("OBSERVATORY_ADAPTER_SOURCE", "tiannara.runtime"),
        environment=os.getenv("OBSERVATORY_ADAPTER_ENVIRONMENT", "local"),
        actor_id=os.getenv("OBSERVATORY_ADAPTER_ACTOR_ID",
                           "tiannara-runtime-adapter"),
        actor_role=os.getenv("OBSERVATORY_ADAPTER_ACTOR_ROLE", "system"),
        timeout_seconds=_env_float("OBSERVATORY_ADAPTER_TIMEOUT_SECONDS", 2.0),
        queue_size=_env_int("OBSERVATORY_ADAPTER_QUEUE_SIZE", 10_000),
        max_retries=_env_int("OBSERVATORY_ADAPTER_MAX_RETRIES", 3),
        initial_retry_delay_seconds=_env_float(
            "OBSERVATORY_ADAPTER_INITIAL_RETRY_DELAY_SECONDS", 0.1),
        max_retry_delay_seconds=_env_float(
            "OBSERVATORY_ADAPTER_MAX_RETRY_DELAY_SECONDS", 2.0),
        redaction_enabled=_env_bool("OBSERVATORY_ADAPTER_REDACTION_ENABLED",
                                    True),
        failure_log_path=os.getenv(
            "OBSERVATORY_ADAPTER_FAILURE_LOG_PATH",
            "observatory_adapter_failures.jsonl"),
        batch_size=_env_int("OBSERVATORY_ADAPTER_BATCH_SIZE", 100),
        flush_interval_seconds=_env_float(
            "OBSERVATORY_ADAPTER_FLUSH_INTERVAL_SECONDS", 0.5),
    )
