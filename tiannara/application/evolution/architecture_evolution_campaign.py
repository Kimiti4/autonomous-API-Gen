"""34.8 Campaign -- 100 to 100M + spikes/failures."""
from __future__ import annotations
def campaign_scenarios():
    return [100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000, 100_000_000] + ["spike","regional_failure","contention"]
