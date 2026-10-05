defmodule Tiannara.Observatory.RepairNotificationsTest do
  use ExUnit.Case
  alias Tiannara.Observatory.RepairNotifications

  test "blocked repair raises actionable notification" do
    e=%{type: :repair_report,subject_id: "r1",payload: %{status: :blocked},severity: :warning}
    n=RepairNotifications.from_event(e)
    assert n.action_required
    assert n.severity==:warning
  end

  test "deployment-ready repair requests human authorization" do
    e=%{type: :repair_report,subject_id: "r1",payload: %{status: :deployment_ready,report_digest: "d"},severity: :info}
    n=RepairNotifications.from_event(e)
    assert n.deployment_authorization_required
    assert n.action_required
  end

  test "unrelated events do not notify" do
    assert RepairNotifications.from_event(%{type: :evolution,subject_id: "r1",payload: %{}})==nil
  end
end
