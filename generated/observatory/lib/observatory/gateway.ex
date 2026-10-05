defmodule Tiannara.Observatory.Gateway do
  alias Tiannara.Observatory.{API,Query,Event,EventBus,Ingestion,Governance,Tracer}
  defdelegate dashboard(), to: Query
  defdelegate overview(), to: API.Overview
  defdelegate runtime(), to: API.Runtime
  defdelegate evolution(id), to: API.Evolution, as: :get
  defdelegate evidence(id), to: API.Evidence, as: :get
  defdelegate requirement(id), to: API.Requirements, as: :get
  defdelegate knowledge(id \ nil), to: API.Knowledge, as: :get
  defdelegate governance(), to: API.Governance
  defdelegate repair(id), to: Query
  defdelegate repair_notification(id), to: API.Notifications, as: :repair
  defdelegate recent_notifications(limit \\ 20), to: API.Notifications, as: :recent
  defdelegate timeline(opts \ []), to: Query
  defdelegate health(), to: Query
  defdelegate trace(id), to: Tracer
  defdelegate explain(id), to: Tracer
  def observe(%Event{}=e), do: Ingestion.ingest(e)
  def observe_many(es) when is_list(es), do: Ingestion.ingest_many(es)
  def subscribe(:all), do: EventBus.subscribe_all()
  def subscribe({:category,c}), do: EventBus.subscribe_category(c)
  def subscribe({:subject,s}), do: EventBus.subscribe_subject(s)
  def subscribe(s) when is_binary(s), do: subscribe({:subject,s})
  def unsubscribe(:all), do: EventBus.unsubscribe_all()
  def unsubscribe({:category,c}), do: EventBus.unsubscribe_category(c)
  def unsubscribe({:subject,s}), do: EventBus.unsubscribe_subject(s)
  def unsubscribe(s) when is_binary(s), do: unsubscribe({:subject,s})
end
