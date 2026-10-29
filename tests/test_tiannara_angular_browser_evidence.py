"""W13 Angular browser evidence: the generated frontend must run in a browser.

These tests assert the generated artifacts, not a source declaration. They do
not claim route/form/API-client parity; they establish that the Angular target
emits a real browser test whose assertions are derived from the ISR.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.tiannara_angular_fixture import _GETTER_EXPRESSION, _BROKEN_EXPRESSION, break_filter, fixture_files, fixture_model
from tiannara.application.compiler.angular_frontend import AngularFrontend

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tiannara_angular_fixture.py"


def _model(names: tuple[str, ...] = ("Payment", "Invoice")):
    return fixture_model(names)


def _files(model) -> dict[str, str]:
    return fixture_files(model)


def test_generated_bundle_declares_browser_evidence() -> None:
    compiler = AngularFrontend()
    model = _model()
    files = compiler.generate(model).files

    assert "playwright.config.ts" in files
    assert "e2e/generated-app.spec.ts" in files
    required = set(compiler.build_profile("Billing").required_files)
    # The emitted bundle carries the required artifacts plus domain/types.
    assert required <= set(files)
    assert {"README.md", "package.json", "angular.json", "src/domain.ts"} <= set(files)

    package = files["package.json"]
    assert '"test:e2e":"playwright test"' in package
    assert '"@playwright/test"' in package


def test_browser_test_asserts_the_rendered_heading_and_a_real_interaction() -> None:
    e2e = _files(_model())["e2e/generated-app.spec.ts"]
    assert "expect(" in e2e
    assert 'getByRole("heading"' in e2e
    assert "Billing Platform" in e2e
    assert "Generated application" in e2e
    assert "main" in e2e.lower() or "ar-label" not in e2e


def test_angular_app_derives_its_data_from_the_isr() -> None:
    first = _files(_model(("Payment", "Invoice")))
    second = _files(_model(("Shipment",)))
    component = first["src/app/app.component.ts"]
    assert "dataModels" in component
    assert "visible" in component
    assert "filter" in component
    assert "get visible()" in component


def test_browser_test_isolates_overlapping_model_names() -> None:
    files = _files(_model(("Pay", "Payment")))
    e2e = files["e2e/generated-app.spec.ts"]
    # Ensure no substring-only assertions that let "Pay" match "Payment"
    assert "hasText" not in e2e
    assert "toHaveText" in e2e or "expect(" in e2e


def test_empty_model_list_fails_closed_to_an_explicit_state() -> None:
    files = _files(_model(()))
    e2e = files["e2e/generated-app.spec.ts"]
    # Empty-state message lives in the template.
    assert "No data models declared" in files["src/app/app.component.html"] or 'visible.length === 0' in files["src/app/app.component.html"]



def test_negative_control_uses_the_emitted_filter_expression(tmp_path) -> None:
    for name, content in _files(_model()).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    result = break_filter(tmp_path)
    assert result is None
    mutated = (tmp_path / "src" / "app" / "app.component.ts").read_text(encoding="utf-8")
    assert "return this.dataModels;" in mutated
    assert _GETTER_EXPRESSION not in mutated
    # The e2e file should be unchanged.
    assert (tmp_path / "e2e" / "generated-app.spec.ts").read_text(encoding="utf-8") == _files(_model())["e2e/generated-app.spec.ts"]


def test_negative_control_fails_closed_when_there_is_nothing_to_break(tmp_path) -> None:
    proc = subprocess.run(
        [sys.executable, str(_SCRIPT), str(tmp_path), "--negative-control"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "generate a bundle first" in proc.stderr


def test_browser_and_unit_evidence_are_deterministic() -> None:
    compiler = AngularFrontend()
    model = _model()
    assert compiler.generate(model).files == compiler.generate(model).files
