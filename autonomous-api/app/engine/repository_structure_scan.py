"""Evidence-first structural repository analysis for ESAP."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Iterable


@dataclass(frozen=True)
class StructuralFinding:
    finding_id: str
    category: str
    severity: str
    path: str
    line: int
    rule: str
    message: str
    evidence: tuple[str, ...]
    repairable: bool

    @property
    def digest(self) -> str:
        return sha256("|".join((self.finding_id,self.category,self.severity,self.path,
            str(self.line),self.rule,self.message,*self.evidence)).encode()).hexdigest()


@dataclass(frozen=True)
class StructuralScan:
    files_scanned: int
    imports: tuple[tuple[str,str],...]
    findings: tuple[StructuralFinding,...]
    digest: str


_IMPORT_PATTERNS = (
    re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)"),
    re.compile(r"^\s*from\s+([A-Za-z_][\w.]*)\s+import\s+"),
)


def analyze_repository_structure(files: Iterable[tuple[str,str]]) -> StructuralScan:
    ordered=sorted(files,key=lambda x:x[0])
    imports=[]; findings=[]
    known={p for p,_ in ordered}
    for path,source in ordered:
        for n,line in enumerate(source.splitlines(),1):
            match=next((p.search(line) for p in _IMPORT_PATTERNS if p.search(line)),None)
            if match:
                module=match.group(1); imports.append((path,module))
                local=module.replace(".","/")+".py"
                if local not in known and module.split(".")[0] not in {"os","sys","re","typing","json","math","pytest"}:
                    findings.append(_finding(path,n,"dependency-risk","medium","unresolved-local-import",
                        f"imported module may be absent from supplied repository: {module}"))
            if len(line.rstrip()) > 120:
                findings.append(_finding(path,n,"code-smell","low","long-line",
                    "line exceeds 120 characters; inspect for readability/maintainability"))
            if re.search(r"\bif\s+False\s*:",line):
                findings.append(_finding(path,n,"bug-risk","high","dead-branch","constant-false branch detected"))
    canonical="\n".join(f.digest for f in findings)+"|"+"\n".join(f"{a}:{b}" for a,b in imports)
    return StructuralScan(len(ordered),tuple(imports),tuple(findings),sha256(canonical.encode()).hexdigest())


def _finding(path,line,category,severity,rule,message):
    fid=sha256(f"{path}:{line}:{rule}:{message}".encode()).hexdigest()[:20]
    return StructuralFinding(fid,category,severity,path,line,rule,message,
        (f"{path}:{line}",message),True)
