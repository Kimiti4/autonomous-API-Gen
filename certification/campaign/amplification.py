"""Retry amplification — the honesty telescope for the execution substrate.

A campaign can technically reach CERTIFIED while hiding an increasingly
unhealthy execution environment behind unbounded retries.  These metrics make
that visible: every retry is counted, every retry must carry a recognized
signature, and campaign-level honesty bounds (max_retry_rate,
unexplained_retries == 0) are hard boundaries, not suggestions.

Unexecuted, timed-out, resource-exhausted, or infrastructure-failed trials can
never disappear from the denominator or become CERTIFIED.
"""
from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class RetryAmplification(BaseModel):
    model_config = ConfigDict(frozen=True)
    planned_trials: int
    actual_trials: int
    stage_executions: int
    retry_executions: int
    retry_rate: float
    cascade_skipped: int
    infrastructure_failures: int
    product_failures: int
    unexplained_retries: int


def compute_amplification(
    trials,
    planned: int,
    max_retry_rate: float = 0.2,
) -> RetryAmplification:
    """Aggregate retry/cascade/failure accounting across trial stage evidence.

    `trials` accepts Trial objects or dumped dicts (unified via _stage_get).
    A retry is explained iff it is backed by an equal number of recorded
    retry_signatures; anything else is an unexplained retry (dishonesty).
    """
    se = ret = unex = casc = infra = prod = 0
    for t in trials:
        stages = stage_list(t)
        for s in stages:
            se += 1
            r = _get(s, "retries") or 0
            sigs = _get(s, "retry_signatures") or []
            ret += r
            if r > len(sigs):
                unex += r - len(sigs)
            if (_get(s, "mode") or "").lower() == "skipped":
                # Cascade-SKIPPED stages are honest visibility, not successes.
                casc += 1
            if not _get(s, "passed"):
                fc = _get(s, "failure_class") or ""
                if fc == "infrastructure":
                    infra += 1
                elif fc in ("product", "semantic", "compiler"):
                    prod += 1
    return RetryAmplification(
        planned_trials=planned,
        actual_trials=len(trials),
        stage_executions=se,
        retry_executions=ret,
        retry_rate=round(ret / se, 4) if se else 0.0,
        cascade_skipped=casc,
        infrastructure_failures=infra,
        product_failures=prod,
        unexplained_retries=unex,
    )


def amplification_problems(
    amp: RetryAmplification, max_retry_rate: float,
) -> list[str]:
    """Honesty enforcement — returns [] when the substrate is honest."""
    problems: list[str] = []
    if amp.unexplained_retries > 0:
        problems.append(f"unexplained retries: {amp.unexplained_retries}")
    if amp.retry_rate > max_retry_rate:
        problems.append(
            f"retry_rate {amp.retry_rate} > max_retry_rate {max_retry_rate}"
        )
    if amp.product_failures > 0:
        problems.append(f"product failures: {amp.product_failures}")
    return problems


def _get(s, key, default=None):
    if isinstance(s, dict):
        return s.get(key, default)
    return getattr(s, key, default)


def stage_list(t):
    if isinstance(t, dict):
        return t.get("stages", [])
    return list(getattr(t, "stages", []))