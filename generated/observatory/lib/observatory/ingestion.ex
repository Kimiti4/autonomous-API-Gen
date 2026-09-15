defmodule Tiannara.Observatory.Ingestion do
  @moduledoc """
  Non-blocking Observatory ingestion buffer.

  Runtime callers should never block on Observatory projection work.
  Events are buffered and published asynchronously.
  """

  use GenServer

  require Logger

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.EventBus

  @max_buffer_size 10_000

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @spec ingest(Event.t()) :: :ok
  def ingest(%Event{} = event) do
    GenServer.cast(__MODULE__, {:ingest, event})
  end

  @spec ingest_many([Event.t()]) :: :ok
  def ingest_many(events) when is_list(events) do
    Enum.each(events, &ingest/1)
  end

  @impl true
  def init(_opts) do
    {:ok, %{buffer: :queue.new(), size: 0}}
  end

  @impl true
  def handle_cast({:ingest, event}, %{buffer: buffer, size: size} = state) do
    {buffer, size} =
      if size >= @max_buffer_size do
        case :queue.out(buffer) do
          {{:value, _dropped}, reduced} ->
            {reduced, size - 1}

          {:empty, _} ->
            {buffer, size}
        end
      else
        {buffer, size}
      end

    buffer = :queue.in(event, buffer)
    send(self(), :flush)

    {:noreply, %{state | buffer: buffer, size: size + 1}}
  end

  @impl true
  def handle_info(:flush, %{buffer: buffer, size: size} = state) do
    case :queue.out(buffer) do
      {:empty, _} ->
        {:noreply, %{state | buffer: buffer, size: 0}}

      {{:value, event}, new_buffer} ->
        try do
          EventBus.publish(event)
        rescue
          error ->
            Logger.warning(
              "Observatory ingestion publish failed: #{inspect(error)}"
            )
        end

        unless :queue.is_empty(new_buffer) do
          send(self(), :flush)
        end

        {:noreply, %{state | buffer: new_buffer, size: max(size - 1, 0)}}
    end
  end
end
