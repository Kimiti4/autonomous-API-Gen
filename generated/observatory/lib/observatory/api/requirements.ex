defmodule Tiannara.Observatory.API.Requirements do
  @moduledoc """
  API boundary for Observatory requirement reads.
  """

  alias Tiannara.Observatory.Query

  @spec get(String.t()) :: {:ok, map()} | {:error, term()}
  def get(requirement_id)
      when is_binary(requirement_id) and byte_size(requirement_id) > 0 do
    Query.requirement(requirement_id)
  end

  def get(_), do: {:error, :invalid_id}
end
