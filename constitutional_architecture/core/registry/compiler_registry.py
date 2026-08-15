from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from constitutional_architecture.core.contracts.compiler import CompilerBackend
from constitutional_architecture.core.models.genome import ArchitectureGenome
from constitutional_architecture.core.models.isr import UniversalISR


class CompilerMetadata:
    def __init__(
        self,
        compiler_id: str,
        target_technology: str,
        supported_domains: List[str],
        required_genes: Optional[List[str]] = None,
        meta_compiler: bool = False,
    ) -> None:
        self.compiler_id = compiler_id
        self.target_technology = target_technology
        self.supported_domains = supported_domains
        self.required_genes = required_genes or []
        self.meta_compiler = meta_compiler


class CompilerRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Type[CompilerBackend]] = {}
        self._metadata: Dict[str, CompilerMetadata] = {}

    def register(self, compiler_class: Type[CompilerBackend], metadata: CompilerMetadata) -> None:
        self._registry[metadata.compiler_id] = compiler_class
        self._metadata[metadata.compiler_id] = metadata

    def resolve_compilers(self, genome: ArchitectureGenome, isr: UniversalISR) -> List[str]:
        required_compilers: List[str] = []

        for comp_id, meta in self._metadata.items():
            if meta.meta_compiler:
                continue
            genes_present = all(
                genome.get_gene(gene) is not None
                for gene in meta.required_genes
            )
            if genes_present:
                required_compilers.append(comp_id)

        return required_compilers

    def resolve_meta_compilers(self) -> List[str]:
        return [
            comp_id
            for comp_id, meta in self._metadata.items()
            if meta.meta_compiler
        ]

    def get_compiler(self, compiler_id: str) -> CompilerBackend:
        if compiler_id not in self._registry:
            raise ValueError(f"Compiler '{compiler_id}' not found in registry.")
        return self._registry[compiler_id]()
