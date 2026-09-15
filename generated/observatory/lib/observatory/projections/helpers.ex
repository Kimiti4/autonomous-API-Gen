defmodule Tiannara.Observatory.Projections.Helpers do
  @moduledoc """
  Shared pure helpers for Observatory projections.

  These helpers do not access external state.
  They operate only on the event list supplied by the caller.
  """

  alias Tiannara.Observatory.Event

  @spec sort_asc([Event.t()]) :: [Event.t()]
  def sort_asc(events) when is_list(events) do
    Enum.sort_by(
      events,
      & &1.timestamp,
      fn left, right ->
        DateTime.compare(left, right) != :gt
      end
    )
  end

  @spec latest([Event.t()]) :: Event.t() | nil
  def latest(events) when is_list(events) do
    Enum.reduce(events, nil, fn event, acc ->
      if acc == nil or DateTime.compare(event.timestamp, acc.timestamp) == :gt do
        event
      else
        acc
      end
    end)
  end

  @spec payload_get(map(), atom(), any()) :: any()
  def payload_get(payload, key, default \\ nil) when is_map(payload) do
    case Map.fetch(payload, key) do
      {:ok, value} ->
        value

      :error ->
        Map.get(payload, Atom.to_string(key), default)
    end
  end

  @spec count_by_epistemic([Event.t()]) :: map()
  def count_by_epistemic(events) when is_list(events) do
    Enum.reduce(
      events,
      %{
        observed: 0,
        inferred: 0,
        unknown: 0,
        contradiction: 0
      },
      fn event, acc ->
        Map.update(acc, event.epistemic_status, 1, &(&1 + 1))
      end
    )
  end
end
