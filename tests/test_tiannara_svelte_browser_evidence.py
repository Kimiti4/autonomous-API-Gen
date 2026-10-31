"""W13 Svelte browser evidence: the generated frontend must run in a browser.

These tests assert the generated artifacts, not a source declaration. They do
not claim route/form/API-client parity; they establish that the Svelte target
emits a real browser test whose assertions are derived from the ISR.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.tiannara_svelte_fixture import _FILTER_EXPRESSION, break_filter, fixture_files, fixture_model
from tiannara.application.compiler.svelte_frontend import SvelteFrontend

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tiannara_svelte_fixture.py"


def _model(names: tuple[str, ...] = ("Payment", "Invoice")):
    return fixture_model(names)


def _files(model) -> dict[str, str]:
    return fixture_files(model)


def test_generated_bundle_declares_browser_evidence() -> None:
    compiler = SvelteFrontend()
    model = _model()
    files = compiler.generate(model).files

    assert "playwright.config.ts" in files
    assert "e2e/generated-app.spec.ts" in files
    required = set(compiler.build_profile("Billing Platform").required_files)
    assert {"playwright.config.ts", "e2e/generated-app.spec.ts", "tsconfig.json"} <= required
    assert set(files) == required | {"README.md"}

    package = files["package.json"]
    assert '"test:e2e":"playwright test"' in package
    assert '"@playwright/test"' in package
    assert '"build":"svelte-check --tsconfig ./tsconfig.json && vite build"' in package
    assert 'include: ["src/**/*.test.ts"]' in files["vite.config.ts"]
    assert "src/App.svelte" in files


def test_browser_test_asserts_the_rendered_heading_and_a_real_interaction() -> None:
    e2e = _files(_model())["e2e/generated-app.spec.ts"]

    assert "expect(" in e2e
    assert 'getByRole("heading"' in e2e
    assert "Billing Platform" in e2e
    assert 'getByLabel("Filter data models")' in e2e
    assert 'toHaveText(["Payment","Invoice"])' in e2e
    assert 'toHaveText(["Payment"])' in e2e
    assert "async () => {}" not in e2e


def test_svelte_app_derives_its_model_list_from_the_isr() -> None:
    first = _files(_model(("Payment", "Invoice")))
    second = _files(_model(("Shipment",)))

    app = first["src/App.svelte"]
    assert "Payment" in app
    assert "Invoice" in app
    assert "Shipment" not in app
    assert "Shipment" in second["src/App.svelte"]
    assert "Payment" not in second["src/App.svelte"]
    # Svelte 5 runes and a real two-way binding, not a static render.
    assert "$state" in app
    assert "$derived" in app
    assert "bind:value={filter}" in app


def test_browser_test_isolates_overlapping_model_names() -> None:
    files = _files(_model(("Pay", "Payment")))
    e2e = files["e2e/generated-app.spec.ts"]

    assert "hasText" not in e2e
    assert 'toHaveText(["Pay","Payment"])' in e2e
    assert 'toHaveText(["Payment"])' in e2e


def test_duplicate_model_names_do_not_collide_as_keys() -> None:
    files = _files(_model(("Payment", "Payment")))

    assert files["src/App.svelte"].count('"Payment"') == 1
    assert 'toHaveText(["Payment","Payment"])' not in files["e2e/generated-app.spec.ts"]


def test_empty_model_list_fails_closed_to_an_explicit_state() -> None:
    files = _files(_model(()))
    e2e = files["e2e/generated-app.spec.ts"]

    assert "No data models declared" in files["src/App.svelte"]
    assert "No data models declared" in files["src/App.test.ts"]
    assert "No data models declared" in e2e
    assert 'toHaveCount(0)' in e2e
    assert "expect(" in e2e
    assert "async () => {}" not in e2e


def test_ci_fixture_is_the_isr_generation_run_through_the_cli(tmp_path: Path) -> None:
    """The bundle CI tests is byte-identical to what the compiler emits from ISR."""
    subprocess.run(
        [sys.executable, str(_SCRIPT), str(tmp_path), "Payment,Invoice"],
        check=True,
        capture_output=True,
        text=True,
    )
    expected = fixture_files(fixture_model(("Payment", "Invoice")))
    read_back = {name: (tmp_path / name).read_text(encoding="utf-8") for name in expected}
    assert read_back == expected


def test_generated_content_is_the_isr_made_literal() -> None:
    model = _model(("Payment", "Invoice", "Transfer"))
    app = _files(model)["src/App.svelte"]

    names = [dm.name for dm in model.data_models]
    assert f"const dataModels: readonly string[] = {json.dumps(names, ensure_ascii=True)};" in app
    assert f"const title = {json.dumps(model.system_name, ensure_ascii=True)};" in app
    unit = _files(model)["src/App.test.ts"]
    for name in names:
        assert f"toContain({json.dumps(name, ensure_ascii=True)})" in unit


def test_isr_value_cannot_terminate_the_script_element() -> None:
    """A system name is data: it must not be able to close the Svelte script block."""
    hostile = "Evil </script><script>alert(1)</script>"
    app = _files(fixture_model(("Payment",), system_name=hostile))["src/App.svelte"]

    script = app.split("</script>", 1)[0]
    assert "alert(1)" in script
    assert app.count("</script>") == 1
    assert "<\\/script>" in script


def test_negative_control_targets_the_emitted_filter(tmp_path: Path) -> None:
    for name, content in _files(_model()).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    break_filter(tmp_path)

    mutated = (tmp_path / "src" / "App.svelte").read_text(encoding="utf-8")
    assert "dataModels.slice()" in mutated
    assert _FILTER_EXPRESSION not in mutated
    assert (tmp_path / "e2e" / "generated-app.spec.ts").read_text(encoding="utf-8") == _files(_model())["e2e/generated-app.spec.ts"]


def test_negative_control_fails_closed_when_there_is_nothing_to_break(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(tmp_path), "--negative-control"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "generate a bundle first" in proc.stderr


def test_browser_and_unit_evidence_are_deterministic() -> None:
    compiler = SvelteFrontend()
    model = _model()
    assert compiler.generate(model).files == compiler.generate(model).files
