defmodule Tiannara.Observatory.Query do
  alias Tiannara.Observatory.Projections
  alias Tiannara.Observatory.Projections.Helpers
  alias Tiannara.Observatory.Store

  def dashboard do
    with {:ok, overview} <- overview(), {:ok, runtime} <- runtime(),
         {:ok, governance} <- governance(), {:ok, timeline} <- timeline(limit: 20) do
      {:ok, %{overview: overview, runtime: runtime, governance: governance, timeline: timeline}}
    end
  end
  def overview do
    recent=Store.recent_events(100); runtime=runtime_state(); governance=governance_state()
    current_cycle=current_cycle(recent)
    {:ok,%{current_cycle: current_cycle,status: overall_status(runtime,governance),
      runtime_health: runtime.health,safe_mode: governance.safe_mode,
      evidence_count: Store.count_events_by_category(:evidence),
      authorization_state: authorization_state(current_cycle,governance),recent_event_count: length(recent)}}
  end
  def runtime, do: {:ok,runtime_state()}
  def evolution(id) when is_binary(id) and byte_size(id)>0 do
    e=Store.get_events_for_subject(id); if e==[], do: {:error,:not_found}, else: {:ok,Projections.build_evolution_state(id,e)}
  end
  def evolution(_), do: {:error,:invalid_id}
  def repair(id) when is_binary(id) and byte_size(id)>0 do
    e=Store.get_events_for_subject(id)
    if e==[], do: {:error,:not_found}, else: {:ok,Projections.build_repair_state(id,e)}
  end
  def repair(_), do: {:error,:invalid_id}
  def evidence(id) when is_binary(id) and byte_size(id)>0 do
    e=Store.get_events_for_subject(id); e=if e==[], do: Store.get_events_by_category(:evidence), else: e
    Projections.get_evidence(e,id)
  end
  def evidence(_), do: {:error,:invalid_id}
  def governance, do: {:ok,governance_state()}
  def timeline(opts \ []) do
    subject=Keyword.get(opts,:subject); limit=Keyword.get(opts,:limit,50)
    e=if subject, do: Store.get_events_for_subject(subject), else: Store.recent_events(limit)
    if subject && e==[], do: {:error,:not_found}, else: {:ok,e |> Enum.take(limit) |> Enum.map(&format_timeline_event/1)}
  end
  def health do
    r=runtime_state(); g=governance_state()
    {:ok,%{status: overall_status(r,g),runtime:r,governance:g,store:%{
      event_count:Store.count_events(),evidence_event_count:Store.count_events_by_category(:evidence),
      runtime_event_count:Store.count_events_by_category(:runtime),governance_event_count:Store.count_events_by_category(:governance)}}
  end
  defp runtime_state, do: Store.get_events_by_category(:runtime)|>Projections.build_runtime_state()
  defp governance_state, do: Store.get_events_by_category(:governance)|>Projections.build_governance_state()
  defp current_cycle(events) do
    events |> Enum.filter(&(&1.category==:evolution)) |> Helpers.latest()
    |> case do nil->nil; e->%{evolution_id:e.subject_id,latest_event_type:e.type,updated_at:e.timestamp} end
  end
  defp overall_status(r,g) do
    cond do r.health==:degraded->:degraded; g.safe_mode==true->:safe_mode; r.health==:green->:operational; true->:unknown end
  end
  defp authorization_state(nil,_), do: :not_applicable
  defp authorization_state(_,g), do: if(g.current_authority.implementation==:none,:required,:granted)
  defp format_timeline_event(e), do: %{event_id:e.id,timestamp:e.timestamp,category:e.category,type:e.type,subject_id:e.subject_id,epistemic_status:e.epistemic_status,severity:e.severity,summary: Helpers.payload_get(e.payload,:summary,"#{e.type}: #{e.subject_id}")}
end
