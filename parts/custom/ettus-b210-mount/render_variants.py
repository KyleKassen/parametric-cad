"""
Render each mount variant with the radio sitting in it.

    C:/venvs/cadquery/Scripts/python.exe \
        parts/custom/ettus-b210-mount/render_variants.py [--out DIR]

Product views follow DESIGN_LANGUAGE.md: no axis triad, dark matte body, the
radio in a contrasting tone, three-quarter iso from slightly above.  The mount
draws opaque and the radio translucent, so the mount is what you look at.
"""

import importlib.util
import sys
from pathlib import Path

PART_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.render_step import render_scene  # noqa: E402

_spec = importlib.util.spec_from_file_location("b210_mount", PART_DIR / "model.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

MOUNT = (0.18, 0.18, 0.19, 1.0)       # dark matte
RADIO = (0.88, 0.52, 0.20, 0.45)      # contrast, translucent


def main() -> int:
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv \
        else PART_DIR / "references" / "views"
    out.mkdir(parents=True, exist_ok=True)

    params = M.load_params()
    print("importing the vendor solid ...")
    radio_all = M.create_b210(params).solids().vals()
    # the four rubber feet are the only material below the seating plane; they
    # come off for the bolted variants and stay on for the cradle
    body = [s for s in radio_all if s.BoundingBox().zmin >= -0.5]

    import cadquery as cq
    radio_no_feet = cq.Workplane(obj=cq.Compound.makeCompound(body))
    radio_full = cq.Workplane(obj=cq.Compound.makeCompound(radio_all))

    for name in M.VARIANTS:
        mount = M.BUILDERS[name](params)
        radio = radio_full if name == "clamp_cradle" else radio_no_feet
        scene = [(mount.val(), MOUNT[:3], MOUNT[3]),
                 (radio.val(), RADIO[:3], RADIO[3])]
        for f in render_scene(scene, out, f"{name}_fitted",
                              views=("iso", "front", "right", "top"),
                              size=1400, axes=False):
            print(f"  ok  {f}")

        # the mount on its own, for the shop
        for f in render_scene([(mount.val(), MOUNT[:3], 1.0)], out,
                              f"{name}_part", views=("iso",),
                              size=1400, axes=False):
            print(f"  ok  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
