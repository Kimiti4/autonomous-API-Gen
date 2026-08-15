"""
Cloud Provider Adapter abstraction — decouples the Infrastructure Compiler from
specific cloud vendors. Technology neutrality is preserved until final emission.

Constitutional Alignment:
- "Treat every framework and platform as a compiler backend."
- "Security by Design... Principle of least privilege."
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class CloudProviderAdapter(ABC):
    """Translates abstract infrastructure requirements into provider-specific IaC."""

    @abstractmethod
    def generate_network(self, context: Dict[str, Any]) -> str:
        """Generate networking resources (VPC, subnets, security groups)."""

    @abstractmethod
    def generate_compute(self, context: Dict[str, Any]) -> str:
        """Generate compute resources (clusters, task definitions, services)."""

    @abstractmethod
    def generate_database(self, context: Dict[str, Any]) -> str:
        """Generate database resources (RDS, managed DB, NoSQL)."""

    @abstractmethod
    def generate_observability(self, context: Dict[str, Any]) -> str:
        """Generate observability resources (log groups, alarms, dashboards)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g. 'aws', 'google', 'azurerm')."""


class AWSAdapter(CloudProviderAdapter):
    def generate_network(self, context: Dict[str, Any]) -> str:
        genome_id = context.get("genome_id", "app")
        backend_port = context.get("backend_port", 8000)

        return f'''resource "aws_vpc" "main" {{
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  tags = {{ Name = "{genome_id}-vpc" }}
}}

# Security by Design: Strict Ingress Rules
resource "aws_security_group" "backend_sg" {{
  name        = "{genome_id}-backend-sg"
  description = "Strict least-privilege access to backend API"
  vpc_id      = aws_vpc.main.id

  ingress {{
    description = "Allow traffic from Load Balancer to Backend Port"
    from_port   = {backend_port}
    to_port     = {backend_port}
    protocol    = "tcp"
    cidr_blocks = ["10.0.1.0/24"]
  }}

  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  tags = {{
    Name = "{genome_id}-backend-sg"
  }}
}}
'''

    def generate_compute(self, context: Dict[str, Any]) -> str:
        genome_id = context.get("genome_id", "app")
        backend_port = context.get("backend_port", 8000)
        desired_count = context.get("desired_count", 2)

        return f'''resource "aws_ecs_cluster" "main" {{
  name = "{genome_id}-cluster"

  setting {{
    name  = "containerInsights"
    value = "enabled" # Observability by Design
  }}
}}

resource "aws_ecs_task_definition" "backend" {{
  family                   = "{genome_id}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"

  container_definitions = jsonencode([
    {{
      name      = "backend-api"
      image     = var.backend_image_uri
      essential = true
      portMappings = [{{ containerPort = {backend_port}, hostPort = {backend_port} }}]
      logConfiguration = {{
        logDriver = "awslogs"
        options = {{
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }}
      }}
    }}
  ])
}}

resource "aws_ecs_service" "backend" {{
  name            = "{genome_id}-backend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = {desired_count}
  launch_type     = "FARGATE"

  network_configuration {{
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.backend_sg.id]
    assign_public_ip = false
  }}
}}
'''

    def generate_database(self, context: Dict[str, Any]) -> str:
        genome_id = context.get("genome_id", "app")
        requires_db = context.get("requires_database", False)
        tenancy = context.get("tenancy_strategy", "single_tenant")

        hcl = ""
        if requires_db:
            hcl += f'''resource "aws_db_instance" "relational_db" {{
  identifier     = "{genome_id}-db"
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.micro"
  allocated_storage = 20

  # Security by Design: Never hardcode secrets
  username = var.db_username
  password = var.db_password

  # Reliability: Multi-AZ for production readiness
  multi_az = true

  vpc_security_group_ids = [aws_security_group.backend_sg.id]

  tags = {{ TenancyStrategy = "{tenancy}" }}
}}

'''
        return hcl

    def generate_observability(self, context: Dict[str, Any]) -> str:
        genome_id = context.get("genome_id", "app")
        retention_days = context.get("retention_days", 186)

        return f'''resource "aws_cloudwatch_log_group" "backend" {{
  name              = "/ecs/{genome_id}-backend"
  retention_in_days = {retention_days}
}}

resource "aws_cloudwatch_metric_alarm" "high_cpu" {{
  alarm_name          = "{genome_id}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors ECS CPU utilization"

  dimensions = {{
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.backend.name
  }}

  alarm_actions = []
}}
'''

    @property
    def provider_name(self) -> str:
        return "aws"


class GCPAdapter(CloudProviderAdapter):
    def generate_network(self, context: Dict[str, Any]) -> str:
        genome_id = context.get("genome_id", "app")
        backend_port = context.get("backend_port", 8000)

        return f'''resource "google_compute_network" "main" {{
  name                    = "{genome_id}-network"
  auto_create_subnetworks = false
}}

resource "google_compute_subnetwork" "private" {{
  name          = "{genome_id}-private"
  network       = google_compute_network.main.id
  ip_cidr_range = "10.0.0.0/16"
}}

resource "google_compute_firewall" "backend" {{
  name    = "{genome_id}-backend-firewall"
  network = google_compute_network.main.name

  allow {{
    protocol = "tcp"
    ports    = ["{backend_port}"]
  }}

  source_ranges = ["10.0.1.0/24"]
}}
'''

    def generate_compute(self, context: Dict[str, Any]) -> str:
        genome_id = context.get("genome_id", "app")
        backend_port = context.get("backend_port", 8000)

        return f'''resource "google_cloud_run_service" "backend" {{
  name     = "{genome_id}-backend"
  location = "us-central1"

  template {{
    spec {{
      containers {{
        image = var.backend_image_uri
        ports {{
          container_port = {backend_port}
        }}
      }}
    }}
  }}
}}
'''

    def generate_database(self, context: Dict[str, Any]) -> str:
        genome_id = context.get("genome_id", "app")
        requires_db = context.get("requires_database", False)
        if not requires_db:
            return "# No database resources required\n"

        return f'''resource "google_sql_database_instance" "main" {{
  name             = "{genome_id}-db"
  database_version = "POSTGRES_15"

  settings {{
    tier              = "db-f1-micro"
    availability_type = "ZONAL"
  }}
}}
'''

    def generate_observability(self, context: Dict[str, Any]) -> str:
        genome_id = context.get("genome_id", "app")
        retention_days = context.get("retention_days", 186)

        return f'''resource "google_logging_project_sink" "backend" {{
  name        = "{genome_id}-logs"
  destination = "storage.googleapis.com/{genome_id}-log-bucket"
}}

resource "google_monitoring_alert_policy" "high_cpu" {{
  display_name = "{genome_id}-high-cpu"
  combiner     = "OR"

  conditions {{
    display_name = "CPU utilization"
    condition_threshold {{
      filter     = "metric.type=\\"run.googleapis.com/container/cpu/utilizations\\""
      threshold_value = 0.8
      duration   = "120s"
    }}
  }}
}}
'''

    @property
    def provider_name(self) -> str:
        return "google"
