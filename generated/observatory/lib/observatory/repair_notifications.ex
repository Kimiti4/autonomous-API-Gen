defmodule Tiannara.Observatory.RepairNotifications do
  @moduledoc """Governed notification projection for ESAP repair lifecycle events."""

  alias Tiannara.Observatory.Event

  @type notification :: %{
    id: String.t(),
    severity: atom(),
    title: String.t(),
    message: String.t(),
    repair_id: String.t(),
    action_required: boolean(),
    deployment_authorization_required: boolean()
  }

  @spec from_event(Event.t()) :: notification() | nil
  def from_event(%Event{type: :repair_report, subject_id: repair_id, payload: payload, severity: severity}) do
    status = get(payload, :status, :unknown)
    {title, message, action} =
      case status do
        :blocked -> {"Repair blocked", "ESAP repair requires investigation before admission.", true}
        :deployment_ready -> {"Repair ready for authorization", "Verified repair is ready for human deployment authorization.", true}
        :validated -> {"Repair validated", "Repair verification completed without reported regressions.", false}
        _ -> {"Repair state updated", "ESAP repair state changed; review the Observatory evidence.", true}
      end

    %{
      id: :crypto.hash(:sha256, "#{repair_id}|#{status}|#{get(payload, :report_digest, "")}") |> Base.encode16(case: :lower),
      severity: severity,
      title: title,
      message: message,
      repair_id: repair_id,
      action_required: action,
      deployment_authorization_required: status == :deployment_ready
    }
  end

  def from_event(_), do: nil

  defp get(map, key, default) do
    Map.get(map, key, Map.get(map, Atom.to_string(key), default))
  end
end
