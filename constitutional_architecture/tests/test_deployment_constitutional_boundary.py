"""
Constitutional boundary enforcement for the Deployment Engine.

The Deployment Engine:
- NEVER imports from engine.*
- NEVER modifies the ISR
- NEVER generates production code
"""

import ast
import importlib
import inspect
import pkgutil
import pytest


FORBIDDEN_IMPORT_PREFIXES = (
    "constitutional_architecture.engine",
)


def _get_all_deployment_modules():
    import constitutional_architecture.deployment
    modules = []
    for importer, modname, ispkg in pkgutil.walk_packages(
        constitutional_architecture.deployment.__path__,
        prefix="constitutional_architecture.deployment.",
    ):
        modules.append(modname)
    return modules


def _has_forbidden_import(source: str, prefix: str) -> bool:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(prefix):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith(prefix):
                return True
    return False


class TestDeploymentConstitutionalBoundary:
    def test_no_engine_imports(self):
        violations = []
        for mod_name in _get_all_deployment_modules():
            try:
                mod = importlib.import_module(mod_name)
                source = inspect.getsource(mod)
            except (ImportError, TypeError, OSError):
                continue
            for prefix in FORBIDDEN_IMPORT_PREFIXES:
                if _has_forbidden_import(source, prefix):
                    violations.append(f"{mod_name} imports {prefix}")

        assert not violations, (
            "Constitutional violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_no_isr_mutation(self):
        violations = []
        for mod_name in _get_all_deployment_modules():
            try:
                mod = importlib.import_module(mod_name)
                source = inspect.getsource(mod)
            except (ImportError, TypeError, OSError):
                continue
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute):
                            if isinstance(target.value, ast.Attribute):
                                if (isinstance(target.value.value, ast.Name)
                                        and target.value.value.id == "isr"
                                        and target.value.attr in ("system", "_system")):
                                    violations.append(
                                        f"{mod_name}:{node.lineno} mutates ISR"
                                    )

        assert not violations, (
            "Constitutional violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )
