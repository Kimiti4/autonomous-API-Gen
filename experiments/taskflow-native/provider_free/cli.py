"""Command-line entry point for offline acceptance analysis.

Run from the TaskFlow trial directory:
    python -m provider_free.cli --acceptance /path/to/ACCEPTANCE.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .requirements import analyze_acceptance


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze a structured ESAP acceptance contract offline."
    )
    parser.add_argument(
        "--acceptance",
        required=True,
        type=Path,
        help="Path to the canonical or snapshotted ACCEPTANCE.json file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the JSON report; stdout is used when omitted.",
    )
    args = parser.parse_args(argv)

    try:
        acceptance = json.loads(args.acceptance.read_text(encoding="utf-8"))
        result = analyze_acceptance(acceptance, source=str(args.acceptance)).as_dict()
        rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"provider-free analysis failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
