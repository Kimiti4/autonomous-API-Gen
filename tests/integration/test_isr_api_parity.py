"""Execute one ISR-derived HTTP contract, or record an explicit refusal.

Python is checked through the generated ASGI application. Rust, Elixir, Ruby,
and C# are the same plan passed to their compilers. A refusal is the expected
result when the backend cannot implement the contract. It does not establish
backend parity and it does not boot Rails.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from pydantic import ValidationError

from certification.remediation.register import COMPILER_TARGETS, Status, WORK_PACKAGES
from compiler.backends.elixir_phoenix import ElixirPhoenixBackend
from compiler.backends.python_fastapi import PythonFastAPIBackend
from compiler.backends.rust_axum import RustAxumBackend
from compiler.core.capabilities import UnsupportedSemanticsError
from compiler.core.isr_parity import (
    PAYROLL_EMPLOYEE_FIELDS as _EMPLOYEE,
    aspnet_parity_backend,
    assess_contract,
    canonical_payroll_http_contract,
    canonical_payroll_parity_plan,
    durable_database_claims,
    http_contract,
    payroll_parity_operation as _operation,
    ruby_rails_parity_backend,
)
from compiler.core.plan import (
    CompilationPlan,
    Effect,
)
from isr.core.behavior import (
    EffectBehavior,
)


parity_plan = canonical_payroll_parity_plan


def _compilers():
    return (
        PythonFastAPIBackend(),
        RustAxumBackend(),
        ElixirPhoenixBackend(),
        ruby_rails_parity_backend(),
        aspnet_parity_backend(),
    )


_PROBE = r'''
import json, os, sys
os.environ["GENERATED_API_KEY"] = "generated-dev-key"
os.environ["GENERATED_AUTH_SECRET"] = "generated-dev-secret"
from fastapi.testclient import TestClient
from app.main import app
from compiler.core.isr_parity import assess_contract

client = TestClient(app)

def send(method, path, body, headers):
    kwargs = {"headers": headers}
    if body is not None:
        kwargs["json"] = body
    response = client.request(method, path, **kwargs)
    try:
        payload = response.json()
    except Exception:
        payload = None
    return response.status_code, payload

report = assess_contract(send, json.loads(sys.argv[1]))
print(json.dumps(report))
sys.exit(0 if report["ok"] else 1)
'''


def test_python_executes_the_shared_isr_contract_over_http(tmp_path: Path):
    plan = parity_plan()
    contract = http_contract(plan)
    assert contract["create"]["path"] == "/payroll/employees"
    assert contract["read"]["path"] == "/payroll/employees/{employee_id}"
    repo = PythonFastAPIBackend().compile(plan)
    assert durable_database_claims(repo.files) == []
    assert "class InMemoryRepository" in repo.files["app/infrastructure/repositories.py"]
    for path, content in repo.files.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join((str(tmp_path), str(Path(__file__).resolve().parents[2])))
    probe = subprocess.run(
        [sys.executable, "-c", _PROBE, json.dumps(contract)],
        cwd=tmp_path,
        check=False,
        timeout=120,
        capture_output=True,
        text=True,
        env=env,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr
    report = json.loads(probe.stdout)
    assert report["ok"], report["failures"]


def _http_send(base: str):
    def send(method: str, path: str, body: object, headers: dict[str, str]):
        data = None if body is None else json.dumps(body).encode("utf-8")
        request_headers = dict(headers)
        if data is not None:
            request_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(
            base + path, data=data, headers=request_headers, method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = response.read()
                return response.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            return exc.code, json.loads(raw) if raw else None
    return send


def _terminate_process(process: subprocess.Popen) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            check=False, capture_output=True, text=True,
        )
    else:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def test_elixir_executes_the_same_isr_contract_over_http(tmp_path: Path):
    if shutil.which("mix") is None:
        pytest.fail("Elixir mix is required to execute the shared ISR contract")
    plan = parity_plan()
    contract = http_contract(plan)
    repo = ElixirPhoenixBackend().compile(plan)
    assert durable_database_claims(repo.files) == []
    assert "psycopg" not in "\n".join(repo.files.values())
    root = tmp_path / "elixir"
    for path, content in repo.files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    env = os.environ.copy()
    env["GENERATED_API_KEY"] = "generated-dev-key"
    env["GENERATED_AUTH_SECRET"] = "generated-dev-secret"
    log = root / "parity.log"
    with log.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            ["mix", "run", "--no-halt", "-e",
             'server = Esap.Server.start(); File.write!("parity.port", Integer.to_string(server.port)); Process.sleep(:infinity)'],
            cwd=root,
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=env,
        )
    port_file = root / "parity.port"
    try:
        deadline = time.time() + 90
        while not port_file.exists():
            if process.poll() is not None or time.time() > deadline:
                pytest.fail(log.read_text(encoding="utf-8", errors="replace")[-4000:])
            time.sleep(0.2)
        report = assess_contract(_http_send(f"http://127.0.0.1:{port_file.read_text(encoding='utf-8').strip()}"), contract)
    finally:
        _terminate_process(process)
    assert report["ok"], report["failures"]



def _cargo_environment() -> dict[str, str]:
    """Include the MSVC linker when Build Tools are installed but not on PATH."""
    env = os.environ.copy()
    if shutil.which("link", path=env.get("PATH")):
        return env
    vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / (
        "Microsoft Visual Studio/Installer/vswhere.exe"
    )
    if not vswhere.is_file():
        return env
    install = subprocess.run(
        [
            str(vswhere), "-latest", "-products", "*",
            "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
            "-property", "installationPath",
        ],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    script = Path(install) / "VC/Auxiliary/Build/vcvars64.bat"
    if not script.is_file():
        return env
    captured = subprocess.run(
        f'cmd.exe /s /c ""{script}" >nul && set"',
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    for line in captured.stdout.splitlines():
        key, separator, value = line.partition("=")
        if separator and key:
            env[key] = value
    return env


def _has_windows_sdk_libraries(env: dict[str, str]) -> bool:
    if sys.platform != "win32":
        return True
    lib_paths = env.get("LIB", "").split(os.pathsep)
    return any((Path(p) / "kernel32.lib").is_file() for p in lib_paths if p)


def test_rust_axum_routes_use_axum_parameter_syntax():
    repo = RustAxumBackend().compile(parity_plan())
    main = repo.files["src/main.rs"]
    assert (
        '.route("/payroll/employees/:employee_id", get(read_record).delete(delete_record))'
        in main
    )
    assert "/payroll/employees/{employee_id}" in repo.files["openapi.json"]


def test_rust_executes_the_same_isr_contract_over_http(tmp_path: Path):
    if shutil.which("cargo") is None:
        pytest.fail("cargo is required to execute the shared ISR contract")
    env = _cargo_environment()
    if not _has_windows_sdk_libraries(env):
        pytest.skip(
            "Windows SDK libraries (kernel32.lib) are not installed on this host; "
            "Rust Axum parity execution requires a supported Windows SDK or CI runner"
        )
    plan = parity_plan()
    contract = http_contract(plan)
    repo = RustAxumBackend().compile(plan)
    assert durable_database_claims(repo.files) == []
    root = tmp_path / "rust"
    for path, content in repo.files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    env["GENERATED_API_KEY"] = "generated-dev-key"
    env["GENERATED_AUTH_SECRET"] = "generated-dev-secret"
    log = root / "parity.log"
    with log.open("w", encoding="utf-8") as handle:
        process = subprocess.Popen(
            ["cargo", "run", "--quiet"],
            cwd=root,
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=env,
        )
    port_file = root / "parity.port"
    try:
        deadline = time.time() + 300
        while not port_file.exists():
            if process.poll() is not None or time.time() > deadline:
                pytest.fail(log.read_text(encoding="utf-8", errors="replace")[-4000:])
            time.sleep(0.5)
        report = assess_contract(
            _http_send(f"http://127.0.0.1:{port_file.read_text(encoding='utf-8').strip()}"),
            contract,
        )
    finally:
        _terminate_process(process)
    assert report["ok"], report["failures"]


def test_elixir_refuses_declared_methods_outside_the_slice():
    plan = parity_plan()
    update = _operation(
        "api:replace", "replaceEmployee", "PUT",
        "/payroll/employees/{employee_id}", "employee.read",
        request=_EMPLOYEE, response=_EMPLOYEE,
    )
    plan = plan.model_copy(update={"apis": [*plan.apis, update]})
    with pytest.raises(UnsupportedSemanticsError, match="does not implement PUT"):
        ElixirPhoenixBackend().compile(plan)


def test_backends_without_the_contract_refuse_the_same_plan():
    plan = parity_plan()
    http_contract(plan)
    for backend in _compilers():
        if backend.name in {"python-fastapi", "elixir-phoenix", "rust-axum"}:
            continue
        with pytest.raises(UnsupportedSemanticsError, match="api_contracts"):
            backend.compile(plan)


def test_durable_persistence_is_refused_until_a_repository_exists():
    plan = parity_plan()
    service = plan.services[0]
    model = service.data_models[0]
    durable = model.model_copy(update={
        "behavior": model.behavior.model_copy(update={"storage": "durable"}),
    })
    plan = plan.model_copy(update={
        "services": [service.model_copy(update={"data_models": [durable]})],
    })
    for backend in _compilers():
        with pytest.raises(UnsupportedSemanticsError, match="durable_persistence"):
            backend.compile(plan)


def test_unsupported_effect_is_refused_by_every_parity_backend():
    plan = parity_plan().model_copy(update={"effects": [Effect(
        id="effect:transfer",
        name="Transfer",
        behavior=EffectBehavior(
            effect_kind="bank_transfer",
            idempotent=True,
            idempotency_key_required=True,
        ),
    )]})
    for backend in _compilers():
        with pytest.raises(UnsupportedSemanticsError, match="effect_semantics"):
            backend.compile(plan)


def test_parity_gate_does_not_promote_backends_or_boot_rails():
    package = next(item for item in WORK_PACKAGES if item.id == "W07")
    assert package.status is Status.IN_PROGRESS
    targets = {item.target_id: item for item in COMPILER_TARGETS}
    for target_id in ("python-fastapi", "rust-axum", "elixir-phoenix", "ruby-rails", "aspnet-core"):
        assert targets[target_id].production_ready is False
    assert "Rails process was not booted" in targets["ruby-rails"].note
    assert "ISR-derived API contract" in targets["ruby-rails"].note
    assert "ISR-derived API contract" in targets["aspnet-core"].note


def test_canonical_payroll_fixture_is_genuinely_immutable():
    """Verify the canonical fixture isolation and mutability contracts.

    Contract 1: CompilationPlan and constituent models are frozen Pydantic models.
    Attribute reassignment must raise pydantic.ValidationError, preventing in-place
    mutation of model metadata.

    Contract 2: canonical_payroll_parity_plan() generates a fresh, isolated graph
    per call. Even if a caller mutates an internal list on an existing instance,
    subsequent calls return a clean, unpolluted canonical graph.

    Contract 3: canonical_payroll_http_contract() defensively deep-copies the
    projected contract dict on every call so nested dictionary or list modifications
    cannot leak into subsequent test executions.
    """
    plan = canonical_payroll_parity_plan()
    with pytest.raises(ValidationError):
        plan.plan_id = "mutated"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        plan.services = []  # type: ignore[misc]
    with pytest.raises(ValidationError):
        plan.services[0].name = "mutated"  # type: ignore[misc]

    # Contract 2: fresh graph per call isolates list mutations
    plan1 = canonical_payroll_parity_plan()
    plan1.services.append(None)  # type: ignore[arg-type]
    plan1.apis.append(None)  # type: ignore[arg-type]

    plan2 = canonical_payroll_parity_plan()
    assert None not in plan2.services
    assert None not in plan2.apis
    assert len(plan2.services) == 1
    assert len(plan2.apis) == 3

    # Contract 3: defensive deep copy isolates contract dictionary modifications
    contract1 = canonical_payroll_http_contract()
    contract1["create"]["sample_body"]["employee_id"] = "TAMPERED"
    contract1["paths"].append("/injected/route")
    contract1["create"]["allow_roles"].append("injected_role")

    contract2 = canonical_payroll_http_contract()
    assert contract2["create"]["sample_body"]["employee_id"] != "TAMPERED"
    assert "/injected/route" not in contract2["paths"]
    assert "injected_role" not in contract2["create"]["allow_roles"]
