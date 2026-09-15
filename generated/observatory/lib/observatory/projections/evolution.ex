defmodule Tiannara.Observatory.Projections.Evolution do
  @moduledoc """
  Pure projection from evolution-cycle events to an evolution read model.

  This projection preserves the governance boundary:
  it reports pipeline state, epistemic state, capability checks,
  decision state, and authorization state without authorizing anything.
  """

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Projections.Helpers

  @stages [
    :requirement_parsed,
    :isr_consulted,
    :constraints_derived,
    :candidate_generated,
    :static_validation,
    :runtime_validation,
    :evidence_certification
  ]

  @default_authorization %{
    interpretation: :granted,
    evolution: :definition_only,
    implementation: :none,
    runtime: :none,
    deployment: :none,
    production: :none,
    governance: :granted
  }

  @spec build_evolution_state(String.t(), [Event.t()]) :: map()
  def build_evolution_state(evolution_id, events)
      when is_binary(evolution_id) and is_list(events) do
    relevant =
      Enum.filter(events, fn event ->
        event.subject_id == evolution_id
      end)

    sorted = Helpers.sort_asc(relevant)

    pipeline = build_pipeline(sorted)

    %{
      evolution_id: evolution_id,
      status: derive_status(sorted, pipeline),
      epistemic_state: derive_epistemic_state(sorted),
      capability_check: derive_capability_check(sorted),
      pipeline: pipeline,
      decision: derive_decision(sorted),
      authorization: derive_authorization(sorted),
      unknowns: derive_unknowns(sorted),
      contradictions: derive_contradictions(sorted),
      updated_at: updated_at(Helpers.latest(sorted))
    }
  end

  defp build_pipeline(events) do
    blocked? = Enum.any?(events, &(&1.type == :evolution_blocked))

    pipeline =
      Enum.map(@stages, fn stage ->
        status =
          cond do
            stage_failed?(events, stage) ->
              :failed

            blocked? and not stage_done?(events, stage) ->
              :blocked

            stage_done?(events, stage) ->
              :done

            true ->
              :pending
          end

        %{
          stage: stage,
          status: status
        }
      end)

    mark_current_stage(pipeline)
  end

  defp stage_done?(events, stage) do
    Enum.any?(events, fn event ->
      direct_stage_complete?(event, stage) or explicit_stage_complete?(event, stage)
    end)
  end

  defp direct_stage_complete?(event, stage) do
    event.type == stage and
      Helpers.payload_get(event.payload, :result, :success) in [
        :success,
        :pass,
        :ok
      ]
  end

  defp explicit_stage_complete?(event, stage) do
    event.type == :stage_completed and
      Helpers.payload_get(event.payload, :stage) == stage and
      Helpers.payload_get(event.payload, :result, :success) in [
        :success,
        :pass,
        :ok
      ]
  end

  defp stage_failed?(events, stage) do
    Enum.any?(events, fn event ->
      event.type == :stage_failed and
        Helpers.payload_get(event.payload, :stage) == stage
    end)
  end

  defp mark_current_stage(pipeline) do
    if Enum.any?(pipeline, &(&1.status in [:failed, :blocked])) do
      pipeline
    else
      mark_first_pending(pipeline, false)
    end
  end

  defp mark_first_pending([], _marked), do: []

  defp mark_first_pending([stage | rest], false) do
    if stage.status == :pending do
      [%{stage | status: :current} | rest]
    else
      [stage | mark_first_pending(rest, false)]
    end
  end

  defp mark_first_pending(pipeline, true), do: pipeline

  defp derive_status([], _pipeline), do: :unknown

  defp derive_status(events, pipeline) do
    blocked? =
      Enum.any?(events, &(&1.type == :evolution_blocked)) or
        Enum.any?(pipeline, &(&1.status == :failed))

    complete? = Enum.all?(pipeline, &(&1.status == :done))

    cond do
      blocked? -> :blocked
      complete? -> :complete
      true -> :in_progress
    end
  end

  defp derive_epistemic_state(events) do
    evidence_events =
      Enum.filter(events, fn event ->
        event.category == :evidence
      end)

    Helpers.count_by_epistemic(evidence_events)
  end

  defp derive_capability_check(events) do
    default = %{
      generation: :unknown,
      validation: :unknown,
      runtime: :unknown,
      production: :unknown
    }

    Enum.reduce(events, default, fn event, acc ->
      if event.type in [:capability_check, :capability_assessed] do
        capability =
          event.payload
          |> Helpers.payload_get(:capability)
          |> normalize_capability()

        status =
          event.payload
          |> Helpers.payload_get(:status, :unknown)
          |> normalize_capability_status()

        if capability in Map.keys(acc) do
          Map.put(acc, capability, status)
        else
          acc
        end
      else
        acc
      end
    end)
  end

  defp normalize_capability(value) when is_atom(value), do: value

  # SECURITY: to_existing_atom only. Unbounded String.to_atom/1 on
  # external input exhausts the atom table and crashes the VM.
  defp normalize_capability(value) when is_binary(value) do
    value
    |> String.downcase()
    |> String.to_existing_atom()
  rescue
    ArgumentError -> :unknown
  end

  defp normalize_capability(_), do: :unknown

  defp normalize_capability_status(value) when is_atom(value), do: value

  defp normalize_capability_status(value) when is_binary(value) do
    value
    |> String.downcase()
    |> String.to_existing_atom()
  rescue
    ArgumentError -> :unknown
  end

  defp normalize_capability_status(_), do: :unknown

  defp derive_decision(events) do
    decision_events =
      Enum.filter(events, fn event ->
        event.type in [
          :decision_recorded,
          :evolution_decision,
          :evolution_advanced,
          :evolution_held,
          :evolution_blocked
        ]
      end)

    case Helpers.latest(decision_events) do
      nil ->
        :unknown

      event ->
        payload_decision = Helpers.payload_get(event.payload, :decision)

        if payload_decision != nil do
          payload_decision
        else
          case event.type do
            :evolution_advanced -> :advanced
            :evolution_held -> :held
            :evolution_blocked -> :blocked
            _ -> :recorded
          end
        end
    end
  end

  defp derive_authorization(events) do
    authorization_events =
      Enum.filter(events, fn event ->
        event.type == :authorization_updated
      end)

    case Helpers.latest(authorization_events) do
      nil ->
        @default_authorization

      event ->
        authority =
          event.payload
          |> Helpers.payload_get(:authority, %{})
          |> normalize_authority()

        Map.merge(@default_authorization, authority)
    end
  end

  defp normalize_authority(authority) when is_map(authority) do
    Enum.into(authority, %{}, fn {key, value} ->
      {normalize_authority_key(key), normalize_authority_value(value)}
    end)
  end

  defp normalize_authority(_), do: %{}

  defp normalize_authority_key(key) when is_atom(key), do: key

  # SECURITY: to_existing_atom only (see normalize_capability/1).
  defp normalize_authority_key(key) when is_binary(key) do
    String.to_existing_atom(key)
  rescue
    ArgumentError ->
      :unknown
  end

  defp normalize_authority_key(_), do: :unknown

  defp normalize_authority_value(value) when is_atom(value), do: value

  defp normalize_author_value(value) when is_binary(value) do
    String.to_existing_atom(value)
  rescue
    ArgumentError ->
      :none
  end

  defp normalize_authority_value(_), do: :none

  defp derive_unknowns(events) do
    events
    |> Enum.filter(&(&1.epistemic_status == :unknown))
    |> Enum.map(fn event ->
      Helpers.payload_get(event.payload, :unknown_id, event.subject_id)
    end)
    |> Enum.uniq()
    |> Enum.sort()
  end

  defp derive_contradictions(events) do
    events
    |> Enum.filter(&(&1.epistemic_status == :contradiction))
    |> Enum.map(fn event ->
      Helpers.payload_get(event.payload, :contradiction_id, event.subject_id)
    end)
    |> Enum.uniq()
    |> Enum.sort()
  end

  defp updated_at(nil), do: nil
  defp updated_at(event), do: event.timestamp
end
