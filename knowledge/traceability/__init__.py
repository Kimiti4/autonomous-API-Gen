"""
Knowledge Graph advanced traceability and impact explanation runtime.

This package provides read-only impact analysis, trace explanation, and
evidence-aware path reasoning over the Enterprise Knowledge Graph.

Constitutional constraints:
- The ISR remains the sole architectural source of truth.
- The Knowledge Graph is an evidence and traceability substrate.
- This package must not mutate ISR.
- This package must not execute governance actions.
- All impact reasoning must be explainable.
"""

__version__ = "0.1.0"
