defmodule Tiannara.Observatory.Projections.Runtime do
  @moduledoc """
  Pure projection from runtime events to runtime state.

  This projection never fabricates measurements.
  Missing metrics remain :not_measured.
  """

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Projections.Helpers

  @spec build_runtime_state([Event.t()]) :: map()
  def build_runtime_state(events) when is_list(events) do
    sorted = Helpers.sort_asc(events)

    process_started = count_type(sorted, :process_started)
    process_stopped = count_type(sorted, :process_stopped)
    restart_count = count_type(sorted, :process_restarted)
    supervisors = count_type(sorted, :supervisor_started)

    processes =
      process_started
      |> Kernel.-(process_stopped)
      |> max(0)

    messages_per_sec = latest_metric(sorted, :messages_per_sec)
    memory_total = latest_metric(sorted, :memory_total)
    health = derive_health(sorted)
    latest_event = Helpers.latest(sorted)

    %{
      processes: processes,
      supervisors: supervisors,
      messages_per_sec: messages_per_sec,
      memory_total: memory_total,
      restart_count: restart_count,
      health: health,
      updated_at: updated_at(latest_event)
    }
  end

  defp count_type(events, type) do
    Enum.count(events, &(&1.type == type))
  end

  defp latest_metric(events, key) do
    metric_events =
      Enum.filter(events, fn event ->
        event.type == :metric and
          not is_nil(Helpers.payload_get(event.payload, key))
      end)

    case Helpers.latest(metric_events) do
      nil ->
        :not_measured

      event ->
        Helpers.payload_get(event.payload, key)
    end
  end

  defp derive_health([]), do: :unknown

  defp derive_health(events) do
    degraded? =
      Enum.any?(events, fn event ->
        event.severity in [:error, :fatal] or
          event.type in [:process_crashed, :supervisor_crashed, :runtime_failure]
      end)

    if degraded? do
      :degraded
    else
      :green
    end
  end

  defp updated_at(nil), do: nil
  defp updated_at(event), do: event.timestamp
end
