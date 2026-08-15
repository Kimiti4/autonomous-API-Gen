"""R2.4.0b Step 1 -- async-resolution codegen + naming contract (hermetic).

Grounds the R2.3 ``TransitionRestoration`` naming contract in the REAL FastAPI
backend: each ``WorkflowState.metadata['awaits']`` value becomes a coroutine
named *exactly* that value, awaited iff its resolving ``WorkflowTransition``
(trigger == coroutine) is present, fire-and-forget otherwise.

These are source-level assertions only (no Docker / no pytest): Step 2 wires the
emitted module into the real compile+run closed loop. The contrast here -- the
*same* coroutine name, differing only in await vs fire-and-forget based on the
single resolution edge -- is what lets the Evolution Engine repair by restoring
that one edge.
"""
from __future__ import annotations

from constitutional_architecture.isr.model import (
    StateType,
    Workflow,
    WorkflowState,
    WorkflowTransition,
)

from tiannara.application.compiler.fastapi_hexagonal_backend import FastAPIHexagonalBackend

COROUTINE = "process_payment"


def _workflow(resolving: bool) -> Workflow:
    awaiting = WorkflowState(
        id="order-await",
        name="awaiting",
        state_type=StateType.INTERMEDIATE,
        metadata={"awaits": COROUTINE},
    )
    final = WorkflowState(id="order-final", name="final", state_type=StateType.FINAL)
    transitions = ()
    if resolving:
        transitions = (
            WorkflowTransition(
                id="resolve-payment",
                name="resolve payment",
                from_state_id=awaiting.id,
                to_state_id=final.id,
                trigger=COROUTINE,
            ),
        )
    return Workflow(
        id="order", name="order", states=(awaiting, final), transitions=transitions
    )


def _src(resolving: bool) -> str:
    return FastAPIHexagonalBackend().async_resolution_module((_workflow(resolving),))


# --- naming contract --------------------------------------------------------


def test_coroutine_name_is_exactly_the_awaits_value():
    """The emitted coroutine name must mirror WorkflowState.metadata['awaits']
    character-for-character -- no aliasing, no prefix -- so the operator's stderr
    regex (`coroutine '<name>' was never awaited`) round-trips to the right edge."""
    src = _src(resolving=False)
    assert f"async def {COROUTINE}():" in src
    # guard against accidental renames/aliasing
    assert "async def process_payment():" in src


def test_resolved_workflow_emits_await():
    """Resolving transition present -> awaited call (no RuntimeWarning)."""
    src = _src(resolving=True)
    assert f"await {COROUTINE}()" in src
    assert f"{COROUTINE}()  # fire-and-forget" not in src


def test_broken_workflow_emits_fire_and_forget():
    """Resolving transition absent -> fire-and-forget (no await) -> under
    ``-W error::RuntimeWarning`` surfaces the coroutine-never-awaited warning."""
    src = _src(resolving=False)
    assert f"await {COROUTINE}()" not in src
    assert f"{COROUTINE}()  # fire-and-forget" in src


def test_contrast_same_coroutine_differs_only_by_resolution_edge():
    """The only thing distinguishing broken from repaired is the single resolving
    edge -- same coroutine name, same def. This is the minimal mutation the
    Evolution Engine performs (restore one transition)."""
    repaired = _src(resolving=True)
    broken = _src(resolving=False)
    assert f"async def {COROUTINE}():" in repaired and f"async def {COROUTINE}():" in broken
    assert f"await {COROUTINE}()" in repaired and f"await {COROUTINE}()" not in broken
    assert f"{COROUTINE}()  # fire-and-forget" in broken and f"{COROUTINE}()  # fire-and-forget" not in repaired


# --- structural contract ----------------------------------------------------


def test_emits_orchestrator_entry_point():
    src = _src(resolving=True)
    assert "\nasync def orchestrate():\n" in src


def test_workflow_without_awaits_state_emits_noop_orchestrator():
    idle = Workflow(id="noop", name="noop", states=(
        WorkflowState(id="s", name="s", state_type=StateType.INITIAL),
        WorkflowState(id="f", name="f", state_type=StateType.FINAL),
    ), transitions=())
    src = FastAPIHexagonalBackend().async_resolution_module((idle,))
    assert "async def orchestrate():" in src
    assert "    pass" in src
    # No await *call* emitted (the header comment contains "awaits", so assert on
    # the awaited-form "await " rather than the bare substring).
    assert "await " not in src


def test_multiple_workflows_share_coroutine_definitions():
    """Two workflows awaiting the same coroutine emit one def + both call sites."""
    src = FastAPIHexagonalBackend().async_resolution_module((_workflow(True), _workflow(False)))
    defs = src.count(f"async def {COROUTINE}():")
    assert defs == 1
    assert src.count(f"await {COROUTINE}()") == 1
    assert src.count(f"{COROUTINE}()  # fire-and-forget") == 1
