"""
Drop the real vendor solids into every mount variant and measure the fit.

Run by `lib.evaluate` as a part validator (exit 0 = PASS), and standalone while
iterating. Four things get asserted, and each is the kind of mistake a render
would not catch:

  1. INTERFERENCE — no mount may overlap the chassis or a connector. Zero.
  2. CONTACT AREA — the opposite failure. A bracket that clears everything is
     not a mount; it has to *bear*. Contact area is measured by pushing the unit
     0.05 mm into the bracket and dividing the overlap volume by 0.05, which
     gives real mm2 of seated face rather than a yes/no touch.
  3. KEEP-OUTS — nothing inside the fin volume, the 55 mm I/O cable envelope or
     the 45 mm antenna envelope.
  4. CROSS-VARIANT FIT — the three general mounts must also take the 30 W and
     Tile chassis, since they only ever touch the two faces all three share.

Screw penetration is not checked here: `interface.check_backwall_screw()` and
`check_bottom_screw()` raise during the build, so a bracket whose fastener
schedule bottoms out never gets as far as a fit check.

    uv run python parts/custom/bedrock-v3000-mount/fit_check.py [--verbose]

Units: mm, mm2, mm3.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:      # for `lib.*` only — never this part's dir
    sys.path.insert(0, str(PROJECT_ROOT))


# Sibling modules are loaded by explicit path under a namespaced key, never by
# putting this part's directory on sys.path. Every part in this repo has a
# `model.py` and pytest runs them all in one process, so a stray sys.path entry
# here silently hands OUR model.py to another part's tests.
def _sibling(name: str):
    key = f"bedrock_v3000_mount.{name}"
    mod = sys.modules.get(key)
    if mod is None:
        spec = importlib.util.spec_from_file_location(key, PART_DIR / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return mod


iface = _sibling("interface")
model = _sibling("model")

from lib.housing import clearance, interference  # noqa: E402

PROBE = 0.05          # mm of interpenetration used to measure contact area
MAX_INTERFERENCE = 0.5   # mm3 — tessellation-free booleans, so this is tight

# Each bearing face is probed on its own axis, so the reported area belongs to
# that face alone: (label, press direction, minimum mm2).
#   variant -> (chassis it is for, [bearing faces])
EXPECT = {
    "upright_deck": ("60w", [
        ("pan on the -Z cap", (0.0, 0.0, -PROBE), 1200.0),
        ("spine tongue on the +Y land", (0.0, PROBE, 0.0), 1200.0),
    ]),
    "upright_bulkhead": ("60w", [
        ("shelf on the -Z cap", (0.0, 0.0, -PROBE), 700.0),
        ("web tongue on the +Y land", (0.0, PROBE, 0.0), 1200.0),
    ]),
    "low_profile_side": ("60w", [
        ("end wall on the -Z cap", (0.0, 0.0, -PROBE), 2500.0),
        ("back wall tongue on the +Y land", (0.0, PROBE, 0.0), 1500.0),
    ]),
    "tile_side_plate": ("tile", [
        ("plate on the -X side flat", (-PROBE, 0.0, 0.0), 12000.0),
    ]),
    "hybrid_cold_plate": ("hybrid_posx", [
        ("cold plate on the flat side", (-PROBE, 0.0, 0.0), 14000.0),
    ]),
}

# Which chassis each mount must ALSO take unedited. The three general mounts work
# only the +Y land and the -Z cap, which every chassis shares. The two side plates
# work a flat side, which only the Tile core has — so they take the Tile and both
# hybrid handednesses, and nothing else.
ALSO_FITS = {
    "upright_deck": ("30w", "tile", "hybrid_posx", "hybrid_negx"),
    "upright_bulkhead": ("30w", "tile", "hybrid_posx", "hybrid_negx"),
    "low_profile_side": ("30w", "tile", "hybrid_posx", "hybrid_negx"),
    "tile_side_plate": ("hybrid_posx",),
    "hybrid_cold_plate": ("tile",),
}


def contact_area(mount, unit, press: tuple) -> float:
    """
    Seated face area in mm2, from the overlap when the unit is pressed in by PROBE.

    A clearance of 0.0 only says two solids touch somewhere — a single corner
    counts. Volume per unit of interpenetration says how much of the bracket is
    actually carrying, which is the number a joint is designed around. Press on
    one axis at a time or the faces get conflated.
    """
    depth = max(abs(c) for c in press)
    return interference(mount, unit.translate(press)) / depth


def check(verbose: bool = False) -> int:
    p = model.load_params()
    units = {k: iface.bedrock_unit(k)
             for k in ("60w", "30w", "tile", "hybrid_posx", "hybrid_negx")}
    failures = []

    for name, builder in model.BUILDERS.items():
        target, faces = EXPECT[name]
        mount = builder(p)
        unit = units[target]

        overlap = interference(mount, unit)
        gap = clearance(mount, unit)
        print(f"\n  {name}  (vs {target})")
        print(f"    interference   {overlap:8.3f} mm3   (limit {MAX_INTERFERENCE})")
        print(f"    clearance      {gap:8.3f} mm")
        if overlap > MAX_INTERFERENCE:
            failures.append(f"{name}: overlaps the unit by {overlap:.2f} mm3")

        for label, press, min_area in faces:
            area = contact_area(mount, unit, press)
            flag = "" if area >= min_area else "   <-- NOT SEATED"
            print(f"    bearing: {label:<32} {area:8.1f} mm2 (min {min_area:.0f}){flag}")
            if area < min_area:
                failures.append(f"{name}: {label} bears on only {area:.0f} mm2, "
                                f"wanted {min_area:.0f}")

        for ko in ("io_cables", "sma_cables", "fin_bank_neg_x", "fin_bank_pos_x"):
            solid = None
            try:
                solid = iface.keepout_solid(ko, target)
            except KeyError:
                continue          # the Tile has no fin banks
            v = interference(mount, solid)
            flag = "" if v <= MAX_INTERFERENCE else "   <-- INTRUSION"
            if verbose or flag:
                print(f"    keep-out {ko:<15} {v:8.2f} mm3{flag}")
            if v > MAX_INTERFERENCE:
                failures.append(f"{name}: {v:.1f} mm3 inside the {ko} envelope")

        for other in ALSO_FITS[name]:
            v = interference(mount, units[other])
            if verbose:
                print(f"    fits {other:<12} {v:8.3f} mm3")
            if v > MAX_INTERFERENCE:
                failures.append(f"{name}: does not take the {other} chassis "
                                f"({v:.1f} mm3 overlap)")

    print()
    if failures:
        for f in failures:
            print(f"  FAIL  {f}")
        return 1
    print("  all fit checks passed")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--verbose", action="store_true")
    sys.exit(check(ap.parse_args().verbose))
