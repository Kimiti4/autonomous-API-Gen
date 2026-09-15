defmodule Tiannara.Observatory.Projections do
  @moduledoc """
  Facade over all Observatory projection modules.

  This preserves the original projection entrypoint while delegating
  to the specialized pure projection implementations.
  """

  alias Tiannara.Observatory.Projections.{
    Evidence,
    Evolution,
    Governance,
    Knowledge,
    Runtime
  }

  defdelegate build_runtime_state(events), to: Runtime
  defdelegate build_evolution_state(evolution_id, events), to: Evolution
  defdelegate build_evidence_state(events), to: Evidence
  defdelegate get_evidence(events, evidence_id), to: Evidence
  defdelegate build_knowledge_state(events), to: Knowledge
  defdelegate get_knowledge(events, subject_id), to: Knowledge
  defdelegate build_governance_state(events), to: Governance
end
