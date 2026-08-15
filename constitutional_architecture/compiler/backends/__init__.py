"""
Compiler Backends — Backend-specific code generators.
"""

from constitutional_architecture.compiler.backends.backend_interface import CompilerBackend, BackendResult
from constitutional_architecture.compiler.backends.backend_registry import BackendRegistry
from constitutional_architecture.compiler.backends.backend_selector import BackendSelector


def FastAPIBackend(*args, **kwargs):
    from constitutional_architecture.compiler.backends.fastapi_backend import FastAPIBackend as _cls
    return _cls(*args, **kwargs)


__all__ = [
    "CompilerBackend", "BackendResult", "BackendRegistry", "BackendSelector", "FastAPIBackend",
]
