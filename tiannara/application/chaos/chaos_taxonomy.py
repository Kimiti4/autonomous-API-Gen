"""35.1 Chaos Taxonomy."""
TAXONOMY = {
    "infrastructure": ("container_death","vm_failure","disk_exhaustion","memory_exhaustion"),
    "network": ("packet_loss","partition","dns_failure","tls_failure"),
    "data": ("database_deletion","corruption","duplicate_event"),
    "distributed": ("clock_skew","split_brain","leader_failure"),
    "application": ("api_failure","deadlock","race_condition"),
}
ALL = tuple(v for vs in TAXONOMY.values() for v in vs)
