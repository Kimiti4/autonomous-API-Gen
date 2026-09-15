defmodule Tiannara.Observatory.API.Evolution do
  @moduledoc """
  API boundary for Observatory evolution reads.
  """

  alias Tiannara.Observatory.Query

  @spec get(String.t()) :: {:ok, map()} | {:error, term()}
  def get(evolution_id) when is_binary(evolution_id) and byte_size(evolution_id) > 0 do
    Query.evolution(evolution_id)
  end

  def get(_), do: {:error, :invalid_id}
end
