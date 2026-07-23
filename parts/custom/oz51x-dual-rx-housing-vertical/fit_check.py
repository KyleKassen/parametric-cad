"""Fit check wrapper for the stacked vertical dual-RX housing."""

import importlib.util
import sys
from pathlib import Path

PART_DIR = Path(__file__).parent
CANONICAL = PART_DIR.parent / "oz510-dual-housing" / "fit_check.py"

spec = importlib.util.spec_from_file_location("oz51x_fit_check", CANONICAL)
_fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_fc)

if __name__ == "__main__":
    sys.exit(_fc.main(PART_DIR))
