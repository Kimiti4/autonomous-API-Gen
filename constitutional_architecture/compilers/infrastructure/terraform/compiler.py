"""
Phase 9 — Terraform Infrastructure Compiler (Pass 9)
Translates the Universal ISR, Genome, and Orchestration Context into Terraform HCL.

Constitutional Alignment:
- "Treat every framework and platform as a compiler backend."
- "Security by Design... Principle of least privilege... Secure secrets management."
- "Observability by Design... Operational visibility should exist from the first generated version."
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from constitutional_architecture.compilers.infrastructure.adapters import (
    AWSAdapter, CloudProviderAdapter,
)
from constitutional_architecture.compilers.infrastructure.base import InfrastructureCompiler
from constitutional_architecture.core.models.bundle import (
    ArtifactType, CompilationBundle, CompilationManifest,
)
from constitutional_architecture.core.models.genome import (
    ArchitectureGenome, DeploymentTopology, MessagingTopology, PersistenceModel,
)
from constitutional_architecture.core.models.isr import UniversalISR


class TerraformCompiler(InfrastructureCompiler):
    def __init__(self, provider_adapter: Optional[CloudProviderAdapter] = None) -> None:
        self.provider_adapter = provider_adapter or AWSAdapter()

    def compile(
        self,
        isr: UniversalISR,
        genome: ArchitectureGenome,
        context: Dict[str, Any],
    ) -> CompilationBundle:
        files: Dict[str, str] = {}

        files["main.tf"] = self._generate_main_tf(genome)
        files["network.tf"] = self.provider_adapter.generate_network(
            self._adapter_context(genome, context),
        )
        files["compute.tf"] = self._generate_compute_tf(genome, context)
        files["data.tf"] = self._generate_data_tf(genome, context)
        files["observability.tf"] = self._generate_observability_tf(genome)
        files["variables.tf"] = self._generate_variables_tf()
        files["outputs.tf"] = self._generate_outputs_tf(self.provider_adapter.provider_name)

        infra_manifest = CompilationManifest(
            artifact_type=ArtifactType.INFRASTRUCTURE,
            domain="infra",
            files=files,
            metadata={"iac_tool": "terraform", "provider": self.provider_adapter.provider_name},
        )

        exposed = {
            "tf_state_backend": "s3",
            "deployment_cmd": "terraform apply -auto-approve",
            "cloud_provider": self.provider_adapter.provider_name,
        }

        return CompilationBundle(
            compiler_id="terraform_aws",
            target_technology="terraform",
            manifests=[infra_manifest],
            exposed_interfaces=exposed,
        )

    def _adapter_context(self, genome: ArchitectureGenome, context: Dict[str, Any]) -> Dict[str, Any]:
        persistence = genome.persistence_model
        tenancy = genome.tenancy_strategy
        return {
            "genome_id": genome.genome_id or "app",
            "backend_port": context.get("backend_port", 8000),
            "frontend_port": context.get("frontend_port", 3000),
            "requires_database": persistence == PersistenceModel.RELATIONAL
            if persistence else False,
            "requires_message_broker": context.get("requires_message_broker", False)
            or genome.messaging_topology == MessagingTopology.ASYNC_EVENT_BUS,
            "tenancy_strategy": tenancy.value if tenancy else "single_tenant",
            "desired_count": context.get("desired_count", 2),
        }

    def _generate_main_tf(self, genome: ArchitectureGenome) -> str:
        genome_id = genome.genome_id or "app"
        intent_id = genome.intent_hash or "unknown"
        return f'''terraform {{
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
  backend "s3" {{
    bucket = "evolved-platform-tf-state"
    key    = "{genome_id}/terraform.tfstate"
    region = "us-east-1"
  }}
}}

provider "aws" {{
  region = var.aws_region
  default_tags {{
    tags = {{
      # GENETIC WATERMARK: every provisioned resource is tagged with its Genome
      Genome = "{genome_id}"
      Intent = "{intent_id}"
    }}
  }}
}}
'''

    def _generate_compute_tf(self, genome: ArchitectureGenome, context: Dict[str, Any]) -> str:
        if genome.deployment_topology != DeploymentTopology.CONTAINERIZED:
            return "# Fallback compute generation\n"

        return self.provider_adapter.generate_compute(self._adapter_context(genome, context))

    def _generate_data_tf(self, genome: ArchitectureGenome, context: Dict[str, Any]) -> str:
        hcl = self.provider_adapter.generate_database(self._adapter_context(genome, context))

        adapter_ctx = self._adapter_context(genome, context)
        if adapter_ctx["requires_message_broker"]:
            hcl += '''resource "aws_sqs_queue" "event_bus" {
  name                      = "evolved-event-bus"
  message_retention_seconds = 1209600
  visibility_timeout_seconds = 300
}
'''
        return hcl

    def _generate_observability_tf(self, genome: ArchitectureGenome) -> str:
        depth = genome.observability_depth or 0.5
        retention_days = int(7 + (depth * 358))
        adapter_ctx = {
            "genome_id": genome.genome_id or "app",
            "retention_days": retention_days,
        }
        return self.provider_adapter.generate_observability(adapter_ctx)

    def _generate_variables_tf(self) -> str:
        return '''variable "aws_region" { default = "us-east-1" }
variable "db_username" { sensitive = true }
variable "db_password" { sensitive = true }
variable "backend_image_uri" { description = "URI of the compiled backend Docker image" }
'''

    def _generate_outputs_tf(self, provider_name: str) -> str:
        return '''output "vpc_id" { value = aws_vpc.main.id }
output "db_endpoint" { value = aws_db_instance.relational_db.endpoint }
output "ecs_cluster_name" { value = aws_ecs_cluster.main.name }
'''
