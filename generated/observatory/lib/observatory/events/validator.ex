defmodule Tiannara.Observatory.Events.Validator do
  @moduledoc """
  Shared validation and coercion rules for Observatory events.

  This module enforces that Observatory events are strongly typed,
  explicitly identified, and epistemically classified.
  """

  @severities [:debug, :info, :warning, :error, :fatal]
  @epistemic_statuses [:observed, :inferred, :unknown, :contradiction]

  @spec fetch(map(), atom()) :: any()
  def fetch(attrs, key) when is_map(attrs) do
    case Map.fetch(attrs, key) do
      {:ok, value} ->
        value

      :error ->
        Map.get(attrs, Atom.to_string(key))
    end
  end

  @spec require_fields(map(), [atom()]) :: :ok | {:error, {:missing_fields, [atom()]}}
  def require_fields(attrs, fields) when is_map(attrs) and is_list(fields) do
    missing =
      Enum.filter(fields, fn field ->
        attrs
        |> fetch(field)
        |> blank?()
      end)

    if missing == [] do
      :ok
    else
      {:error, {:missing_fields, missing}}
    end
  end

  @spec blank?(any()) :: boolean()
  def blank?(nil), do: true
  def blank?(""), do: true
  def blank?([]), do: true
  def blank?(%{} = map), do: map == %{}
  def blank?(_), do: false

  @spec coerce_atom(any()) :: {:ok, atom()} | {:error, :invalid_atom}
  def coerce_atom(value) when is_atom(value), do: {:ok, value}

  def coerce_atom(value) when is_binary(value) do
    try do
      {:ok, String.to_existing_atom(value)}
    rescue
      ArgumentError ->
        {:error, :invalid_atom}
    end
  end

  def coerce_atom(_), do: {:error, :invalid_atom}

  @spec coerce_nonempty_binary(any()) :: {:ok, String.t()} | {:error, :invalid_string}
  def coerce_nonempty_binary(value) when is_binary(value) and byte_size(value) > 0 do
    {:ok, value}
  end

  def coerce_nonempty_binary(value) when is_atom(value) and not is_nil(value) do
    {:ok, Atom.to_string(value)}
  end

  def coerce_nonempty_binary(_), do: {:error, :invalid_string}

  @spec coerce_map(any()) :: {:ok, map()} | {:error, :invalid_map}
  def coerce_map(value) when is_map(value), do: {:ok, value}
  def coerce_map(_), do: {:error, :invalid_map}

  @spec coerce_list(any()) :: {:ok, list()} | {:error, :invalid_list}
  def coerce_list(value) when is_list(value), do: {:ok, value}
  def coerce_list(_), do: {:error, :invalid_list}

  @spec coerce_severity(any()) :: {:ok, atom()} | {:error, :invalid_severity}
  def coerce_severity(value) do
    with {:ok, atom} <- coerce_atom(value) do
      if atom in @severities do
        {:ok, atom}
      else
        {:error, :invalid_severity}
      end
    end
  end

  @spec coerce_epistemic(any()) :: {:ok, atom()} | {:error, :invalid_epistemic_status}
  def coerce_epistemic(value) do
    with {:ok, atom} <- coerce_atom(value) do
      if atom in @epistemic_statuses do
        {:ok, atom}
      else
        {:error, :invalid_epistemic_status}
      end
    end
  end

  # EPISTEMIC HYGIENE: never fabricate a timestamp. An invalid timestamp
  # is an error the caller must handle (fail closed), not silently now().
  @spec coerce_timestamp(any()) :: {:ok, DateTime.t()} | {:error, :invalid_timestamp}
  def coerce_timestamp(%DateTime{} = timestamp), do: {:ok, timestamp}

  def coerce_timestamp(value) when is_binary(value) do
    case DateTime.from_iso8601(value) do
      {:ok, timestamp, _offset} ->
        {:ok, timestamp}

      {:error, _reason} ->
        {:error, :invalid_timestamp}
    end
  end

  def coerce_timestamp(_), do: {:error, :invalid_timestamp}

  @spec generate_id(atom(), map(), DateTime.t()) :: String.t()
  def generate_id(category, attrs, %DateTime{} = timestamp) do
    binary =
      :erlang.term_to_binary(
        {
          category,
          attrs,
          timestamp
        }
      )

    hash =
      :crypto.hash(:sha256, binary)
      |> Base.encode16(case: :lower)

    "evt-#{category}-" <> binary_part(hash, 0, 24)
  end
end
