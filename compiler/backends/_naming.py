"""Shared deterministic naming helpers for generated backend code.

Plan element ids are heterogeneous ("service:a", "dm:core") while emitted file
names, module names, and class names must be valid identifiers derived from
the human labels (entity_name / service name / event name). Every backend
uses these helpers so paths and contents always agree.
"""
from __future__ import annotations
import re

from compiler.core.plan import CompilationPlan


def slug(name: str) -> str:
    s = re.sub(r"\W", "_", name.strip())
    if not s:
        s = "item"
    if s[0].isdigit():
        s = f"_{s}"
    return s


def cls_name(slug_str: str) -> str:
    return slug_str[0].upper() + slug_str[1:]


def plural(slug_str: str) -> str:
    low = slug_str.lower()
    return low if low.endswith("s") else low + "s"


def plan_entities(plan: CompilationPlan) -> list[dict]:
    """Ordered, deduplicated data models with owner service info."""
    out: list[dict] = []
    seen: set[str] = set()
    for s in plan.services:
        svc_mod = slug(s.name)
        for mp in s.data_models:
            mod = slug(mp.entity_name)
            if mod in seen:
                continue
            seen.add(mod)
            out.append({
                "entity": mp.entity_name,
                "mod": mod,
                "cls": cls_name(mod),
                "plural": plural(mod),
                "service_mod": svc_mod,
                "service_cls": cls_name(svc_mod),
            })
    return out


def plan_services(plan: CompilationPlan) -> list[dict]:
    entities = plan_entities(plan)
    out = []
    for s in plan.services:
        mod = slug(s.name)
        owned = [e["mod"] for e in entities if e["service_mod"] == mod]
        out.append({"name": s.name, "mod": mod, "cls": cls_name(mod), "owned": owned})
    return out


def plan_events(plan: CompilationPlan) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for s in plan.services:
        for ev in s.published_events + s.consumed_events:
            mod = slug(ev.name)
            if mod in seen:
                continue
            seen.add(mod)
            out.append({"name": ev.name, "mod": mod})
    return out
