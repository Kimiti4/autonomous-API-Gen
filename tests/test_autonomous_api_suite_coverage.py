"""D08 regression: repository-engine tests run in the root canonical workflow.

The suite under ``autonomous-api/tests`` cannot join the root ``testpaths``
because it has its own package root, Postgres service and dependency set. These
tests pin the coverage contract instead: the Root Canonical Suite workflow must
keep executing it on every PR and main push.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "root-canonical-suite.yml"
SUITE = ROOT / "autonomous-api" / "tests"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _triggers(data: dict) -> dict:
    # PyYAML follows YAML 1.1 and parses the `on` key as boolean True.
    return data.get("on") or data.get(True)


def _repository_jobs(data: dict) -> dict:
    return {
        name: job
        for name, job in data["jobs"].items()
        if job.get("defaults", {}).get("run", {}).get("working-directory")
        == "autonomous-api"
    }


def test_repository_engine_suite_is_present():
    tests = sorted(SUITE.glob("test_*.py"))

    assert len(tests) >= 200
    names = {path.name for path in tests}
    assert "test_repository_structure_scan.py" in names
    assert "test_repository_audit_gate.py" in names


def test_root_workflow_runs_the_repository_engine_suite():
    jobs = _repository_jobs(_workflow())

    assert len(jobs) == 1
    job = next(iter(jobs.values()))
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "pytest tests/" in commands
    assert "requirements.txt" in commands
    assert "postgres:16-alpine" in yaml.safe_dump(job)
    assert job["env"]["TEST_PG_DSN"].startswith("postgresql+asyncpg://")


def test_root_workflow_runs_on_every_pr_and_main_push():
    triggers = _triggers(_workflow())

    assert "pull_request" in triggers
    assert "push" in triggers
