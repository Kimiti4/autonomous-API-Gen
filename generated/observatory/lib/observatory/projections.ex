defmodule Tiannara.Observatory.Projections do
  alias Tiannara.Observatory.Projections.{Evidence, Evolution, Governance, Knowledge, Runtime, Repair}

  defdelegate build_runtime_state(events), to: Runtime
  defdelegate build_evolution_state(evolution_id, events), to: Evolution
  defdelegate build_evidence_state(events), to: Evidence
  defdelegate get_evidence(events, evidence_id), to: Evidence
  defdelegate build_knowledge_state(events), to: Knowledge
  defdelegate get_knowledge(events, subject_id), to: Knowledge
  defdelegate build_governance_state(events), to: Governance
  defdelegate build_repair_state(repair_id, events), to: Repair
end
