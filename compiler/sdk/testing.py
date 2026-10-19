"""
Backend contract test harness.

Every compiler backend should pass these contract tests before certification.
"""

from __future__ import annotations

import ast
from typing import Any, Optional

from ..ids import deterministic_id, sha256_hex
from ..models import CompilationContext, CompilationPlan
from ..validation import validate_compilation_output
from .base import ensure_sdk_backend
from .capabilities import validate_capabilities
from .models import ContractTestResult, DeterminismResult


FIXED_CERTIFICATION_TIMESTAMP = "1970-01-01T00:00:00+00:00"


def default_test_isr() -> dict[str, Any]:
    """Return the default certification ISR."""

    return {
        "isr_id": "isr_certification_sample",
        "version": "1.0.0",
        "name": "Certification Sample",
        "domains": [
            {
                "name": "certification",
                "services": [
                    {
                        "name": "CertificationService",
                        "apis": [
                            {
                                "name": "certify"
                            }
                        ],
                    }
                ],
            }
        ],
        "events": [
            {
                "name": "CertificationCompleted"
            }
        ],
        "data_models": [
            {
                "name": "CertificationRecord"
            }
        ],
    }


def _build_plan(
    test_isr: dict[str, Any],
    backend_manifest,
) -> CompilationPlan:
    """Build a deterministic certification compilation plan."""

    plan_id = deterministic_id(
        "contract_plan",
        {
            "isr_id": test_isr.get("isr_id"),
            "isr_version": test_isr.get("version"),
            "backend_id": backend_manifest.backend_id,
            "backend_version": backend_manifest.version,
        },
    )

    return CompilationPlan(
        plan_id=plan_id,
        isr_id=str(test_isr.get("isr_id")),
        isr_version=str(test_isr.get("version")),
        backend_id=backend_manifest.backend_id,
        backend_version=backend_manifest.version,
        environment="certification",
        parameters={
            "contract_test": True,
        },
        passes=[],
        validation_level="standard",
        created_at=FIXED_CERTIFICATION_TIMESTAMP,
    )


def _hash_output(output) -> tuple[tuple[str, str], ...]:
    """Hash backend artifacts deterministically."""

    return tuple(
        sorted(
            (
                artifact.path,
                sha256_hex(artifact.content),
            )
            for artifact in output.artifacts
        )
    )


_ROUTE_DECORATOR_METHODS = {"get"}
_EXCLUDED_BUSINESS_PREFIXES = ("/health", "/docs", "/redoc", "/openapi.json")


def _join_route_path(base: str, rel: str) -> str:
    if not rel:
        return base or "/"
    if not rel.startswith("/"):
        rel = "/" + rel
    if not base:
        return rel
    return base.rstrip("/") + rel


def _module_business_get_paths(tree: ast.AST) -> set[str]:
    """Resolve GET route paths in a FastAPI module, honouring APIRouter
    prefixes and include_router nesting (relative paths count only through
    their router's prefix)."""
    router_prefix: dict[str, list[str]] = {}
    include_extra: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(
            node.targets[0], ast.Name
        ):
            target = node.targets[0].id
            value = node.value
            if isinstance(value, ast.Call):
                fname = getattr(value.func, "id", None) or getattr(
                    value.func, "attr", None
                )
                if fname == "APIRouter":
                    base = ""
                    for kw in value.keywords:
                        if kw.arg == "prefix" and isinstance(
                            kw.value, ast.Constant
                        ) and isinstance(kw.value.value, str):
                            base = kw.value.value
                    router_prefix.setdefault(target, []).append(base)
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "attr", None) == "include_router"
            and node.args
            and isinstance(node.args[0], ast.Name)
        ):
            extra = ""
            for kw in node.keywords:
                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(
                    kw.value.value, str
                ):
                    extra = kw.value.value
            include_extra.setdefault(node.args[0].id, []).append(extra)

    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            if dec.func.attr not in _ROUTE_DECORATOR_METHODS:
                continue
            if not dec.args or not isinstance(dec.args[0], ast.Constant):
                continue
            if not isinstance(dec.args[0].value, str):
                continue
            rel = dec.args[0].value
            receiver = dec.func.value.id if isinstance(dec.func.value, ast.Name) else None
            bases = list(router_prefix.get(receiver, [])) if receiver in router_prefix else [""]
            extras = list(include_extra.get(receiver, [])) if receiver in include_extra else [""]
            for base in bases:
                for extra in extras:
                    found.add(_join_route_path(base.rstrip("/") + extra, rel))
    return found


