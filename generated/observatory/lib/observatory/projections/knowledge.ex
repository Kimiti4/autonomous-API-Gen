defmodule Tiannara.Observatory.Projections.Knowledge do
  @moduledoc """
  Pure projection from knowledge/evidence events to knowledge state.

  This projection tracks epistemic state by subject identifier.
  """

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Projections.Helpers

  @spec build_knowledge_state([Event.t()]) :: [map()]
  def build_knowledge_state(events) when is_list(events) do
    relevant =
      Enum.filter(events, fn event ->
        event.category in [:knowledge, :evidence]
      end)

    relevant
    |> Enum.group_by(& &1.subject_id)
    |> Enum.map(fn {subject_id, grouped_events} ->
      sorted = Helpers.sort_asc(grouped_events)
      latest = Helpers.latest(sorted)

      %{
        subject_id: subject_id,
        epistemic_state: Helpers.count_by_epistemic(sorted),
        latest_status: latest.epistemic_status,
        updated_at: latest.timestamp
      }
    end)
    |> Enum.sort_by(& &1.subject_id)
  end

  @spec get_knowledge([Event.t()], String.t()) :: {:ok, map()} | {:error, :not_found}
  def get_knowledge(events, subject_id)
      when is_list(events) and is_binary(subject_id) do
    case Enum.find(build_knowledge_state(events), &(&1.subject_id == subject_id)) do
      nil ->
        {:error, :not_found}

      record ->
        {:ok, record}
    end
  end
end
