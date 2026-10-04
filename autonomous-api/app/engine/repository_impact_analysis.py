"""Deterministic dependency impact analysis for repository findings."""

from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import re
from collections import defaultdict, deque
from typing import Iterable

@dataclass(frozen=True)
class ImpactNode:
    path: str
    distance: int
    relationship: str

@dataclass(frozen=True)
class ImpactAnalysis:
    finding_id: str
    source_path: str
    affected: tuple[ImpactNode, ...]
    digest: str

_IMPORT_PATTERNS=(
    re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)"),
    re.compile(r"^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+"),
)

def analyze_finding_impact(
    finding_id: str,
    source_path: str,
    files: Iterable[tuple[str,str]],
) -> ImpactAnalysis:
    ordered=sorted(files,key=lambda x:x[0])
    known={p for p,_ in ordered}
    graph=defaultdict(set)
    module_to_path={_module_name(p):p for p in known}
    for path,source in ordered:
        for line in source.splitlines():
            for pattern in _IMPORT_PATTERNS:
                match=pattern.search(line)
                if not match:
                    continue
                module=match.group(1)
                target=module_to_path.get(module) or module_to_path.get(module.split(".")[0])
                if target and target != path:
                    graph[target].add(path)
    distances={source_path:0}
    queue=deque([source_path])
    while queue:
        current=queue.popleft()
        for dependent in sorted(graph[current]):
            if dependent not in distances:
                distances[dependent]=distances[current]+1
                queue.append(dependent)
    affected=tuple(
        ImpactNode(path,d,"direct-dependent" if d==1 else "transitive-dependent")
        for path,d in sorted(distances.items(),key=lambda x:(x[1],x[0]))
        if path != source_path
    )
    canonical="|".join(f"{n.path}:{n.distance}:{n.relationship}" for n in affected)
    digest=sha256(f"{finding_id}|{source_path}|{canonical}".encode()).hexdigest()
    return ImpactAnalysis(finding_id,source_path,affected,digest)

def _module_name(path:str)->str:
    if path.endswith(".py"):
        return path[:-3].replace("/","\.").replace("\","_").replace(".__init__","")
    return path.replace("/","\.").replace("\","_")
