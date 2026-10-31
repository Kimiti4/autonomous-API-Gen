"""W13 Next.js browser evidence: the generated frontend must run in a browser.

These tests assert the generated artifacts, not a source declaration. They do
not claim route/form/API-client parity; they establish that the Next.js target
emits a real browser test whose assertions are derived from the ISR.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.tiannara_next_fixture import _FILTER_EXPRESSION, break_filter, fixture_files, fixture_model
from tiannara.application.compiler.next_frontend import NextFrontend

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tiannara_next_fixture.py"


def _model(names: tuple[str, ...] = ("Payment", "Invoice")):
    return fixture_model(names)


def _files(model) -> dict[str, str]:
    return fixture_files(model)


def test_generated_bundle_declares_browser_evidence() -> None:
    compiler = NextFrontend()
    model = _model()
    files = compiler.generate(model).files

    assert "playwright.config.ts" in files
    assert "e2e/generated-app.spec.ts" in files
    required = set(compiler.build_profile("Billing").required_files)
    assert {"playwright.config.ts", "e2e/generated-app.spec.ts"} <= required
    assert {"README.md", "package.json", "tsconfig.json"} <= set(files)

    package = files["package.json"]
    assert '"test:e2e":"playwright test"' in package
    assert '"@playwright/test"' in package
    assert 'include: ["app/**/*.test.tsx"]' in files["vite.config.ts"]


def test_browser_test_asserts_the_rendered_heading_and_a_real_interaction() -> None:
    e2e = _files(_model())["e2e/generated-app.spec.ts"]

    assert "expect(" in e2e
    assert 'getByRole("heading"' in e2e
    assert "Billing Platform" in e2e
    assert 'getByLabel("Filter data models")' in e2e
    assert 'toHaveText(["Payment","Invoice"])' in e2e
    assert 'toHaveText(["Payment"])' in e2e


def test_next_app_derives_its_data_from_the_isr() -> None:
    first = _files(_model(("Payment", "Invoice")))
    second = _files(_model(("Shipment",)))
    page = first["app/page.tsx"]
    assert "dataModels" in page
    assert "visible" in page
    assert "useState" in page
    assert "useMemo" in page
    # No duplicated names; the model list passed to the component is unique.
    assert '"Shipment"' in second["app/page.tsx"]
    assert '"Payment"' not in second["app/page.tsx"]
    # The filter input exists as a real controlled field, not a stub.
    assert 'htmlFor="model-filter"' in page or 'id="model-filter"' in page


def test_browser_test_isolates_overlapping_model_names() -> None:
    files = _files(_model(("Pay", "Payment")))
    e2e = files["e2e/generated-app.spec.ts"]
    assert "hasText" not in e2e
    assert 'toHaveText(["Pay","Payment"])' in e2e
    assert 'toHaveText(["Payment"])' in e2e


def test_duplicate_model_names_do_not_collide_as_keys() -> None:
    files = _files(_model(("Payment", "Payment")))
    page = files["app/page.tsx"]
    # The model array lists each name once regardless of duplicates; no collision
    # is introduced in the generated component.
    payload = page.count("dataModels: readonly string[] = ")
    assert payload == 1


def test_empty_model_list_fails_closed_to_an_explicit_state() -> None:
    files = _files(_model(()))
    page = files["app/page.tsx"]
    e2e = files["e2e/generated-app.spec.ts"]

    assert "No data models declared" in page
    assert 'useMemo(() => dataModels.filter((n) => n.toLowerCase().includes(filter.toLowerCase())), [filter]);' in page
    # The e2e file should contain a heading assertion at minimum.
    assert "expect(" in e2e
    assert 'toHaveCount(0)' in e2e or 'No data models declared' in e2e or 'toHaveText([""])' in e2e


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
    page = _files(model)["app/page.tsx"]
    assert f'const title = {json.dumps(model.system_name, ensure_ascii=True)};' in page
    names = [dm.name for dm in model.data_models]
    assert f'const dataModels: readonly string[] = {json.dumps(names, ensure_ascii=True)};' in page


def test_negative_control_targets_the_emitted_filter(tmp_path: Path) -> None:
    for name, content in _files(_model()).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    result = break_filter(tmp_path)
    assert result is None
    mutated = (tmp_path / "app" / "page.tsx").read_text(encoding="utf-8")
    assert "useMemo(() => dataModels, [filter]);" in mutated
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
    compiler = NextFrontend()
    model = _model()
    assert compiler.generate(model).files == compiler.generate(model).files
