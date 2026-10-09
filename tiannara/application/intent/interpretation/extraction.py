"""Stage 3 interpretation: requirement-graph seeds and data-entity design.

Deterministic analysis that turns an arbitrary natural-language problem
statement into ``ExtractionOutput`` (requirement nodes, edges, and persisted
entity designs). All rules are specification-agnostic: they key on generic
requirement phrasing (possession declarations, containment relations,
behaviour bullets, access-control phrasing, vagueness markers) and never on
any particular application domain.

Traceability: every derived node/edge/field carries a rationale containing
the source sentence and its content hash, so each requirement links back to
the exact text it came from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field

from ..schemas import (
    DataSeed,
    ElicitationOutput,
    EdgeSeed,
    ExtractionOutput,
    FieldSeed,
    NodeSeed,
    NormalizedIntent,
)
from .errors import UninterpretableSpecificationError
from .text import (
    is_behavior_section,
    singular,
    snake,
    split_sections,
    source_hash,
    strip_leading_stopwords,
    trace,
)

_GENERIC_SUBJECTS = frozenset(
    {
        "system", "service", "application", "app", "page", "website", "browser",
        "api", "endpoint", "server", "client", "everything", "data", "user",
        "users", "it", "they", "one", "thing", "stuff",
    }
)

_CONTAINER_MODIFIERS = frozenset(
    {"named", "new", "separate", "different", "shared", "simple", "various",
     "several", "many", "other", "distinct"}
)

_POSSESSION = re.compile(
    r"^(?:each|every|any|all)\s+(?:an?\s+|the\s+)?"
    r"(?P<subject>[a-z][a-z0-9 _-]*?)"
    r"\s+(?:has|have|carries|carry|includes|include|contains|contain|"
    r"holds|hold|comes with)\s+(?P<rest>.+)$"
)
_OPTIONAL_POSSESSION = re.compile(
    r"^(?:a|an|the)\s+(?P<subject>[a-z][a-z0-9 _-]*?)"
    r"\s+(?:may|can)\s+(?:carry|include|hold|contain|hold)\s+(?P<rest>.+)$"
)
_DECLARATION = re.compile(
    r"^(?P<subject>[a-z][a-z0-9 _-]*?)s\s+are\s+"
    r"(?:[a-z0-9]+\s+)*(?:records|entities)(?:\s+with\s+(?P<rest>.+))?$"
)
_CONTAINER = re.compile(
    r"^(?:the\s+)?(?P<child>[a-z][a-z0-9 _-]*?)"
    r"\s+(?:live|lives|belong|belongs|sit|sits|are stored|is stored)"
    r"\s+(?:in|within|under|to)\s+(?:an?\s+|the\s+)?"
    r"(?P<container>[a-z][a-z0-9 _-]*)$"
)

_ENUM_MOVES_FROM = re.compile(
    r"(?P<field>[a-z][a-z0-9 _-]*?)\s+that\s+moves?\s+from\s+"
    r"(?P<vals>[a-z0-9_ -]+(?:\s+to\s+[a-z0-9_ -]+)+)"
)
#: Enumerated-list atom: consumes comma-separated list items but stops right
#: before the next field's article -- directly or after an ``and``/``or``
#: join -- so a trailing ", an optional note" never gets swallowed into the
#: value list.
_CLAUSE_ATOM = (
    r"(?:(?!,\s+(?:(?:an?|the)\b|(?:and|or)\s+(?:an?|the)\b))[a-z0-9_, -])"
)
_ENUM_STARTS_AT = re.compile(
    r"(?P<field>[a-z][a-z0-9 _-]*?)\s+that\s+starts\s+at\s+"
    r"(?P<first>[a-z0-9_ -]+?)\s+and\s+(?:can\s+)?(?:move|moves|transition)"
    r"\s+(?:to|from)\s+(?P<rest>" + _CLAUSE_ATOM + r"+)"
)
_ENUM_CHOSEN_FROM = re.compile(
    r"(?P<field>[a-z][a-z0-9 _-]*?)\s+(?:chosen|selected)\s+from\s+"
    r"(?P<vals>" + _CLAUSE_ATOM + r"+)"
)
_ENUM_OF_VALUES = re.compile(
    r"(?P<field>[a-z][a-z0-9 _-]*?)\s+of\s+"
    r"(?P<vals>[a-z0-9]+(?:\s*,\s*[a-z0-9]+)*(?:\s+or\s+[a-z0-9]+|\s+and\s+[a-z0-9]+)+)"
)

_AUTH_PATTERN = re.compile(
    r"\baccess key\b|\bapi key\b|\bauthentication\b|\bcredentials\b|"
    r"\b401\b|\bunauthorized\b|\bwithout it are rejected\b"
)
_HEALTH_PATTERN = re.compile(r"\bhealth\b|\bliveness\b|\breadiness\b|/health")
_QUALITY_PATTERN = re.compile(
    r"\bunderstandable\b|\bmaintainable\b|\bperformance\b|\blatency\b|"
    r"\bsimple\b|\beasy\b|\bfast\b|\busable\b|\bclarity\b"
)
_SCOPE_PATTERN = re.compile(
    r"\bone person\b|\bsmall team\b|\bper installation\b|\bsingle maintainer\b"
    r"|\bstandalone\b|\bno cross[- ]"
)
_NEGATIVE_PATTERN = re.compile(
    r"\bno cross\b|\bnever\b|\bonly\b|\bmust\b|\bwithout\b|\bis refused\b|"
    r"\bare refused\b|\bis rejected\b|\bare rejected\b|\bnot one of\b|"
    r"\bis valid\b|\bare valid\b|\bmust not\b|\bforbidden\b|\brejected\b"
)
_BROWSER_PATTERN = re.compile(
    r"\bbrowser\b|\bweb page\b|\bpage lists\b|\bwithout reloading\b|"
    r"\bsingle page\b|\binterface\b"
)
_BEHAVIOR_VERBS = (
    "create", "creating", "record", "records", "list", "listing", "fetch",
    "fetching", "get", "mark", "marking", "change", "changing", "update",
    "updates", "delete", "deleting", "remove", "removes", "submit",
    "submitting", "approve", "approves", "reject", "rejects", "review",
    "returns", "return", "show", "shows", "display", "displays", "track",
    "tracks", "store", "stores", "save", "saves", "add", "adds", "edit",
    "edits", "book", "books", "cancel", "cancels", "notify", "notifies",
    "search", "searches", "filter", "filters", "report", "reports",
    "organize", "organizes", "group", "groups", "belong", "belongs",
)
_BEHAVIOR_SET = frozenset(_BEHAVIOR_VERBS)

_TYPE_WORDS = frozenset(
    {"decimal", "numeric", "monetary", "integer", "whole", "boolean", "text"}
)
_FUNCTION_WORDS = frozenset({"optional", "mandatory", "may", "can", "must"})
_TYPE_SUFFIX = re.compile(
    r"\s+in\s+(?:decimal|integer|whole|numeric|monetary)\s*"
    r"(?:currency|numbers?|units?|amounts?)?\b"
)
_TS_NAME = re.compile(r"\bdate\b|\btime\b|\btimestamp\b|\bdue\b|\bdeadline\b")
_DECIMAL_NAME = frozenset(
    {"amount", "price", "cost", "total", "balance", "fee", "subtotal", "rate", "tax"}
)
_INTEGER_NAME = frozenset(
    {"quantity", "count", "number", "age", "stock", "units", "miles", "pages", "seats"}
)
_BOOLEAN_NAME = frozenset({"enabled", "flagged", "pinned", "archived", "active_flag"})
_MAX_NODES = 40

_SUFFIX_CLAUSE = re.compile(r"\s+(?:it|that|which|who|where)\b.*$")


@dataclass
class _Entity:
    name: str
    fields: list[FieldSeed] = dc_field(default_factory=list)
    sources: list[str] = dc_field(default_factory=list)


def _val_list(raw: str) -> list[str]:
    parts = re.split(r"\s*,\s*|\s+or\s+|\s+and\s+|\s+to\s+", raw)
    values: list[str] = []
    for part in parts:
        value = snake(part)
        if value and value not in values:
            values.append(value)
    return values


def _field_name_from(phrase: str) -> str:
    tokens = snake(phrase).split("_")
    tokens = [
        t
        for t in tokens
        if t and t not in _TYPE_WORDS and t not in _FUNCTION_WORDS
    ]
    tokens = strip_leading_stopwords(tokens)
    return "_".join(tokens)


def _infer_type(name: str, segment: str) -> str:
    if name.endswith("_id") or name.endswith("_reference") or " reference" in f" {segment} ":
        return "reference"
    if "decimal" in segment or name in _DECIMAL_NAME:
        return "decimal"
    if name in _INTEGER_NAME:
        return "integer"
    if name in _BOOLEAN_NAME:
        return "boolean"
    if _TS_NAME.search(name.replace("_", " ")):
        return "timestamp"
    return "text"


def _field_from_segment(segment: str) -> FieldSeed | None:
    original = _SUFFIX_CLAUSE.sub("", segment).strip().strip(",").strip()
    if not original:
        return None
    lowered = original.lower()
    optional = bool(re.search(r"\boptional\b|\bmay\b|\bcan be omitted\b", lowered))
    cleaned = _TYPE_SUFFIX.sub(" ", lowered)
    name = _field_name_from(cleaned)
    if not name:
        return None
    field_type = _infer_type(name, lowered)
    if field_type == "reference" and name.endswith("_reference"):
        stripped = name[: -len("_reference")]
        name = stripped or name
    return FieldSeed(
        name=name,
        type=field_type,
        required=not optional,
        enumeration_values=[],
        description=f"interpreted from source text {source_hash(original)}",
    )


def _parse_field_clause(rest: str) -> list[FieldSeed]:
    """Parse a comma/and separated field clause into typed field seeds.

    Enum constructs are extracted first (and their spans removed) so ordinary
    comma-splitting never tears an enumeration list apart.
    """
    fields: list[FieldSeed] = []
    working = f" {rest.lower()} "

    enum_patterns = (
        _ENUM_MOVES_FROM,
        _ENUM_STARTS_AT,
        _ENUM_CHOSEN_FROM,
        _ENUM_OF_VALUES,
    )
    for pattern in enum_patterns:
        while True:
            match = pattern.search(working)
            if not match:
                break
            phrase = match.group("field")
            if pattern is _ENUM_STARTS_AT:
                values = _val_list(match.group("first")) + _val_list(
                    match.group("rest")
                )
            else:
                values = _val_list(match.group("vals"))
            values = [v for v in values if v]
            deduped: list[str] = []
            for value in values:
                if value not in deduped:
                    deduped.append(value)
            if phrase and deduped:
                span_start, span_end = match.span()
                preceding = working[:span_start]
                optional = bool(re.search(r"\boptional\b", preceding.rsplit(",", 1)[-1]))
                name = _field_name_from(phrase)
                if name:
                    fields.append(
                        FieldSeed(
                            name=name,
                            type="enumeration",
                            required=not optional,
                            enumeration_values=deduped,
                            description=(
                                "interpreted from source text "
                                f"{source_hash(match.group(0).strip())}"
                            ),
                        )
                    )
                working = working[:span_start] + f" {phrase} " + working[span_end:]
                continue
            # Matched but unusable (no field phrase/values): blank it out and
            # stop this pattern to avoid an infinite loop.
            working = working[: match.start()] + " " + working[match.end() :]
            break

    segments = re.split(r"\s*,\s*|\s+and\s+(?:an?\s+)?|;\s*", working)
    seen = {f.name for f in fields}
    for segment in segments:
        cleaned = segment.strip().strip(",").strip()
        if not cleaned:
            continue
        seed = _field_from_segment(cleaned)
        if seed is None or seed.name in seen:
            continue
        seen.add(seed.name)
        fields.append(seed)
    return fields


def _entity_subject(phrase: str) -> str | None:
    name = singular(snake(phrase))
    if not name or name in _GENERIC_SUBJECTS or not name[0].isalpha():
        return None
    return name


def _strip_container_modifiers(phrase: str) -> str:
    tokens = snake(phrase).split("_")
    kept = [t for t in tokens if t not in _CONTAINER_MODIFIERS]
    return singular("_".join(kept)) if kept else singular("_".join(tokens))


def _collect_entities(
    sentence: str, entities: dict[str, _Entity], consumed: dict[str, str]
) -> None:
    lowered = sentence.lower().strip()

    match = _POSSESSION.match(lowered)
    if match is None:
        match = _OPTIONAL_POSSESSION.match(lowered)
    if match is not None:
        subject = _entity_subject(match.group("subject"))
        if subject:
            entity = entities.setdefault(subject, _Entity(name=subject))
            for source in entity.sources:
                if source_hash(source) == source_hash(sentence):
                    return
            entity.sources.append(sentence)
            consumed[source_hash(sentence)] = subject
            for seed in _parse_field_clause(match.group("rest")):
                if seed.name not in {f.name for f in entity.fields}:
                    entity.fields.append(seed)
            return

    match = _DECLARATION.match(lowered)
    if match is not None:
        subject = _entity_subject(match.group("subject"))
        if subject:
            entity = entities.setdefault(subject, _Entity(name=subject))
            entity.sources.append(sentence)
            consumed[source_hash(sentence)] = subject
            rest = match.group("rest")
            if rest:
                for seed in _parse_field_clause(rest):
                    if seed.name not in {f.name for f in entity.fields}:
                        entity.fields.append(seed)
            return

    match = _CONTAINER.match(lowered)
    if match is not None:
        child = _entity_subject(match.group("child"))
        container = _strip_container_modifiers(match.group("container"))
        if child and container and container not in _GENERIC_SUBJECTS:
            child_entity = entities.setdefault(child, _Entity(name=child))
            if sentence not in child_entity.sources and not child_entity.sources:
                child_entity.sources.append(sentence)
            compound = f"{child}_{container}"
            container_entity = entities.setdefault(
                compound, _Entity(name=compound)
            )
            container_entity.sources.append(sentence)
            ref_name = f"{container}_id"
            if ref_name not in {f.name for f in child_entity.fields}:
                child_entity.fields.append(
                    FieldSeed(
                        name=ref_name,
                        type="reference",
                        required=False,
                        enumeration_values=[],
                        description=(
                            f"container membership from source "
                            f"{source_hash(sentence)}"
                        ),
                    )
                )


def _slug_ref(sentence: str, used: set[str]) -> str:
    tokens = snake(sentence).split("_")
    tokens = strip_leading_stopwords(tokens)[:5]
    base = "-".join(tokens) or "req"
    ref = f"req-{base}"
    counter = 2
    while ref in used:
        ref = f"req-{base}-{counter}"
        counter += 1
    used.add(ref)
    return ref


def _classify(
    sentence: str, is_behavior: bool, consumed_entity: str | None
) -> tuple[str, dict[str, bool]]:
    """Return (kind, flags) for a sentence; kind ``""`` means skip."""
    lowered = sentence.lower()
    flags: dict[str, bool] = {}

    if consumed_entity is not None:
        return "data", flags
    if _AUTH_PATTERN.search(lowered):
        return "constraint", flags
    if _HEALTH_PATTERN.search(lowered):
        return "constraint", flags
    if _QUALITY_PATTERN.search(lowered):
        return "quality", flags
    if _SCOPE_PATTERN.search(lowered) and not _NEGATIVE_PATTERN.search(lowered):
        return "", flags
    if _CONTAINER.match(lowered):
        flags["container"] = True
        return "functional", flags
    if _BROWSER_PATTERN.search(lowered):
        flags["browser"] = True
        return "functional", flags
    if _NEGATIVE_PATTERN.search(lowered):
        return "constraint", flags
    for token in re.findall(r"[a-z]+", lowered):
        if token in _BEHAVIOR_SET:
            return "functional", flags
    if is_behavior:
        return "functional", flags
    return "", flags


def _creation_core(statements: dict[str, str], functional_ids: list[str]) -> str:
    for node_id in functional_ids:
        lowered = statements[node_id].lower()
        if re.search(
            r"\bcreat|\brecord|\bsubmit|\bstore|\bmake\b|\badd\b|\bnew\b",
            lowered,
        ):
            return node_id
    return functional_ids[0]


def interpret_extraction(
    normalized: NormalizedIntent, elicitation: ElicitationOutput
) -> ExtractionOutput:
    """Derive requirement-graph seeds and entity designs from the statement.

    Raises ``UninterpretableSpecificationError`` when the statement yields no
    functional requirements or no persisted entities -- generation cannot be
    performed safely from an empty interpretation.
    """
    del elicitation  # context is available; rules operate on the statement.
    pairs = split_sections(normalized.normalized_statement)
    if not pairs:
        raise UninterpretableSpecificationError("statement produced no sentences")

    entities: dict[str, _Entity] = {}
    consumed: dict[str, str] = {}
    for _section, sentence in pairs:
        if not is_behavior_section(_section):
            _collect_entities(sentence, entities, consumed)
    if not entities:
        for _section, sentence in pairs:
            _collect_entities(sentence, entities, consumed)

    used_refs: set[str] = set()
    nodes: list[NodeSeed] = []
    edge_specs: list[tuple[str, str, str, str]] = []
    functional_ids: list[str] = []
    statements: dict[str, str] = {}
    data_node_done: set[str] = set()
    container_ids: list[str] = []
    browser_ids: list[str] = []

    for section, sentence in pairs:
        consumed_entity = consumed.get(source_hash(sentence))
        kind, flags = _classify(sentence, is_behavior_section(section), consumed_entity)
        if not kind:
            continue
        if len(nodes) >= _MAX_NODES:
            break
        if kind == "data" and consumed_entity:
            ref = f"data-{consumed_entity}"
            if ref in data_node_done:
                continue
            data_node_done.add(ref)
            used_refs.add(ref)
            nodes.append(
                NodeSeed(
                    ref=ref,
                    kind="data",
                    statement=sentence,
                    priority="must",
                    acceptance_criteria=[],
                    rationale=trace(sentence),
                )
            )
            continue
        ref = _slug_ref(sentence, used_refs)
        statements[ref] = sentence
        nodes.append(
            NodeSeed(
                ref=ref,
                kind=kind,
                statement=sentence,
                priority="should" if kind == "quality" else "must",
                acceptance_criteria=[],
                rationale=trace(sentence),
            )
        )
        if kind == "functional":
            functional_ids.append(ref)
            if flags.get("container"):
                container_ids.append(ref)
            if flags.get("browser"):
                browser_ids.append(ref)

    for entity in entities.values():
        ref = f"data-{entity.name}"
        if ref in data_node_done:
            continue
        data_node_done.add(ref)
        used_refs.add(ref)
        source = entity.sources[0] if entity.sources else normalized.normalized_statement
        nodes.append(
            NodeSeed(
                ref=ref,
                kind="data",
                statement=(
                    f"The system persists {entity.name} as a structured record "
                    "with stable identifiers"
                ),
                priority="must",
                acceptance_criteria=[],
                rationale=trace(source),
            )
        )

    if not functional_ids:
        raise UninterpretableSpecificationError(
            "statement yielded no functional requirements"
        )
    if not entities:
        raise UninterpretableSpecificationError(
            "statement yielded no persistable entities"
        )

    core = _creation_core(statements, functional_ids)
    for ref in container_ids:
        if ref != core:
            edge_specs.append((ref, core, "depends_on", "container structure builds on the core record flow"))
    for ref in browser_ids:
        if ref != core:
            edge_specs.append((ref, core, "depends_on", "user surface exercises the core record flow"))
    for node in nodes:
        if node.kind == "constraint":
            edge_specs.append((node.ref, core, "constrains", "constraint governs the core record flow"))

    seen_edges: set[tuple[str, str, str]] = set()
    edges: list[EdgeSeed] = []
    for source, target, kind, rationale in edge_specs:
        key = (source, target, kind)
        if source == target or key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append(
            EdgeSeed(source_ref=source, target_ref=target, kind=kind, rationale=rationale)
        )

    data_models: list[DataSeed] = []
    for entity in entities.values():
        if not entity.fields:
            entity.fields.append(
                FieldSeed(
                    name="name",
                    type="text",
                    required=True,
                    enumeration_values=[],
                    description=f"synthesized namable key from {source_hash(entity.sources[0]) if entity.sources else source_hash(normalized.normalized_statement)}",
                )
            )
        data_ref = f"data-{entity.name}"
        owner = None
        for node_id in functional_ids:
            lowered = statements.get(node_id, "").lower()
            if singular(entity.name) in lowered:
                owner = node_id
                break
        if owner is None:
            owner = core
        invariants = [
            f"{f.name} is one of {', '.join(f.enumeration_values)}"
            for f in entity.fields
            if f.type == "enumeration" and f.enumeration_values
        ]
        requirement_refs = [data_ref]
        if owner not in requirement_refs:
            requirement_refs.append(owner)
        data_models.append(
            DataSeed(
                ref=data_ref,
                name=entity.name,
                fields=list(entity.fields),
                invariants=invariants,
                owning_service_ref=owner,
                requirement_refs=requirement_refs,
            )
        )

    return ExtractionOutput(nodes=nodes, edges=edges, data_models=data_models)
