"""34.7 Semantic preservation -- intent, contracts, API, policies."""
from __future__ import annotations
def is_semantically_preserved(before_intent: str, after_intent: str, contracts_preserved: bool) -> bool:
    return before_intent == after_intent and contracts_preserved
