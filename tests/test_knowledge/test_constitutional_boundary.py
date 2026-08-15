"""
Constitutional boundary enforcement for Knowledge Engine.
"""

import importlib
import inspect
import pkgutil
import pytest

FORBIDDEN_IMPORTS = (
    "constitutional_architecture.engine",
    "constitutional_architecture.compiler",
    "constitutional_architecture.deployment",
)


def _get_all_knowledge_modules():
    import constitutional_architecture.knowledge
    modules = []
    for importer, modname, ispkg in pkgutil.walk_packages(
        constitutional_architecture.knowledge.__path__,
        prefix="constitutional_architecture.knowledge.",
    ):
        modules.append(modname)
    return modules


class TestConstitutionalBoundary:
    def test_no_engine_imports(self):
        violations = []
        for mod_name in _get_all_knowledge_modules():
            try:
                mod = importlib.import_module(mod_name)
                source = inspect.getsource(mod)
            except (ImportError, TypeError, OSError):
                continue
            for forbidden in FORBIDDEN_IMPORTS:
                if f"import {forbidden}" in source or f"from {forbidden}" in source:
                    violations.append(f"{mod_name} imports {forbidden}")
        assert not violations, (
            "Constitutional violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_no_isr_modification_patterns(self):
        forbidden_patterns = [
            "isr.system =",
            "isr._system =",
            "isr.version =",
            "isr._version =",
        ]
        violations = []
        for mod_name in _get_all_knowledge_modules():
            try:
                mod = importlib.import_module(mod_name)
                source = inspect.getsource(mod)
            except (ImportError, TypeError, OSError):
                continue
            for pattern in forbidden_patterns:
                if pattern in source:
                    violations.append(f"{mod_name} contains '{pattern}'")
        assert not violations, (
            "ISR modification patterns found:\n" + "\n".join(f"  - {v}" for v in violations)
        )
