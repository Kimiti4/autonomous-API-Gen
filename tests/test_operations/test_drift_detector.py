"""Tests for drift detection."""

import pytest

from constitutional_architecture.isr.model.entity import Entity
from constitutional_architecture.isr.model.fields import Field, FieldType
from constitutional_architecture.isr.model.isr import ISR
from constitutional_architecture.isr.model.module import Module
from constitutional_architecture.isr.model.service import Operation, OperationType, Service
from constitutional_architecture.isr.model.system import System
from constitutional_architecture.operations.drift_detector import DriftDetector, RunningSystemSnapshot


def _create_isr():
    return ISR(
        system=System(
            id="shop", name="Shop",
            modules=(
                Module(
                    id="mod-orders", name="Orders",
                    entities=(
                        Entity(id="ent-order", name="Order",
                               fields=(Field(name="id", field_type=FieldType.UUID, is_primary_key=True),)),
                    ),
                    services=(
                        Service(id="svc-orders", name="OrderService",
                                operations=(Operation(id="op-create", name="create_order"),)),
                    ),
                ),
            ),
        ),
    )


class TestDriftDetector:
    def test_no_drift(self):
        detector = DriftDetector()
        isr = _create_isr()
        snapshot = RunningSystemSnapshot(
            deployment_id="deploy-1", isr_hash=isr.content_hash,
            running_modules=("Orders",),
            running_services=("OrderService",),
        )
        detector.record_snapshot(snapshot)
        report = detector.detect_drift(isr, snapshot)
        assert report.drift_type == "none"

    def test_topology_drift_missing_service(self):
        detector = DriftDetector()
        isr = _create_isr()
        snapshot = RunningSystemSnapshot(
            deployment_id="deploy-1", isr_hash=isr.content_hash,
            running_modules=(),
            running_services=(),
        )
        detector.record_snapshot(snapshot)
        report = detector.detect_drift(isr, snapshot)
        assert report.drift_type == "topology"
        assert len(report.missing_from_running) > 0
        assert report.recommended_action == "rollback"

    def test_behaviour_drift(self):
        detector = DriftDetector()
        isr = _create_isr()
        snapshot = RunningSystemSnapshot(
            deployment_id="deploy-1", isr_hash=isr.content_hash,
            running_modules=("Orders",),
            running_services=("OrderService",),
            unhealthy_services=("OrderService",),
        )
        detector.record_snapshot(snapshot)
        report = detector.detect_drift(isr, snapshot)
        assert report.drift_type == "behaviour"
