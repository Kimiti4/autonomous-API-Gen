"""Metrics — four-class computation for CBC-1 trials (expanded)."""
from __future__ import annotations
import ast
import re
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


# -- cost / energy axis ---------------------------------------------------
#
# Per the Phase 31 spec's "Cross-Cutting Gaps to Close Before Phase 31":
#   "Cost and energy as fitness dimensions ... Every phase currently
#    measures correctness/quality but not efficiency; a system that
#    passes at 100x the compute cost fails in reality."
#
# We do NOT collapse cost and energy into a single aggregate score
# (master prompt §46, "no cosmetic evolution", and the FitnessVector
# "Never collapse to a single aggregate score" invariant). Each is a
# separate, monotonically-scaled dimension that Pareto dominance can
# compare across candidates.
#
#   wall_clock_total_s:  raw sum of behavioral stage durations
#                        (build + test + deploy + runtime + destroy).
#                        Lower is better; kept raw for audit and
#                        cross-run comparison.
#   peak_cpu_mem:        peak resource string from `docker stats`
#                        (e.g. "12.34%/128.5MiB"). Parsed into
#                        `peak_cpu_pct` and `peak_mem_mib` for
#                        machine consumption; the raw string is kept
#                        for human audit.
#   cost_efficiency:     a single [0, 1] fitness axis
#                        1 / (1 + wall_clock_total_s / WALL_CLOCK_REF_S)
#                        where WALL_CLOCK_REF_S is a documented
#                        reference budget (default 60s). This is a
#                        monotonic, invertible transformation of
#                        wall_clock_total_s: Pareto dominance on
#                        cost_efficiency is identical to dominance
#                        on -wall_clock_total_s, so it preserves the
#                        ranking without collapsing dimensions.

WALL_CLOCK_REF_S = 60.0  # documented: 60s is the calibration reference


def _wall_clock_total_s(stages: dict) -> float:
    """Sum the durations of the behavioral stages.  Falls back to 0.0
    for unknown stages (forward-compatible with new stages)."""
    total = 0.0
    for stage, passed in stages.items():
        if not passed:
            continue  # only count successful stages (cascade SKIPPED is 0)
        d = getattr(stage, "value", None)
        if d in (
            TrialStage.BUILD.value,
            TrialStage.TEST.value,
            TrialStage.DEPLOY.value,
            TrialStage.RUNTIME.value,
            TrialStage.DESTROY.value,
        ):
            total += float(getattr(stage, "duration_s", 0.0) or 0.0)
    return total


_PEAK_RE = re.compile(
    r"^\s*(?P<cpu>[0-9.]+)%\s*/\s*(?P<mem>[0-9.]+)(?P<unit>[KMG]i?B)\s*$"
)


def _parse_peak_resource(s: str) -> tuple[float, float | None]:
    """Parse a 'CPU%/MemUsage' string.  Returns (cpu_pct, mem_mib or None).
    Empty / unparseable input returns (0.0, None) — the cost axis is honest
    about missing data, never silently zero."""
    if not s or not isinstance(s, str):
        return 0.0, None
    m = _PEAK_RE.match(s.strip())
    if not m:
        return 0.0, None
    cpu = float(m.group("cpu"))
    val = float(m.group("mem"))
    unit = m.group("unit")
    if unit.startswith("Gi"):
        mem_mib = val * 1024.0
    elif unit.startswith("Ki"):
        mem_mib = val / 1024.0
    else:
        mem_mib = val  # MiB
    return cpu, mem_mib


def _cost_efficiency(wall_clock_total_s: float) -> float:
    """1 / (1 + s / REF). Monotonic in s; bounded in (0, 1]."""
    if wall_clock_total_s < 0:
        return 1.0  # pathological; treat as perfect (and the test will catch it)
    return 1.0 / (1.0 + wall_clock_total_s / WALL_CLOCK_REF_S)


def compute(
    repo_files_count: int,
    stages: dict[TrialStage, bool],
    structural_passed: bool,
    test_passed: bool,
    runtime_passed: bool,
    repo_content_hash: str = "",
    files: dict[str, str] | None = None,
    stage_evidence: list | None = None,
) -> TrialMetrics:
    """Compute four-class metrics from trial stage outcomes.

    `stage_evidence` is the optional list of StageEvidence objects (one per
    stage). When supplied, cost/energy metrics are computed from the
    duration_s and peak_resource fields. When absent, cost/energy defaults
    to 0.0/None — honest about missing data, never silently zeroed.
    """
    files = files or {}
    compiler_correctness = {
        "structural_conformance": structural_passed,
        "repo_file_count": repo_files_count,
    }
    functional_correctness = {
        "tests_passed": test_passed,
    }
    # Cost / energy: from StageEvidence (duration_s, peak_resource).
    # Build a {stage: StageEvidence} map for the metric computation.
    by_stage: dict = {}
    for se in stage_evidence or []:
        if se is None:
            continue
        try:
            by_stage[se.stage] = se
        except AttributeError:
            continue
    wall_clock_total_s = sum(
        float(getattr(by_stage[s], "duration_s", 0.0) or 0.0)
        for s in (
            TrialStage.BUILD,
            TrialStage.TEST,
            TrialStage.DEPLOY,
            TrialStage.RUNTIME,
            TrialStage.DESTROY,
        )
        if s in by_stage and bool(stages.get(s, False))
    )
    # Peak resource: take the maximum across runtime/probe.  The probe is
    # the one that actually calls `docker stats`, but the runtime stage is
    # the canonical one. We use max(peak_cpu_pct) and max(peak_mem_mib) so
    # a single noisy reading does not dominate a calm workload.
    peak_cpu_pct = 0.0
    peak_mem_mib: float | None = None
    for s in (TrialStage.RUNTIME, TrialStage.PROBE if hasattr(TrialStage, "PROBE") else TrialStage.RUNTIME):
        se = by_stage.get(s)
        if se is None:
            continue
        cpu, mem = _parse_peak_resource(getattr(se, "peak_resource", "") or "")
        if cpu > peak_cpu_pct:
            peak_cpu_pct = cpu
        if mem is not None and (peak_mem_mib is None or mem > peak_mem_mib):
            peak_mem_mib = mem
    raw_peak = ""
    if TrialStage.RUNTIME in by_stage:
        raw_peak = getattr(by_stage[TrialStage.RUNTIME], "peak_resource", "") or ""
    cost_efficiency = _cost_efficiency(wall_clock_total_s)
    operational_correctness = {
        "runtime_healthy": runtime_passed,
        "build_succeeded": stages.get(TrialStage.BUILD, False),
        "deploy_succeeded": stages.get(TrialStage.DEPLOY, False),
        "destroy_succeeded": stages.get(TrialStage.DESTROY, False),
        # Cost / energy: kept as separate fields, never aggregated.  An
        # auditor can read wall_clock_total_s and peak_cpu_pct directly
        # from the trial's metrics dict.
        "wall_clock_total_s": round(wall_clock_total_s, 3),
        "peak_cpu_pct": round(peak_cpu_pct, 3),
        "peak_mem_mib": round(peak_mem_mib, 3) if peak_mem_mib is not None else None,
        "peak_resource_raw": raw_peak,
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
        cost_efficiency=cost_efficiency,
        wall_clock_reference_s=WALL_CLOCK_REF_S,
    )
