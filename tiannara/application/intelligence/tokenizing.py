"""Deterministic reference token estimators.

Both are pure functions: identical text always yields identical counts.
They are conservative heuristics, documented as such; deployments may plug
model-specific tokenizers behind the TokenEstimator port without touching
the compiler.
"""

from __future__ import annotations

import math
import re


class CharRatioEstimator:
    """ceil(chars / ratio), minimum 1 for non-empty text."""

    name = "char_ratio_4"

    def __init__(self, ratio: int = 4) -> None:
        if ratio < 1:
            raise ValueError("ratio must be >= 1")
        self._ratio = ratio

    def count(self, text: str) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text) / self._ratio))


class WhitespaceEstimator:
    """Counts alphanumeric runs and individual punctuation characters."""

    name = "whitespace_punct"
    _pattern = re.compile(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]")

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._pattern.findall(text))
