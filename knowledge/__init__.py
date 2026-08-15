"""
Enterprise Knowledge Graph runtime.

This package implements the Phase 23 Knowledge Graph kernel.

Constitutional constraints:
- The ISR remains the canonical architectural source of truth.
- The Knowledge Graph is an evidence and traceability substrate.
- The Knowledge Graph must not directly mutate ISR or execute governance actions.
- Storage, search, and visualization backends are replaceable through adapters.
"""

__version__ = "0.1.0"
