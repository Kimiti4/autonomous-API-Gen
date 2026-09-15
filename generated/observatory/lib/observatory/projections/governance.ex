defmodule Tiannara.Observatory.Projections.Governance do
  @moduledoc """
  Pure projection from governance events to governance read model.

  The default authority state is least-privilege:
  interpretation is granted, evolution definition is allowed,
  and execution/production authority is absent.
  """

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Projections.Helpers

  @default_authority %{
    interpretation: :granted,
    evolution: :definition_only,
    implementation: :none,
    runtime: :none,
    deployment: :none,
    production: :none,
    governance: :granted
  }

  @human_controls [
    :safe_mode,
    :stop,
    :restart,
    :request_authorization
  ]

  @spec build_governance_state([Event.t()]) :: map()
  def build_governance_state(events) when is_list(events) do
    governance_events =
      events
      |> Enum.filter(&(&1.category == :governance))
      |> Helpers.sort_asc()

    state =
      Enum.reduce(
        governance_events,
        %{
          authority: @default_authority,
          gates: %{},
          safe_mode: :unknown,
          commands: %{
            requested: 0,
            accepted: 0,
            rejected: 0
          }
        },
        &apply_event/2
      )

    %{
      current_authority: state.authority,
      active_gates: format_gates(state.gates),
      safe_mode: state.safe_mode,
      human_controls: @human_controls,
      command_activity: state.commands
    }
  end

  defp apply_event(event, state) do
    case event.type do
      :authority_updated ->
        authority =
          event.payload
          |> Helpers.payload_get(:authority, %{})
          |> normalize_authority()

        %{state | authority: Map.merge(state.authority, authority)}

      :gate_updated ->
        gate = Helpers.payload_get(event.payload, :gate)
        status = Helpers.payload_get(event.payload, :status)

        if gate == nil do
          state
        else
          gates = Map.put(state.gates, gate, status)
          %{state | gates: gates}
        end

      :safe_mode_enabled ->
        %{state | safe_mode: true}

      :safe_mode_disabled ->
        %{state | safe_mode: false}

      :command_requested ->
        commands = Map.update!(state.commands, :requested, &(&1 + 1))
        %{state | commands: commands}

      :command_accepted ->
        commands = Map.update!(state.commands, :accepted, &(&1 + 1))
        %{state | commands: commands}

      :command_rejected ->
        commands = Map.update!(state.commands, :rejected, &(&1 + 1))
        %{state | commands: commands}

      _ ->
        state
    end
  end

  defp normalize_authority(authority) when is_map(authority) do
    Enum.into(authority, %{}, fn {key, value} ->
      {normalize_key(key), normalize_value(value)}
    end)
  end

  defp normalize_authority(_), do: %{}

  defp normalize_key(key) when is_atom(key), do: key

  defp normalize_key(key) when is_binary(key) do
    String.to_atom(key)
  rescue
    ArgumentError -> :unknown
  end

  defp normalize_key(_), do: :unknown

  defp normalize_value(value) when is_atom(value), do: value

  defp normalize_value(value) when is_binary(value) do
    String.to_atom(value)
  rescue
    ArgumentError -> :none
  end

  defp normalize_value(_), do: :none

  defp format_gates(gates) do
    gates
    |> Enum.map(fn {gate, status} ->
      %{
        gate: gate,
        status: status
      }
    end)
    |> Enum.sort_by(&to_string(&1.gate))
  end
end
