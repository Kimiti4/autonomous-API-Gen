"""33.13 Feedback -- ISR only, never thresholds."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class SecurityMutation: isr_ref: str; change: str
def propose_mutation(finding):
    if not finding.get("provenance_resolves"): raise ValueError("provenance must resolve")
    return SecurityMutation(finding["isr_hash"], "harden")
def is_threshold_mutation(m): return "threshold" in str(m).lower()
