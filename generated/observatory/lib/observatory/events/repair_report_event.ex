defmodule Tiannara.Observatory.Events.RepairReportEvent do
  @moduledoc """Typed Observatory event for ESAP repair reports."""

  alias Tiannara.Observatory.Event
  alias Tiannara.Observatory.Events.Validator

  @spec new(map()) :: {:ok, Event.t()} | {:error, term()}
  def new(attrs) when is_map(attrs) do
    with :ok <- Validator.require_fields(attrs, [:source, :subject_id, :payload, :timestamp]),
         {:ok, source} <- Validator.coerce_atom(Validator.fetch(attrs, :source)),
         {:ok, subject_id} <- Validator.coerce_nonempty_binary(Validator.fetch(attrs, :subject_id)),
         {:ok, payload} <- Validator.coerce_map(Validator.fetch(attrs, :payload)),
         {:ok, severity} <- Validator.coerce_severity(Validator.fetch(attrs, :severity) || :info),
         {:ok, epistemic} <- Validator.coerce_epistemic(Validator.fetch(attrs, :epistemic_status) || :observed),
         {:ok, evidence_refs} <- Validator.coerce_list(Validator.fetch(attrs, :evidence_refs) || []),
         {:ok, provenance} <- Validator.coerce_map(Validator.fetch(attrs, :provenance) || %{}),
         {:ok, timestamp} <- Validator.coerce_timestamp(Validator.fetch(attrs, :timestamp)) do
      id = Validator.fetch(attrs, :id) ||
        Validator.generate_id(:repair_report, %{source: source, subject_id: subject_id, payload: payload}, timestamp)

      {:ok, %Event{id: id, timestamp: timestamp, source: source, category: :evolution,
        type: :repair_report, subject_id: subject_id,
        correlation_id: Validator.fetch(attrs, :correlation_id),
        causation_id: Validator.fetch(attrs, :causation_id), payload: payload,
        epistemic_status: epistemic, authorization: Validator.fetch(attrs, :authorization),
        evidence_refs: evidence_refs, provenance: provenance, severity: severity}}
    end
  end
end
