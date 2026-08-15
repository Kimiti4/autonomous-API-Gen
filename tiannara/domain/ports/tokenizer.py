"""TokenEstimator port — dependency-inverted token counting.

The platform core never depends on a vendor tokenizer. Deterministic
reference estimators live in application/intelligence/tokenizing.py;
model-specific tokenizers are deployment plugins behind this port.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenEstimator(Protocol):
    name: str

    def count(self, text: str) -> int:
        """Deterministic token count for the given text."""
        ...
