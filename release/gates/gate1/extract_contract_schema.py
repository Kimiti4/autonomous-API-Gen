#!/usr/bin/env python3
# Canonical contract-schema extractor.
#
# Field TYPES are rendered through render_type(): a deterministic,
# interpreter-version-independent encoding of the annotation graph. Never use
# str(annotation) here — typing reprs vary across Python versions (3.12 vs
# 3.14 differ) and would corrupt the golden with environment artifacts.
import argparse, importlib, inspect, json, os, sys, types, typing
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
def render_type(t):
    if t is type(None):
        return "none"
    origin = typing.get_origin(t)
    if origin is None:
        return getattr(t, "__name__", str(t))
    args = typing.get_args(t)
    if origin is typing.Literal:
        return "literal(" + ",".join(repr(a) for a in args) + ")"
    if origin in (typing.Union, types.UnionType):
        parts = sorted({render_type(a) for a in args if a is not type(None)})
        has_none = any(a is type(None) for a in args)
        body = "|".join(parts)
        return f"{body} | none" if has_none else body
    if origin in (list, tuple, set, frozenset):
        inner = ",".join(render_type(a) for a in args)
        return f"{origin.__name__}[{inner}]" if args else origin.__name__
    if origin is dict:
        kv = ",".join(render_type(a) for a in args)
        return f"dict[{kv}]" if args else "dict"
    # Unknown construct (e.g. Annotated remnants): fall back to a stable name.
    return getattr(origin, "__name__", str(origin))

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
        schema["models"][name] = {"fields": {f: {"required": i.is_required(), "type": render_type(i.annotation)} for f, i in model.model_fields.items()}}
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
            continue
        for f in sorted(gf):
            gv, cv = g["models"][m]["fields"][f], c["models"][m]["fields"][f]
            if gv != cv:
                print(f"  {m}.{f}: {gv} -> {cv}", file=sys.stderr)
    print("  Re-run with --update and commit ONLY after an intentional contract change.", file=sys.stderr)
    return 1
if __name__ == "__main__": sys.exit(main())
