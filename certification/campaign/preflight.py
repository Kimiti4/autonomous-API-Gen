"""Execution-environment port preflight for Campaign B.

The campaign allocates a contiguous host-port window whose stability the
runtime depends on (Windows host-ported Docker frequently reserves excluded
ranges via Hyper-V/WSL — binding those exact ports fails with the daemon error
"ports are not available ... forbidden by its access permissions").

This is an EXPLICIT preparation step, not a hidden retry mechanism:

    environment preflight
        |-> TCP excluded-port assessment
        |-> free contiguous window selection
        |-> capacity check
        |-> evidence record (excluded ranges, chosen base, capacity verdict)

If the environment cannot provide the required port capacity, the campaign
must fail/stop honestly rather than silently changing the workload.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from certification.campaign.waves import portpool_path_for


Range = tuple[int, int]

DEFAULT_PREFERRED = (8000, 9999)
DEFAULT_SPAN = 1000
DEFAULT_MIN_FREE = 936  # B3 scale 12: 468 intents x 2 backends


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def query_excluded_tcp_ranges() -> list[Range]:
    """Host TCP ports currently excluded from user binding (OS dependant).

    Windows: `netsh interface ipv4 show excludedportrange protocol=tcp`.
    Non-Windows hosts (or a failed probe) -> [] (no assessment available;
    the caller treats this as "no excluded ranges known" for the window
    decision, which is the honest neutral value on hosts without exclusion).
    """
    if os.name != "nt":
        return []
    try:
        p = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "excludedportrange", "protocol=tcp"],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return []
    ranges: list[Range] = []
    for line in p.stdout.splitlines():
        m = re.match(r"^\s*(\d+)\s+(\d+)\s*$", line)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start <= end:
                ranges.append((start, end))
    return ranges


def _free_window(
    preferred: Range, span: int, excluded: list[Range],
) -> Range | None:
    """Return the lowest contiguous span-long window wholly outside `excluded`.

    Merges overlapping/nested excluded ranges first, then scans the preferred
    window left-to-right.  Returns None when no spanning window exists.
    """
    if span <= 0:
        return None
    lo, hi = preferred
    if lo + span - 1 > hi:
        return None
    if not excluded:
        return (lo, lo + span - 1)
    merged: list[Range] = []
    for s, e in sorted(excluded):
        if merged and s <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    cursor = lo
    for s, e in merged:
        if e < lo:
            continue
        if cursor + span - 1 < s:
            return (cursor, cursor + span - 1)
        cursor = max(cursor, e + 1)
        if cursor + span - 1 > hi:
            break
    if cursor + span - 1 <= hi:
        return (cursor, cursor + span - 1)
    return None


@dataclass(frozen=True)
class PortAllocation:
    ok: bool
    base: int
    span: int
    excluded_ranges: tuple[Range, ...]
    window: tuple[int, int] | None
    reason: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def allocate_port_window(
    preferred: Range = DEFAULT_PREFERRED,
    span: int = DEFAULT_SPAN,
    min_free: int = DEFAULT_MIN_FREE,
    excluded: list[Range] | None = None,
) -> PortAllocation:
    """Choose a host TCP window for trial container port mapping.

    The window spans `span` consecutive host ports that are ALL available (no
    intersection with excluded ranges).  If no window of at least `min_free`
    consecutive ports exists in the preferred range, the allocation FAILS —
    the campaign must stop honestly, never silently reuse/overlap ports.
    """
    excluded = list(excluded or [])
    win = _free_window(preferred, span, excluded)
    if win is None:
        # Fall back to "as contiguous as possible": if the window intersects
        # exclusions, capacity is genuinely short -> fail for the requested span.
        return PortAllocation(
            ok=False, base=preferred[0], span=span,
            excluded_ranges=tuple(excluded), window=None,
            reason=(
                f"no {span}-port contiguous window in {preferred[0]}..{preferred[1]} "
                f"free of excluded ranges {excluded}"
            ),
        )
    usable = win[1] - win[0] + 1
    if usable < min_free:
        return PortAllocation(
            ok=False, base=win[0], span=span,
            excluded_ranges=tuple(excluded), window=win,
            reason=f"only {usable} contiguous free ports < required {min_free}",
        )
    return PortAllocation(
        ok=True, base=win[0], span=span,
        excluded_ranges=tuple(excluded), window=win,
        reason=f"contiguous free window {win[0]}..{win[1]} ({usable} ports)",
    )


def preflight_ports(
    wave_id: str,
    preferred: Range = DEFAULT_PREFERRED,
    span: int = DEFAULT_SPAN,
    min_free: int = DEFAULT_MIN_FREE,
) -> tuple[PortAllocation, str]:
    """Run the explicit environment preflight and persist its evidence.

    Returns (allocation, evidence_path).  The evidence file records the
    assessment and the chosen window so the campaign's port strategy is
    auditable — preparation is a first-class artifact, not a hidden retry.
    """
    excluded = query_excluded_tcp_ranges()
    alloc = allocate_port_window(
        preferred=preferred, span=span, min_free=min_free, excluded=excluded,
    )
    record = {
        "wave": wave_id,
        "assessed_at": _now_iso(),
        "host_os": os.name,
        "excluded_tcp_ranges_count": len(excluded),
        "excluded_tcp_ranges": excluded,
        "preferred": list(preferred),
        "span": span,
        "min_free_required": min_free,
        "allocation": alloc.to_dict(),
    }
    path = portpool_path_for(wave_id)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return alloc, path


def port_for_trial(trial_id: str, base: int, span: int) -> int:
    """Deterministic per-trial host port inside the allocated window (base..base+span)."""
    h = int.from_bytes(trial_id.encode("utf-8")[:8].ljust(8, b"\0"), "big")
    return base + (h % span)