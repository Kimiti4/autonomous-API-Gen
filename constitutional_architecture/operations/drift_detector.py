"""
Drift Detector.

Detects drift between the running system and the ISR.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.operations.observation_model import (
    DriftReport,
    ObservationSeverity,
)


@dataclass(frozen=True)
class RunningSystemSnapshot:
    deployment_id: str
    isr_hash: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    running_modules: tuple[str, ...] = ()
    running_services: tuple[str, ...] = ()
    running_endpoints: tuple[str, ...] = ()
    running_config: dict[str, str] = field(default_factory=dict)
    running_versions: dict[str, str] = field(default_factory=dict)
    healthy_services: tuple[str, ...] = ()
    unhealthy_services: tuple[str, ...] = ()


class DriftDetector:

    def __init__(self) -> None:
        self._snapshots: list[RunningSystemSnapshot] = []
        self._drift_history: list[DriftReport] = []

    def record_snapshot(self, snapshot: RunningSystemSnapshot) -> None:
        self._snapshots.append(snapshot)
        if len(self._snapshots) > 1000:
            self._snapshots = self._snapshots[-1000:]

    def detect_drift(
        self,
        isr: ISR,
        snapshot: RunningSystemSnapshot,
    ) -> DriftReport:
        drift_type = "none"
        missing_from_running: list[str] = []
        extra_in_running: list[str] = []
        modified: list[dict] = []

        isr_modules = {m.name for m in isr.system.modules}
        running_modules = set(snapshot.running_modules)
        missing_modules = isr_modules - running_modules
        extra_modules = running_modules - isr_modules

        if missing_modules:
            missing_from_running.extend(f"module:{m}" for m in missing_modules)
        if extra_modules:
            extra_in_running.extend(f"module:{m}" for m in extra_modules)

        isr_services = {s.name for m in isr.system.modules for s in m.services}
        running_services = set(snapshot.running_services)
        missing_services = isr_services - running_services
        extra_services = running_services - isr_services

        if missing_services:
            missing_from_running.extend(f"service:{s}" for s in missing_services)
        if extra_services:
            extra_in_running.extend(f"service:{s}" for s in extra_services)

        isr_endpoints = {
            f"{e.method.value} {e.path}"
            for m in isr.system.modules
            for i in m.interfaces
            for e in i.endpoints
        }
        running_endpoints = set(snapshot.running_endpoints)
        missing_endpoints = isr_endpoints - running_endpoints
        extra_endpoints = running_endpoints - isr_endpoints

        if missing_endpoints:
            missing_from_running.extend(f"endpoint:{e}" for e in missing_endpoints)
        if extra_endpoints:
            extra_in_running.extend(f"endpoint:{e}" for e in extra_endpoints)

        for service in snapshot.unhealthy_services:
            if service in isr_services:
                modified.append({
                    "type": "health", "component": service,
                    "expected": "healthy", "actual": "unhealthy",
                })

        if missing_from_running or extra_in_running:
            drift_type = "topology"
            severity = ObservationSeverity.ERROR
        elif modified:
            drift_type = "behaviour"
            severity = ObservationSeverity.WARNING
        else:
            drift_type = "none"
            severity = ObservationSeverity.INFO

        if drift_type == "topology":
            if missing_from_running and not extra_in_running:
                recommended = "rollback"
            elif extra_in_running and not missing_from_running:
                recommended = "update_isr"
            else:
                recommended = "investigate"
        elif drift_type == "behaviour":
            recommended = "investigate"
        else:
            recommended = "none"

        description = (
            f"No drift detected" if drift_type == "none"
            else f"{drift_type.capitalize()} drift: "
                 f"{len(missing_from_running)} missing, "
                 f"{len(extra_in_running)} extra, "
                 f"{len(modified)} modified"
        )

        report = DriftReport(
            id=f"drift-{uuid.uuid4().hex[:12]}",
            deployment_id=snapshot.deployment_id,
            isr_hash=isr.content_hash,
            drift_type=drift_type,
            severity=severity,
            description=description,
            missing_from_running=tuple(missing_from_running),
            extra_in_running=tuple(extra_in_running),
            modified_components=tuple(modified),
            recommended_action=recommended,
            confidence=0.9 if drift_type != "none" else 1.0,
        )

        self._drift_history.append(report)
        return report

    @property
    def drift_history(self) -> list[DriftReport]:
        return list(self._drift_history)

    @property
    def has_drift(self) -> bool:
        if not self._drift_history:
            return False
        return self._drift_history[-1].drift_type != "none"
