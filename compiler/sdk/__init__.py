"""
Compiler Backend SDK.

This package defines the backend extension, verification, and certification
layer for the Universal Software Compiler.

Constitutional constraints:
- The ISR remains the sole architectural source of truth.
- Compiler backends consume the ISR.
- Compiler backends must never redefine architecture.
- Backends must be replaceable, testable, and certifiable.
"""

__version__ = "0.1.0"
