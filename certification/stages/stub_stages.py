"""Stub stages — explicit in-memory substitute for Campaign A / unit tests.

Used only where allow_stub=True. Every stage reports STUB, never REAL_DOCKER.
"""
from __future__ import annotations
import hashlib
import time

from certification.core.trial import TrialStage
from certification.stages.execution_mode import ExecutionMode, StageExecution


def _h(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class StubStages:
    """In-memory stages that report STUB for every execution."""

    def build(self, repo_dir: str, tag: str) -> StageExecution:
        t0 = time.time()
        return StageExecution(
            stage=TrialStage.BUILD,
            mode=ExecutionMode.STUB,
            passed=True,
            duration_s=time.time() - t0,
            logs_hash=_h("stub-build"),
            detail="stub-build",
        )

    def run_tests(self, image: str, spec: "TestSpec", **kwargs) -> StageExecution:
        from compiler.core.protocol import TestSpec
        t0 = time.time()
        return StageExecution(
            stage=TrialStage.TEST,
            mode=ExecutionMode.STUB,
            passed=True,
            duration_s=time.time() - t0,
            logs_hash=_h("stub-test"),
            detail=f"stub-test cmd={' '.join(spec.command)}",
        )

    def deploy(self, image: str, port: int) -> StageExecution:
        t0 = time.time()
        return StageExecution(
            stage=TrialStage.DEPLOY,
            mode=ExecutionMode.STUB,
            passed=True,
            duration_s=time.time() - t0,
            logs_hash=_h("stub-deploy"),
            container_id="stub-container",
            detail="stub-deploy",
        )

    def probe(self, port: int, cid: str) -> StageExecution:
        t0 = time.time()
        return StageExecution(
            stage=TrialStage.RUNTIME,
            mode=ExecutionMode.STUB,
            passed=True,
            duration_s=time.time() - t0,
            logs_hash=_h("stub-runtime"),
            detail="stub-runtime",
        )

    def destroy(self, cid: str) -> StageExecution:
        t0 = time.time()
        return StageExecution(
            stage=TrialStage.DESTROY,
            mode=ExecutionMode.STUB,
            passed=True,
            duration_s=time.time() - t0,
            logs_hash=_h("stub-destroy"),
            detail="stub-destroy",
        )
