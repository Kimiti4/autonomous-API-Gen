defmodule Tiannara.Observatory.API.Evidence do
  @moduledoc """
  API boundary for Observatory evidence reads.
  """

  alias Tiannara.Observatory.Query

  @spec get(String.t()) :: {:ok, map()} | {:error, term()}
  def get(evidence_id) when is_binary(evidence_id) and byte_size(evidence_id) > 0 do
    Query.evidence(evidence_id)
  end

  def get(_), do: {:error, :invalid_id}
end
