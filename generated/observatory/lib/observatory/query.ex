defmodule Tiannara.Observatory.Query do
  @moduledoc """
  Read-only query facade for the Observatory.

  All functions here are read-side operations.
  They do not mutate runtime state, issue commands, or trigger evolution.
  """

  alias Tiannara.Observatory.Projections
  alias Tiannara.Observatory.Projections.Helpers
  alias Tiannara.Observatory.Store

  @spec dashboard() :: {:ok, map()} | {:error, term()}
  def dashboard do
    with {:ok, overview} <- overview(),
         {:ok, runtime} <- runtime(),
         {:ok, governance} <- governance(),
         {:ok, timeline} <- timeline(limit: 20) do
      {:ok,
       %{
         overview: overview,
         runtime: runtime,
         governance: governance,
         timeline: timeline
       }}
    end
  end

  @spec overview() :: {:ok, map()} | {:error, term()}
  def overview do
    recent = Store.recent_events(100)

    runtime = runtime_state()
    governance = governance_state()
    current_cycle = current_cycle(recent)

    {:ok,
     %{
       current_cycle: current_cycle,
       status: overall_status(runtime, governance),
       runtime_health: runtime.health,
       safe_mode: governance.safe_mode,
       evidence_count: Store.count_events_by_category(:evidence),
       authorization_state: authorization_state(current_cycle, governance),
       recent_event_count: length(recent)
     }}
  end

  @spec runtime() :: {:ok, map()}
  def runtime do
    {:ok, runtime_state()}
  end

  @spec evolution(String.t()) :: {:ok, map()} | {:error, :not_found}
  def evolution(evolution_id) when is_binary(evolution_id) and byte_size(evolution_id) > 0 do
    events = Store.get_events_for_subject(evolution_id)

    if events == [] do
      {:error, :not_found}
    else
      {:ok, Projections.build_evolution_state(evolution_id, events)}
    end
  end

  def evolution(_), do: {:error, :invalid_id}

  @spec evidence(String.t()) :: {:ok, map()} | {:error, :not_found}
  def evidence(evidence_id) when is_binary(evidence_id) and byte_size(evidence_id) > 0 do
    subject_events = Store.get_events_for_subject(evidence_id)

    evidence_events =
      if subject_events == [] do
        Store.get_events_by_category(:evidence)
      else
        subject_events
      end

    Projections.get_evidence(evidence_events, evidence_id)
  end

  def evidence(_), do: {:error, :invalid_id}

  @spec requirement(String.t()) :: {:ok, map()} | {:error, :not_found}
  def requirement(requirement_id)
      when is_binary(requirement_id) and byte_size(requirement_id) > 0 do
    events = Store.get_events_for_subject(requirement_id)

    if events == [] do
      {:error, :not_found}
    else
      {:ok, build_requirement_state(requirement_id, events)}
    end
  end

  def requirement(_), do: {:error, :invalid_id}

  @spec capability(String.t()) :: {:ok, map()} | {:error, :not_found}
  def capability(capability_id)
      when is_binary(capability_id) and byte_size(capability_id) > 0 do
    events = Store.get_events_for_subject(capability_id)

    if events == [] do
      {:error, :not_found}
    else
      {:ok, build_capability_state(capability_id, events)}
    end
  end

  def capability(_), do: {:error, :invalid_id}

  @spec knowledge(String.t() | nil) :: {:ok, map() | [map()]} | {:error, :not_found}
  def knowledge(nil) do
    events = Store.get_events_by_category(:knowledge) ++ Store.get_events_by_category(:evidence)
    {:ok, Projections.build_knowledge_state(events)}
  end

  def knowledge(subject_id) when is_binary(subject_id) and byte_size(subject_id) > 0 do
    events = Store.get_events_for_subject(subject_id)

    if events == [] do
      {:error, :not_found}
    else
      Projections.get_knowledge(events, subject_id)
    end
  end

  def knowledge(_), do: {:error, :invalid_id}

  @spec governance() :: {:ok, map()}
  def governance do
    {:ok, governance_state()}
  end

  @spec timeline(keyword()) :: {:ok, [map()]} | {:error, :not_found}
  def timeline(opts \\ []) do
    subject = Keyword.get(opts, :subject)
    limit = Keyword.get(opts, :limit, 50)

    events =
      if subject do
        Store.get_events_for_subject(subject)
      else
        Store.recent_events(limit)
      end

    if subject && events == [] do
      {:error, :not_found}
    else
      entries =
        events
        |> Enum.take(limit)
        |> Enum.map(&format_timeline_event/1)

      {:ok, entries}
    end
  end

  @spec health() :: {:ok, map()}
  def health do
    runtime = runtime_state()
    governance = governance_state()

    {:ok,
     %{
       status: overall_status(runtime, governance),
       runtime: runtime,
       governance: governance,
       store: %{
         event_count: Store.count_events(),
         evidence_event_count: Store.count_events_by_category(:evidence),
         runtime_event_count: Store.count_events_by_category(:runtime),
         governance_event_count: Store.count_events_by_category(:governance)
       }
     }}
  end

  defp runtime_state do
    Store.get_events_by_category(:runtime)
    |> Projections.build_runtime_state()
  end

  defp governance_state do
    Store.get_events_by_category(:governance)
    |> Projections.build_governance_state()
  end

  defp current_cycle(recent_events) do
    evolution_events =
      Enum.filter(recent_events, fn event ->
        event.category == :evolution
      end)

    case Helpers.latest(evolution_events) do
      nil ->
        nil

      event ->
        %{
          evolution_id: event.subject_id,
          latest_event_type: event.type,
          updated_at: event.timestamp
        }
    end
  end

  defp overall_status(runtime, governance) do
    cond do
      runtime.health == :degraded -> :degraded
      governance.safe_mode == true -> :safe_mode
      runtime.health == :green -> :operational
      true -> :unknown
    end
  end

  defp authorization_state(nil, _governance), do: :not_applicable

  defp authorization_state(_current_cycle, governance) do
    if governance.current_authority.implementation == :none do
      :required
    else
      :granted
    end
  end

  defp build_requirement_state(requirement_id, events) do
    sorted = Helpers.sort_asc(events)
    latest = Helpers.latest(sorted)

    %{
      requirement_id: requirement_id,
      status: Helpers.payload_get(latest.payload, :status, latest.epistemic_status),
      epistemic_state: Helpers.count_by_epistemic(sorted),
      evidence_refs: collect_evidence_refs(sorted),
      related_capabilities: collect_payload_list(sorted, :capabilities),
      related_evolutions: collect_payload_list(sorted, :evolutions),
      unknown_dependencies: collect_payload_list(sorted, :unknown_dependencies),
      updated_at: latest.timestamp
    }
  end

  defp build_capability_state(capability_id, events) do
    sorted = Helpers.sort_asc(events)
    latest = Helpers.latest(sorted)

    %{
      capability_id: capability_id,
      status: Helpers.payload_get(latest.payload, :status, latest.epistemic_status),
      epistemic_state: Helpers.count_by_epistemic(sorted),
      evidence_refs: collect_evidence_refs(sorted),
      related_requirements: collect_payload_list(sorted, :requirements),
      related_evolutions: collect_payload_list(sorted, :evolutions),
      updated_at: latest.timestamp
    }
  end

  defp collect_evidence_refs(events) do
    events
    |> Enum.flat_map(& &1.evidence_refs)
    |> Enum.uniq()
    |> Enum.sort()
  end

  defp collect_payload_list(events, key) do
    events
    |> Enum.flat_map(fn event ->
      value = Helpers.payload_get(event.payload, key, [])

      if is_list(value) do
        value
      else
        [value]
      end
    end)
    |> Enum.reject(&is_nil/1)
    |> Enum.uniq()
    |> Enum.sort()
  end

  defp format_timeline_event(event) do
    %{
      event_id: event.id,
      timestamp: event.timestamp,
      category: event.category,
      type: event.type,
      subject_id: event.subject_id,
      epistemic_status: event.epistemic_status,
      severity: event.severity,
      summary: summarize_event(event)
    }
  end

  defp summarize_event(event) do
    case Helpers.payload_get(event.payload, :summary) do
      nil ->
        "#{event.type}: #{event.subject_id}"

      summary ->
        to_string(summary)
    end
  end
end