def _python_sources_parse(artifacts: list) -> tuple[bool, str]:
    bad: list[str] = []
    for artifact in artifacts:
        if not artifact.path.endswith(".py"):
            continue
        try:
            ast.parse(artifact.content)
        except SyntaxError as exc:
            bad.append(f"{artifact.path}:{exc.msg}")
    return (not bad), "; ".join(bad)


def _business_routes_present(artifacts: list) -> tuple[bool, str]:
    py_artifacts = [a for a in artifacts if a.path.endswith(".py")]
    framework_y = any(
        "FastAPI(" in a.content or "APIRouter(" in a.content for a in py_artifacts
    )
    if not framework_y:
        return True, "no FastAPI application in output"
    paths: set[str] = set()
    unparsed: list[str] = []
    for artifact in py_artifacts:
        try:
            tree = ast.parse(artifact.content)
        except SyntaxError as exc:
            unparsed.append(f"{artifact.path}:{exc.msg}")
            continue
        paths |= _module_business_get_paths(tree)
    business = sorted(
        p
        for p in paths
        if p
        and p != "/"
        and not any(p == x or p.startswith(x) for x in _EXCLUDED_BUSINESS_PREFIXES)
    )
    if not business:
        detail = "no non-health GET routes"
        if unparsed:
            detail += f" (unparsed: {', '.join(unparsed)})"
        return False, detail
    return True, f"business GET routes: {', '.join(business)}"


