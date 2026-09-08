"""Regenerate this part's presentation and verification renders.

Product shots follow DESIGN_LANGUAGE.md's render rules: no axis triad, dark
matte body on a white ground, hero three-quarter iso plus supporting views.
Verification renders keep the triad, because there they are the point.

    uv run python parts/custom/<this-dir>/make_views.py
"""

import importlib.util
import sys
from pathlib import Path

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.render_step import render_scene  # noqa: E402

spec = importlib.util.spec_from_file_location("part_model", PART_DIR / "model.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)

BODY = (0.30, 0.32, 0.35)  # dark matte; the low end of the house range
ACCENT = (0.40, 0.42, 0.46)  # cover, one step lighter


def main() -> int:
    params = model.load_params()
    base = model.create_base(params).val()
    lid = model.create_lid(params).val()
    out = PART_DIR / "references"

    render_scene(
        [(base, BODY, 1.0), (lid, ACCENT, 1.0)],
        out,
        "product",
        views=("iso", "front", "right", "back"),
        size=1100,
        axes=False,
    )
    render_scene(
        [(base, BODY, 1.0)],
        out,
        "base",
        views=("iso", "top", "bottom", "right"),
        size=1100,
        axes=False,
    )
    render_scene(
        [(lid, ACCENT, 1.0)],
        out,
        "cover",
        views=("iso", "top", "bottom"),
        size=1100,
        axes=False,
    )
    print("  ✓ renders written to", out.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
