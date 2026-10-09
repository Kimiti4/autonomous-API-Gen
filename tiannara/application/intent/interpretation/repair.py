"""Deterministic repair for pre-validation issues (stage 5 of the compiler).

The interpretation layer is deterministic, so repairs are too: each known
issue class from ``graph_builder.prevalidate*`` / structural validation is
rewritten by a targeted, idempotent fix. Unknown issues are left untouched
-- the compiler's bounded repair loop re-reports them and the run fails
honestly rather than masking a problem the rewriter cannot prove fixed.
"""

from __future__ import annotations

import ast
import re

from ..schemas import EdgeSeed, ExtractionOutput, NodeSeed

_VALID_KINDS = frozenset(
    {
        "functional",
        "quality",
        "constraint",
        "compliance",
        "integration",
        "data",
        "business_rule",
        "assumption",
        "unclassified",
    }
)
_VALID_PRIORITIES = frozenset({"must", "should", "could", "wont"})
_FIELD_TYPE_MAP = {
    "str": "text",
    "string": "text",
    "int": "integer",
    "integer": "integer",
    "float": "decimal",
    "double": "decimal",
    "bool": "boolean",
    "boolean": "boolean",
    "datetime": "timestamp",
    "date": "timestamp",
    "list": "document",
    "dict": "document",
    "object": "document",
    "json": "document",
}

_DANGLING = re.compile(r"^dangling edge (\S+) -> (\S+)")
_SELF_LOOP = re.compile(r"^self-loop on directed edge kind at node '([^']+)'")
_CYCLE = re.compile(r"^directed cycle: (.+)$")
_ASYMMETRIC = re.compile(r"^asymmetric conflict between '([^']+)' and '([^']+)'")
_DUPLICATE_NODE_IDS = re.compile(r"^duplicate node ids: (\[.*\])$")
_KIND_ENUM = re.compile(r"'([^']+)' is not a valid RequirementKind")
_PRIORITY_ENUM = re.compile(r"'([^']+)' is not a valid Priority")
_DM_DUP_REF = re.compile(r"^data model duplicate ref: (.+)$")
_DM_DUP_NAME = re.compile(r"^data model duplicate name: (.+)$")
_DM_BAD_REF = re.compile(r"^data model ref '([^']+)' does not match")
_DM_FIELD = re.compile(r"^data model '([^']+)' duplicate field: (.+)$")
_DM_BAD_TYPE = re.compile(r"^data model '([^']+)' field '([^']+)' has non-abstract type '([^']*)'")
_DM_EMPTY_ENUM = re.compile(r"^data model '([^']+)' enumeration field '([^']+)' requires")
_DM_BAD_OWNER = re.compile(r"^data model '([^']+)' owning_service_ref '([^']+)' is not")
_DM_BAD_REQREF = re.compile(r"^data model '([^']+)' requirement_refs entry '([^']+)' is not")


def _drop_edges(edges: list[EdgeSeed], predicate) -> None:
    edges[:] = [e for e in edges if not predicate(e)]


def _has_edge(edges: list[EdgeSeed], source: str, target: str, kind: str) -> bool:
    return any(
        e.source_ref == source and e.target_ref == target and e.kind == kind
        for e in edges
    )


def _find_model(fixed: ExtractionOutput, ref: str):
    for model in fixed.data_models:
        if model.ref == ref:
            return model
    return None


