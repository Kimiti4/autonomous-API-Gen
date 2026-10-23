"""The authorization certification corpus.

Four independently authored, source-bound workloads, each with a distinct
resource and operation pattern:

``payroll-authorization``
    A granting role with a read/write surface and one forbidden operation.
``orders-authorization``
    A read-only role: one permitted operation, three forbidden ones.
``inventory-authorization``
    A role that may perform every operation, but only for one warehouse; the
    grant depends on a subject attribute.
``shipments-authorization``
    A service that owns two resources while the policy governs only one; the
    other resource's routes are refused because no rule grants them.

A fifth workload adds the declared-operation surface:

``payroll-declared-api-authorization``
    Four reviewed API operations, each explicitly exposed by the payroll
    service and bound to one typed policy. Certification requires the emitted
    route, the operation-bound guard, and the runtime proof.

The corpus is versioned and hashed. It is deliberately separate from the
general Campaign A substrate matrix, whose 39-workload, 78-trial scope is
unchanged.
"""
from __future__ import annotations

from certification.authorization.corpus import (
    CORPUS_VERSION,
    AuthorizationWorkload,
    OperationBinding,
    build_workload,
    corpus_hash,
    validate_workload,
)
from certification.authorization.workload_inventory import WORKLOAD as INVENTORY_WORKLOAD
from certification.authorization.workload_declared_api import (
    WORKLOAD as DECLARED_API_WORKLOAD,
)
from certification.authorization.workload_orders import WORKLOAD as ORDERS_WORKLOAD
from certification.authorization.workload_payroll import WORKLOAD as PAYROLL_WORKLOAD
from certification.authorization.workload_shipments import WORKLOAD as SHIPMENTS_WORKLOAD


CORPUS_ID = "tiannara.authorization.corpus"

AUTHORIZATION_CORPUS: tuple[AuthorizationWorkload, ...] = (
    PAYROLL_WORKLOAD,
    ORDERS_WORKLOAD,
    INVENTORY_WORKLOAD,
    SHIPMENTS_WORKLOAD,
    DECLARED_API_WORKLOAD,
)

AUTHORIZATION_CORPUS_HASH = corpus_hash(AUTHORIZATION_CORPUS)

CORPUS_METADATA = {
    "schema_id": CORPUS_ID,
    "corpus_version": CORPUS_VERSION,
    "corpus_hash": AUTHORIZATION_CORPUS_HASH,
    "workload_ids": [workload.workload_id for workload in AUTHORIZATION_CORPUS],
    "workload_count": len(AUTHORIZATION_CORPUS),
    "mutation_kinds": sorted({
        mutation.kind
        for workload in AUTHORIZATION_CORPUS
        for mutation in workload.mutations
    }),
    "declared_operation_workloads": [
        workload.workload_id
        for workload in AUTHORIZATION_CORPUS
        if workload.declared_operations
    ],
}
