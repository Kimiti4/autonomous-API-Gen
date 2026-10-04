defmodule Tiannara.Observatory.Projections.Repair do
  @moduledoc """Pure projection of ESAP repair-report events."""

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Projections.Helpers

  def build_repair_state(subject_id, events) when is_binary(subject_id) and is_list(events) do
    relevant = events |> Enum.filter(&(&1.subject_id == subject_id and &1.type == :repair_report)) |> Helpers.sort_asc()
    latest = Helpers.latest(relevant)
    if latest == nil do
      %{repair_id: subject_id, status: :unknown, report: nil, events: 0, updated_at: nil}
    else
      %{repair_id: subject_id, status: Helpers.payload_get(latest.payload, :status, :unknown),
        report: latest.payload, events: length(relevant), updated_at: latest.timestamp}
    end
  end
end
