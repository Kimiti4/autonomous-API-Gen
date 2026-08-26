"""Metrics — four-class computation for CBC-1 trials (expanded)."""
from __future__ import annotations
import ast
from certification.core.trial import TrialMetrics, TrialStage


def _python_complexity(files: dict[str, str]) -> int:
    """Branch-point proxy: count if/for/while/except/boolop/comprehension nodes."""
    total = 0
    for p, c in files.items():
        if not p.endswith(".py"):
            continue
        try:
            tree = ast.parse(c)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.BoolOp, ast.comprehension)):
                total += 1
    return total


def _lint_score(files: dict[str, str]) -> float:
    """Bounded static checks: penalise bare except and wildcard imports."""
    bad = 0
    for p, c in files.items():
        if not p.endswith(".py"):
            continue
        if "except:" in c or "import *" in c:
            bad += 1
    return 1.0 if bad == 0 else max(0.0, 1.0 - 0.25 * bad)


def _doc_completeness(files: dict[str, str]) -> float:
    need = ["README.md", "docs/architecture.md"]
    have = sum(1 for n in need if n in files)
    return have / len(need) if need else 1.0


def _maintainability(complexity: int) -> float:
    return max(0.0, 1.0 - min(1.0, complexity / 200.0))


def compute(
    repo_files_count: int,
    stages: dict[TrialStage, bool],
    structural_passed: bool,
    test_passed: bool,
    runtime_passed: bool,
    repo_content_hash: str = "",
    files: dict[str, str] | None = None,
) -> TrialMetrics:
    """Compute four-class metrics from trial stage outcomes."""
    files = files or {}
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
    complexity = _python_complexity(files)
    engineering_quality = {
        "deterministic_output": bool(repo_content_hash),
        "independent_verify": stages.get(TrialStage.VERIFY, False),
        "lint_score": _lint_score(files),
        "complexity": complexity,
        "maintainability": _maintainability(complexity),
        "documentation_completeness": _doc_completeness(files),
    }
    isr_semantic_conformance = 1.0 if structural_passed else 0.0
    return TrialMetrics(
        compiler_correctness=compiler_correctness,
        functional_correctness=functional_correctness,
        engineering_quality=engineering_quality,
        operational_correctness=operational_correctness,
        isr_semantic_conformance=isr_semantic_conformance,
    )
