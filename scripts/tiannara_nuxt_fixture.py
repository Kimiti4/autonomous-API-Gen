"""Generate a deterministic tiannara Nuxt bundle for browser evidence."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tiannara.application.compiler.nuxt_frontend import NuxtFrontend
from tiannara.domain.models.system_model import AbstractFieldType, DataModelSpec, FieldSpec, RequirementsReference, SystemModel
DEFAULT_NAMES = ("Payment", "Invoice")
FILTER = "const visible = computed(() => dataModels.filter((name) => name.toLowerCase().includes(filter.value.toLowerCase())));"
BROKEN = "const visible = computed(() => dataModels);"

def fixture_model(names=DEFAULT_NAMES, system_name="Billing Platform") -> SystemModel:
    return SystemModel(system_name=system_name, requirements_ref=RequirementsReference(graph_id="g1", graph_hash="h1"),
        data_models=[DataModelSpec(id=f"dm_{i}_{n.lower()}", name=n, owning_service_id="svc", fields=[FieldSpec(name="amount", type=AbstractFieldType.DECIMAL)]) for i, n in enumerate(names)])

def fixture_files(model=None) -> dict[str, str]:
    return NuxtFrontend().generate(model or fixture_model()).files

def break_filter(target: Path) -> None:
    comp = target / "app" / "app.vue"
    if not comp.exists(): raise RuntimeError(f"{comp} missing; generate first")
    s = comp.read_text(encoding="utf-8")
    if FILTER not in s: raise RuntimeError("filter expression drifted")
    comp.write_text(s.replace(FILTER, BROKEN), encoding="utf-8")

def write_fixture(target: Path, names=DEFAULT_NAMES) -> int:
    files = fixture_files(fixture_model(names))
    for n, c in files.items():
        p = target / n; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(c, encoding="utf-8")
    return len(files)

def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if len(args) < 1: print(__doc__); return 2
    target = Path(args[0])
    if "--negative-control" in flags:
        if len(args) > 1: print("--negative-control takes no names", file=sys.stderr); return 2
        try:
            break_filter(target)
        except RuntimeError as exc:
            print(f"generate a bundle first: {exc}", file=sys.stderr)
            return 1
        print(f"broke filter in {target}"); return 0
    names = tuple(args[1].split(",")) if len(args) > 1 and args[1] else ()
    written = write_fixture(target, names); print(f"wrote {written} files to {target}"); return 0

if __name__ == "__main__": raise SystemExit(main(sys.argv))
