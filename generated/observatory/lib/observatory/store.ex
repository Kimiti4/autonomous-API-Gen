defmodule Tiannara.Observatory.Store do
  @moduledoc """
  Observatory read-model store.

  This store maintains in-memory indexes for:
  - event identity
  - subject identity
  - category identity
  - chronological timeline

  Reads are concurrent.
  Writes are serialized through the GenServer.
  """

  use GenServer

  alias Tiannara.Observatory.Event

  @events_table :observatory_events
  @subjects_table :observatory_subjects
  @categories_table :observatory_categories
  @timeline_table :observatory_timeline

  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @spec write(Event.t()) :: :ok
  def write(%Event{} = event) do
    GenServer.call(__MODULE__, {:write, event})
  end

  @spec get_event(String.t()) :: {:ok, Event.t()} | {:error, :not_found}
  def get_event(event_id) when is_binary(event_id) do
    case fetch_event(event_id) do
      nil -> {:error, :not_found}
      event -> {:ok, event}
    end
  end

  @spec get_events_for_subject(String.t()) :: [Event.t()]
  def get_events_for_subject(subject_id) when is_binary(subject_id) do
    fetch_events_by_index(@subjects_table, subject_id)
  end

  @spec get_events_by_category(atom()) :: [Event.t()]
  def get_events_by_category(category) when is_atom(category) do
    fetch_events_by_index(@categories_table, category)
  end

  @spec recent_events(pos_integer()) :: [Event.t()]
  def recent_events(limit) when is_integer(limit) and limit > 0 do
    if table_exists?(@timeline_table) do
      collect_recent(:ets.last(@timeline_table), limit, [])
    else
      []
    end
  end

  @spec count_events() :: non_neg_integer()
  def count_events do
    if table_exists?(@events_table) do
      :ets.info(@events_table, :size)
    else
      0
    end
  end

  @spec count_events_by_category(atom()) :: non_neg_integer()
  def count_events_by_category(category) when is_atom(category) do
    if table_exists?(@categories_table) do
      @categories_table
      |> :ets.lookup(category)
      |> length()
    else
      0
    end
  end

  @impl true
  def init(_opts) do
    :ets.new(@events_table, [
      :named_table,
      :public,
      :set,
      read_concurrency: true
    ])

    :ets.new(@subjects_table, [
      :named_table,
      :public,
      :bag,
      read_concurrency: true
    ])

    :ets.new(@categories_table, [
      :named_table,
      :public,
      :bag,
      read_concurrency: true
    ])

    :ets.new(@timeline_table, [
      :named_table,
      :public,
      :ordered_set,
      read_concurrency: true
    ])

    {:ok, %{event_count: 0}}
  end

  @impl true
  def handle_call({:write, %Event{} = event}, _from, state) do
    timeline_key = {DateTime.to_unix(event.timestamp, :microsecond), event.id}

    true = :ets.insert(@events_table, {event.id, event})
    true = :ets.insert(@subjects_table, {event.subject_id, event.id})
    true = :ets.insert(@categories_table, {event.category, event.id})
    true = :ets.insert(@timeline_table, {timeline_key, event.id})

    {:reply, :ok, %{state | event_count: state.event_count + 1}}
  end

  defp table_exists?(table) do
    :ets.info(table) != :undefined
  end

  defp fetch_event(event_id) do
    if table_exists?(@events_table) do
      case :ets.lookup(@events_table, event_id) do
        [{^event_id, event}] -> event
        [] -> nil
      end
    else
      nil
    end
  end

  defp fetch_events_by_index(table, key) do
    if table_exists?(table) do
      table
      |> :ets.lookup(key)
      |> Enum.map(fn {_index_key, event_id} ->
        fetch_event(event_id)
      end)
      |> Enum.reject(&is_nil/1)
      |> Enum.sort_by(
        & &1.timestamp,
        fn left, right ->
          DateTime.compare(left, right) != :gt
        end
      )
    else
      []
    end
  end

  defp collect_recent(_key, 0, acc), do: Enum.reverse(acc)

  defp collect_recent(:"$end_of_table", _remaining, acc), do: Enum.reverse(acc)

  defp collect_recent(key, remaining, acc) do
    case :ets.lookup(@timeline_table, key) do
      [{_timeline_key, event_id}] ->
        case fetch_event(event_id) do
          nil ->
            collect_recent(:ets.prev(@timeline_table, key), remaining, acc)

          event ->
            collect_recent(
              :ets.prev(@timeline_table, key),
              remaining - 1,
              [event | acc]
            )
        end

      [] ->
        collect_recent(:ets.prev(@timeline_table, key), remaining, acc)
    end
  end
end
