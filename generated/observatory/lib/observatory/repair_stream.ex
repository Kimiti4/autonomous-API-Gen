defmodule Tiannara.Observatory.RepairStream do
  @moduledoc """Live repair-report subscription adapter for Observatory consumers."""

  alias Tiannara.Observatory.EventBus

  @spec subscribe(String.t()) :: :ok | {:error, term()}
  def subscribe(repair_id) when is_binary(repair_id) and byte_size(repair_id) > 0 do
    EventBus.subscribe_subject(repair_id)
  end

  def subscribe(_), do: {:error, :invalid_repair_id}

  @spec subscribe_all() :: :ok | {:error, term()}
  def subscribe_all, do: EventBus.subscribe_category(:evolution)

  @spec unsubscribe(String.t()) :: :ok | {:error, term()}
  def unsubscribe(repair_id) when is_binary(repair_id) and byte_size(repair_id) > 0 do
    EventBus.unsubscribe_subject(repair_id)
  end

  def unsubscribe(_), do: {:error, :invalid_repair_id}

  @spec event?(term()) :: boolean()
  def event?({:observatory_event, %{type: :repair_report, subject_id: id}}) when is_binary(id), do: true
  def event?(_), do: false
end
