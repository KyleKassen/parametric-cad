"""Standalone fit gate for the sealed AM59 mast-head V2 concept."""

import sys
from pathlib import Path

from lib.fit import main

PART_DIR = Path(__file__).parent


if __name__ == "__main__":
    sys.exit(main([str(PART_DIR)]))
