defmodule Tiannara.Observatory.Events.GovernanceEvent do
  @moduledoc """
  Typed constructor for governance events.

  Governance events record authority changes, gate transitions,
  command requests, command rejections, and safe-mode controls.
  """

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Events.Validator

  @spec new(map()) :: {:ok, Event.t()} | {:error, term()}
  def new(attrs) when is_map(attrs) do
    payload_input = Validator.fetch(attrs, :payload) || %{}

    reason =
      Validator.fetch(attrs, :reason) ||
        Validator.fetch(payload_input, :reason)

    with :ok <- Validator.require_fields(attrs, [:source, :type]),
         {:ok, source} <- Validator.coerce_atom(Validator.fetch(attrs, :source)),
         {:ok, type} <- Validator.coerce_atom(Validator.fetch(attrs, :type)),
         {:ok, subject_id} <-
           Validator.coerce_nonempty_binary(
             Validator.fetch(attrs, :subject_id) || "GOVERNANCE"
           ),
         {:ok, severity} <-
           Validator.coerce_severity(Validator.fetch(attrs, :severity) || :info),
         {:ok, epistemic_status} <-
           Validator.coerce_epistemic(
             Validator.fetch(attrs, :epistemic_status) || :observed
           ),
         {:ok, payload} <- Validator.coerce_map(payload_input),
         {:ok, evidence_refs} <-
           Validator.coerce_list(Validator.fetch(attrs, :evidence_refs) || []),
         {:ok, provenance} <-
           Validator.coerce_map(Validator.fetch(attrs, :provenance) || %{}) do
      if type == :command_rejected and Validator.blank?(reason) do
        {:error, {:missing_fields, [:reason]}}
      else
        case Validator.coerce_timestamp(Validator.fetch(attrs, :timestamp)) do
          {:error, _} ->
            {:error, :invalid_timestamp}

          {:ok, timestamp} ->
            {:ok, build_governance_event(attrs, %{
              timestamp: timestamp,
              payload: payload,
              source: source,
              type: type,
              subject_id: subject_id,
              epistemic_status: epistemic_status,
              authorization: Validator.fetch(attrs, :authorization),
              evidence_refs: evidence_refs,
              provenance: provenance,
              severity: severity
            })}
        end
      end
    end
  end

  # Split so the timestamp failure returns an error tuple instead of
  # fabricating DateTime.utc_now() (see Validator.coerce_timestamp/1).
  defp build_governance_event(attrs, coerced) do
    id =
      Validator.fetch(attrs, :id) ||
        Validator.generate_id(
          :governance,
          %{
            source: coerced.source,
            type: coerced.type,
            subject_id: coerced.subject_id,
            payload: coerced.payload
          },
          coerced.timestamp
        )

    {:ok,
     %Event{
       id: id,
       timestamp: coerced.timestamp,
       source: coerced.source,
       category: :governance,
       type: coerced.type,
       subject_id: coerced.subject_id,
       correlation_id: Validator.fetch(attrs, :correlation_id),
       causation_id: Validator.fetch(attrs, :causation_id),
       payload: coerced.payload,
       epistemic_status: coerced.epistemic_status,
       authorization: coerced.authorization,
       evidence_refs: coerced.evidence_refs,
       provenance: coerced.provenance,
       severity: coerced.severity
     }}
  end
end
