"""Backend-supplied build/verification contract (Phase 19).

Constitutional rule: a compiler backend describes WHAT it produces (its
capability manifest) *and* HOW it is to be verified (its build profile). The
meta-compiler must never hardcode a backend's verification shape — it must be
read from the backend's own profile. This is what makes "adding a backend ==
implementing a backend, not modifying the core" real.

``BackendBuildProfile`` is produced by each backend's ``build_profile`` method
(see ``FastAPIHexagonalBackend`` / ``GoHexagonalBackend``); this module owns the
profile data type and the language-dispatched verifier lookup so the verifier
selection seam lives in exactly one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from tiannara.application.compiler.verification import (
    BundleVerificationReport,
    BundleVerifier,
    GoBundleVerifier,
)


@dataclass(frozen=True)
class BackendBuildProfile:
    """The build/verification contract a backend declares for its output.

    ``language`` keys both the verifier selection and (optionally) the runtime
    test command handed to the execution environment. ``required_files`` are
    package-relative to the bundle root and are always verified deterministically,
    with no toolchain dependency.
    """

    language: str
    required_files: tuple[str, ...] = ()
    verifier_kind: str = ""
    build_command: Optional[list[str]] = None
    test_command: Optional[list[str]] = None
    # Optional container image in which ``test_command`` runs (e.g.
    # ``golang:1.22-alpine``). Lets backends run their toolchain without it being
    # installed on the host. Empty/unset -> harness falls back to local execution
    # or honest ``skipped:toolchain_absent``.
    runtime_image: Optional[str] = None
    # When True, the harness hands ``build_command`` to the execution environment
    # so the runtime image's deps are installed before ``test_command`` runs (e.g.
    # ``pip install -r requirements*.txt && pytest``). Backends whose image already
    # carries the toolchain (e.g. Go) leave this False -- their ``build_command``
    # is contract-only for the verifier, never executed at runtime.
    requires_build_phase: bool = False


class RequiredFilesVerifier:
    """Minimal verifier: checks required-file presence only (fallback)."""

    def __init__(self, required_files: list[str]) -> None:
        self._required = list(required_files)

    def verify(self, root: str | Path) -> BundleVerificationReport:
        root = Path(root)
        missing = [f for f in self._required if not (root / f).exists()]
        return BundleVerificationReport(
            ok=not missing,
            missing_files=missing,
        )


def make_verifier(
    language: str,
    package: str,
    required_files: list[str],
) -> BundleVerifier | GoBundleVerifier | RequiredFilesVerifier:
    """Dispatch on the backend's language to the right verifier implementation.

    Python -> BundleVerifier (syntax + AST import direction).
    Go      -> GoBundleVerifier (go.mod + required files + import direction).
    Other   -> RequiredFilesVerifier (presence only; static, toolchain-free).
    """
    if language == "python":
        return BundleVerifier(package=package, required_files=required_files)
    if language == "go":
        return GoBundleVerifier(required_files=required_files)
    return RequiredFilesVerifier(required_files=required_files)
