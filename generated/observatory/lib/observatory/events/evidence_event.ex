defmodule Tiannara.Observatory.Events.EvidenceEvent do
  @moduledoc """
  Typed constructor for evidence events.

  Evidence events carry epistemic claims and their boundaries.
  They must preserve observed / inferred / unknown / contradiction distinctions.
  """

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Events.Validator

  @spec new(map()) :: {:ok, Event.t()} | {:error, term()}
  def new(attrs) when is_map(attrs) do
    payload_input = Validator.fetch(attrs, :payload) || %{}

    claim =
      Validator.fetch(attrs, :claim) ||
        Validator.fetch(payload_input, :claim)

    result =
      Validator.fetch(attrs, :result) ||
        Validator.fetch(payload_input, :result)

    scope =
      Validator.fetch(attrs, :scope) ||
        Validator.fetch(payload_input, :scope) ||
        []

    not_proven =
      Validator.fetch(attrs, :not_proven) ||
        Validator.fetch(payload_input, :not_proven) ||
        []

    with :ok <- Validator.require_fields(attrs, [:source, :subject_id]),
         {:ok, source} <- Validator.coerce_atom(Validator.fetch(attrs, :source)),
         {:ok, type} <-
           Validator.coerce_atom(Validator.fetch(attrs, :type) || :evidence_recorded),
         {:ok, subject_id} <-
           Validator.coerce_nonempty_binary(Validator.fetch(attrs, :subject_id)),
         {:ok, claim} <- Validator.coerce_nonempty_binary(claim),
         {:ok, epistemic_status} <-
           Validator.coerce_epistemic(
             Validator.fetch(attrs, :epistemic_status) || :observed
           ),
         {:ok, severity} <-
           Validator.coerce_severity(Validator.fetch(attrs, :severity) || :info),
         {:ok, evidence_refs} <-
           Validator.coerce_list(Validator.fetch(attrs, :evidence_refs) || []),
         {:ok, provenance} <-
           Validator.coerce_map(Validator.fetch(attrs, :provenance) || %{}) do
      if Validator.blank?(result) do
        {:error, {:missing_fields, [:result]}}
      else
        # Outer with-block already bound source/type/subject_id/severity/
        # epistemic_status/evidence_refs/provenance; only the timestamp
        # needs fail-closed handling here.
        case Validator.coerce_timestamp(Validator.fetch(attrs, :timestamp)) do
          {:error, _} ->
            {:error, :invalid_timestamp}

          {:ok, timestamp} ->
            payload =
              Map.merge(payload_input, %{
                claim: claim,
                result: result,
                scope: scope,
                not_proven: not_proven
              })

            id =
              Validator.fetch(attrs, :id) ||
                Validator.generate_id(
                  :evidence,
                  %{
                    source: source,
                    type: type,
                    subject_id: subject_id,
                    claim: claim,
                    result: result,
                    epistemic_status: epistemic_status
                  },
                  timestamp
                )

            {:ok,
             %Event{
               id: id,
               timestamp: timestamp,
               source: source,
               category: :evidence,
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
  end
end
