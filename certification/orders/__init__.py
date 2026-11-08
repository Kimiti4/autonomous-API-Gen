"""Orders proving-case package (Checkpoint 049)."""
import sys
from pathlib import Path

_AUTONOMOUS_API_ROOT = Path(__file__).resolve().parents[2] / "autonomous-api"
if _AUTONOMOUS_API_ROOT.is_dir() and str(_AUTONOMOUS_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_AUTONOMOUS_API_ROOT))
