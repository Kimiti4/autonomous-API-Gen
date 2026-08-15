"""
Universal Software Compiler runtime.

This package implements the Phase 25 compiler kernel.

Constitutional constraints:
- The ISR is the sole architectural source of truth.
- Compiler backends consume the ISR.
- Compiler backends must never redefine architecture.
- The compiler core remains technology-neutral.
"""

__version__ = "0.1.0"
