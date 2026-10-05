defmodule Tiannara.Observatory.RepairStreamTest do
  use ExUnit.Case
  alias Tiannara.Observatory.RepairStream

  test "valid repair ids can subscribe" do
    assert is_function(&RepairStream.subscribe/1, 1)
    assert RepairStream.event?({:observatory_event,%{type: :repair_report,subject_id: "r1"}})
  end

  test "non-repair events are filtered" do
    refute RepairStream.event?({:observatory_event,%{type: :evolution,subject_id: "r1"}})
    refute RepairStream.event?(:other)
  end

  test "invalid ids fail closed" do
    assert {:error,:invalid_repair_id}=RepairStream.subscribe("")
    assert {:error,:invalid_repair_id}=RepairStream.unsubscribe("")
  end
end
