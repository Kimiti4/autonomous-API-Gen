defmodule Tiannara.Observatory.API.Governance do
  @moduledoc """
  API boundary for Observatory governance reads.
  """

  alias Tiannara.Observatory.Query

  @spec get() :: {:ok, map()} | {:error, term()}
  def get do
    Query.governance()
  end
end
