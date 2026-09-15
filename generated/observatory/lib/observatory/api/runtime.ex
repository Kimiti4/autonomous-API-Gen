defmodule Tiannara.Observatory.API.Runtime do
  @moduledoc """
  API boundary for Observatory runtime reads.
  """

  alias Tiannara.Observatory.Query

  @spec get() :: {:ok, map()} | {:error, term()}
  def get do
    Query.runtime()
  end
end
