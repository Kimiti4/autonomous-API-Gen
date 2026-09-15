defmodule Tiannara.Observatory.Tracer do
  @moduledoc """
  Traceability engine for the Observatory.

  Reconstructs causal lineage and explanation for any subject.
  """

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Projections
  alias Tiannara.Observatory.Projections.Helpers
  alias Tiannara.Observatory.Store

  @spec trace(String.t()) :: {:ok, [Event.t()]} | {:error, :not_found}
  def trace(subject_id) when is_binary(subject_id) and byte_size(subject_id) > 0 do
    events = Store.get_events_for_subject(subject_id)

    if events == [] do
      {:error, :not_found}
    else
      {:ok, Helpers.sort_asc(events)}
    end
  end

  def trace(_), do: {:error, :invalid_subject_id}

  @spec explain(String.t()) :: {:ok, map()} | {:error, term()}
  def explain(subject_id) when is_binary(subject_id) and byte_size(subject_id) > 0 do
    case trace(subject_id) do
      {:error, reason} ->
        {:error, reason}

      {:ok, events} ->
        {:ok, build_explanation(subject_id, events)}
    end
  end

  def explain(_), do: {:error, :invalid_subject_id}

  defp build_explanation(subject_id, events) do
    cond do
      Enum.any?(events, &(&1.category == :evolution)) ->
        evolution_explanation(subject_id, events)

      Enum.any?(events, &(&1.category == :evidence)) ->
        evidence_explanation(subject_id, events)

      true ->
        generic_explanation(subject_id, events)
    end
  end

  defp evolution_explanation(subject_id, events) do
    state = Projections.build_evolution_state(subject_id, events)

    %{
      subject_id: subject_id,
      explanation_type: :evolution,
      decision: state.decision,
      status: state.status,
      epistemic_state: state.epistemic_state,
      capability_check: state.capability_check,
      authorization: state.authorization,
      unknowns: state.unknowns,
      contradictions: state.contradictions,
      pipeline: state.pipeline,
      trace: Enum.map(events, & &1.id)
    }
  end

  defp evidence_explanation(subject_id, events) do
    case Projections.get_evidence(events, subject_id) do
      {:ok, evidence} ->
        %{
          subject_id: subject_id,
          explanation_type: :evidence,
          claim: evidence.claim,
          epistemic_status: evidence.epistemic_status,
          result: evidence.result,
          scope: evidence.scope,
          not_proven: evidence.not_proven,
          provenance: evidence.provenance,
          trace: Enum.map(events, & &1.id)
        }

      {:error, :not_found} ->
        generic_explanation(subject_id, events)
    end
  end

  defp generic_explanation(subject_id, events) do
    latest = Helpers.latest(events)

    %{
      subject_id: subject_id,
      explanation_type: :generic,
      epistemic_state: Helpers.count_by_epistemic(events),
      latest_event_type: latest.type,
      latest_timestamp: latest.timestamp,
      trace: Enum.map(events, & &1.id)
    }
  end
end
