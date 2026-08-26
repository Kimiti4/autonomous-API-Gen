"""Metrics — four-class computation for CBC-1 trials."""
from __future__ import annotations
from compiler.core.conformance import ConformanceReport
from certification.core.trial import TrialMetrics, TrialStage


def compute(
    repo_files_count: int,
    stages: dict[TrialStage, bool],
    structural_passed: bool,
    test_passed: bool,
    runtime_passed: bool,
    repo_content_hash: str = "",
) -> TrialMetrics:
    """Compute four-class metrics from trial stage outcomes."""
    compiler_correctness = {
        "structural_conformance": structural_passed,
        "repo_file_count": repo_files_count,
    }
    functional_correctness = {
        "tests_passed": test_passed,
    }
    operational_correctness = {
        "runtime_healthy": runtime_passed,
        "build_succeeded": stages.get(TrialStage.BUILD, False),
        "deploy_succeeded": stages.get(TrialStage.DEPLOY, False),
        "destroy_succeeded": stages.get(TrialStage.DESTROY, False),
    }
    engineering_quality = {
        "deterministic_output": bool(repo_content_hash),
        "independent_verify": stages.get(TrialStage.VERIFY, False),
    }
    isr_semantic_conformance = 1.0 if structural_passed else 0.0
    return TrialMetrics(
        compiler_correctness=compiler_correctness,
        functional_correctness=functional_correctness,
        engineering_quality=engineering_quality,
        operational_correctness=operational_correctness,
        isr_semantic_conformance=isr_semantic_conformance,
    )
