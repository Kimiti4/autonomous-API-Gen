from __future__ import annotations

import ast
import time
from typing import Optional

from constitutional_architecture.verification.verification_context import VerificationContext
from constitutional_architecture.verification.verification_result import (
    CheckSeverity,
    CheckStatus,
    VerificationCheck,
    VerificationLevel,
    VerificationResult,
)
from constitutional_architecture.verification.verifiers.verifier_interface import Verifier


class StaticVerifier(Verifier):
    @property
    def name(self) -> str:
        return "static"

    @property
    def description(self) -> str:
        return "Static analysis of generated source code"

    @property
    def level(self) -> VerificationLevel:
        return VerificationLevel.L1_STATIC

    def verify(self, ctx: VerificationContext) -> VerificationResult:
        start = time.perf_counter()
        checks: list[VerificationCheck] = []

        source_artifacts = ctx.get_artifacts_by_type("source")
        config_artifacts = ctx.get_artifacts_by_type("config")

        checks.append(self._check_sources_exist(source_artifacts))
        checks.extend(self._check_python_syntax(source_artifacts))
        checks.append(self._check_no_empty_files(source_artifacts))
        checks.append(self._check_config_present(config_artifacts))
        checks.append(self._check_entry_point(source_artifacts))

        duration = (time.perf_counter() - start) * 1000
        success = all(c.passed or c.status == CheckStatus.WARNING for c in checks)

        return VerificationResult(
            verifier_name=self.name,
            level=self.level,
            checks=tuple(checks),
            duration_ms=duration,
            success=success,
        )

    def _check_sources_exist(self, artifacts) -> VerificationCheck:
        passed = len(artifacts) > 0
        return VerificationCheck(
            check_id="STATIC-001",
            name="source_files_exist",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.BLOCKER if not passed else CheckSeverity.INFO,
            message=f"{len(artifacts)} source file(s) found",
        )

    def _check_python_syntax(self, artifacts) -> list[VerificationCheck]:
        checks: list[VerificationCheck] = []
        py_files = [a for a in artifacts if a.path.endswith(".py")]

        syntax_errors = 0
        for artifact in py_files:
            try:
                ast.parse(artifact.content)
            except SyntaxError as e:
                syntax_errors += 1
                checks.append(VerificationCheck(
                    check_id=f"STATIC-002-{artifact.path}",
                    name="python_syntax",
                    verifier=self.name,
                    level=self.level,
                    status=CheckStatus.FAILED,
                    severity=CheckSeverity.ERROR,
                    message=f"Syntax error in {artifact.path}: {e.msg} (line {e.lineno})",
                    artifact_path=artifact.path,
                    isr_node_id=artifact.isr_node_id,
                    suggested_repair="Fix syntax error in generated code (compiler bug)",
                ))

        if syntax_errors == 0:
            checks.append(VerificationCheck(
                check_id="STATIC-002",
                name="python_syntax",
                verifier=self.name,
                level=self.level,
                status=CheckStatus.PASSED,
                severity=CheckSeverity.INFO,
                message=f"All {len(py_files)} Python files have valid syntax",
            ))

        return checks

    def _check_no_empty_files(self, artifacts) -> VerificationCheck:
        empty = [a.path for a in artifacts if not a.content.strip()]
        passed = len(empty) == 0
        return VerificationCheck(
            check_id="STATIC-003",
            name="no_empty_files",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message="No empty files" if passed else f"Empty files: {empty[:5]}",
        )

    def _check_config_present(self, artifacts) -> VerificationCheck:
        passed = len(artifacts) > 0
        return VerificationCheck(
            check_id="STATIC-004",
            name="config_files_present",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.WARNING,
            severity=CheckSeverity.WARNING,
            message=f"{len(artifacts)} config file(s) found",
        )

    def _check_entry_point(self, artifacts) -> VerificationCheck:
        entry_points = [a for a in artifacts if "main" in a.path.lower()]
        passed = len(entry_points) > 0
        return VerificationCheck(
            check_id="STATIC-005",
            name="entry_point_exists",
            verifier=self.name,
            level=self.level,
            status=CheckStatus.PASSED if passed else CheckStatus.FAILED,
            severity=CheckSeverity.ERROR if not passed else CheckSeverity.INFO,
            message="Entry point found" if passed else "No main entry point found",
        )
