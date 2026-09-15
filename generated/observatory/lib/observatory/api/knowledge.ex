defmodule Tiannara.Observatory.API.Knowledge do
  @moduledoc """
  API boundary for Observatory knowledge reads.
  """

  alias Tiannara.Observatory.Query

  @spec get(String.t() | nil) :: {:ok, map() | [map()]} | {:error, term()}
  def get(subject_id \\ nil) do
    Query.knowledge(subject_id)
  end
end
