"""V1-04 HeartbeatEmitter -- liveness, sequence monotonic."""
import asyncio
from core.contracts.events import EventTypes
class HeartbeatEmitter:
    def __init__(self, dispatcher, interval_seconds: float = 15.0):
        self._dispatcher = dispatcher
        self._interval = interval_seconds
        self._task = None
        self._active_streams = set()
    def track_stream(self, stream_id: str): self._active_streams.add(stream_id)
    def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._loop())
    async def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None
    async def _loop(self):
        while True:
            await asyncio.sleep(self._interval)
            for sid in list(self._active_streams):
                try:
                    await self._dispatcher.emit(stream_id=sid, event_type=EventTypes.HEARTBEAT, payload={"purpose": "liveness"}, correlation_id=f"heartbeat-{sid}", generation=0)
                except Exception:
                    pass
