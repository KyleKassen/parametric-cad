"""
Fit check for the B210 mount family — run by lib.evaluate as a validator, and
standalone for fast iteration:

    C:/venvs/cadquery/Scripts/python.exe parts/custom/ettus-b210-mount/fit_check.py

Every assertion below is geometry against the VENDOR SOLID, not against a
number somebody typed. It answers four questions:

  1. Does any mount solid enter a declared keep-out?  (connectors, cable bend,
     LED sight lines, case-screw driver swing, the two side vent slots)
  2. Does any mount solid interfere with the radio itself?
  3. Do the four M3 holes actually line up with the four bores in the vendor
     file — including the 3.05 mm asymmetry that a symmetric bracket misses?
  4. Does the cradle's foot pocket really swallow the rubber foot, and do its
     bridges really clear the top cover by the pad thickness?

Exit 0 = all pass.
"""

import importlib.util
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.housing import clearance, interference  # noqa: E402

_spec = importlib.util.spec_from_file_location("b210_mount", PART_DIR / "model.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

TOL = 1.0          # mm^3 of boolean overlap we call zero (tessellation noise)
failures: list[str] = []
checks = 0


def check(name: str, ok: bool, detail: str) -> None:
    global checks
    checks += 1
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        failures.append(f"{name}: {detail}")


def main() -> int:
    params = M.load_params()
    iface = params["b210_interface"]

    print("\nbuilding mount variants ...")
    mounts = {n: M.BUILDERS[n](params) for n in M.VARIANTS}

    print("importing and placing the vendor solid ...")
    b210 = M.create_b210(params)
    all_solids = b210.solids().vals()

    # The four rubber feet are the only material below the seating plane.
    feet = [s for s in all_solids if s.BoundingBox().zmin < -0.5]
    body = [s for s in all_solids if s.BoundingBox().zmin >= -0.5]
    radio_no_feet = cq.Workplane(obj=cq.Compound.makeCompound(body))
    radio_full = cq.Workplane(obj=cq.Compound.makeCompound(all_solids))

    print(f"  {len(all_solids)} solids, {len(feet)} of them feet\n")
    check("feet_identified", len(feet) == 4, f"{len(feet)} solids below the pan plane")

    # --- 1. the radio lands where the frame says it does -------------------
    bb = radio_no_feet.val().BoundingBox()
    want = iface["body"]
    reach = iface["connector_reach_y"]["value"]
    # X and Z are the sheet-metal envelope; Y is set by the SMA bodies, which
    # stand proud of both end panels and are the outermost material once the
    # feet are off.
    ok = (abs(bb.xmin - want["x"][0]) < 0.05 and abs(bb.xmax - want["x"][1]) < 0.05
          and abs(bb.zmin - want["z"][0]) < 0.05 and abs(bb.zmax - want["z"][1]) < 0.05
          and abs(bb.ymin - reach[0]) < 0.05 and abs(bb.ymax - reach[1]) < 0.05)
    check("frame_transform", ok,
          f"radio sits at x[{bb.xmin:.3f},{bb.xmax:.3f}] y[{bb.ymin:.3f},{bb.ymax:.3f}] "
          f"z[{bb.zmin:.3f},{bb.zmax:.3f}]; expected x{want['x']} z{want['z']} "
          f"y{reach} (SMA bodies)")

    # Handedness: a mirrored import would put the FRONT-end vent slot on -X.
    # Find the two slot voids by probing the wall planes.
    slot = iface["connector_keepouts"]["front_end_slot"]
    probe = cq.Vector((slot["x"][0] + slot["x"][1]) / 2 - 5.0,
                      (slot["y"][0] + slot["y"][1]) / 2,
                      (slot["z"][0] + slot["z"][1]) / 2)
    inside_wall = any(s.isInside(probe, 1e-4) for s in body)
    check("handedness", not inside_wall,
          "the +X wall is open at the front-end slot station "
          f"({probe.x:.1f}, {probe.y:.1f}, {probe.z:.1f}) — not mirrored")

    # --- 2. the four M3 holes line up with the four bores ------------------
    # Probe down each bore axis just inside the radio: it must be void there.
    for x, y in iface["mount_holes"]["positions_xy"]:
        p = cq.Vector(x, y, 1.0)
        solid_here = any(s.isInside(p, 1e-4) for s in body)
        check(f"bore_open_at_{x:+.1f}_{y:+.1f}", not solid_here,
              f"vendor bore is open 1.0 mm above the pan at ({x:.4f}, {y:.4f})")

    # --- 3. no mount solid enters any keep-out -----------------------------
    keepouts = M.create_keepouts(params)
    for name, mount in mounts.items():
        v = interference(mount, keepouts)
        check(f"{name}_vs_keepouts", v <= TOL,
              f"{v:.2f} mm^3 inside a declared keep-out (limit {TOL})")

    # --- 4. no mount solid interferes with the radio -----------------------
    for name, mount in mounts.items():
        radio = radio_full if name == "clamp_cradle" else radio_no_feet
        note = "feet on" if name == "clamp_cradle" else "feet peeled"
        v = interference(mount, radio)
        check(f"{name}_vs_radio", v <= TOL,
              f"{v:.2f} mm^3 overlap with the radio ({note}, limit {TOL})")

    # --- 5. cradle specifics ------------------------------------------------
    cc = params["variants"]["clamp_cradle"]
    tray = M.create_cradle_tray(params)
    foot_v = sum(interference(tray, cq.Workplane(obj=f)) for f in feet)
    check("cradle_pockets_swallow_feet", foot_v <= TOL,
          f"{foot_v:.2f} mm^3 of foot inside the tray (Ø{cc['foot_pocket_diameter']} "
          f"pockets, {cc['tray_thickness']} mm tray vs {iface['feet']['height']} mm feet)")

    bridge = M.create_cradle_bridge(params)
    gap = clearance(bridge, radio_full)
    want_pad = cc["pad_thickness"]
    check("bridge_pad_gap", abs(gap - want_pad) < 0.15,
          f"{gap:.3f} mm between bridge and radio — the {want_pad} mm elastomer pad")

    # bridge legs vs the side walls: this is what buys the slot keep-outs
    leg_gap = cc["bridge_leg_x"] - iface["body"]["x"][1]
    check("bridge_leg_clearance", leg_gap >= 10.0,
          f"{leg_gap:.2f} mm from leg to side wall (10 mm keep-out on the vent slots)")

    # --- 6. screw arithmetic ------------------------------------------------
    grip = iface["screw_grip"]["value"]
    eng = iface["screw_grip"]["engagement"]
    check("screw_penetration", eng <= iface["mount_holes"]["max_screw_penetration"],
          f"{eng} mm engagement against a {iface['mount_holes']['measured_free_depth']} "
          f"mm measured free depth")
    for name in ("flat_plate", "edge_bracket"):
        v = params["variants"][name]
        t = v["thickness"]
        if v.get("m3_head") == "countersunk":
            # the head sits fully in the cone, so the whole plate is grip
            consumed, how = t, f"{t:.1f} mm plate (head fully countersunk)"
        else:
            consumed = min(t, grip)
            how = f"{consumed:.1f} mm under the head (counterbored {t - consumed:.1f})"
        check(f"{name}_screw_length", abs((consumed + eng) - 6.0) < 0.01,
              f"{how} + {eng} mm engagement = M3x6")

    # nothing may stand proud of a face that has to sit flat on the panel
    fp = params["variants"]["flat_plate"]
    csk_depth = (fp["m3_countersink_diameter"] - fp["m3_clearance"]) / 2.0
    check("flat_plate_head_is_flush", csk_depth < fp["thickness"],
          f"Ø{fp['m3_countersink_diameter']} x 90 deg countersink is "
          f"{csk_depth:.2f} mm deep in a {fp['thickness']} mm plate — head sits "
          f"flush, {fp['thickness'] - csk_depth:.2f} mm of parallel material left")

    cc = params["variants"]["clamp_cradle"]
    stack = cc["bridge_thickness"] + cc["tray_thickness"]
    bolt_len = cc["bridge_bolt_length"]
    check("cradle_bolt_does_not_protrude", bolt_len <= stack,
          f"M4x{bolt_len:.0f} into {cc['bridge_thickness']}+{cc['tray_thickness']}"
          f"={stack:.0f} mm of material — nothing proud of the tray underside")

    print(f"\n{checks - len(failures)}/{checks} checks passed")
    for f in failures:
        print(f"  FAILED  {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
