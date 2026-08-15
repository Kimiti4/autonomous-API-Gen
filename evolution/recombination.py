"""
Evolutionary crossover and recombination.

This module recombines ISR payloads. It does not recombine source code.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, Field

from .models import CandidateArchitecture, utcnow
from .utils import canonical_json, deep_copy, deterministic_id, sha256_hex


ARCHITECTURAL_BLOCKS = (
    "architecture",
    "persistence",
    "infrastructure",
    "security",
    "messaging",
    "observability",
    "ai",
    "testing",
    "deployment",
    "frontend",
    "backend",
    "governance",
    "documentation",
    "performance",
    "reliability",
)


BLOCK_TO_OBJECTIVE = {
    "reliability": "reliability",
    "security": "security_posture",
    "performance": "performance_efficiency",
    "observability": "operational_stability",
    "infrastructure": "cost_efficiency",
    "frontend": "user_satisfaction",
    "testing": "testability",
    "deployment": "deployment_readiness",
    "documentation": "documentation_quality",
    "governance": "governance_readiness",
}


class RecombinationPolicy(BaseModel):
    """Policy controlling recombination behavior."""

    operator: str = "policy_block"

    max_offspring: int = Field(default=2, ge=1, le=10)

    preserve_base_identity: bool = True

    objective_prefix: str = "feedback_"

    seed: int = 0


class RecombinationContext(BaseModel):
    """Context supplied to recombination operators."""

    parent_candidate_ids: list[str] = Field(default_factory=list)

    objectives_by_parent: Dict[str, Dict[str, float]] = Field(
        default_factory=dict
    )

    genome: Optional[Dict[str, Any]] = None

    generation: int = 0


class OffspringCandidate(BaseModel):
    """Offspring produced by recombination."""

    id: str

    operator: str

    parent_candidate_ids: list[str] = Field(default_factory=list)

    base_parent_candidate_id: Optional[str] = None
    base_parent_content_hash: Optional[str] = None

    isr: Dict[str, Any]

    content_hash: str

    created_at: str


class RecombinationResult(BaseModel):
    """Result of a recombination operation."""

    operator: str

    parent_candidate_ids: list[str] = Field(default_factory=list)

    offspring: list[OffspringCandidate] = Field(default_factory=list)

    notes: list[str] = Field(default_factory=list)


class CrossoverOperator(Protocol):
    """Contract for crossover operators."""

    name: str

    def recombine(
        self,
        parent_a: Dict[str, Any],
        parent_b: Dict[str, Any],
        policy: RecombinationPolicy,
        context: RecombinationContext,
    ) -> List[Dict[str, Any]]:
        ...


def _objective_value(
    objectives: Dict[str, float],
    objective_name: str,
) -> Optional[float]:
    if not objectives:
        return None

    direct_keys = [
        objective_name,
        f"feedback_{objective_name}",
        f"compiler_{objective_name}",
    ]

    for key in direct_keys:
        if key in objectives:
            try:
                return float(objectives[key])
            except Exception:
                continue

    for key, value in objectives.items():
        if key.endswith(objective_name):
            try:
                return float(value)
            except Exception:
                continue

    return None


def _add_crossover_metadata(
    isr: Dict[str, Any],
    operator_name: str,
    context: RecombinationContext,
    offspring_role: str,
) -> None:
    evolution = isr.setdefault("evolution", {})

    crossovers = evolution.setdefault("crossovers", [])

    crossovers.append(
        {
            "operator": operator_name,
            "parent_candidate_ids": list(context.parent_candidate_ids),
            "generation": context.generation,
            "offspring_role": offspring_role,
        }
    )


class PolicyBlockCrossover:
    """
    Recombines top-level architectural policy blocks.

    This operator preserves domains and services from the base parent while
    recombining architectural policy blocks such as security, reliability,
    observability, deployment, and testing.
    """

    name = "policy_block"

    def recombine(
        self,
        parent_a: Dict[str, Any],
        parent_b: Dict[str, Any],
        policy: RecombinationPolicy,
        context: RecombinationContext,
    ) -> List[Dict[str, Any]]:
        parent_a_id = (
            context.parent_candidate_ids[0]
            if len(context.parent_candidate_ids) > 0
            else "parent_a"
        )

        parent_b_id = (
            context.parent_candidate_ids[1]
            if len(context.parent_candidate_ids) > 1
            else "parent_b"
        )

        blocks = self._select_blocks(parent_a, parent_b, context)

        choices_child_one: Dict[str, str] = {}
        choices_child_two: Dict[str, str] = {}

        for index, block in enumerate(blocks):
            has_a = block in parent_a
            has_b = block in parent_b

            if has_a and has_b:
                default_parent = (
                    parent_a_id
                    if index % 2 == 0
                    else parent_b_id
                )

                chosen_parent = self._choose_better_parent(
                    block=block,
                    parent_a_id=parent_a_id,
                    parent_b_id=parent_b_id,
                    objectives_by_parent=context.objectives_by_parent,
                    default_parent_id=default_parent,
                )

                choices_child_one[block] = chosen_parent

                choices_child_two[block] = (
                    parent_b_id
                    if chosen_parent == parent_a_id
                    else parent_a_id
                )

            elif has_a:
                choices_child_one[block] = parent_a_id
                choices_child_two[block] = parent_a_id

            else:
                choices_child_one[block] = parent_b_id
                choices_child_two[block] = parent_b_id

        child_one = self._build_offspring(
            parent_a=parent_a,
            parent_b=parent_b,
            parent_a_id=parent_a_id,
            parent_b_id=parent_b_id,
            choices=choices_child_one,
            policy=policy,
            context=context,
            offspring_role="policy_block_child_one",
        )

        child_two = self._build_offspring(
            parent_a=parent_a,
            parent_b=parent_b,
            parent_a_id=parent_a_id,
            parent_b_id=parent_b_id,
            choices=choices_child_two,
            policy=policy,
            context=context,
            offspring_role="policy_block_child_two",
        )

        return [child_one, child_two]

    def _select_blocks(
        self,
        parent_a: Dict[str, Any],
        parent_b: Dict[str, Any],
        context: RecombinationContext,
    ) -> List[str]:
        blocks = sorted(
            {
                block
                for block in ARCHITECTURAL_BLOCKS
                if block in parent_a or block in parent_b
            }
        )

        return blocks

    def _choose_better_parent(
        self,
        block: str,
        parent_a_id: str,
        parent_b_id: str,
        objectives_by_parent: Dict[str, Dict[str, float]],
        default_parent_id: str,
    ) -> str:
        objective_name = BLOCK_TO_OBJECTIVE.get(block, block)

        parent_a_objectives = objectives_by_parent.get(parent_a_id, {})
        parent_b_objectives = objectives_by_parent.get(parent_b_id, {})

        a_value = _objective_value(parent_a_objectives, objective_name)
        b_value = _objective_value(parent_b_objectives, objective_name)

        if a_value is None and b_value is None:
            return default_parent_id

        if a_value is None:
            return parent_b_id

        if b_value is None:
            return parent_a_id

        if a_value == b_value:
            return default_parent_id

        return parent_a_id if a_value > b_value else parent_b_id

    def _build_offspring(
        self,
        parent_a: Dict[str, Any],
        parent_b: Dict[str, Any],
        parent_a_id: str,
        parent_b_id: str,
        choices: Dict[str, str],
        policy: RecombinationPolicy,
        context: RecombinationContext,
        offspring_role: str,
    ) -> Dict[str, Any]:
        base_parent = parent_a if policy.preserve_base_identity else parent_b

        child = deep_copy(base_parent)

        for block in ARCHITECTURAL_BLOCKS:
            child.pop(block, None)

        for block, chosen_parent_id in choices.items():
            if chosen_parent_id == parent_a_id:
                value = parent_a.get(block)
            else:
                value = parent_b.get(block)

            if value is not None:
                child[block] = deep_copy(value)

        _add_crossover_metadata(
            isr=child,
            operator_name=self.name,
            context=context,
            offspring_role=offspring_role,
        )

        return child


class DomainCrossover:
    """
    Reconates domains and services.

    This operator merges domains from both parents. Shared domains merge
    services where possible.
    """

    name = "domain"

    def recombine(
        self,
        parent_a: Dict[str, Any],
        parent_b: Dict[str, Any],
        policy: RecombinationPolicy,
        context: RecombinationContext,
    ) -> List[Dict[str, Any]]:
        child_one = deep_copy(parent_a)
        child_two = deep_copy(parent_b)

        child_one["domains"] = self._merge_domains(
            parent_a.get("domains", []) or [],
            parent_b.get("domains", []) or [],
        )

        child_two["domains"] = self._merge_domains(
            parent_b.get("domains", []) or [],
            parent_a.get("domains", []) or [],
        )

        _add_crossover_metadata(
            isr=child_one,
            operator_name=self.name,
            context=context,
            offspring_role="domain_child_one",
        )

        _add_crossover_metadata(
            isr=child_two,
            operator_name=self.name,
            context=context,
            offspring_role="domain_child_two",
        )

        return [child_one, child_two]

    def _merge_domains(
        self,
        base_domains: List[Any],
        other_domains: List[Any],
    ) -> List[Any]:
        domains_by_name: Dict[str, Dict[str, Any]] = {}

        for domain in base_domains:
            normalized = self._normalize_domain(domain)
            domains_by_name[normalized["name"]] = normalized

        for domain in other_domains:
            normalized = self._normalize_domain(domain)

            existing = domains_by_name.get(normalized["name"])

            if not existing:
                domains_by_name[normalized["name"]] = normalized
                continue

            existing["services"] = self._merge_services(
                existing.get("services", []) or [],
                normalized.get("services", []) or [],
            )

        return sorted(
            domains_by_name.values(),
            key=lambda domain: domain.get("name", ""),
        )

    def _normalize_domain(self, domain: Any) -> Dict[str, Any]:
        if isinstance(domain, str):
            return {
                "name": domain,
                "services": [],
            }

        if isinstance(domain, dict):
            normalized = deep_copy(domain)

            normalized.setdefault("name", "UnnamedDomain")
            normalized.setdefault("services", [])

            return normalized

        return {
            "name": "UnnamedDomain",
            "services": [],
        }

    def _merge_services(
        self,
        base_services: List[Any],
        other_services: List[Any],
    ) -> List[Any]:
        services_by_name: Dict[str, Dict[str, Any]] = {}

        for service in base_services:
            normalized = self._normalize_service(service)
            services_by_name[normalized["name"]] = normalized

        for service in other_services:
            normalized = self._normalize_service(service)

            existing = services_by_name.get(normalized["name"])

            if not existing:
                services_by_name[normalized["name"]] = normalized
                continue

            existing["apis"] = self._merge_apis(
                existing.get("apis", []) or [],
                normalized.get("apis", []) or [],
            )

            existing_depends_on = set(
                existing.get("depends_on", []) or []
            )

            other_depends_on = set(
                normalized.get("depends_on", []) or []
            )

            existing["depends_on"] = sorted(
                existing_depends_on.union(other_depends_on)
            )

        return sorted(
            services_by_name.values(),
            key=lambda service: service.get("name", ""),
        )

    def _normalize_service(self, service: Any) -> Dict[str, Any]:
        if isinstance(service, str):
            return {
                "name": service,
                "apis": [],
                "depends_on": [],
            }

        if isinstance(service, dict):
            normalized = deep_copy(service)

            normalized.setdefault("name", "UnnamedService")
            normalized.setdefault("apis", [])
            normalized.setdefault("depends_on", [])

            return normalized

        return {
            "name": "UnnamedService",
            "apis": [],
            "depends_on": [],
        }

    def _merge_apis(
        self,
        base_apis: List[Any],
        other_apis: List[Any],
    ) -> List[Any]:
        merged: List[Any] = []
        seen_names: set[str] = set()

        for api in base_apis:
            merged.append(deep_copy(api))
            seen_names.add(self._api_name(api))

        for api in other_apis:
            name = self._api_name(api)

            if name not in seen_names:
                merged.append(deep_copy(api))
                seen_names.add(name)

        return merged

    def _api_name(self, api: Any) -> str:
        if isinstance(api, str):
            return api

        if isinstance(api, dict):
            return str(api.get("name", ""))

        return ""


class GenomeGuidedCrossover(PolicyBlockCrossover):
    """
    Genome-guided policy-block crossover.

    If a genome is present in the context, only active chromosome families
    are recombined. Inactive families remain inherited from the base parent.
    """

    name = "genome_guided"

    def _select_blocks(
        self,
        parent_a: Dict[str, Any],
        parent_b: Dict[str, Any],
        context: RecombinationContext,
    ) -> List[str]:
        blocks = super()._select_blocks(parent_a, parent_b, context)

        genome = context.genome

        if not genome:
            return blocks

        genes = genome.get("genes", []) or []

        active_blocks: set[str] = set()

        for gene in genes:
            if not isinstance(gene, dict):
                continue

            if not gene.get("active", True):
                continue

            family = str(gene.get("chromosome_family", "")).lower()

            if family in ARCHITECTURAL_BLOCKS:
                active_blocks.add(family)

        if not active_blocks:
            return blocks

        return [
            block
            for block in blocks
            if block in active_blocks
        ]


class RecombinationEngine:
    """Coordinates recombination operators."""

    def __init__(
        self,
        operators: Optional[Dict[str, CrossoverOperator]] = None,
    ) -> None:
        self.operators = operators or {
            "policy_block": PolicyBlockCrossover(),
            "domain": DomainCrossover(),
            "genome_guided": GenomeGuidedCrossover(),
        }

    def recombine_candidates(
        self,
        parent_a: Any,
        parent_b: Any,
        policy: Optional[RecombinationPolicy] = None,
        context: Optional[RecombinationContext] = None,
    ) -> RecombinationResult:
        policy = policy or RecombinationPolicy()

        parent_a_isr = self._extract_isr(parent_a)
        parent_b_isr = self._extract_isr(parent_b)

        parent_a_id = self._extract_candidate_id(parent_a, "parent_a")
        parent_b_id = self._extract_candidate_id(parent_b, "parent_b")

        if context is None:
            context = RecombinationContext(
                parent_candidate_ids=[parent_a_id, parent_b_id],
            )
        else:
            if not context.parent_candidate_ids:
                context.parent_candidate_ids = [parent_a_id, parent_b_id]

        operator = self.operators.get(policy.operator)

        if not operator:
            raise ValueError(
                f"Unknown recombination operator: {policy.operator}"
            )

        offspring_isrs = operator.recombine(
            parent_a=parent_a_isr,
            parent_b=parent_b_isr,
            policy=policy,
            context=context,
        )

        offspring: List[OffspringCandidate] = []

        parent_a_content_hash = self._extract_content_hash(
            parent_a,
            parent_a_isr,
        )

        for index, offspring_isr in enumerate(offspring_isrs):
            if len(offspring) >= policy.max_offspring:
                break

            content_hash = sha256_hex(canonical_json(offspring_isr))

            offspring_id = deterministic_id(
                "offspring_candidate",
                {
                    "operator": operator.name,
                    "parent_a_id": parent_a_id,
                    "parent_b_id": parent_b_id,
                    "index": index,
                    "content_hash": content_hash,
                },
            )

            offspring.append(
                OffspringCandidate(
                    id=offspring_id,
                    operator=operator.name,
                    parent_candidate_ids=[parent_a_id, parent_b_id],
                    base_parent_candidate_id=parent_a_id,
                    base_parent_content_hash=parent_a_content_hash,
                    isr=offspring_isr,
                    content_hash=content_hash,
                    created_at=utcnow().isoformat(),
                )
            )

        return RecombinationResult(
            operator=operator.name,
            parent_candidate_ids=[parent_a_id, parent_b_id],
            offspring=offspring,
            notes=[
                f"Produced {len(offspring)} offspring using "
                f"{operator.name} crossover."
            ],
        )

    def _extract_isr(self, candidate: Any) -> Dict[str, Any]:
        if isinstance(candidate, dict):
            return candidate

        isr = getattr(candidate, "isr", None)

        if not isinstance(isr, dict):
            raise ValueError("Candidate does not contain an ISR payload.")

        return isr

    def _extract_candidate_id(self, candidate: Any, fallback: str) -> str:
        candidate_id = getattr(candidate, "id", None)

        if candidate_id:
            return str(candidate_id)

        return fallback

    def _extract_content_hash(
        self,
        candidate: Any,
        isr: Dict[str, Any],
    ) -> str:
        content_hash = getattr(candidate, "content_hash", None)

        if content_hash:
            return str(content_hash)

        return sha256_hex(canonical_json(isr))


def register_offspring_candidate(
    base_engine,
    proposal_id: str,
    offspring: OffspringCandidate,
) -> CandidateArchitecture:
    """Register recombined offspring as a candidate in a proposal."""

    proposal = base_engine._get_proposal(proposal_id)

    candidate_id = deterministic_id(
        "candidate",
        {
            "proposal_id": proposal_id,
            "offspring_id": offspring.id,
        },
    )

    candidate = CandidateArchitecture(
        id=candidate_id,
        proposal_id=proposal_id,
        mutation_spec_id=f"crossover:{offspring.operator}",
        base_isr_hash=offspring.base_parent_content_hash
        or offspring.content_hash,
        content_hash=offspring.content_hash,
        isr=offspring.isr,
        created_at=utcnow().isoformat(),
    )

    base_engine.candidates[candidate_id] = candidate

    if candidate_id not in proposal.candidate_ids:
        proposal.candidate_ids.append(candidate_id)

    base_engine.history.record(
        proposal_id=proposal_id,
        event_type="offspring_candidate_registered",
        actor_id="recombination_engine",
        details={
            "candidate_id": candidate_id,
            "offspring_id": offspring.id,
            "operator": offspring.operator,
            "parent_candidate_ids": offspring.parent_candidate_ids,
        },
    )

    return candidate
