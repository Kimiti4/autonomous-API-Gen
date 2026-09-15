defmodule Tiannara.Observatory.Gateway do
  @moduledoc """
  Public Observatory gateway.

  This module is the only sanctioned entrypoint for UI and subsystem access
  to Observatory read models and governed command requests.

  It does not execute commands.
  It does not mutate runtime state.
  It does not bypass governance.
  """

  alias Tiannara.Observatory.{
    API,
    Event,
    EventBus,
    Governance,
    Ingestion,
    Query,
    Tracer
  }

  alias Tiannara.Observatory.Events.GovernanceEvent

  @allowed_command_actions [
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

  # --------------------------------------------------------------------
  # Read-only views
  # --------------------------------------------------------------------

  @spec dashboard() :: {:ok, map()} | {:error, term()}
  def dashboard do
    Query.dashboard()
  end

  @spec overview() :: {:ok, map()} | {:error, term()}
  def overview do
    API.Overview.get()
  end

  @spec runtime() :: {:ok, map()} | {:error, term()}
  def runtime do
    API.Runtime.get()
  end

  @spec evolution(String.t()) :: {:ok, map()} | {:error, term()}
  def evolution(evolution_id) do
    API.Evolution.get(evolution_id)
  end

  @spec evidence(String.t()) :: {:ok, map()} | {:error, term()}
  def evidence(evidence_id) do
    API.Evidence.get(evidence_id)
  end

  @spec requirement(String.t()) :: {:ok, map()} | {:error, term()}
  def requirement(requirement_id) do
    API.Requirements.get(requirement_id)
  end

  @spec capability(String.t()) :: {:ok, map()} | {:error, term()}
  def capability(capability_id) do
    Query.capability(capability_id)
  end

  @spec knowledge(String.t() | nil) :: {:ok, map() | [map()]} | {:error, term()}
  def knowledge(subject_id \\ nil) do
    API.Knowledge.get(subject_id)
  end

  @spec governance() :: {:ok, map()} | {:error, term()}
  def governance do
    API.Governance.get()
  end

  @spec timeline(keyword()) :: {:ok, [map()]} | {:error, term()}
  def timeline(opts \\ []) do
    Query.timeline(opts)
  end

  @spec health() :: {:ok, map()} | {:error, term()}
  def health do
    Query.health()
  end

  @spec trace(String.t()) :: {:ok, [Event.t()]} | {:error, term()}
  def trace(subject_id) do
    Tracer.trace(subject_id)
  end

  @spec explain(String.t()) :: {:ok, map()} | {:error, term()}
  def explain(subject_id) do
    Tracer.explain(subject_id)
  end

  # --------------------------------------------------------------------
  # Event ingestion
  # --------------------------------------------------------------------

  @spec observe(Event.t()) :: :ok
  def observe(%Event{} = event) do
    Ingestion.ingest(event)
  end

  @spec observe_many([Event.t()]) :: :ok
  def observe_many(events) when is_list(events) do
    Ingestion.ingest_many(events)
  end

  # --------------------------------------------------------------------
  # Live subscription
  # --------------------------------------------------------------------

  @spec subscribe(:all | {:category, atom()} | {:subject, String.t()} | String.t()) ::
          :ok | {:error, term()}
  def subscribe(:all), do: EventBus.subscribe_all()
  def subscribe({:category, category}), do: EventBus.subscribe_category(category)
  def subscribe({:subject, subject_id}), do: EventBus.subscribe_subject(subject_id)
  def subscribe(subject_id) when is_binary(subject_id), do: subscribe({:subject, subject_id})
  def subscribe(_), do: {:error, :invalid_subscription}

  @spec unsubscribe(:all | {:category, atom()} | {:subject, String.t()} | String.t()) ::
          :ok | {:error, term()}
  def unsubscribe(:all), do: EventBus.unsubscribe_all()
  def unsubscribe({:category, category}), do: EventBus.unsubscribe_category(category)
  def unsubscribe({:subject, subject_id}), do: EventBus.unsubscribe_subject(subject_id)

  def unsubscribe(subject_id) when is_binary(subject_id),
    do: unsubscribe({:subject, subject_id})

  def unsubscribe(_), do: {:error, :invalid_subscription}

  # --------------------------------------------------------------------
  # Governed command boundary
  # --------------------------------------------------------------------

  @spec request_command(atom() | String.t(), map(), map()) ::
          {:ok, String.t()} | {:error, term()}
  def request_command(action, params, actor)
      when is_map(params) and is_map(actor) do
    with {:ok, action} <- coerce_action(action),
         :ok <- validate_command_action(action),
         :ok <- Governance.authorize(action, params, actor) do
      request_id = generate_request_id(action, params)
      target_id = get_param(params, :target_id) || request_id

      case GovernanceEvent.new(%{
             source: :observatory_gateway,
             type: :command_requested,
             subject_id: target_id,
             epistemic_status: :observed,
             severity: :info,
             payload: %{
               request_id: request_id,
               action: action,
               params: redact(params),
               actor_id: actor_id(actor)
             }
           }) do
        {:ok, event} ->
          :ok = EventBus.publish(event)
          {:ok, request_id}

        {:error, reason} ->
          {:error, {:event_construction_failed, reason}}
      end
    else
      {:error, reason} ->
        audit_rejection(action, params, actor, reason)
        {:error, reason}
    end
  end

  def request_command(_action, _params, _actor), do: {:error, :invalid_request}

  # --------------------------------------------------------------------
  # Private helpers
  # --------------------------------------------------------------------

  defp coerce_action(action) when is_atom(action), do: {:ok, action}

  defp coerce_action(action) when is_binary(action) do
    try do
      {:ok, String.to_existing_atom(action)}
    rescue
      ArgumentError ->
        {:error, :unsupported_action}
    end
  end

  defp coerce_action(_), do: {:error, :unsupported_action}

  defp validate_command_action(action) do
    if action in @allowed_command_actions do
      :ok
    else
      {:error, :unsupported_action}
    end
  end

  defp audit_rejection(action, params, actor, reason) do
    target_id = get_param(params, :target_id) || "GOVERNANCE"

    case GovernanceEvent.new(%{
           source: :observatory_gateway,
           type: :command_rejected,
           subject_id: to_string(target_id),
           epistemic_status: :observed,
           severity: :warning,
           reason: inspect(reason),
           payload: %{
             action: normalize_action_for_audit(action),
             params: redact(params),
             actor_id: actor_id(actor),
             reason: reason
           }
         }) do
      {:ok, event} ->
        EventBus.publish(event)

      {:error, _reason} ->
        :ok
    end
  end

  defp normalize_action_for_audit(action) when is_atom(action), do: action
  defp normalize_action_for_audit(action), do: to_string(action)

  defp generate_request_id(action, params) do
    binary =
      :erlang.term_to_binary({
        action,
        redact(params),
        DateTime.utc_now()
      })

    hash =
      :crypto.hash(:sha256, binary)
      |> Base.encode16(case: :lower)

    "REQ-" <> binary_part(hash, 0, 20)
  end

  defp get_param(params, key) when is_map(params) do
    case Map.fetch(params, key) do
      {:ok, value} ->
        value

      :error ->
        Map.get(params, Atom.to_string(key))
    end
  end

  defp actor_id(actor) when is_map(actor) do
    Map.get(actor, :id) || Map.get(actor, "id") || "anonymous"
  end

  defp actor_id(_), do: "anonymous"

  defp redact(params) when is_map(params) do
    Enum.into(params, %{}, fn {key, value} ->
      if secret_key?(key) do
        {key, "[REDACTED]"}
      else
        {key, redact(value)}
      end
    end)
  end

  defp redact(params) when is_list(params) do
    Enum.map(params, &redact/1)
  end

  defp redact(value), do: value

  defp secret_key?(key) do
    normalized =
      key
      |> to_string()
      |> String.downcase()

    Enum.any?(
      [
        "password",
        "secret",
        "token",
        "credential",
        "api_key",
        "apikey",
        "private_key",
        "session"
      ],
      &String.contains?(normalized, &1)
    )
  end
end
