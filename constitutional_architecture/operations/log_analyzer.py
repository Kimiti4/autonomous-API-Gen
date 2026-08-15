"""
Log Analyzer.

Analyzes structured logs to detect patterns, errors, and anomalies.
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.operations.observation_model import (
    Observation,
    ObservationSeverity,
    ObservationSource,
)


@dataclass(frozen=True)
class LogEntry:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    level: str = "info"
    message: str = ""
    service_name: str = ""
    deployment_id: str = ""
    trace_id: str = ""
    fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LogPattern:
    pattern: str
    count: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    severity: ObservationSeverity = ObservationSeverity.INFO
    services: tuple[str, ...] = ()


class LogAnalyzer:

    ERROR_PATTERNS = [
        re.compile(r"(?i)exception"),
        re.compile(r"(?i)error"),
        re.compile(r"(?i)failed"),
        re.compile(r"(?i)timeout"),
        re.compile(r"(?i)unavailable"),
    ]

    def __init__(self) -> None:
        self._entries: list[LogEntry] = []
        self._patterns: dict[str, LogPattern] = {}
        self._error_counts: Counter = Counter()

    def ingest(self, entry: LogEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > 100000:
            self._entries = self._entries[-100000:]
        if entry.level in ("error", "critical"):
            pattern = self._normalize_message(entry.message)
            self._error_counts[pattern] += 1
            if pattern not in self._patterns:
                self._patterns[pattern] = LogPattern(
                    pattern=pattern, count=1,
                    first_seen=entry.timestamp, last_seen=entry.timestamp,
                    severity=ObservationSeverity.ERROR,
                    services=(entry.service_name,),
                )
            else:
                existing = self._patterns[pattern]
                self._patterns[pattern] = LogPattern(
                    pattern=existing.pattern, count=existing.count + 1,
                    first_seen=existing.first_seen, last_seen=entry.timestamp,
                    severity=existing.severity,
                    services=tuple(set(existing.services + (entry.service_name,))),
                )

    def _normalize_message(self, message: str) -> str:
        normalized = re.sub(r"\b\d+\b", "<NUM>", message)
        normalized = re.sub(r"\b[0-9a-f]{8,}\b", "<HEX>", normalized)
        normalized = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\b", "<EMAIL>", normalized)
        if len(normalized) > 200:
            normalized = normalized[:200] + "..."
        return normalized

    def analyze(self) -> list[Observation]:
        observations: list[Observation] = []
        for pattern, count in self._error_counts.most_common(10):
            if count >= 5:
                pattern_info = self._patterns.get(pattern)
                observations.append(Observation(
                    id=f"obs-{uuid.uuid4().hex[:12]}",
                    source=ObservationSource.LOGS,
                    severity=ObservationSeverity.ERROR if count >= 20 else ObservationSeverity.WARNING,
                    title=f"Recurring error pattern ({count} occurrences)",
                    description=f"Pattern: {pattern}",
                    details={
                        "pattern": pattern, "count": count,
                        "services": list(pattern_info.services) if pattern_info else [],
                    },
                ))
        critical_count = sum(1 for e in self._entries if e.level == "critical")
        if critical_count > 0:
            observations.append(Observation(
                id=f"obs-{uuid.uuid4().hex[:12]}",
                source=ObservationSource.LOGS,
                severity=ObservationSeverity.CRITICAL,
                title=f"{critical_count} critical log entries",
                description="Critical issues detected in logs",
                details={"critical_count": critical_count},
            ))
        return observations

    @property
    def total_entries(self) -> int:
        return len(self._entries)

    @property
    def error_patterns(self) -> list[LogPattern]:
        return list(self._patterns.values())
