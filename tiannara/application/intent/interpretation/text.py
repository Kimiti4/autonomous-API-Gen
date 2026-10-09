"""Deterministic text utilities for requirement interpretation.

Pure string operations only: sentence segmentation over plain/markdown
prose, snake-case naming, naive singularization, and source hashing for
traceability. Every function is total (no exceptions for ordinary input) so
interpretation stays deterministic across specifications.
"""

from __future__ import annotations

import re

from tiannara.domain.services.canonical import sha256_hex

_SENTENCE_BREAK = re.compile(r"[.!?\n]+")
_LIST_MARK = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+")
_HEADING = re.compile(r"^\s*#{1,6}\s*")
_EMPHASIS = re.compile(r"\*\*([^*]+)\*\*|\*([^*]+)\*|`([^`]+)`")
_INLINE_HEADING = re.compile(r"(?:^| )#{1,6} ")

_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
        "that", "which", "is", "are", "be", "it", "its", "their", "this",
        "from", "at", "by", "as", "into", "onto", "than", "then",
    }
)


def _layout_lines(text: str) -> list[str]:
    """Normalize prose into one structural element per line.

    ``prompts.normalize`` collapses every whitespace run (including
    newlines) into single spaces before interpretation ever sees the text,
    so markdown headings, bullets, and following prose all arrive on one
    line. This restores a deterministic line layout for both raw and
    normalized input:

    1. list markers start their own line;
    2. inline heading markers start their own line;
    3. a heading line that runs into prose (title merged by normalization)
       is split after the heading's first sentence end.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\n ?", "\n", text)
    text = re.sub(r" - ", "\n- ", text)
    text = _INLINE_HEADING.sub(
        lambda m: "\n" + m.group(0).strip() + " ", text
    )
    expanded: list[str] = []
    for line in text.split("\n"):
        heading_match = _HEADING.match(line)
        if heading_match:
            rest = line[heading_match.end():]
            stop = re.search(r"\.\s", rest)
            if stop:
                cut = heading_match.end() + stop.end()
                expanded.append(line[:cut].strip())
                remainder = line[cut:].strip()
                if remainder:
                    expanded.append(remainder)
                continue
        expanded.append(line)
    return [line.strip() for line in expanded if line.strip()]


def _strip_markup(line: str) -> str:
    line = _LIST_MARK.sub("", line)
    line = _EMPHASIS.sub(lambda m: next(g for g in m.groups() if g), line)
    return line.strip()


def iter_sentences(text: str) -> list[str]:
    """Split prose into trimmed, markdown-stripped sentences/bullets.

    Headings become their own segments so section labels can be detected by
    callers; blank segments are dropped; order is preserved.
    """
    sentences: list[str] = []
    for raw_line in _layout_lines(text):
        if _HEADING.match(raw_line):
            heading = _HEADING.sub("", raw_line).strip()
            if heading:
                sentences.append(heading)
            continue
        line = _strip_markup(raw_line)
        if not line:
            continue
        for part in _SENTENCE_BREAK.split(line):
            part = part.strip().strip(",").strip()
            if part:
                sentences.append(part)
    return sentences


def split_sections(text: str) -> list[tuple[str, str]]:
    """Return (section_title, sentence) pairs in document order.

    Text before the first heading lands in section ``""``.
    """
    pairs: list[tuple[str, str]] = []
    section = ""
    for raw_line in _layout_lines(text):
        if _HEADING.match(raw_line):
            section = _HEADING.sub("", raw_line).strip()
            continue
        line = _strip_markup(raw_line)
        if not line:
            continue
        for part in _SENTENCE_BREAK.split(line):
            part = part.strip().strip(",").strip()
            if part:
                pairs.append((section, part))
    return pairs


def is_behavior_section(title: str) -> bool:
    lowered = title.lower()
    return "behavior" in lowered or "behaviour" in lowered


def snake(phrase: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", phrase.strip()).strip("_").lower()
    return re.sub(r"_+", "_", value)


def singular(word: str) -> str:
    """Naive English singularization for entity naming (deterministic)."""
    w = word.strip().lower()
    if w.endswith("ies") and len(w) > 3:
        return w[:-3] + "y"
    if w.endswith("sses") or w.endswith("shes") or w.endswith("ches"):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 1:
        return w[:-1]
    return w


def strip_leading_stopwords(tokens: list[str]) -> list[str]:
    result = list(tokens)
    while result and result[0] in _STOPWORDS:
        result.pop(0)
    return result


def source_hash(sentence: str) -> str:
    """Short content hash of a source sentence for requirement traceability."""
    return sha256_hex(" ".join(sentence.split()))[:12]


def trace(sentence: str) -> str:
    """Rationale fragment linking a derived element back to its source text."""
    return f"derived from source text {source_hash(sentence)!r}: {sentence!r}"
