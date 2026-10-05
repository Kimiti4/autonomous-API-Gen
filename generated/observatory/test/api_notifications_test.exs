defmodule Tiannara.Observatory.API.NotificationsTest do
  use ExUnit.Case
  alias Tiannara.Observatory.API.Notifications

  test "notification API exposes repair notifications" do
    assert function_exported?(Notifications, :repair, 1)
    assert function_exported?(Notifications, :recent, 1)
  end

  test "invalid repair id fails closed" do
    assert {:error, :invalid_repair_id} = Notifications.repair("")
  end

  test "invalid limit fails closed" do
    assert {:error, :invalid_limit} = Notifications.recent(-1)
  end
end
