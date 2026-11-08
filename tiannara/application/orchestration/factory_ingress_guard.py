"""Factory/create CLI ingress policy (Checkpoint 057)."""
from __future__ import annotations

import os
import sys


def governed_production_blocks_subordinate_factory(*, dev_subordinate_override: bool) -> int | None:
    if dev_subordinate_override:
        return None
    flag = os.getenv("ESAP_GOVERNED_PRODUCTION", "").strip().lower()
    if flag not in {"1", "true", "yes", "on"}:
        return None
    print(
        "error: factory/create blocked under ESAP_GOVERNED_PRODUCTION; "
        "use `tiannara full-stack run` or POST /api/v1/orchestration/full-stack/run",
        file=sys.stderr,
    )
    return 2
