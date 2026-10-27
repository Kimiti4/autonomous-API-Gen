"""W13 React browser evidence: the generated frontend must run in a browser.

These tests assert the generated artifacts, not a source declaration. They do
not claim route/form/API-client parity; they establish that the React target
emits a real browser test whose assertions are derived from the ISR.
"""

from __future__ import annotations

from scripts.tiannara_react_fixture import fixture_files, fixture_model
from tiannara.application.compiler.react_frontend import ReactFrontend


def _model(names: tuple[str, ...] = ("Payment", "Invoice")):
    return fixture_model(names)


def _files(model) -> dict[str, str]:
    return fixture_files(model)


def test_generated_bundle_declares_browser_evidence() -> None:
    compiler = ReactFrontend()
    model = _model()
    files = compiler.generate(model).files

    assert "playwright.config.ts" in files
    assert "e2e/generated-app.spec.ts" in files
    required = set(compiler.build_profile("Billing Platform").required_files)
    assert {"playwright.config.ts", "e2e/generated-app.spec.ts"} <= required
    assert set(files) == required | {"src/domain.ts", "README.md"}

    package = files["package.json"]
    assert '"test:e2e":"playwright test"' in package
    assert '"@playwright/test"' in package
    assert 'include: ["src/**/*.test.tsx"]' in files["vite.config.ts"]


def test_browser_test_asserts_the_rendered_heading_and_a_real_interaction() -> None:
    files = _files(_model())
    e2e = files["e2e/generated-app.spec.ts"]

    assert "expect(" in e2e
    assert 'getByRole("heading"' in e2e
    assert "Billing Platform" in e2e
    assert 'getByLabel("Filter data models")' in e2e
    assert 'toHaveText(["Payment","Invoice"])' in e2e
    assert 'toHaveText(["Payment"])' in e2e
    assert "async () => {}" not in e2e


def test_generated_app_derives_its_model_list_from_the_isr() -> None:
    first = _files(_model(("Payment", "Invoice")))
    second = _files(_model(("Shipment",)))

    assert "Payment" in first["src/App.tsx"]
    assert "Invoice" in first["src/App.tsx"]
    assert "Shipment" not in first["src/App.tsx"]
    assert "Shipment" in second["src/App.tsx"]
    assert "Payment" not in second["src/App.tsx"]
    assert "Filter data models" in first["src/App.tsx"]


def test_browser_test_isolates_overlapping_model_names() -> None:
    """A shorter name must not be satisfied by a longer one, and vice versa."""
    files = _files(_model(("Pay", "Payment")))
    e2e = files["e2e/generated-app.spec.ts"]

    assert '"Pay"' in files["src/App.tsx"]
    assert "hasText" not in e2e
    assert 'toHaveText(["Pay","Payment"])' in e2e
    assert 'toHaveText(["Payment"])' in e2e


def test_duplicate_model_names_do_not_collide_as_list_keys() -> None:
    files = _files(_model(("Payment", "Payment")))

    assert files["src/App.tsx"].count('"Payment"') == 1
    assert 'toHaveText(["Payment","Payment"])' not in files["e2e/generated-app.spec.ts"]


def test_empty_model_list_fails_closed_to_an_explicit_state() -> None:
    files = _files(_model(()))
    e2e = files["e2e/generated-app.spec.ts"]

    assert "No data models declared" in files["src/App.tsx"]
    assert "No data models declared" in files["src/App.test.tsx"]
    assert "No data models declared" in e2e
    assert "expect(" in e2e
    assert "async () => {}" not in e2e


def test_browser_and_unit_evidence_are_deterministic() -> None:
    compiler = ReactFrontend()
    model = _model()
    assert compiler.generate(model).files == compiler.generate(model).files
