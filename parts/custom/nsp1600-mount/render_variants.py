"""
Product and fit views of every variant, written to references/views/.

    C:/venvs/cadquery/Scripts/python.exe parts/custom/nsp1600-mount/render_variants.py [--out DIR]

Hero views have no axis triad (DESIGN_LANGUAGE.md); the hood's verification
view keeps it so the cable-slot handedness can be read.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
for _p in (str(PROJECT_ROOT), str(PART_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import interface as iface  # noqa: E402
import model  # noqa: E402

from lib.render_step import render_scene  # noqa: E402

METAL = (0.18, 0.19, 0.21)
RING = (0.35, 0.36, 0.38)
HOOD = (0.22, 0.22, 0.24)
UNIT = (0.62, 0.62, 0.64)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", default=str(PART_DIR / "references" / "views"))
    ap.add_argument("--size", type=int, default=1300)
    args = ap.parse_args(argv)
    out = Path(args.out)

    p = model.load_params()
    unit = iface.nsp1600_unit().val()

    # v2 kits: every fabricated piece placed, the unit dropped in
    for kit in ("deck_tab_kit", "bulkhead_strap_kit"):
        items = []
        for name, wp in model.kit_solids(p, kit):
            items.append((wp.val(), HOOD if name == "terminal_box" else METAL, 1.0))
        items.append((unit, UNIT, 1.0))
        for path in render_scene(items, out, f"{kit}_fitted", views=("iso", "top", "right"),
                                 size=args.size, axes=False):
            print(f"  ok {path}")
    for name in ("side_tab", "bulkhead_strap", "terminal_box"):
        solid = model.BUILDERS[name](p).val()
        for path in render_scene([(solid, HOOD if name == "terminal_box" else METAL, 1.0)], out,
                                 f"{name}_part", views=("iso",), size=1000, axes=True):
            print(f"  ok {path}")
    box = model.create_terminal_box(p).val()
    for path in render_scene([(box, HOOD, 1.0)], out, "terminal_box_part",
                             views=("back",), size=1000, axes=True):
        print(f"  ok {path}")

    # v1 kits
    hood = model.create_busbar_hood(p).val()
    for name in model.METAL_VARIANTS:
        mount = model.BUILDERS[name](p).val()
        rings = model.create_spacers(p, name).val()
        for path in render_scene([(mount, METAL, 1.0), (rings, RING, 1.0), (hood, HOOD, 1.0),
                                  (unit, UNIT, 1.0)],
                                 out, f"{name}_fitted", views=("iso", "top", "right"),
                                 size=args.size, axes=False):
            print(f"  ok {path}")
        for path in render_scene([(mount, METAL, 1.0)], out, f"{name}_part",
                                 views=("iso",), size=args.size, axes=False):
            print(f"  ok {path}")
    for path in render_scene([(hood, HOOD, 1.0)], out, "busbar_hood_part",
                             views=("iso", "back"), size=1000, axes=True):
        print(f"  ok {path}")
    for path in render_scene([(hood, HOOD, 0.35), (unit, UNIT, 1.0)], out, "busbar_hood_fitted",
                             views=("iso",), size=args.size, axes=False):
        print(f"  ok {path}")
    # the developed blanks, as the shop will see them
    import flat_patterns

    for name in model.FOLDED_VARIANTS:
        blank, _ = flat_patterns.develop(name, p)
        for path in render_scene([(blank.val(), METAL, 1.0)], out, f"flat_{name}",
                                 views=("top",), size=args.size, axes=True):
            print(f"  ok {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
