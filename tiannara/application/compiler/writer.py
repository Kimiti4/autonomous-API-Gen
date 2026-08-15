"""Materialize a CompilationResult to a directory tree."""

from __future__ import annotations

from pathlib import Path

from tiannara.domain.models.compilation import CompilationResult


def write_bundle(result: CompilationResult, output_dir: str | Path) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    for relative_path, content in result.files.items():
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return root
