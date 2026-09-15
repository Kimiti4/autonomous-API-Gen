defmodule Tiannara.Observatory.API.Overview do
  @moduledoc """
  API boundary for Observatory overview reads.
  """

  alias Tiannara.Observatory.Query

  @spec get() :: {:ok, map()} | {:error, term()}
  def get do
    Query.overview()
  end
end
