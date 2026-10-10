from tiannara.application.compiler.frontend_targets import FRONTEND_TARGETS

def test_frontend_matrix_contains_requested_targets():
    ids={x.target_id for x in FRONTEND_TARGETS}
    assert {"react_ts","vue_ts","angular_ts","next_ts","nuxt_ts","svelte_ts",
            "phoenix_liveview","hologram","scenic"} <= ids

def test_frontend_targets_are_not_marked_production_ready_by_registration():
    assert all(not x.production_ready for x in FRONTEND_TARGETS)

def test_elixir_targets_have_distinct_runtime_models():
    models={x.target_id:x.runtime_model for x in FRONTEND_TARGETS if x.language=="elixir"}
    assert models["phoenix_liveview"]=="server_reactive"
    assert models["hologram"]=="server_client_elixir"
    assert models["scenic"]=="native_gui"
