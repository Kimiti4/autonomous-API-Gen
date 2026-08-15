"""BundleVerifier — independent verification of a compiled bundle.

Structured checks, all deterministic and dependency-light:
  * structure: required files present;
  * syntax: every Python file compiles;
  * dependency direction: domain imports nothing from outer layers.

Behavioral verification (loading the app, exercising endpoints) lives in the
test suite, gated on framework availability — this verifier stays framework-free
so it can run in any environment.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from pydantic import BaseModel, Field


class BundleVerificationReport(BaseModel):
    ok: bool
    missing_files: list[str] = Field(default_factory=list)
    syntax_errors: list[str] = Field(default_factory=list)
    dependency_violations: list[str] = Field(default_factory=list)


_OUTER_PREFIXES = ("api", "application", "infrastructure")


class BundleVerifier:
    """Verify a materialized bundle rooted at ``root``.

    ``package`` is the generated package basename (e.g. ``inventory_tracker``);
    its ``domain/`` subpackage must never import from siblings.
    ``required_files`` are paths relative to ``root``.
    """

    def __init__(self, package: str, required_files: list[str]) -> None:
        self._package = package
        self._required = list(required_files)

    def verify(self, root: str | Path) -> BundleVerificationReport:
        root = Path(root)
        missing = [f for f in self._required if not (root / f).exists()]

        syntax_errors: list[str] = []
        for py in sorted(root.rglob("*.py")):
            try:
                compile(py.read_text(encoding="utf-8"), str(py), "exec")
            except SyntaxError as exc:
                syntax_errors.append(f"{py}: {exc}")

        violations = self._dependency_direction(root)

        ok = not missing and not syntax_errors and not violations
        return BundleVerificationReport(
            ok=ok,
            missing_files=missing,
            syntax_errors=syntax_errors,
            dependency_violations=violations,
        )

    def _dependency_direction(self, root: Path) -> list[str]:
        violations: list[str] = []
        domain_dir = root / self._package / "domain"
        if not domain_dir.exists():
            return violations
        for py in sorted(domain_dir.rglob("*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                module = ""
                if isinstance(node, ast.Import):
                    module = node.names[0].name if node.names else ""
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                if module and module.startswith(f"{self._package}."):
                    segment = module[len(self._package) + 1 :].split(".")[0]
                    if segment in _OUTER_PREFIXES:
                        violations.append(
                            f"{py}: domain imports outer layer '{module}'"
                        )
        return violations


class GoBundleVerifier:
    """Deterministic, toolchain-free verifier for Go backend bundles.

    Honors the same ``BundleVerificationReport`` contract as ``BundleVerifier``
    so the meta-compiler treats every backend's result uniformly. Static checks:

    * required files present (package-relative, toolchain-free);
    * ``go.mod`` is well-formed (``module`` directive);
    * inward-dependency: ``internal/domain`` must not import
      ``internal/application``, ``internal/infrastructure``, or ``internal/api``.

    Runtime execution (``go test``) is the job of the execution environment,
    gated on ``shutil.which("go")`` there -- never faked here.
    """

    _FORBIDDEN_SEGMENTS = ("api", "application", "infrastructure")

    def __init__(self, required_files: list[str]) -> None:
        self._required = list(required_files)

    def verify(self, root: str | Path) -> BundleVerificationReport:
        root = Path(root)
        missing = [f for f in self._required if not (root / f).exists()]

        syntax_errors: list[str] = []
        go_mod = root / "go.mod"
        if not go_mod.exists():
            syntax_errors.append("go.mod: missing (required for Go module)")
        else:
            first_line = go_mod.read_text(encoding="utf-8").strip().splitlines()[0]
            if not first_line.startswith("module "):
                syntax_errors.append(f"go.mod: missing 'module' directive ({first_line!r})")

        violations = self._dependency_direction(root)

        ok = not missing and not syntax_errors and not violations
        return BundleVerificationReport(
            ok=ok,
            missing_files=missing,
            syntax_errors=syntax_errors,
            dependency_violations=violations,
        )

    def _dependency_direction(self, root: Path) -> list[str]:
        violations: list[str] = []
        domain_dir = root / "internal" / "domain"
        if not domain_dir.exists():
            return violations
        for go_file in sorted(domain_dir.rglob("*.go")):
            for imp in _go_imports(go_file.read_text(encoding="utf-8")):
                if any(
                    f"internal/{seg}" in imp for seg in self._FORBIDDEN_SEGMENTS
                ):
                    violations.append(
                        f"{go_file}: domain imports outer package '{imp}'"
                    )
        return violations


def _go_imports(text: str) -> list[str]:
    """Extract Go import paths from source text (stdlib `go/parser`-free).

    Handles both standalone ``import "path"`` and grouped ``import ( ... )``
    forms. Toolchain-free so the verifier stays deterministic and hermetic.
    """
    paths: list[str] = []
    for m in re.finditer(r'import\s+"([^"]+)"', text):
        paths.append(m.group(1))
    for block in re.finditer(r"import\s*\(([^)]*)\)", text, re.DOTALL):
        for m in re.finditer(r'"([^"]+)"', block.group(1)):
            paths.append(m.group(1))
    return paths