def run_backend_contract_tests(
    backend: Any,
    test_isr: Optional[dict[str, Any]] = None,
) -> tuple[bool, list[ContractTestResult], Any]:
    """
    Run required backend contract tests.

    Returns:
    - overall pass/fail
    - individual test results
    - sample compilation output, if produced
    """

    results: list[ContractTestResult] = []

    try:
        sdk_backend = ensure_sdk_backend(backend)
        manifest = sdk_backend.manifest
    except Exception as exc:
        results.append(
            ContractTestResult(
                name="backend_adapter",
                passed=False,
                message=str(exc),
            )
        )

        return False, results, None

    # ------------------------------------------------------------------
    # Manifest validation
    # ------------------------------------------------------------------

    try:
        manifest_valid = bool(
            manifest.backend_id
            and manifest.name
            and manifest.version
        )

        capability_report = validate_capabilities(manifest.capabilities)

        manifest_passed = manifest_valid and capability_report.valid

        message = ""

        if not manifest_valid:
            message = "Backend manifest is incomplete."
        elif not capability_report.valid:
            message = "Backend capabilities are invalid."

        results.append(
            ContractTestResult(
                name="manifest_valid",
                passed=manifest_passed,
                message=message,
            )
        )

        if not manifest_passed:
            return False, results, None

    except Exception as exc:
        results.append(
            ContractTestResult(
                name="manifest_valid",
                passed=False,
                message=str(exc),
            )
        )

        return False, results, None

    # ------------------------------------------------------------------
    # Minimal ISR compilation
    # ------------------------------------------------------------------

    if test_isr is None:
        test_isr = default_test_isr()

    context = CompilationContext(
        plan=_build_plan(test_isr, manifest),
        isr=test_isr,
        output_directory=".contract",
    )

    sample_output = None

    try:
        sample_output = sdk_backend.compile(context)

        passed = bool(sample_output.artifacts)

        message = ""

        if not passed:
            message = "Backend produced no artifacts."

        results.append(
            ContractTestResult(
                name="compile_minimal_isr",
                passed=passed,
                message=message,
            )
        )

        if not passed:
            return False, results, sample_output

    except Exception as exc:
        results.append(
            ContractTestResult(
                name="compile_minimal_isr",
                passed=False,
                message=str(exc),
            )
        )

        return False, results, None

    # ------------------------------------------------------------------
    # Output validation
    # ------------------------------------------------------------------

    output_report = validate_compilation_output(sample_output)

    results.append(
        ContractTestResult(
            name="output_validation",
            passed=output_report.valid,
            message=(
                ""
                if output_report.valid
                else "Backend output failed validation."
            ),
        )
    )

    # ------------------------------------------------------------------
    # Generated Python sources must parse (fail-closed syntax gate)
    # ------------------------------------------------------------------

    if sample_output is not None:
        parse_ok, parse_detail = _python_sources_parse(sample_output.artifacts)
        results.append(
            ContractTestResult(
                name="sources_parse",
                passed=parse_ok,
                message="" if parse_ok else f"Python source does not parse: {parse_detail}",
            )
        )

        # ------------------------------------------------------------------
        # FastAPI applications must expose business routes — a service that
        # only answers /health has not demonstrated any working capability.
        # ------------------------------------------------------------------

        routes_ok, routes_detail = _business_routes_present(sample_output.artifacts)
        results.append(
            ContractTestResult(
                name="business_routes_present",
                passed=routes_ok,
                message="" if routes_ok else routes_detail,
            )
        )

    # ------------------------------------------------------------------
    # Invalid ISR must fail explicitly
    # ------------------------------------------------------------------

    invalid_isr = default_test_isr()
    invalid_isr.pop("version", None)

    invalid_context = CompilationContext(
        plan=_build_plan(invalid_isr, manifest),
        isr=invalid_isr,
        output_directory=".contract-invalid",
    )

    try:
        sdk_backend.compile(invalid_context)

        results.append(
            ContractTestResult(
                name="invalid_isr_fails_explicitly",
                passed=False,
                message="Backend accepted invalid ISR.",
            )
        )

    except Exception:
        results.append(
            ContractTestResult(
                name="invalid_isr_fails_explicitly",
                passed=True,
                message="Backend rejected invalid ISR.",
            )
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    try:
        health = sdk_backend.health_check()

        passed = health.status != "error"

        results.append(
            ContractTestResult(
                name="health_check",
                passed=passed,
                message=health.message,
            )
        )

    except Exception as exc:
        results.append(
            ContractTestResult(
                name="health_check",
                passed=False,
                message=str(exc),
            )
        )

    all_passed = all(result.passed for result in results)

    return all_passed, results, sample_output


def run_determinism_test(
    backend: Any,
    test_isr: Optional[dict[str, Any]] = None,
) -> DeterminismResult:
    """Verify deterministic backend compilation for identical inputs."""

    sdk_backend = ensure_sdk_backend(backend)

    if test_isr is None:
        test_isr = default_test_isr()

    manifest = sdk_backend.manifest

    try:
        context_one = CompilationContext(
            plan=_build_plan(test_isr, manifest),
            isr=test_isr,
            output_directory=".contract-determinism-1",
        )

        context_two = CompilationContext(
            plan=_build_plan(test_isr, manifest),
            isr=test_isr,
            output_directory=".contract-determinism-2",
        )

        output_one = sdk_backend.compile(context_one)
        output_two = sdk_backend.compile(context_two)

        hashes_one = _hash_output(output_one)
        hashes_two = _hash_output(output_two)

        artifact_count_match = len(output_one.artifacts) == len(output_two.artifacts)
        content_hashes_match = hashes_one == hashes_two

        passed = artifact_count_match and content_hashes_match

        message = ""

        if not artifact_count_match:
            message = "Artifact count differed between compilations."
        elif not content_hashes_match:
            message = "Artifact content hashes differed between compilations."

        return DeterminismResult(
            passed=passed,
            artifact_count_match=artifact_count_match,
            content_hashes_match=content_hashes_match,
            message=message,
        )

    except Exception as exc:
        return DeterminismResult(
            passed=False,
            artifact_count_match=False,
            content_hashes_match=False,
            message=str(exc),
        )