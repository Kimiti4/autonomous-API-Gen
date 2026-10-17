"""certification.campaign — CBC-1 campaign runner and aggregation."""
# The source tree is named autonomous-api (hyphenated), while Python imports
# use the app package beneath it. Add that source root explicitly so Campaign A
# behaves the same from its CLI and from test runners. The parent package is
# always imported before any submodule, so every campaign consumer gets the
# same import environment regardless of module import order.
import sys
from pathlib import Path

_AUTONOMOUS_API_ROOT = Path(__file__).resolve().parents[2] / "autonomous-api"
if _AUTONOMOUS_API_ROOT.is_dir() and str(_AUTONOMOUS_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_AUTONOMOUS_API_ROOT))
