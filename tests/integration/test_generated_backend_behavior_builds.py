"""Real generated Python and Rust behavioral builds and independent runtime tests."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.lowering import isr_to_plan
from isr.core.graph import Edge, EdgeType, ISRGraph, Node, NodeType
from isr.core.identity import Provenance
from isr.core.revision import ISRRevision


def _plan():
    nodes = {
        "data:employee": Node(id="data:employee", type=NodeType.DATA_MODEL, properties={
            "label": "Employee",
            "behavior": {"fields": [
                {"name": "employee_id", "value_type": "identifier"},
                {"name": "base_salary", "value_type": "money", "precision": 12, "scale": 2},
                {"name": "allowances", "value_type": "money", "precision": 12, "scale": 2},
            ]},
        }),
        "effect:bank-transfer": Node(id="effect:bank-transfer", type=NodeType.EFFECT, properties={
            "label": "BankTransfer",
            "behavior": {"effect_kind": "bank_transfer", "idempotent": True, "idempotency_key_required": True},
        }),
        "service:payroll": Node(id="service:payroll", type=NodeType.SERVICE, properties={
            "label": "Payroll",
            "behavior": {
                "rules": [{
                    "rule_id": "payroll.gross",
                    "description": "Gross pay equals base salary plus allowances.",
                    "expression": {"op": "add", "args": [
                        {"op": "field", "field_ref": "Employee.base_salary"},
                        {"op": "field", "field_ref": "Employee.allowances"},
                    ]},
                }],
                "transitions": [{
                    "transition_id": "payroll.submit",
                    "source_state": "draft",
                    "target_state": "submitted",
                    "guard": {"op": "greater_than", "args": [
                        {"op": "field", "field_ref": "Employee.base_salary"},
                        {"op": "literal", "value": 0},
                    ]},
                }],
            },
        }),
    }
    edges = {
        "persist": Edge(id="persist", type=EdgeType.PERSISTS, source_id="service:payroll", target_id="data:employee"),
        "effect": Edge(id="effect", type=EdgeType.CAUSES_EFFECT, source_id="service:payroll", target_id="effect:bank-transfer"),
    }
    revision = ISRRevision.create(
        "generated-behavior-build",
        "rev-1",
        "1.0",
        ISRGraph(nodes=nodes, edges=edges),
        Provenance(created_by="generated-behavior-build-test", created_at="2026-01-01T00:00:00Z"),
    )
    return isr_to_plan(revision)


def _write_repo(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def test_generated_python_app_runs_its_independent_behavior_suite(tmp_path: Path):
    repo = PythonFastAPIBackend().compile(_plan())
    root = tmp_path / "python-app"
    _write_repo(root, repo.files)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        cwd=root,
        check=True,
        timeout=600,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=root,
        check=True,
        timeout=180,
        capture_output=True,
        text=True,
    )


def test_generated_rust_app_passes_cargo_tests(tmp_path: Path):
    repo = RustAxumBackend().compile(_plan())
    root = tmp_path / "rust-app"
    _write_repo(root, repo.files)
    subprocess.run(
        ["cargo", "test"],
        cwd=root,
        check=True,
        timeout=900,
        capture_output=True,
        text=True,
    )
    assert (root / "target" / "debug" / "deps").is_dir()
