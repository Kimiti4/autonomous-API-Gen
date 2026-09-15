"""Logging bridge: selected Tiannara logs → Observatory (non-blocking, fail-safe).

If the adapter is unavailable, logging must never crash the runtime:
emit() catches everything and delegates to handleError.
"""
from __future__ import annotations

import logging
from typing import Optional

from .runtime_adapter import TiannaraRuntimeAdapter


class ObservatoryRuntimeLogHandler(logging.Handler):
    def __init__(self, adapter: TiannaraRuntimeAdapter,
                 subject: str = "Tiannara.Runtime",
                 level: int = logging.INFO) -> None:
        super().__init__(level=level)
        self.adapter = adapter
        self.subject = subject

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = {"logger": record.name, "level": record.levelname,
                       "message": record.getMessage()}
            if record.exc_info:
                exc_type, exc_value, _ = record.exc_info
                if exc_type is not None:
                    payload["error_type"] = exc_type.__name__
                if exc_value is not None:
                    payload["error_summary"] = str(exc_value)
            self.adapter.observe_blocking(
                category="runtime", type="log", subject_id=self.subject,
                payload=payload, severity=self._map_severity(record.levelno))
        except Exception:
            self.handleError(record)

    def _map_severity(self, levelno: int) -> str:
        if levelno >= logging.CRITICAL:
            return "fatal"
        if levelno >= logging.ERROR:
            return "error"
        if levelno >= logging.WARNING:
            return "warning"
        if levelno >= logging.INFO:
            return "info"
        return "debug"
