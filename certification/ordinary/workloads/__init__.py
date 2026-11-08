"""Ordinary workload specifications (Checkpoint 054)."""

from certification.ordinary.workloads.appointments import (
    CANDIDATE_ID as APPOINTMENTS_CANDIDATE_ID,
    appointments_isr_revision,
    approved_appointments_requirements,
)
from certification.ordinary.workloads.inventory import (
    CANDIDATE_ID as INVENTORY_CANDIDATE_ID,
    approved_inventory_requirements,
    inventory_isr_revision,
)
from certification.ordinary.workloads.projects import (
    CANDIDATE_ID as PROJECTS_CANDIDATE_ID,
    approved_projects_requirements,
    projects_isr_revision,
)

ORDINARY_WORKLOADS = (
    ("appointments", APPOINTMENTS_CANDIDATE_ID, appointments_isr_revision, approved_appointments_requirements),
    ("inventory", INVENTORY_CANDIDATE_ID, inventory_isr_revision, approved_inventory_requirements),
    ("projects", PROJECTS_CANDIDATE_ID, projects_isr_revision, approved_projects_requirements),
)
