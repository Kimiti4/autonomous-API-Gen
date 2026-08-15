"""
Phase 0: Constitutional Stabilization — ConstitutionValidator.

Automated gatekeeper that enforces all 7 axioms of the Core Constitution.
Designed to run in CI/CD pipelines, pre-commit hooks, and at runtime
to validate ISR mutations and compiler backend implementations.

Axiom Checks:
  I.   ISR Supremacy — scans ISR instances for the Forbidden Lexicon
  II.  Genome Isolation — verifies evolution flows through Transcriber
  III. Compiler Purity — ensures compilers don't modify the ISR
  IV.  Knowledge Externality — audits operators for hardcoded heuristics
  V.   Dual-Track Evolution — verifies both tracks in every run
  VI.  Boundary Integrity — traces transformation lineages
  VII. Auditability — checks provenance metadata completeness

Runtime Governance:
  - validate_isr_mutation()  — full ISR governance gate (tech agnosticism,
                               security by design, acyclic deps)
  - validate_compiler_purity() — runtime check that a CompilerBackend
                                 does not mutate the UniversalISR it receives
"""

from __future__ import annotations

import ast
import copy
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Violation:
    axiom: str
    description: str
    file: str = ""
    line: int = 0
    severity: str = "error"


@dataclass
class ValidationResult:
    passed: bool = True
    violations: list[Violation] = field(default_factory=list)
    constitution_version: str = "v1.0.0"


class ConstitutionalViolation(Exception):
    """Raised when a constitutional rule is violated at runtime."""


