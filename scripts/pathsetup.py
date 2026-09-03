"""Import this module from scripts/ci or scripts/ops before evaluation imports."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "tools" / "evaluation"

for directory in (ROOT, EVAL):
    entry = str(directory)
    if entry not in sys.path:
        sys.path.insert(0, entry)
