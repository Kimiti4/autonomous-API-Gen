defmodule Tiannara.Observatory.Events.EvolutionEvent do
  @moduledoc """
  Typed constructor for evolution-cycle events.

  Evolution events track the pipeline from requirement through ISR constraints,
  candidate generation, validation, runtime validation, and evidence certification.
  """

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Events.Validator

  @spec new(map()) :: {:ok, Event.t()} | {:error, term()}
  def new(attrs) when is_map(attrs) do
    with :ok <- Validator.require_fields(attrs, [:source, :type, :subject_id]),
         {:ok, source} <- Validator.coerce_atom(Validator.fetch(attrs, :source)),
         {:ok, type} <- Validator.coerce_atom(Validator.fetch(attrs, :type)),
         {:ok, subject_id} <-
           Validator.coerce_nonempty_binary(Validator.fetch(attrs, :subject_id)),
         {:ok, severity} <-
           Validator.coerce_severity(Validator.fetch(attrs, :severity) || :info),
         {:ok, epistemic_status} <-
           Validator.coerce_epistemic(
             Validator.fetch(attrs, :epistemic_status) || :observed
           ),
         {:ok, payload} <- Validator.coerce_map(Validator.fetch(attrs, :payload) || %{}),
         {:ok, evidence_refs} <-
           Validator.coerce_list(Validator.fetch(attrs, :evidence_refs) || []),
          {:ok, provenance} <-
            Validator.coerce_map(Validator.fetch(attrs, :provenance) || %{}),
          {:ok, timestamp} <-
            Validator.coerce_timestamp(Validator.fetch(attrs, :timestamp)) do
       id =
        Validator.fetch(attrs, :id) ||
          Validator.generate_id(
            :evolution,
            %{
              source: source,
              type: type,
              subject_id: subject_id,
              payload: payload
            },
            timestamp
          )

      {:ok,
       %Event{
         id: id,
         timestamp: timestamp,
         source: source,
         category: :evolution,
         type: type,
         subject_id: subject_id,
         correlation_id: Validator.fetch(attrs, :correlation_id),
         causation_id: Validator.fetch(attrs, :causation_id),
         payload: payload,
         epistemic_status: epistemic_status,
         authorization: Validator.fetch(attrs, :authorization),
         evidence_refs: evidence_refs,
         provenance: provenance,
         severity: severity
       }}
    end
  end
end