class ConstitutionValidator:
    """Validates the codebase against the 7 constitutional axioms.

    Also provides runtime governance gates for ISR mutations and
    compiler backend purity enforcement.
    """

    def __init__(self, repo_root: str = "") -> None:
        self._repo_root = repo_root or os.getcwd()
        self._forbidden_lexicon = self._load_lexicon()

    def _load_lexicon(self) -> set[str]:
        """Load the Forbidden Lexicon from the core constitution module."""
        from constitutional_architecture.core.constitution import FORBIDDEN_LEXICON
        return set(FORBIDDEN_LEXICON)

    # ==========================================================================
    # Axiom I: ISR Supremacy
    # ==========================================================================

    def check_isr_purity(self, isr_text: str, source_file: str = "") -> list[Violation]:
        violations: list[Violation] = []
        text_lower = isr_text.lower()

        for term in sorted(self._forbidden_lexicon, key=len, reverse=True):
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text_lower):
                violations.append(Violation(
                    axiom="I",
                    description=f"ISR contains forbidden term '{match.group()}' — must be replaced with abstract equivalent",
                    file=source_file,
                    line=self._count_lines(isr_text[:match.start()]),
                    severity="error",
                ))
        return violations

    # ==========================================================================
    # Axiom II: Genome Isolation
    # ==========================================================================

    def check_genome_isolation(self, python_source: str, source_file: str = "") -> list[Violation]:
        violations: list[Violation] = []
        try:
            tree = ast.parse(python_source)
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                call_name = ""
                if isinstance(func, ast.Attribute):
                    call_name = f"{self._get_full_name(func)}"
                elif isinstance(func, ast.Name):
                    call_name = func.id

                if not call_name:
                    continue

                isr_write_patterns = [
                    ".tokens[", ".components.", ".layouts.",
                    ".pages.", ".design_system.",
                ]
                isr_exact_names = ["ISR"]

                is_match = False
                for pattern in isr_write_patterns:
                    if pattern in call_name:
                        is_match = True
                        break
                if call_name in isr_exact_names:
                    is_match = True

                if is_match and self._is_outside_transcriber(python_source, node):
                    violations.append(Violation(
                        axiom="II",
                        description=f"Direct ISR construction/write '{call_name}' outside Transcriber — "
                                    f"evolution must flow through Genome -> Transcriber -> ISR",
                        file=source_file,
                        line=node.lineno if hasattr(node, 'lineno') else 0,
                        severity="error",
                    ))
        return violations

    # ==========================================================================
    # Axiom III: Compiler Purity
    # ==========================================================================

    def check_compiler_purity(self, python_source: str, source_file: str = "") -> list[Violation]:
        violations: list[Violation] = []
        is_compiler = "compiler" in source_file.lower() or "backend" in source_file.lower()

        if not is_compiler:
            return violations

        try:
            tree = ast.parse(python_source)
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if "isr.model" in (node.module or "") and alias.name not in ("FrontendISRProfile",):
                        violations.append(Violation(
                            axiom="III",
                            description=f"Compiler imports '{node.module}.{alias.name}' — "
                                        f"compilers may read ISR profiles but must not import ISR model types",
                            file=source_file,
                            line=node.lineno,
                            severity="error",
                        ))
        return violations

    # ==========================================================================
    # Axiom IV: Knowledge Externality
    # ==========================================================================

    def check_knowledge_externality(self, python_source: str, source_file: str = "") -> list[Violation]:
        violations: list[Violation] = []
        hardcoded_heuristic_patterns = [
            r'typography.*modular.*scale.*=.*1\.\d+',
            r'spacing.*base.*unit.*=.*\d+',
            r'density.*profile.*=.*0\.\d+',
        ]

        try:
            tree = ast.parse(python_source)
        except SyntaxError:
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Attribute):
                        attr_path = f"{self._get_full_name(target.value)}.{target.attr}"
                        for pattern_name in ("typography_scale", "spacing_scale", "density_profile"):
                            if pattern_name in attr_path and isinstance(node.value, ast.Constant):
                                violations.append(Violation(
                                    axiom="IV",
                                    description=f"Hardcoded genome allele '{attr_path} = {node.value.value}' "
                                                f"— heuristics should come from CKB, not hardcoded constants",
                                    file=source_file,
                                    line=node.lineno,
                                    severity="warning",
                                ))
        return violations

    # ==========================================================================
    # Axiom V: Dual-Track Evolution
    # ==========================================================================

    def check_dual_track_evolution(self, evaluator_names: list[str]) -> list[Violation]:
        violations: list[Violation] = []
        functional = any("Consistency" in n or "Hierarchy" in n for n in evaluator_names)
        non_functional = any("Accessibility" in n or "Quality" in n or "Performance" in n for n in evaluator_names)

        if not functional:
            violations.append(Violation(
                axiom="V",
                description="No functional evaluator found — at least one required (e.g., TokenConsistencyEvaluator)",
                severity="error",
            ))
        if not non_functional:
            violations.append(Violation(
                axiom="V",
                description="No non-functional evaluator found — at least one required (e.g., AccessibilityEvaluator)",
                severity="error",
            ))
        return violations

    # ==========================================================================
    # Axiom VI: Boundary Integrity
    # ==========================================================================

    def check_boundary_integrity(self, import_graph: dict[str, set[str]]) -> list[Violation]:
        violations: list[Violation] = []

        forbidden_shortcuts = [
            ("requirements", "isr"),       # Pass 1-2 -> Pass 6 (skip 3-5)
            ("genome", "code"),             # Pass 4-5 -> Pass 9 (skip 6-8)
            ("intent", "compiler"),         # Pass 2 -> Pass 8 (skip 3-7)
        ]

        for module, imports in import_graph.items():
            for source_pattern, target_pattern in forbidden_shortcuts:
                if source_pattern in module.lower():
                    for imp in imports:
                        if target_pattern in imp.lower():
                            violations.append(Violation(
                                axiom="VI",
                                description=f"'{module}' imports '{imp}' — bypasses required pipeline stages "
                                            f"({source_pattern} -> {target_pattern} shortcut)",
                                file=module,
                                severity="warning",
                            ))
        return violations

    # ==========================================================================
    # Axiom VII: Auditability
    # ==========================================================================

    def check_auditability(self, provenance_data: dict[str, Any]) -> list[Violation]:
        violations: list[Violation] = []
        required_fields = ["parent_hash", "version", "created_at", "source_pass"]

        for artifact_id, metadata in provenance_data.items():
            for field in required_fields:
                if field not in metadata:
                    violations.append(Violation(
                        axiom="VII",
                        description=f"Artifact '{artifact_id}' missing required provenance field '{field}'",
                        severity="error",
                    ))
                elif metadata.get(field) is None:
                    violations.append(Violation(
                        axiom="VII",
                        description=f"Artifact '{artifact_id}' has null provenance field '{field}'",
                        severity="error",
                    ))
        return violations

    # ==========================================================================
    # Full validation
    # ==========================================================================

    def validate_all(
        self,
        isr_text: str = "",
        intent_text: str = "",
        python_files: Optional[dict[str, str]] = None,
        evaluator_names: Optional[list[str]] = None,
        import_graph: Optional[dict[str, set[str]]] = None,
        provenance_data: Optional[dict[str, Any]] = None,
    ) -> ValidationResult:
        result = ValidationResult()

        if isr_text:
            result.violations.extend(self.check_isr_purity(isr_text))

        if intent_text:
            result.violations.extend(self.check_intent_model_purity(intent_text))

        if python_files:
            for filepath, source in python_files.items():
                result.violations.extend(self.check_genome_isolation(source, filepath))
                result.violations.extend(self.check_compiler_purity(source, filepath))
                result.violations.extend(self.check_knowledge_externality(source, filepath))

        if evaluator_names:
            result.violations.extend(self.check_dual_track_evolution(evaluator_names))

        if import_graph:
            result.violations.extend(self.check_boundary_integrity(import_graph))

        if provenance_data:
            result.violations.extend(self.check_auditability(provenance_data))

        severity_errors = [v for v in result.violations if v.severity == "error"]
        if severity_errors:
            result.passed = False

        return result

    # ==========================================================================
    # Phase 0 Runtime Governance: ISR Mutation Gate
    # ==========================================================================

    def validate_isr_mutation(self, isr: Any) -> None:
        """Validate a UniversalISR against all governance rules.

        Checks (in order):
          1. Technology agnosticism — every node attribute is scanned
             for the Forbidden Lexicon.
          2. Security by design — every Service/APIEndpoint must depend
             on a SecurityPolicy node.
          3. Acyclic dependencies — the ISR dependency graph must not
             contain cycles.

        Raises ConstitutionalViolation on first failure.
        """
        from constitutional_architecture.core.governance import GovernanceRules

        for node_id, node in isr.nodes.items():
            if not GovernanceRules.is_technology_agnostic(node.attributes):
                raise ConstitutionalViolation(
                    f"ISR Node '{node_id}' contains forbidden technology coupling. "
                    f"Move implementation details to a Compiler Backend."
                )

        if not GovernanceRules.has_security_by_design(isr.nodes):
            raise ConstitutionalViolation(
                "ISR violates Security by Design. All Services/APIs must depend on a SecurityPolicy."
            )

        if self._has_cycles(isr):
            raise ConstitutionalViolation(
                "ISR contains cyclic dependencies between domains/services. Modularity violated."
            )

    def _has_cycles(self, isr: Any) -> bool:
        """DFS-based cycle detection in the ISR dependency graph."""
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)
            for neighbor in isr.nodes[node_id].dependencies:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            rec_stack.remove(node_id)
            return False

        for node_id in isr.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    # ==========================================================================
    # Intent Model Purity (Pass 1-2 boundary enforcement)
    # ==========================================================================

    def check_intent_model_purity(self, text: str, source_file: str = "") -> list[Violation]:
        """Scan text for forbidden terms that leaked into an IntentModel.

        Constitutional: If a user prompt results in an IntentModel containing
        a forbidden technology term (e.g., "React", "Tailwind"), the validator
        must reject it. The IntentAnalyzer should have already abstracted these
        via sanitize_forbidden_terms() — this is the defensive gate.
        """
        violations: list[Violation] = []
        text_lower = text.lower()

        for term in sorted(self._forbidden_lexicon, key=len, reverse=True):
            pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for match in pattern.finditer(text_lower):
                violations.append(Violation(
                    axiom="I",
                    description=f"IntentModel contains forbidden term '{match.group()}' — "
                                f"must be abstracted via sanitize_forbidden_terms() before Pass 2 output",
                    file=source_file,
                    line=self._count_lines(text[:match.start()]),
                    severity="error",
                ))
        return violations

    # ==========================================================================
    # Phase 0 Runtime Governance: Compiler Purity Gate
    # ==========================================================================

    def validate_compiler_purity(self, backend: Any, test_isr: Any) -> None:
        """Verify that a CompilerBackend does not mutate the UniversalISR.

        Takes a deep copy of the ISR before compilation, then compares
        after. Raises ConstitutionalViolation if any mutation occurred.

        Args:
            backend: An instance of a CompilerBackend subclass.
            test_isr: A UniversalISR instance to compile.
        """
        isr_snapshot = copy.deepcopy(test_isr)
        backend.compile(test_isr, "test_profile", {})
        if test_isr != isr_snapshot:
            raise ConstitutionalViolation(
                f"Compiler Backend '{backend.__class__.__name__}' illegally "
                f"mutated the Universal ISR. Compilers must be pure functions."
            )

    # ==========================================================================
    # Helpers
    # ==========================================================================

    def _is_outside_transcriber(self, source: str, node: ast.AST) -> bool:
        """Check if this node appears outside a Transcriber class."""
        lines = source.split('\n')
        for i in range(node.lineno - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith('class ') and 'Transcriber' not in line:
                return True
            if line.startswith('class ') and 'Transcriber' in line:
                return False
        return True

    def _get_full_name(self, node: ast.AST) -> str:
        parts: list[str] = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))

    @staticmethod
    def _count_lines(text: str) -> int:
        return text.count('\n') + 1
