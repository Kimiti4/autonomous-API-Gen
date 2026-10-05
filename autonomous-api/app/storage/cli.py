"""Operational CLI for database backup, system checkpoints, and restore.

    python -m app.storage.cli backup  --database PATH --output PATH
        [--artifact-dir DIR --artifact-digest HEX]
    python -m app.storage.cli verify  --source PATH --digest HEX
    python -m app.storage.cli restore --database PATH --source PATH --digest HEX
        [--artifact-destination DIR]

Machine results go to stdout: the SHA-256 digest for a database image, a
single-line JSON document for a system checkpoint, and ``ok`` for
verify/restore. Diagnostics go to stderr. Exit status is 0 on success.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

from app.storage.backup import _integrity_check, _sha256, backup_sqlite_database, restore_sqlite_database
from app.storage.checkpoint import (
    MANIFEST_NAME,
    create_system_checkpoint,
    restore_system_checkpoint,
    verify_system_checkpoint,
)


def _engine_for(database: str) -> Engine:
    path = Path(database).resolve()
    return create_engine(URL.create("sqlite", database=str(path)))


def _is_checkpoint(source: Path) -> bool:
    return source.is_dir() and (source / MANIFEST_NAME).is_file()


def _cmd_backup(args: argparse.Namespace) -> int:
    if bool(args.artifact_dir) != bool(args.artifact_digest):
        raise ValueError("--artifact-dir and --artifact-digest must be given together")
    engine = _engine_for(args.database)
    if args.artifact_dir:
        manifest = create_system_checkpoint(
            engine,
            artifact_dir=args.artifact_dir,
            artifact_digest=args.artifact_digest,
            checkpoint_dir=args.output,
        )
        print(
            json.dumps(
                {
                    "artifact_digest": manifest["artifact_digest"],
                    "checkpoint_digest": manifest["checkpoint_digest"],
                    "database_digest": manifest["database_digest"],
                },
                sort_keys=True,
            )
        )
        return 0
    print(backup_sqlite_database(engine, args.output))
    return 0


def _cmd_verify(args: argparse.Namespace) -> int:
    source = Path(args.source)
    if _is_checkpoint(source):
        verify_system_checkpoint(str(source), expected_checkpoint_digest=args.digest)
    else:
        _integrity_check(source)
        if _sha256(source) != args.digest:
            raise ValueError("database backup digest mismatch")
    print("ok")
    return 0


def _cmd_restore(args: argparse.Namespace) -> int:
    source = Path(args.source)
    engine = _engine_for(args.database)
    if _is_checkpoint(source):
        if not args.artifact_destination:
            raise ValueError(
                "--artifact-destination is required to restore a system checkpoint"
            )
        restore_system_checkpoint(
            engine,
            str(source),
            expected_checkpoint_digest=args.digest,
            artifact_destination=args.artifact_destination,
        )
    else:
        restore_sqlite_database(engine, source, args.digest)
    print("ok")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.storage.cli",
        description="Integrity-checked database backup, system checkpoints, and restore.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    backup = subparsers.add_parser("backup", help="create a database image or a system checkpoint")
    backup.add_argument("--database", required=True, help="live SQLite database path")
    backup.add_argument("--output", required=True, help="backup image file or checkpoint directory")
    backup.add_argument("--artifact-dir", help="verified artifact tree (enables system checkpoint)")
    backup.add_argument("--artifact-digest", help="expected artifact digest (enables system checkpoint)")
    backup.set_defaults(func=_cmd_backup)

    verify = subparsers.add_parser("verify", help="verify a database image or a system checkpoint")
    verify.add_argument("--source", required=True, help="backup image file or checkpoint directory")
    verify.add_argument("--digest", required=True, help="expected digest")
    verify.set_defaults(func=_cmd_verify)

    restore = subparsers.add_parser("restore", help="restore a database image or a system checkpoint")
    restore.add_argument("--database", required=True, help="live SQLite database path")
    restore.add_argument("--source", required=True, help="backup image file or checkpoint directory")
    restore.add_argument("--digest", required=True, help="expected digest")
    restore.add_argument(
        "--artifact-destination",
        help="live artifact directory (required for a system checkpoint)",
    )
    restore.set_defaults(func=_cmd_restore)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
