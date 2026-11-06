"""Materialize a CompilationResult to a directory tree.

Generated paths are untrusted compiler output. Reject absolute paths, traversal,
Windows drive/UNC paths, and symlink escapes before writing any file.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath, PureWindowsPath

from tiannara.domain.models.compilation import CompilationResult


def _safe_target(root: Path, relative_path: str) -> Path:
    if (
        not isinstance(relative_path, str)
        or not relative_path
        or "\x00" in relative_path
        or "\\" in relative_path
    ):
        raise ValueError(f"unsafe generated path: {relative_path!r}")

    raw_parts = relative_path.split("/")
    posix = PurePosixPath(relative_path)
    windows = PureWindowsPath(relative_path)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or any(part in ("", ".", "..") for part in raw_parts)
        or any(part.casefold() in {".git", ".tiannara"} for part in raw_parts)
    ):
        raise ValueError(f"unsafe generated path: {relative_path!r}")

    root_real = root.resolve()
    target = root_real.joinpath(*posix.parts)

    # Existing symlink components can redirect a lexically safe path outside
    # the workspace. Reject them rather than relying on string-prefix checks.
    current = root_real
    for part in posix.parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"generated path traverses a symlink: {relative_path!r}")
    if target.is_symlink():
        raise ValueError(f"generated path targets a symlink: {relative_path!r}")

    resolved = target.resolve(strict=False)
    if not resolved.is_relative_to(root_real):
        raise ValueError(f"generated path escapes output directory: {relative_path!r}")
    return target


def validate_bundle_paths(result: CompilationResult, output_dir: str | Path) -> tuple[Path, ...]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    targets = tuple(_safe_target(root, relative_path) for relative_path in result.files)
    normalized = ["/".join(part.casefold() for part in target.relative_to(root).parts) for target in targets]
    if len(set(normalized)) != len(normalized):
        raise ValueError("generated bundle contains duplicate normalized paths")
    return targets


def write_bundle(result: CompilationResult, output_dir: str | Path) -> Path:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()

    # Validate the complete path set before the first write. A later unsafe
    # entry must not leave a partially materialized candidate.
    targets = [
        (relative_path, target, content)
        for (relative_path, content), target
        in zip(result.files.items(), validate_bundle_paths(result, root))
    ]
    for _, target, content in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        # Re-check after parent creation to catch pre-existing symlink parents.
        resolved_parent = target.parent.resolve()
        if not resolved_parent.is_relative_to(root):
            raise ValueError(f"generated path escapes output directory: {target}")
        if target.is_symlink():
            raise ValueError(f"generated path targets a symlink: {target}")
        target.write_text(content, encoding="utf-8")
    return root
