"""Phase-31 -- FastAPI backend field-order defect regression.

These tests close the loop on the latent defect the corpus generator surfaced:
the FastAPI backend lowered ``DataModelSpec.fields`` into Python function
signatures *in ISR order*, producing a ``SyntaxError`` whenever an optional
field preceded a required one. The fix reorders parameters (required-first)
at emission. These tests:

  * reproduce the defect with an adversarial corpus (``OPTIONAL_FIRST``) and
    assert every generated file still compiles -- failing loudly if the fix
    regresses;
  * guard against a biased corpus by asserting ``OPTIONAL_FIRST`` actually
    triggers the ordering the fix defends against;
  * pin the default (``REQUIRED_FIRST``) as a no-trigger baseline.
"""
from __future__ import annotations

import shutil

import pytest

from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend
from tiannara.application.compiler.go_hexagonal_backend import GoHexagonalBackend
from tiannara.application.harness.calibration.corpus import load_corpus
from tiannara.application.harness.calibration.generator import (
    CorpusSpec,
    FieldOrder,
    SystemModelCorpusGenerator,
    generate_corpus,
)
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    DataModelSpec,
    FieldSpec,
    RequirementsReference,
    SecurityModel,
    SystemModel,
)


def _compile_all_files(result) -> int:
    """Return count of SyntaxErrors found across all generated .py files."""
    errors = 0
    for path, src in result.files.items():
        if path.endswith(".py"):
            try:
                compile(src, path, "exec")
            except SyntaxError:
                errors += 1
    return errors


def test_fastapi_backend_compiles_optional_first_models():
    """After the fix, an adversarial (optional-before-required) corpus compiles."""
    models = SystemModelCorpusGenerator(
        CorpusSpec(size=8, seed=0, field_order=FieldOrder.OPTIONAL_FIRST)
    ).generate()
    triggered = any(
        any((not f.required) and any(g.required for g in dm.fields[i + 1:])
            for i, f in enumerate(dm.fields))
        for m in models for dm in m.data_models
    )
    assert triggered, "OPTIONAL_FIRST must produce at least one opt-before-req model"

    backend = FastAPIHexagonalBackend()
    for model in models:
        result = backend.generate(model)
        assert _compile_all_files(result) == 0


def test_fix_is_narrowly_local_to_service_signatures():
    """A hand-built optional-before-required ISR must compile post-fix."""
    model = SystemModel(
        system_name="Order System",
        requirements_ref=RequirementsReference(graph_id="corpus-order", graph_hash="0" * 16),
        data_models=[
            DataModelSpec(
                id="dm-order",
                name="order",
                owning_service_id="svc-order",
                fields=[
                    FieldSpec(name="note", type=AbstractFieldType.TEXT, required=False),
                    FieldSpec(name="total", type=AbstractFieldType.DECIMAL, required=True),
                ],
            )
        ],
        security=SecurityModel(),
    )
    result = FastAPIHexagonalBackend().generate(model)
    services_src = next(
        v for k, v in result.files.items() if k.endswith("application/services.py")
    )
    compile(services_src, "services.py", "exec")  # raises SyntaxError if fix absent
    create_sig = next(l.strip() for l in services_src.splitlines() if "def create" in l)
    assert "total: float" in create_sig and "note: Optional[str]" in create_sig
    assert create_sig.index("total") < create_sig.index("note")


def test_optional_first_is_a_real_defect_trigger():
    """The adversarial ordering is a faithful regression signal.

    Independently compiles the *ISR-ordered* parameter list (what the backend
    used to emit verbatim) for the first model whose field order contains an
    optional-before-required sequence, and asserts it raises ``SyntaxError``.
    Proves the trigger is a real defect, not a vacuous test.
    """
    models = SystemModelCorpusGenerator(
        CorpusSpec(size=16, seed=0, field_order=FieldOrder.OPTIONAL_FIRST)
    ).generate()
    found = False
    for model in models:
        dm = model.data_models[0]
        fields = [f for f in dm.fields if f.type is not AbstractFieldType.IDENTIFIER]
        if not any((not f.required) and any(g.required for g in fields[i + 1:])
                   for i, f in enumerate(fields)):
            continue
        params = ", ".join(
            f"{f.name}: " + ("Optional[str]" if not f.required else "str")
            + (" = None" if not f.required else "")
            for f in fields
        )
        sig = f"def create(self, {params}) -> Order:"
        with pytest.raises(SyntaxError):
            compile(sig, "adversarial", "exec")
        found = True
        break
    assert found, "OPTIONAL_FIRST corpus must contain a triggerable (opt-before-req) model"


def test_required_first_default_never_triggers_a_defect():
    """The canonical default ordering must contain no opt-before-req sequences."""
    models = generate_corpus(8, seed=5)
    for m in models:
        for dm in m.data_models:
            seen_optional = False
            for f in dm.fields:
                assert not (seen_optional and f.required), \
                    f"required field after optional in {dm.name}"
                if not f.required:
                    seen_optional = True
    for model in models:
        for backend in (FastAPIHexagonalBackend(), GoHexagonalBackend()):
            result = backend.generate(model)
            assert _compile_all_files(result) == 0


def test_generate_corpus_cli_writes_optional_first_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda *_a, **_k: None)
    from tiannara.interfaces.cli.main import main

    out = tmp_path / "opt-first.json"
    rc = main(["generate-corpus", "--size", "6", "--seed", "0",
               "--field-order", "optional_first", "--out", str(out)])
    assert rc == 0
    loaded = load_corpus(out)
    assert len(loaded) == 6
    assert any(
        any((not f.required) and any(g.required for g in dm.fields[i + 1:])
            for i, f in enumerate(dm.fields))
        for m in loaded for dm in m.data_models
    )
