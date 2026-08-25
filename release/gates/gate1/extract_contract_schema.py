#!/usr/bin/env python3
import argparse, importlib, inspect, json, os, sys
from pydantic import BaseModel
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_here, "..", "..", ".."))
sys.path.insert(0, os.path.join(_root, "autonomous-api"))
CONTRACT_MODULES = [
    "app.core.contracts.provenance", "app.core.contracts.errors",
    "app.core.contracts.events", "app.core.contracts.observations",
    "app.core.contracts.governance", "app.core.contracts.lineage",
    "app.core.contracts.evidence",
]
def collect_models():
    models = {}
    for modname in CONTRACT_MODULES:
        mod = importlib.import_module(modname)
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, BaseModel) and obj.__module__ == modname and name not in models:
                models[name] = obj
    return models
def extract():
    schema = {"version": "1.1.0", "models": {}, "registries": {}}
    for name, model in sorted(collect_models().items()):
        schema["models"][name] = {"fields": {f: {"required": i.is_required(), "type": str(i.annotation)} for f, i in model.model_fields.items()}}
    try:
        from app.core.contracts.events import EventTypes
        schema["registries"]["EventTypes"] = sorted(v for k, v in vars(EventTypes).items() if not k.startswith("_") and isinstance(v, str))
    except Exception: pass
    try:
        from app.core.contracts.errors import ERROR_TAXONOMY
        schema["registries"]["ErrorCodes"] = sorted(ERROR_TAXONOMY.keys())
    except Exception: pass
    return schema
def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--update", metavar="PATH"); g.add_argument("--check", metavar="PATH")
    args = ap.parse_args()
    payload = json.dumps(extract(), indent=2, sort_keys=True) + "\n"
    if args.update:
        with open(args.update, "w") as fh: fh.write(payload)
        print(f"wrote golden contract schema -> {args.update}"); return 0
    golden = open(args.check).read()
    if golden == payload:
        print("contract schema stable: golden matches extraction"); return 0
    g, c = json.loads(golden), json.loads(payload)
    print("CONTRACT DRIFT: Python schema differs from committed golden.", file=sys.stderr)
    gm, cm = set(g["models"]), set(c["models"])
    if gm != cm:
        print(f"  models added={sorted(cm-gm)} removed={sorted(gm-cm)}", file=sys.stderr)
    for m in sorted(gm & cm):
        gf, cf = set(g["models"][m]["fields"]), set(c["models"][m]["fields"])
        if gf != cf:
            print(f"  {m}: fields added={sorted(cf-gf)} removed={sorted(gf-cf)}", file=sys.stderr)
    print("  Re-run with --update and commit ONLY after an intentional contract change.", file=sys.stderr)
    return 1
if __name__ == "__main__": sys.exit(main())
