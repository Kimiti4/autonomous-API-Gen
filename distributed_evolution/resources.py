"""
Resource manager for distributed compute nodes.
"""

from __future__ import annotations

from typing import Dict, List

from .models import (
    ComputeClusterISR,
    ComputeNodeISR,
    NodeStatus,
    ResourceAllocationISR,
    ResourceRequirements,
    new_id,
    utcnow,
)


class ResourceManager:
    """Manages compute nodes, capacity, and allocations."""

    def __init__(
        self,
        cluster_policy_version: str = "constitution.v1",
    ) -> None:
        self.cluster_policy_version = cluster_policy_version

        self.cluster = ComputeClusterISR(
            name="distributed-evolution-cloud",
            policy_version=cluster_policy_version,
        )

        self.nodes: Dict[str, ComputeNodeISR] = {}
        self.allocations: Dict[str, ResourceAllocationISR] = {}

    def register_node(
        self,
        node_id: str,
        region: str,
        capabilities: List[str],
        cpu_capacity: int,
        memory_mb_capacity: int,
        policy_version: str,
        public_key_ref: str,
    ) -> ComputeNodeISR:
        attested = policy_version == self.cluster_policy_version

        status = NodeStatus.ACTIVE if attested else NodeStatus.SUSPENDED

        node = ComputeNodeISR(
            node_id=node_id,
            region=region,
            capabilities=capabilities,
            cpu_capacity=cpu_capacity,
            memory_mb_capacity=memory_mb_capacity,
            status=status,
            attested=attested,
            policy_version=policy_version,
            public_key_ref=public_key_ref,
        )

        self.nodes[node_id] = node

        if node_id not in self.cluster.nodes:
            self.cluster.nodes.append(node_id)

        if region not in self.cluster.regions:
            self.cluster.regions.append(region)

        return node

    def heartbeat(self, node_id: str) -> ComputeNodeISR:
        node = self._get_node(node_id)

        if node.status == NodeStatus.FAILED:
            raise ValueError("Failed nodes must be re-registered.")

        node.last_heartbeat = utcnow()

        if node.status == NodeStatus.ACTIVE:
            node.last_heartbeat = utcnow()

        return node

    def mark_failed(self, node_id: str) -> ComputeNodeISR:
        node = self._get_node(node_id)

        node.status = NodeStatus.FAILED

        return node

    def detect_stale_nodes(
        self,
        timeout_seconds: int = 60,
    ) -> List[ComputeNodeISR]:
        now = utcnow()

        stale: List[ComputeNodeISR] = []

        for node in self.nodes.values():
            if node.status != NodeStatus.ACTIVE:
                continue

            age = (now - node.last_heartbeat).total_seconds()

            if age > timeout_seconds:
                node.status = NodeStatus.FAILED
                stale.append(node)

        return stale

    def available_capacity(self, node_id: str) -> tuple[int, int]:
        node = self._get_node(node_id)

        allocated_cpu = 0
        allocated_memory = 0

        for allocation in self.allocations.values():
            if allocation.node_id != node_id:
                continue

            if allocation.status != "ALLOCATED":
                continue

            allocated_cpu += allocation.cpu
            allocated_memory += allocation.memory_mb

        cpu_free = node.cpu_capacity - allocated_cpu
        memory_free = node.memory_mb_capacity - allocated_memory

        return max(0, cpu_free), max(0, memory_free)

    def allocate(
        self,
        job_id: str,
        node_id: str,
        cpu: int,
        memory_mb: int,
    ) -> ResourceAllocationISR:
        cpu_free, memory_free = self.available_capacity(node_id)

        if cpu_free < cpu or memory_free < memory_mb:
            raise ValueError("Insufficient node capacity.")

        allocation = ResourceAllocationISR(
            job_id=job_id,
            node_id=node_id,
            cpu=cpu,
            memory_mb=memory_mb,
        )

        self.allocations[allocation.allocation_id] = allocation

        return allocation

    def release_allocations_for_job(self, job_id: str) -> int:
        released = 0

        for allocation in self.allocations.values():
            if allocation.job_id != job_id:
                continue

            if allocation.status != "ALLOCATED":
                continue

            allocation.status = "RELEASED"
            allocation.released_at = utcnow()

            released += 1

        return released

    def nodes_matching(
        self,
        requirements: ResourceRequirements,
    ) -> List[ComputeNodeISR]:
        matching: List[ComputeNodeISR] = []

        for node in self.nodes.values():
            if node.status != NodeStatus.ACTIVE:
                continue

            if not node.attested:
                continue

            if requirements.regions and node.region not in requirements.regions:
                continue

            required_capabilities = set(requirements.capabilities)
            node_capabilities = set(node.capabilities)

            if not required_capabilities.issubset(node_capabilities):
                continue

            cpu_free, memory_free = self.available_capacity(node.node_id)

            if cpu_free < requirements.cpu:
                continue

            if memory_free < requirements.memory_mb:
                continue

            matching.append(node)

        return matching

    def autoscale(
        self,
        pending_jobs_count: int,
        threshold: int = 3,
        cpu_capacity: int = 8,
        memory_mb_capacity: int = 8192,
        region: str = "auto-region",
    ) -> ComputeNodeISR | None:
        if pending_jobs_count <= threshold:
            return None

        node_index = len(self.nodes) + 1

        node_id = f"node_auto_{node_index}"

        return self.register_node(
            node_id=node_id,
            region=region,
            capabilities=[],
            cpu_capacity=cpu_capacity,
            memory_mb_capacity=memory_mb_capacity,
            policy_version=self.cluster_policy_version,
            public_key_ref=f"auto:{node_id}",
        )

    def _get_node(self, node_id: str) -> ComputeNodeISR:
        node = self.nodes.get(node_id)

        if not node:
            raise KeyError(f"Node not found: {node_id}")

        return node
