defmodule Tiannara.Observatory.RepairReportObservatoryTest do
  use ExUnit.Case
  alias Tiannara.Observatory.Events.RepairReportEvent
  alias Tiannara.Observatory.Projections

  @ts ~U[2026-10-04 01:00:00Z]

  test "repair report event is typed and projected" do
    {:ok, event} = RepairReportEvent.new(%{source: :esap, subject_id: "r1",
      payload: %{status: :validated, report_digest: "abc"}, timestamp: @ts})
    state = Projections.build_repair_state("r1", [event])
    assert state.status == :validated
    assert state.report.report_digest == "abc"
    assert state.events == 1
  end

  test "missing timestamp fails closed" do
    assert {:error, {:missing_fields, [:timestamp]}} =
      RepairReportEvent.new(%{source: :esap, subject_id: "r1", payload: %{status: :validated}})
  end
end
