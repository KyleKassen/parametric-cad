"""
Drop the real vendor solid into every kit and measure the fit.

Run by `lib.evaluate` as a part validator (exit 0 = PASS) and standalone while
iterating. Everything asserted here is the kind of mistake a render would not
catch:

  v2 tab kits
  1. Each tab lies FLUSH on the side wall - zero interference, and real bearing
     area on the leg when the unit is pressed sideways.
  2. The straps carry the unit: zero interference, bearing on both shelves when
     it is pressed down, the tab feet sitting on the shelf tips.
  3. The terminal box clears the unit and the tabs, sits on the terminal strap,
     keeps every lug and cable envelope inside, and no fixed opening admits a
     finger probe.
  v1 channel kits
  4. Full-footprint bearing on the pan, the 3 mm wall gap with its ring, the
     open-bottom hood on the pan.
  Both
  5. KEEP-OUTS - no metal in the exhaust plume, in front of the terminal face,
     or across the LED / trim-pot sight line.

Screw penetration is not checked here: interface.check_side_screw() and
check_bottom_screw() raise during the build.

    C:/venvs/cadquery/Scripts/python.exe parts/custom/nsp1600-mount/fit_check.py [--verbose]

Units: mm, mm2, mm3.
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

import cadquery as cq  # noqa: E402
import interface as iface  # noqa: E402
import model  # noqa: E402

from lib.housing import clearance, interference  # noqa: E402

PROBE = 0.05
MAX_INTERFERENCE = 0.5
MIN_PAN_BEARING = 20000.0    # mm2 - the unit's footprint is 25551 less slots and holes
MIN_STRAP_BEARING = 4500.0   # mm2 - a full 45 x 85 strip plus the 22.5 x 85 the terminal
                             # strap has under the unit, less arcs and holes
MIN_TAB_BEARING = 250.0      # mm2 per tab - 20 x 24 of flat leg less the hole, the vendor's
                             # recessed screw mouths and, at the terminal station, the
                             # 4.2 mm that overhangs the plate (about 320 there, 450 at the fan end)
KEEPOUTS = ("fan_exhaust", "terminal_face", "led_svr_access")
ENVELOPES = ("lug_long", "lug_short", "ac_cable")


def contact_area(a, b, press: tuple) -> float:
    depth = max(abs(c) for c in press)
    return interference(a, b.translate(press)) / depth


def wall_only(mount, p: dict, side: str):
    """The flat part of one channel wall, above its bend tangent."""
    s = model.channel_stations(p)
    sg = 1 if side == "+X" else -1
    return mount.intersect(model._box(sg * (s["x_in"] - 0.5), sg * (s["x_out"] + 1),
                                      -400, 200, s["z_tan"] + 0.5, 200))


def check(verbose: bool = False) -> int:
    p = model.load_params()
    unit = iface.nsp1600_unit()
    failures: list[str] = []

    def expect(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    def keepouts(name, solid):
        for ko in KEEPOUTS:
            v = interference(solid, iface.keepout_solid(ko))
            flag = "" if v <= MAX_INTERFERENCE else "   <-- INTRUSION"
            if verbose or flag:
                print(f"    keep-out {ko:<18} {v:9.2f} mm3{flag}")
            expect(v <= MAX_INTERFERENCE, f"{name}: {v:.1f} mm3 inside {ko}")

    def cover(name, solid, cavity):
        for env in ENVELOPES:
            env_box = iface.keepout_solid(env)
            hit = interference(solid, env_box)
            outside = sum(abs(s.Volume()) for s in env_box.val().cut(cavity.val()).Solids())
            print(f"    {env:<10} inside: {outside:7.2f} mm3 outside, {hit:7.2f} mm3 in a wall")
            expect(outside <= 1.0, f"{name}: the {env} envelope pokes {outside:.1f} mm3 out")
            expect(hit <= MAX_INTERFERENCE, f"{name}: a wall passes through the {env} envelope")
        sight = interference(solid, iface.keepout_solid("led_svr_access"))
        print(f"    across the LED / trim-pot sight line  {sight:7.2f} mm3")
        expect(sight <= MAX_INTERFERENCE, f"{name}: {sight:.1f} mm3 across the LED sight line")

    # ---------------------------------------------------------------- v2 tabs
    print("\n  side_tab x4 (deck_tab_kit)")
    tabs = model.tabs_deck(p)
    v = interference(tabs, unit)
    print(f"    interference with the unit      {v:9.3f} mm3   (limit {MAX_INTERFERENCE})")
    expect(v <= MAX_INTERFERENCE, f"tabs: overlap the unit by {v:.2f} mm3")
    for one in tabs.val().Solids():
        # push the unit INTO this tab's leg and measure what carries
        c = one.Center()
        press = (PROBE, 0, 0) if c.x > 0 else (-PROBE, 0, 0)     # toward this tab
        area = contact_area(cq.Workplane(obj=one), unit, press)
        where = f"({'+X' if c.x > 0 else '-X'}, Y {c.y:6.1f})"
        print(f"    bearing, side wall on the tab at {where} {area:7.1f} mm2   "
              f"(min {MIN_TAB_BEARING:.0f})")
        expect(area >= MIN_TAB_BEARING, f"tabs: the tab at {where} bears on only {area:.0f} mm2")
    g = clearance(tabs, unit)
    expect(g < 1e-3, f"tabs: do not touch the unit (gap {g:.3f})")
    keepouts("tabs", tabs)

    # -------------------------------------------------------------- v2 straps
    print("\n  bulkhead_strap x2 + side_tab x2 (bulkhead_strap_kit)")
    straps = model.straps_bulkhead(p)
    tabs_b = model.tabs_bulkhead(p)
    v = interference(straps, unit)
    print(f"    straps vs the unit              {v:9.3f} mm3")
    expect(v <= MAX_INTERFERENCE, f"straps: overlap the unit by {v:.2f} mm3")
    area = contact_area(straps, unit, (0, 0, -PROBE))
    print(f"    bearing, unit bottom on both shelves {area:8.1f} mm2   "
          f"(min {MIN_STRAP_BEARING:.0f})")
    expect(area >= MIN_STRAP_BEARING, f"straps: the unit bears on only {area:.0f} mm2")
    v = interference(straps, tabs_b)
    g = clearance(straps, tabs_b)
    print(f"    tab feet on the shelf tips       overlap {v:7.3f} mm3   gap {g:6.3f} mm")
    expect(v <= MAX_INTERFERENCE, f"straps: the tabs overlap them by {v:.2f} mm3")
    expect(g < 1e-3, f"straps: the tab feet do not sit on the shelves (gap {g:.3f})")
    v = interference(tabs_b, unit)
    expect(v <= MAX_INTERFERENCE, f"bulkhead tabs: overlap the unit by {v:.2f} mm3")
    keepouts("straps", straps)
    keepouts("bulkhead tabs", tabs_b)

    # ----------------------------------------------------------------- v2 box
    print("\n  terminal_box")
    box = model.create_terminal_box(p)
    v = interference(box, unit)
    g = clearance(box, unit)
    print(f"    interference with the unit      {v:9.3f} mm3   clearance {g:6.3f} mm")
    expect(v <= MAX_INTERFERENCE, f"box: overlaps the unit by {v:.2f} mm3")
    expect(g >= 2.0, f"box: only {g:.2f} mm from the unit")
    for name, other in (("deck tabs", tabs), ("bulkhead tabs", tabs_b)):
        v = interference(box, other)
        g = clearance(box, other)
        print(f"    vs {name:<14}                  overlap {v:7.3f} mm3   gap {g:6.3f} mm")
        expect(v <= MAX_INTERFERENCE, f"box: overlaps the {name} by {v:.2f} mm3")
        expect(g >= 1.0, f"box: only {g:.2f} mm from the {name}")
    v = interference(box, straps)
    g = clearance(box, straps)
    print(f"    floor on the terminal strap      overlap {v:7.3f} mm3   gap {g:6.3f} mm")
    expect(v <= MAX_INTERFERENCE, f"box: overlaps the straps by {v:.2f} mm3")
    expect(g < 1e-3, f"box: does not sit on the terminal strap (gap {g:.3f})")
    cover("box", box, model.box_cavity(p))
    bv = p["variants"]["terminal_box"]
    widest = max(bv["top_louvres"]["w"], bv["side_louvres"]["w"],
                 bv["led_window"]["x"][1] - bv["led_window"]["x"][0])
    print(f"    widest fixed opening              {widest:6.1f} mm    (IP2X probe 12.5; "
          f"cable exits are filled by cables)")
    expect(widest <= 12.0, f"box: a {widest} mm opening admits an IP2X finger probe")

    # ---------------------------------------------------------- v1 channels
    hood = model.create_busbar_hood(p)
    for name in model.METAL_VARIANTS:
        mount = model.BUILDERS[name](p)
        rings = model.create_spacers(p, name)
        print(f"\n  {name} (v1)")
        v = interference(mount, unit)
        print(f"    interference with the unit      {v:9.3f} mm3   (limit {MAX_INTERFERENCE})")
        expect(v <= MAX_INTERFERENCE, f"{name}: overlaps the unit by {v:.2f} mm3")
        area = contact_area(mount, unit, (0, 0, -PROBE))
        print(f"    bearing, unit bottom on the pan {area:9.1f} mm2   (min {MIN_PAN_BEARING:.0f})")
        expect(area >= MIN_PAN_BEARING, f"{name}: the unit bears on only {area:.0f} mm2")
        for side in model.walls_for(p, name):
            gap = clearance(wall_only(mount, p, side), unit)
            expect(abs(gap - p["dimensions"]["side_gap"]) < 0.02,
                   f"{name}: {side} wall stands {gap:.3f} mm off the unit")
        for other, label in ((unit, "unit"), (mount, name)):
            v = interference(rings, other)
            g = clearance(rings, other)
            expect(v <= MAX_INTERFERENCE, f"{name}: rings overlap the {label} by {v:.2f} mm3")
            expect(g < 1e-3, f"{name}: rings do not touch the {label} (gap {g:.3f})")
        keepouts(name, mount)
        v = interference(hood, mount)
        g = clearance(hood, mount)
        expect(v <= MAX_INTERFERENCE, f"{name}: the hood overlaps the channel by {v:.2f} mm3")
        expect(g < 1e-3, f"{name}: the hood does not sit on the pan (gap {g:.3f})")
    print("\n  busbar_hood (v1)")
    v = interference(hood, unit)
    g = clearance(hood, unit)
    print(f"    interference with the unit      {v:9.3f} mm3   clearance {g:6.3f} mm")
    expect(v <= MAX_INTERFERENCE, f"hood: overlaps the unit by {v:.2f} mm3")
    expect(g >= 0.4, f"hood: only {g:.2f} mm from the unit")
    cover("hood", hood, model.hood_cavity(p))

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
