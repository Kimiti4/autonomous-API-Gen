"""Generate a deterministic tiannara React bundle for browser evidence.

The generated package is exercised by ``tests/test_tiannara_react_browser_evidence.py``
and by the ``tiannara-react-browser-evidence`` workflow, so both use the same
fixture instead of drifting apart.

Usage:
    python scripts/tiannara_react_fixture.py <target-dir> [name,name,...]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tiannara.application.compiler.react_frontend import ReactFrontend
from tiannara.domain.models.system_model import (
    AbstractFieldType,
    DataModelSpec,
    FieldSpec,
    RequirementsReference,
    SystemModel,
)

DEFAULT_NAMES: tuple[str, ...] = ("Payment", "Invoice")
DEFAULT_SYSTEM_NAME = "Billing Platform"


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
    return ReactFrontend().generate(model or fixture_model()).files


def write_fixture(target: Path, names: tuple[str, ...] = DEFAULT_NAMES) -> int:
    files = fixture_files(fixture_model(names))
    for name, content in files.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return len(files)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    target = Path(argv[1])
    names = tuple(argv[2].split(",")) if len(argv) > 2 and argv[2] else ()
    written = write_fixture(target, names)
    print(f"wrote {written} files to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
