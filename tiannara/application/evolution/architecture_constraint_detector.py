"""34.3 Constraint Detector -- evidence-driven, not hardcoded mapping."""
from __future__ import annotations
def detect_constraints(observation: dict) -> tuple[str,...]:
    violations=[]
    if observation.get("throughput", 0) < observation.get("required_throughput", 100):
        violations.append("throughput_violation")
    if observation.get("latency", 0) > observation.get("required_latency", 200):
        violations.append("latency_violation")
    if observation.get("availability", 1) < 0.99:
        violations.append("availability_violation")
    if observation.get("queue_backlog", 0) > 1000:
        violations.append("queue_backlog")
    return tuple(violations)
