#!/usr/bin/env python3
"""Run the shared PII check against this repository."""

from __future__ import annotations

import os
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("PII_ROOT", str(ROOT))
os.environ.setdefault("PII_DENYLIST", str(ROOT / "scripts" / "pii-denylist.sha256"))
_NS = runpy.run_path(str(ROOT / "pii-denylist" / "check_pii.py"))
globals().update(
    {
        key: value
        for key, value in _NS.items()
        if key not in {"__name__", "__file__", "__loader__", "__package__", "__cached__", "__spec__"}
    }
)

if __name__ == "__main__":
    raise SystemExit(_NS["main"]())
