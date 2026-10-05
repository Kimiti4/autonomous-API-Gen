defmodule Tiannara.Observatory.API.Notifications do
  @moduledoc """Read-only Observatory notification API."""

  alias Tiannara.Observatory.{Query, RepairNotifications, Store}

  @spec repair(String.t()) :: {:ok, map()} | {:error, term()}
  def repair(repair_id) when is_binary(repair_id) and byte_size(repair_id) > 0 do
    case Query.repair(repair_id) do
      {:ok, state} ->
        payload = Map.get(state, :report, %{})
        event = %{type: :repair_report, subject_id: repair_id, payload: payload, severity: Map.get(payload, :severity, :info)}
        case RepairNotifications.from_event(event) do
          nil -> {:error, :not_notifiable}
          notification -> {:ok, notification}
        end
      error -> error
    end
  end

  def repair(_), do: {:error, :invalid_repair_id}

  @spec recent(non_neg_integer()) :: {:ok, [map()]}
  def recent(limit \ 20) when is_integer(limit) and limit >= 0 do
    events = Store.recent_events(limit * 3)
    notifications =
      events
      |> Enum.map(&RepairNotifications.from_event/1)
      |> Enum.reject(&is_nil/1)
      |> Enum.take(limit)
    {:ok, notifications}
  end

  def recent(_), do: {:error, :invalid_limit}
end
