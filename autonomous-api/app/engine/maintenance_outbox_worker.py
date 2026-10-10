"""Single-batch maintenance outbox worker for an externally managed scheduler.

This module is deliberately not started by the API process. Run it as a one-shot
job (for example, a scheduled container task) with explicit secrets and a
persistent database volume. It never performs application repairs or deployments.
"""
from __future__ import annotations

import logging
import math
import os
from typing import Any, Callable, Mapping

from .governed_maintenance_outbox import MaintenanceOutbox

logger = logging.getLogger("maintenance_outbox_worker")


def _positive_int(value: str | None, *, default: int, maximum: int) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("maintenance-worker-integer-config-invalid") from exc
    if parsed < 1 or parsed > maximum:
        raise ValueError("maintenance-worker-integer-config-out-of-range")
    return parsed


def _positive_float(value: str | None, *, default: float) -> float:
    if value is None or not value.strip():
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("maintenance-worker-timeout-config-invalid") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError("maintenance-worker-timeout-config-invalid")
    return parsed


def run_once(
    environ: Mapping[str, str] | None = None,
    *,
    outbox_factory: Callable[..., Any] = MaintenanceOutbox,
) -> list[dict[str, Any]]:
    """Deliver at most one bounded batch, returning sanitized outbox results."""
    env = os.environ if environ is None else environ
    database_path = env.get("MAINTENANCE_OUTBOX_DB_PATH", "").strip()
    base_url = env.get("OBSERVATORY_BASE_URL", "").strip()
    token = env.get("OBSERVATORY_API_TOKEN", "").strip()
    if not database_path:
        raise ValueError("maintenance-outbox-database-path-required")
    if not base_url:
        raise ValueError("observatory-base-url-required")
    if not token:
        raise ValueError("observatory-token-required")

    limit = _positive_int(
        env.get("MAINTENANCE_OUTBOX_BATCH_LIMIT"), default=20, maximum=100
    )
    timeout = _positive_float(
        env.get("MAINTENANCE_OUTBOX_HTTP_TIMEOUT_SECONDS"), default=5.0
    )
    outbox = outbox_factory(database_path)
    results = outbox.deliver_pending(
        base_url=base_url,
        token=token,
        timeout=timeout,
        limit=limit,
    )

    # Emit metadata only: never log the token, evidence payload, raw exception,
    # or full transport response.
    for result in results:
        logger.info(
            "maintenance_outbox_delivery event_digest=%s status=%s attempts=%s error=%s",
            result.get("event_digest", ""),
            result.get("status", "unknown"),
            result.get("attempts", 0),
            result.get("error") or "",
        )
    logger.info(
        "maintenance_outbox_batch_complete claimed=%d delivered=%d failed=%d",
        len(results),
        sum(result.get("status") == "delivered" for result in results),
        sum(result.get("status") != "delivered" for result in results),
    )
    return results


def main() -> int:
    """One-shot CLI entry point; external schedulers own cadence and restarts."""
    try:
        results = run_once()
    except Exception as exc:
        # Exception messages may contain deployment configuration. Log class only.
        logger.error("maintenance_outbox_worker_stopped error_class=%s", type(exc).__name__)
        return 2
    return 1 if any(item.get("status") != "delivered" for item in results) else 0


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    raise SystemExit(main())
