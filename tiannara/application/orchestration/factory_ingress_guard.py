"""Factory/create CLI ingress policy (Checkpoint 057 / CP067-W09)."""
from __future__ import annotations

import os
import sys

from certification.orchestration.implir_ingress_guard import (
    ImplirIngressBlocked,
    assert_trusted_factory_ingress,
)


def governed_production_blocks_subordinate_factory(*, dev_subordinate_override: bool) -> int | None:
    if dev_subordinate_override:
        return None
    flag = os.getenv("ESAP_GOVERNED_PRODUCTION", "").strip().lower()
    governed = flag in {"1", "true", "yes", "on"}
    try:
        assert_trusted_factory_ingress(
            governed_production=governed,
            dev_subordinate_override=dev_subordinate_override,
        )
    except ImplirIngressBlocked:
        if not governed:
            return None
        print(
            "error: factory/create blocked under ESAP_GOVERNED_PRODUCTION; "
            "use `tiannara full-stack run` or POST /api/v1/orchestration/full-stack/run",
            file=sys.stderr,
        )
        return 2
    return None
