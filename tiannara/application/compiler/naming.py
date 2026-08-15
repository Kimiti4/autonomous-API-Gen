"""Deterministic naming helpers shared by compiler backends."""

from __future__ import annotations

import re


def snake_case(name: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", name).strip("_").lower()
    return re.sub(r"_+", "_", value) or "component"


def pascal_case(name: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    return "".join(part[:1].upper() + part[1:] for part in parts if part) or "Component"


def slugify(name: str) -> str:
    value = snake_case(name)
    if value[0].isdigit():
        value = f"gen_{value}"
    return value


def pluralize(snake: str) -> str:
    if snake.endswith("s"):
        return snake
    if snake.endswith("y") and len(snake) > 1 and snake[-2] not in "aeiou":
        return snake[:-1] + "ies"
    return snake + "s"
