defmodule Tiannara.Observatory.Supervisor do
  @moduledoc """
  Supervision tree for the Unified Observatory backend.

  The Observatory is an observer and governed command surface.
  It must not become a single point of failure for the cognitive runtime.
  """

  use Supervisor

  alias Tiannara.Observatory.{Ingestion, Store}

  def start_link(opts \\ []) do
    Supervisor.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @impl true
  def init(_opts) do
    children = [
      Store,
      Ingestion
    ]

    Supervisor.init(children, strategy: :one_for_one)
  end
end
