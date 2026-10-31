"""W13 Nuxt browser evidence."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
from scripts.tiannara_nuxt_fixture import FILTER, BROKEN, break_filter, fixture_files, fixture_model
from tiannara.application.compiler.nuxt_frontend import NuxtFrontend
_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tiannara_nuxt_fixture.py"

def test_bundle_declares_evidence():
    m = fixture_model()
    files = NuxtFrontend().generate(m).files
    assert "playwright.config.ts" in files
    assert "e2e/generated-app.spec.ts" in files
    required = set(NuxtFrontend().build_profile("X").required_files)
    assert required <= set(files)
    assert '"test:e2e":"playwright test"' in files["package.json"]
    assert 'include: ["tests/**/*.test.ts"]' in files.get("vitest.config.ts", "")

def test_negative_control_fails_closed(tmp_path):
    for n, c in fixture_files().items():
        p = tmp_path / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(c, encoding="utf-8")
    break_filter(tmp_path)
    assert BROKEN in open(tmp_path / "app/app.vue", encoding="utf-8").read()
    assert FILTER not in open(tmp_path / "app/app.vue", encoding="utf-8").read()

def test_negative_control_fails_when_nothing_to_break(tmp_path):
    proc = subprocess.run([sys.executable, str(_SCRIPT), str(tmp_path), "--negative-control"], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "generate a bundle first" in proc.stderr

def test_isr_filter_derived(tmp_path):
    for n, c in fixture_files(fixture_model(("Pay", "Payment"))).items():
        p = tmp_path / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(c, encoding="utf-8")
    s = open(tmp_path / "app/app.vue", encoding="utf-8").read()
    assert FILTER in s
