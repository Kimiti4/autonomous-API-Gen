"""
Knowledge Compiler.

The Knowledge Compiler transforms source artifacts into Knowledge Graph
entities and relations.

For Phase 23 v0.1, the primary source is the ISR.

Constitutional rule:
- The Knowledge Compiler projects ISR into knowledge entities.
- It must not mutate ISR.
"""

from __future__ import annotations

from typing import Any

from .ids import deterministic_id
from .models import (
    EntityCreate,
    IngestionResult,
    RelationCreate,
    SourceRef,
)
from .runtime import GraphRuntime


class KnowledgeCompiler:
    """
    Compiles source artifacts into Knowledge Graph projections.
    """

    def __init__(self, runtime: GraphRuntime) -> None:
        self._runtime = runtime

    def compile_isr_revision(
        self,
        source_ref: SourceRef,
        payload: dict[str, Any],
    ) -> IngestionResult:
        """
        Compile an ISR revision into knowledge entities and relations.

        Expected payload shape:

        {
          "name": "BillingISR",
          "requirements": [
            {
              "name": "Billing requirement",
              "satisfied_by": ["BillingService"]
            }
          ],
          "domains": [
            {
              "name": "billing",
              "services": [
                {
                  "name": "BillingService",
                  "apis": ["createInvoice"],
                  "produces_events": ["InvoiceCreated"],
                  "consumes_events": [],
                  "data_models": ["Invoice"],
                  "depends_on": []
                }
              ]
            }
          ]
        }
        """

        produced_entities: set[str] = set()
        produced_relations: set[str] = set()
        service_map: dict[str, str] = {}
        requirement_links: list[tuple[str, list[str]]] = []

        def add_entity(
            entity_type: str,
            namespace: str,
            name: str,
            description: str | None = None,
            properties: dict[str, Any] | None = None,
        ) -> str:
            data = EntityCreate(
                entity_type=entity_type,
                namespace=namespace,
                name=name,
                description=description,
                properties=properties or {},
                source_refs=[source_ref],
            )

            entity = self._runtime.create_entity(data, actor="knowledge_compiler")
            produced_entities.add(entity.id)
            return entity.id

        def add_relation(
            relation_type: str,
            source_entity_id: str,
            target_entity_id: str,
            properties: dict[str, Any] | None = None,
        ) -> None:
            if source_entity_id == target_entity_id:
                return

            data = RelationCreate(
                relation_type=relation_type,
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                properties=properties or {},
                source_refs=[source_ref],
            )

            relation = self._runtime.create_relation(
                data,
                actor="knowledge_compiler",
            )

            produced_relations.add(relation.id)

        isr_entity_id = add_entity(
            entity_type="ISR_REVISION",
            namespace="isr",
            name=payload.get("name", source_ref.source_id),
            description="ISR revision ingested into the Knowledge Graph.",
            properties={
                "source_id": source_ref.source_id,
                "source_hash": source_ref.source_hash,
                "version": source_ref.version,
            },
        )

        for requirement in payload.get("requirements", []):
            requirement_name = requirement.get("name")

            if not requirement_name:
                continue

            requirement_id = add_entity(
                entity_type="REQUIREMENT",
                namespace="requirement",
                name=requirement_name,
                description=requirement.get("description"),
            )

            requirement_links.append(
                (requirement_id, list(requirement.get("satisfied_by", [])))
            )

        for domain in payload.get("domains", []):
            domain_name = domain.get("name")

            if not domain_name:
                continue

            domain_namespace = domain.get("namespace", "domain")

            domain_id = add_entity(
                entity_type="DOMAIN",
                namespace=domain_namespace,
                name=domain_name,
                description=domain.get("description"),
            )

            add_relation(
                relation_type="CONTAINS",
                source_entity_id=isr_entity_id,
                target_entity_id=domain_id,
            )

            for service in domain.get("services", []):
                service_name = service.get("name")

                if not service_name:
                    continue

                service_namespace = service.get("namespace", domain_namespace)

                service_id = add_entity(
                    entity_type="SERVICE",
                    namespace=service_namespace,
                    name=service_name,
                    description=service.get("description"),
                )

                service_map[service_name] = service_id

                add_relation(
                    relation_type="CONTAINS",
                    source_entity_id=domain_id,
                    target_entity_id=service_id,
                )

                add_relation(
                    relation_type="DERIVES_FROM",
                    source_entity_id=service_id,
                    target_entity_id=isr_entity_id,
                )

                for api in service.get("apis", []):
                    api_name = api if isinstance(api, str) else api.get("name")

                    if not api_name:
                        continue

                    api_id = add_entity(
                        entity_type="API",
                        namespace=service_namespace,
                        name=api_name,
                    )

                    add_relation(
                        relation_type="EXPOSES",
                        source_entity_id=service_id,
                        target_entity_id=api_id,
                    )

                for event in service.get("produces_events", []):
                    event_name = event if isinstance(event, str) else event.get("name")

                    if not event_name:
                        continue

                    event_id = add_entity(
                        entity_type="EVENT",
                        namespace=service_namespace,
                        name=event_name,
                    )

                    add_relation(
                        relation_type="PRODUCES",
                        source_entity_id=service_id,
                        target_entity_id=event_id,
                    )

                for event in service.get("consumes_events", []):
                    event_name = event if isinstance(event, str) else event.get("name")

                    if not event_name:
                        continue

                    event_id = add_entity(
                        entity_type="EVENT",
                        namespace=service_namespace,
                        name=event_name,
                    )

                    add_relation(
                        relation_type="CONSUMES",
                        source_entity_id=service_id,
                        target_entity_id=event_id,
                    )

                for data_model in service.get("data_models", []):
                    model_name = (
                        data_model
                        if isinstance(data_model, str)
                        else data_model.get("name")
                    )

                    if not model_name:
                        continue

                    model_id = add_entity(
                        entity_type="DATA_MODEL",
                        namespace=service_namespace,
                        name=model_name,
                    )

                    add_relation(
                        relation_type="USES",
                        source_entity_id=service_id,
                        target_entity_id=model_id,
                    )

        for domain in payload.get("domains", []):
            for service in domain.get("services", []):
                service_name = service.get("name")

                if not service_name:
                    continue

                source_service_id = service_map.get(service_name)

                if not source_service_id:
                    continue

                for dependency_name in service.get("depends_on", []):
                    target_service_id = service_map.get(dependency_name)

                    if not target_service_id:
                        target_service_id = add_entity(
                            entity_type="SERVICE",
                            namespace=service.get("namespace", "domain"),
                            name=dependency_name,
                            description="Dependency discovered during ISR ingestion.",
                        )

                        service_map[dependency_name] = target_service_id

                    add_relation(
                        relation_type="DEPENDS_ON",
                        source_entity_id=source_service_id,
                        target_entity_id=target_service_id,
                    )

        for requirement_id, satisfied_by_service_names in requirement_links:
            for service_name in satisfied_by_service_names:
                service_id = service_map.get(service_name)

                if service_id:
                    add_relation(
                        relation_type="SATISFIES",
                        source_entity_id=service_id,
                        target_entity_id=requirement_id,
                    )

        ingestion_job_id = deterministic_id(
            "ingest",
            {
                "source_type": source_ref.source_type,
                "source_id": source_ref.source_id,
                "source_hash": source_ref.source_hash,
            },
        )

        return IngestionResult(
            ingestion_job_id=ingestion_job_id,
            status="SUCCEEDED",
            produced_entities=sorted(produced_entities),
            produced_relations=sorted(produced_relations),
        )
