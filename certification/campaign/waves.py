"""Waves — Campaign B scale progression configuration.

Each wave is a self-contained measurement. B0 proves the Docker substrate
exists before any trials run. B1 is the 78-trial baseline directly
comparable to Campaign A. B2–B4 scale upward only after the previous
wave certifies.

Resource budgets are hard operational safety boundaries. Resource exhaustion
terminates a campaign as NOT_CERTIFIED — it must never silently reduce the
denominator or convert unexecuted trials into passes.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from certification.corpus.corpus import Workload, _w, Category
from certification.stages.execution_mode import ExecutionMode


class WaveId(str, Enum):
    B0 = "B0"
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"
    B4 = "B4"


@dataclass(frozen=True)
class Wave:
    id: str
    purpose: str
    scale_factor: int
    required_mode: ExecutionMode
    max_retry_rate: float = 0.2


@dataclass(frozen=True)
class CampaignBudget:
    """Hard resource boundaries for a campaign run.

    Resource exhaustion → NOT_CERTIFIED. Never silently skip trials.
    """
    max_trials: int
    max_concurrent_trials: int = 1
    max_runtime_per_trial_s: int = 600
    max_total_runtime_s: int = 7200
    max_disk_mb: int = 10240
    cleanup_required: bool = True


WAVES: dict[str, Wave] = {
    WaveId.B0.value: Wave(
        id=WaveId.B0.value,
        purpose="docker substrate certification",
        scale_factor=0,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
    WaveId.B1.value: Wave(
        id=WaveId.B1.value,
        purpose="full corpus real execution (78 trials)",
        scale_factor=1,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
    WaveId.B2.value: Wave(
        id=WaveId.B2.value,
        purpose="hundreds",
        scale_factor=4,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
    WaveId.B3.value: Wave(
        id=WaveId.B3.value,
        purpose="1000+",
        scale_factor=12,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
    WaveId.B4.value: Wave(
        id=WaveId.B4.value,
        purpose="sustained scale",
        scale_factor=24,
        required_mode=ExecutionMode.REAL_DOCKER,
    ),
}

BUDGETS: dict[str, CampaignBudget] = {
    WaveId.B0.value: CampaignBudget(max_trials=1, max_total_runtime_s=300),
    WaveId.B1.value: CampaignBudget(max_trials=78, max_total_runtime_s=3600),
    WaveId.B2.value: CampaignBudget(max_trials=312, max_total_runtime_s=21600),
    WaveId.B3.value: CampaignBudget(max_trials=936, max_total_runtime_s=43200),
    WaveId.B4.value: CampaignBudget(max_trials=1872, max_total_runtime_s=86400),
}


def expand_corpus(factor: int) -> list[Workload]:
    """Deterministically derive parameterized variants from the seed corpus.

    factor=0 returns empty. factor=1 returns the original 39.
    factor>1 creates TEMPLATE-class variants by rotating seeds
    and appending suffixed intents.
    """
    from certification.corpus.corpus import default_corpus
    base = default_corpus()
    if factor <= 0:
        return []
    if factor == 1:
        return list(base)

    out: list[Workload] = list(base)
    for i in range(1, factor):
        for w in base:
            rotated = w.seeds[-i % len(w.seeds):] + w.seeds[:-i % len(w.seeds)] if len(w.seeds) > 1 else w.seeds
            variant = Workload(
                intent=f"{w.intent} variant-{i}",
                category=w.category,
                seeds=rotated,
            )
            out.append(variant)
    return out


def ledger_path_for(wave_id: str) -> str:
    return f"release/evidence/cbc1-b-{wave_id}-ledger.jsonl"


def aggregate_path_for(wave_id: str) -> str:
    return f"release/evidence/cbc1-b-{wave_id}-aggregate.json"
