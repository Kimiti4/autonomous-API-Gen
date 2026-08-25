"""35.3 Stateful -- healthy->degraded->detected->contained->recovered."""
from enum import Enum
class State(str, Enum):
    HEALTHY="healthy"; DEGRADED="degraded"; DETECTED="failure_detected"; CONTAINED="contained"; DIAGNOSED="diagnosed"; REPAIRING="repairing"; RECONFIGURED="reconfigured"; RECOVERED="recovered"
