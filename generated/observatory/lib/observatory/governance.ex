defmodule Tiannara.Observatory.Governance do
  @moduledoc """
  Observatory command authorization boundary.

  The Observatory may request governed actions.
  It may not execute them.

  Authorization is evaluated against:
  - actor role/clearance
  - current constitutional authority state
  - command class
  """

  alias Tiannara.Observatory.Projections
  alias Tiannara.Observatory.Store

  @read_actions [
    :view_dashboard,
    :view_overview,
    :view_runtime,
    :view_evolution,
    :view_evidence,
    :view_requirement,
    :view_capability,
    :view_knowledge,
    :view_governance,
    :trace,
    :explain
  ]

  @command_actions [
    :request_authorization,
    :request_evolution_definition,
    :request_implementation,
    :request_runtime,
    :request_production_deploy,
    :safe_mode_enable,
    :safe_mode_disable,
    :stop_runtime,
    :restart_runtime
  ]

  @spec authorize(atom(), map(), map()) ::
          :ok | {:error, :unauthorized | :blocked_by_constitution | :unsupported_action}
  def authorize(action, params, actor)
      when is_atom(action) and is_map(params) and is_map(actor) do
    with :ok <- validate_action(action),
         :ok <- check_actor(action, actor),
         :ok <- check_authority(action) do
      :ok
    end
  end

  def authorize(_action, _params, _actor), do: {:error, :unauthorized}

  @spec known_actions() :: %{read: [atom()], command: [atom()]}
  def known_actions do
    %{
      read: @read_actions,
      command: @command_actions
    }
  end

  defp validate_action(action) do
    if action in @read_actions or action in @command_actions do
      :ok
    else
      {:error, :unsupported_action}
    end
  end

  defp check_actor(action, actor) do
    role = Map.get(actor, :role, :observer)
    clearance = Map.get(actor, :clearance, role)

    cond do
      action in @read_actions ->
        if role in [:observer, :operator, :architect, :admin] do
          :ok
        else
          {:error, :unauthorized}
        end

      action in @command_actions ->
        if clearance in [:operator, :architect, :admin] do
          :ok
        else
          {:error, :unauthorized}
        end

      true ->
        {:error, :unauthorized}
    end
  end

  defp check_authority(action) do
    authority = current_authority()

    case action do
      :request_authorization ->
        if authorized?(authority.governance, [:granted]) do
          :ok
        else
          {:error, :blocked_by_constitution}
        end

      :request_evolution_definition ->
        if authorized?(authority.evolution, [:granted, :definition_only]) do
          :ok
        else
          {:error, :blocked_by_constitution}
        end

      :request_implementation ->
        if authorized?(authority.implementation, [:granted]) do
          :ok
        else
          {:error, :blocked_by_constitution}
        end

      :request_runtime ->
        if authorized?(authority.runtime, [:granted]) do
          :ok
        else
          {:error, :blocked_by_constitution}
        end

      :request_production_deploy ->
        if authorized?(authority.production, [:granted]) do
          :ok
        else
          {:error, :blocked_by_constitution}
        end

      :safe_mode_enable ->
        if authorized?(authority.governance, [:granted]) do
          :ok
        else
          {:error, :blocked_by_constitution}
        end

      :safe_mode_disable ->
        if authorized?(authority.governance, [:granted]) do
          :ok
        else
          {:error, :blocked_by_constitution}
        end

      :stop_runtime ->
        if authorized?(authority.runtime, [:granted]) do
          :ok
        else
          {:error, :blocked_by_constitution}
        end

      :restart_runtime ->
        if authorized?(authority.runtime, [:granted]) do
          :ok
        else
          {:error, :blocked_by_constitution}
        end

      _ ->
        {:error, :unsupported_action}
    end
  end

  defp current_authority do
    Store.get_events_by_category(:governance)
    |> Projections.build_governance_state()
    |> Map.get(:current_authority)
  end

  defp authorized?(value, allowed_values) do
    value in allowed_values
  end
end