def _repair_issue(fixed: ExtractionOutput, issue: str) -> None:
    match = _DUPLICATE_NODE_IDS.match(issue)
    if match:
        try:
            ids = set(ast.literal_eval(match.group(1)))
        except (ValueError, SyntaxError):
            return
        seen: set[str] = set()
        kept: list[NodeSeed] = []
        for node in fixed.nodes:
            if node.ref in ids:
                if node.ref in seen:
                    continue
                seen.add(node.ref)
            kept.append(node)
        fixed.nodes[:] = kept
        return

    match = _DANGLING.match(issue)
    if match:
        source, target = match.group(1), match.group(2)
        _drop_edges(
            fixed.edges,
            lambda e: (e.source_ref, e.target_ref) == (source, target),
        )
        return

    match = _SELF_LOOP.match(issue)
    if match:
        node_id = match.group(1)
        _drop_edges(
            fixed.edges,
            lambda e: e.source_ref == node_id and e.target_ref == node_id,
        )
        return

    if issue.startswith("duplicate edge:"):
        seen_keys: set[tuple[str, str, str]] = set()
        deduped: list[EdgeSeed] = []
        for edge in fixed.edges:
            key = (edge.source_ref, edge.target_ref, edge.kind)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            deduped.append(edge)
        fixed.edges[:] = deduped
        return

    match = _CYCLE.match(issue)
    if match:
        chain = [part.strip() for part in match.group(1).split("->") if part.strip()]
        if len(chain) >= 2:
            pairs = list(zip(chain, chain[1:]))
            pairs.append((chain[-1], chain[0]))
            _drop_edges(
                fixed.edges,
                lambda e: (e.source_ref, e.target_ref) in pairs,
            )
        return

    match = _ASYMMETRIC.match(issue)
    if match:
        left, right = match.group(1), match.group(2)
        if not _has_edge(fixed.edges, left, right, "conflicts_with"):
            fixed.edges.append(
                EdgeSeed(
                    source_ref=left,
                    target_ref=right,
                    kind="conflicts_with",
                    rationale="symmetric conflict completion during repair",
                )
            )
        if not _has_edge(fixed.edges, right, left, "conflicts_with"):
            fixed.edges.append(
                EdgeSeed(
                    source_ref=right,
                    target_ref=left,
                    kind="conflicts_with",
                    rationale="symmetric conflict completion during repair",
                )
            )
        return

    match = _DM_DUP_REF.match(issue)
    if match:
        dup_ref = match.group(1).strip()
        seen_refs: set[str] = set()
        kept_models = []
        for model in fixed.data_models:
            if model.ref == dup_ref and model.ref in seen_refs:
                continue
            seen_refs.add(model.ref)
            kept_models.append(model)
        fixed.data_models[:] = kept_models
        return

    match = _DM_DUP_NAME.match(issue)
    if match:
        dup_name = match.group(1).strip().lower()
        seen_names: set[str] = set()
        kept_models = []
        for model in fixed.data_models:
            key = model.name.strip().lower()
            if key == dup_name and key in seen_names:
                continue
            seen_names.add(key)
            kept_models.append(model)
        fixed.data_models[:] = kept_models
        return

    match = _DM_BAD_REF.match(issue)
    if match:
        model = _find_model(fixed, match.group(1))
        if model is None:
            return
        node_refs = [n.ref for n in fixed.nodes]
        candidate = f"data-{model.name.strip().lower().replace(' ', '_')}"
        if candidate in node_refs:
            model.ref = candidate
            return
        used = {m.ref for m in fixed.data_models if m is not model}
        for ref in node_refs:
            if ref not in used:
                model.ref = ref
                return
        return

    match = _DM_FIELD.match(issue)
    if match:
        model = _find_model(fixed, match.group(1))
        if model is None:
            return
        dup_field = match.group(2).strip().lower()
        seen_fields: set[str] = set()
        kept_fields = []
        for field in model.fields:
            key = field.name.strip().lower()
            if key == dup_field and key in seen_fields:
                continue
            seen_fields.add(key)
            kept_fields.append(field)
        model.fields[:] = kept_fields
        return

    match = _DM_BAD_TYPE.match(issue)
    if match:
        model = _find_model(fixed, match.group(1))
        if model is None:
            return
        for field in model.fields:
            if field.name == match.group(2):
                field.type = _FIELD_TYPE_MAP.get(
                    match.group(3).strip().lower(), "text"
                )
        return

    match = _DM_EMPTY_ENUM.match(issue)
    if match:
        model = _find_model(fixed, match.group(1))
        if model is None:
            return
        for field in model.fields:
            if field.name == match.group(2) and not field.enumeration_values:
                field.type = "text"
        return

    match = _DM_BAD_OWNER.match(issue)
    if match:
        model = _find_model(fixed, match.group(1))
        if model is not None:
            model.owning_service_ref = None
        return

    match = _DM_BAD_REQREF.match(issue)
    if match:
        model = _find_model(fixed, match.group(1))
        if model is None:
            return
        bad_ref = match.group(2)
        model.requirement_refs = [
            ref for ref in model.requirement_refs if ref != bad_ref
        ]
        return

    match = _KIND_ENUM.search(issue)
    if match:
        valid_values = {value for value in _VALID_KINDS}
        for node in fixed.nodes:
            if node.kind not in valid_values:
                node.kind = "unclassified"
        return

    match = _PRIORITY_ENUM.search(issue)
    if match:
        for node in fixed.nodes:
            if node.priority not in _VALID_PRIORITIES:
                node.priority = "must"
        return


def interpret_repair(
    current: ExtractionOutput, issues: list[str]
) -> ExtractionOutput:
    """Apply targeted fixes for every recognized pre-validation issue."""
    fixed = current.model_copy(deep=True)
    for issue in issues:
        _repair_issue(
            fixed, re.sub(r"^(?:Value error|Assertion error), ", "", issue)
        )
    return fixed
