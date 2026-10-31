"""Generate a deterministic tiannara Angular bundle for browser evidence.

The generated package is exercised by ``tests/test_tiannara_angular_browser_evidence.py``
and by the ``tiannara-angular-browser-evidence`` workflow, so both use the same
fixture instead of drifting apart. This is the Angular target's own fixture and
assertions; it shares no generated source with React, Vue or Svelte.

Usage:
    python scripts/tiannara_angular_fixture.py <target-dir> [name,name,...]
        Write the fixture bundle (empty model list when names are omitted).

    python scripts/tiannara_angular_fixture.py <target-dir> --negative-control
        Deliberately break filtering in an already-generated bundle. The
        bundle's own browser test must then fail; the workflow uses this to
        prove that passed evidence has teeth.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tiannara.application.compiler.angular_frontend import AngularFrontend
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    DataModelSpec,
    FieldSpec,
    RequirementsReference,
    SystemModel,
)

DEFAULT_NAMES: tuple[str, ...] = ("Payment", "Invoice")
DEFAULT_SYSTEM_NAME = "Billing Platform"
_FILTER_EXPRESSIONS = (
    '["dataModels", "filter", "visible"]',  # get visible in template via *ngFor/@IF data bound
)
# The dependency-string filter expressions looked for in the emitted app module and
# component; angular templates render text, never executable markup, so an ISR value
# cannot terminate an HTML element. The negative control targets the .component.ts
# getter expression, not the template.
_GETTER_EXPRESSION = 'return this.dataModels.filter((n) => n.toLowerCase().includes(this.filter.toLowerCase()));'
_BROKEN_EXPRESSION = 'return this.dataModels;'


def fixture_model(
    names: tuple[str, ...] = DEFAULT_NAMES,
    system_name: str = DEFAULT_SYSTEM_NAME,
) -> SystemModel:
    return SystemModel(
        system_name=system_name,
        requirements_ref=RequirementsReference(graph_id="graph-1", graph_hash="hash-1"),
        data_models=[
            DataModelSpec(
                id=f"dm_{index}_{name.lower()}",
                name=name,
                owning_service_id="svc",
                fields=[FieldSpec(name="amount", type=AbstractFieldType.DECIMAL)],
            )
            for index, name in enumerate(names)
        ],
    )


def fixture_files(model: SystemModel | None = None) -> dict[str, str]:
    return AngularFrontend().generate(model or fixture_model()).files


def break_filter(target: Path) -> None:
    """Deliberately break filtering in a generated bundle.

    Negative control: the component's `get visible()` getter filters a real
    array, so a bundle whose filtering is removed must return the whole
    list and its own browser test will assert an exact subset. Fails loudly when
    the emitted expression has drifted, so the control can never silently stop
    being a control.
    """
    comp_path = target / "src" / "app" / "app.component.ts"
    if not comp_path.exists():
        raise RuntimeError(f"{comp_path} does not exist; generate a bundle first")
    source = comp_path.read_text(encoding="utf-8")
    if _GETTER_EXPRESSION not in source:
        raise RuntimeError(
            "the emitted getter expression has drifted; the negative control targets:\n"
            f"  {_GETTER_EXPRESSION}\n"
            "refusing to fake a control — update the control instead"
        )
    comp_path.write_text(source.replace(_GETTER_EXPRESSION, _BROKEN_EXPRESSION), encoding="utf-8")


def write_fixture(target: Path, names: tuple[str, ...] = DEFAULT_NAMES) -> int:
    files = fixture_files(fixture_model(names))
    for name, content in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return len(files)


def main(argv: list[str]) -> int:
    args = [arg for arg in argv[1:] if not arg.startswith("--")]
    flags = {arg for arg in argv[1:] if arg.startswith("--")}
    if len(args) < 1:
        print(__doc__)
        return 2
    target = Path(args[0])
    if "--negative-control" in flags:
        if len(args) > 1:
            print("--negative-control mutates an existing bundle and takes no names", file=sys.stderr)
            return 2
        break_filter(target)
        print(f"broke the getter in {target}; its browser test must now fail")
        return 0
    names = tuple(args[1].split(",")) if len(args) > 1 and args[1] else ()
    written = write_fixture(target, names)
    print(f"wrote {written} files to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
