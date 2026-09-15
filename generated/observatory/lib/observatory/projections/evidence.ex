defmodule Tiannara.Observatory.Projections.Evidence do
  @moduledoc """
  Pure projection from evidence events to evidence read models.

  This projection preserves claim boundaries and does not promote
  unsupported claims into certified conclusions.
  """

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Projections.Helpers

  @spec build_evidence_state([Event.t()]) :: [map()]
  def build_evidence_state(events) when is_list(events) do
    evidence_events =
      Enum.filter(events, fn event ->
        event.category == :evidence
      end)

    evidence_events
    |> Enum.group_by(& &1.subject_id)
    |> Enum.map(fn {evidence_id, grouped_events} ->
      build_evidence_record(evidence_id, Helpers.sort_asc(grouped_events))
    end)
    |> Enum.sort_by(& &1.evidence_id)
  end

  @spec get_evidence([Event.t()], String.t()) :: {:ok, map()} | {:error, :not_found}
  def get_evidence(events, evidence_id)
      when is_list(events) and is_binary(evidence_id) do
    case Enum.find(build_evidence_state(events), &(&1.evidence_id == evidence_id)) do
      nil ->
        {:error, :not_found}

      record ->
        {:ok, record}
    end
  end

  defp build_evidence_record(evidence_id, events) do
    latest = Helpers.latest(events)

    claim = Helpers.payload_get(latest.payload, :claim, "unspecified")

    result =
      cond do
        latest.epistemic_status == :contradiction ->
          :contradiction

        true ->
          Helpers.payload_get(latest.payload, :result, :unknown)
      end

    scope = Helpers.payload_get(latest.payload, :scope, [])
    not_proven = Helpers.payload_get(latest.payload, :not_proven, [])

    provenance_checks =
      events
      |> Enum.filter(&(&1.type == :provenance_verified))
      |> Enum.map(fn event ->
        Helpers.payload_get(event.payload, :checks, %{})
      end)
      |> Enum.reduce(%{}, fn checks, acc ->
        if is_map(checks) do
          Map.merge(acc, checks)
        else
          acc
        end
      end)

    provenance =
      latest.payload
      |> Helpers.payload_get(:provenance, %{})
      |> Map.merge(provenance_checks)

    %{
      evidence_id: evidence_id,
      epistemic_status: latest.epistemic_status,
      claim: claim,
      result: result,
      scope: scope,
      not_proven: not_proven,
      provenance: provenance,
      observed_at: latest.timestamp
    }
  end
end
