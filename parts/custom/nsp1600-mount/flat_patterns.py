"""
Develop each folded part into the blank a shop actually cuts.

A STEP of a bent part is not a shop pack. What gets ordered is a flat blank
with every hole in it, a bend table and a fastener schedule. All three are
built here from the same solids `model.py` produces, so the blank cannot drift
from the part: the convex skin of each leg (the pan's underside, a wall's outer
face, the tab's unit-facing face, the strap's bulkhead face) is lifted straight
off the built solid - holes, slots, keyholes and countersink mouths included -
laid into the blank plane and slid to its developed station, with a
bend-allowance strip between.

    BA = (pi/180) * angle * (Ri + K*t)

At Ri = t = 3.0 and K = 0.42 a 90 degree bend develops 6.692 mm against a
12.000 mm outside dimension - a bend deduction of 5.308 mm. **K = 0.42 is
assumed, not measured.** Confirm it against the shop's own coupon before
cutting a batch, or hand them the folded STEP and the bend table and let them
develop with their own constant. It affects the blanks only, never the folded
solid or a fit result.

Run by `lib.evaluate` as a validator (exit 0 = every blank develops cleanly),
and standalone:

    C:/venvs/cadquery/Scripts/python.exe parts/custom/nsp1600-mount/flat_patterns.py --out DIR

Units: mm.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
if str(PART_DIR) not in sys.path:
    sys.path.insert(0, str(PART_DIR))

import interface as iface  # noqa: E402
import model  # noqa: E402

STRIP_OVERLAP = 0.05    # mm a bend strip reaches into each leg it joins


def bend_allowance(angle_deg: float, ri: float, t: float, k: float) -> float:
    """Developed length of the bend region, tangent to tangent."""
    return math.radians(angle_deg) * (ri + k * t)


def bend_deduction(angle_deg: float, ri: float, t: float, k: float) -> float:
    return 2 * (ri + t) - bend_allowance(angle_deg, ri, t, k)


# ---------------------------------------------------------------------------
# Lifting faces off the solid
# ---------------------------------------------------------------------------
def leg_face(solid: cq.Workplane, axis: str, plane: float, box: tuple) -> cq.Face:
    """
    The largest planar face on `axis = plane` inside `box` - the convex skin of
    one leg, tangent to tangent, with every feature already in it.
    """
    piece = solid.intersect(model._box(*box))
    idx = "XYZ".index(axis)
    best, best_area = None, 0.0
    for f in piece.val().Faces():
        try:
            n = f.normalAt()
        except Exception:
            continue
        if abs(abs((n.x, n.y, n.z)[idx]) - 1.0) > 1e-3:
            continue
        c = f.Center()
        if abs((c.x, c.y, c.z)[idx] - plane) > 1e-3:
            continue
        if f.Area() > best_area:
            best, best_area = f, f.Area()
    if best is None:
        raise RuntimeError(f"no face on {axis}={plane} inside {box}")
    return best


def _slab(face: cq.Face) -> cq.Workplane:
    """A face laid on Z = 0, as a 1 mm slab."""
    bb = face.BoundingBox()
    moved = face.translate(cq.Vector(0, 0, -bb.zmin))
    return cq.Workplane(obj=moved).wires().toPending().extrude(1.0)


def _strip(u0: float, u1: float, v0: float, v1: float) -> cq.Workplane:
    """A bend-allowance strip, grown across the fold so it fuses with both legs."""
    u0, u1 = sorted((u0, u1))
    v0, v1 = sorted((v0, v1))
    return model._box(u0 - STRIP_OVERLAP, u1 + STRIP_OVERLAP, v0, v1, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Fold plans: which face is the root, which faces fold off it, and where
# ---------------------------------------------------------------------------
def fold_plan(variant: str, params: dict | None = None) -> dict:
    """
    root  = (axis, plane, box): the Z-normal face that lands in the blank
            plane unmoved, (u, v) = (X, Y).
    legs  = [(name, plane_x, box, rot_deg, shift_u, strip)]: X-normal faces
            rotated about Y by rot_deg so their Z runs along u, then shifted so
            the leg's bend tangent lands one bend allowance past the root's
            tangent. strip = (u0, u1, v0, v1) is the allowance between them.
    """
    p = params or model.load_params()
    d = p["dimensions"]
    t, ri, k = d["sheet_t"], d["bend_radius_inside"], d["k_factor"]
    ba = bend_allowance(90.0, ri, t, k)

    if variant in model.METAL_VARIANTS:
        s = model.channel_stations(p)
        y0, y1 = d["pan_y"]
        legs = []
        for side, w in model.walls_for(p, variant).items():
            sg = 1 if side == "+X" else -1
            wy0, wy1 = w["y"]
            legs.append((f"{side} wall", sg * s["x_out"],
                         (sg * s["x_out"] - 1, sg * s["x_out"] + 1, wy0 - 1, wy1 + 1,
                          s["z_tan"], w["h"] + 1),
                         sg * 90.0, sg * (s["x_tan"] + ba - s["z_tan"]),
                         (sg * s["x_tan"], sg * (s["x_tan"] + ba), wy0, wy1)))
        return {"root": ("Z", -t, (-s["x_out"] - 1, s["x_out"] + 1, y0 - 1, y1 + 1,
                                   -t - 1, -t + 1)),
                "root_name": "pan underside", "legs": legs, "ba": ba}

    if variant == "side_tab":
        s = model.tab_stations(p)
        v = p["variants"]["side_tab"]
        w = v["width"]
        foot_end = s["leg_out"] + v["foot_len"]
        # root: the foot's underside (Z = 0), flat from the tangent at 48.5 outward.
        # leg: the unit-facing face (X = 42.5), folded toward -u off the foot's tangent.
        return {"root": ("Z", 0.0, (s["foot_tan"] - 0.01, foot_end + 1, -w - 1, w + 1, -1, 1)),
                "root_name": "foot underside",
                "legs": [("leg", s["leg_in"],
                          (s["leg_in"] - 1, s["leg_in"] + 1, -w - 1, w + 1,
                           s["leg_tan"], v["leg_h"] + 1),
                          -90.0, s["foot_tan"] - ba + s["leg_tan"],
                          (s["foot_tan"] - ba, s["foot_tan"], -w / 2, w / 2))],
                "ba": ba}

    if variant == "bulkhead_strap":
        s = model.channel_stations(p)
        v = p["variants"]["bulkhead_strap"]
        w = v["width"]
        x_tan, x_bulk = -s["x_tan"], -s["x_out"]
        z_tan = -t - ri
        # root: the shelf's TOP (Z = 0, the convex skin), flat from the tangent at -42.5.
        # leg: the flange's bulkhead face (X = -48.5), folded toward -u.
        return {"root": ("Z", 0.0, (x_tan - 0.01, v["shelf_x_tip"] + 1, -w - 1, w + 1, -1, 1)),
                "root_name": "shelf top",
                "legs": [("flange", x_bulk,
                          (x_bulk - 1, x_bulk + 1, -w - 1, w + 1, -v["flange_depth"] - 1, z_tan),
                          90.0, x_tan - ba - z_tan,
                          (x_tan - ba, x_tan, -w / 2, w / 2))],
                "ba": ba}

    raise ValueError(f"{variant} is not a folded variant")


def develop(variant: str, params: dict | None = None) -> tuple[cq.Workplane, list[str]]:
    """The flat blank for one folded variant plus a note per leg."""
    p = params or model.load_params()
    plan = fold_plan(variant, p)
    solid = model.BUILDERS[variant](p)

    pieces: list[cq.Workplane] = []
    legs: list[str] = []
    holes = 0

    axis, plane, box = plan["root"]
    root = leg_face(solid, axis, plane, box)
    holes += len(root.innerWires())
    pieces.append(_slab(root))
    bb = root.BoundingBox()
    legs.append(f"{plan['root_name']:<16} u {bb.xmin:7.1f}..{bb.xmax:7.1f}   "
                f"v {bb.ymin:7.1f}..{bb.ymax:7.1f}")

    for name, plane_x, box, rot, shift, strip in plan["legs"]:
        face = leg_face(solid, "X", plane_x, box)
        holes += len(face.innerWires())
        laid = face.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), rot)
        laid = laid.translate(cq.Vector(shift, 0, 0))
        pieces.append(_slab(laid))
        pieces.append(_strip(*strip))
        bb = laid.BoundingBox()
        legs.append(f"{name:<16} u {bb.xmin:7.1f}..{bb.xmax:7.1f}   "
                    f"v {bb.ymin:7.1f}..{bb.ymax:7.1f}")

    blank = pieces[0]
    for piece in pieces[1:]:
        blank = blank.union(piece)
    if len(blank.val().Solids()) != 1:
        raise RuntimeError(
            f"{variant}: the blank came out as {len(blank.val().Solids())} disconnected "
            "solids - a leg or a bend strip is not reaching its neighbour")
    got = len(blank.faces("<Z").val().innerWires())
    if got != holes:
        raise RuntimeError(
            f"{variant}: the legs carry {holes} holes but the blank shows {got}. Fewer "
            "means a hole reached a leg's outline and became a bite out of it; more "
            "means a feature ran off a leg into its bend tangent, which the blank then "
            "closes up again and a press brake cannot form across.")
    return blank, legs


# ---------------------------------------------------------------------------
# Bend table
# ---------------------------------------------------------------------------
def bend_table(variant: str, params: dict | None = None) -> list[dict]:
    """Every bend in a folded variant: line, direction, radius and the developed maths."""
    p = params or model.load_params()
    d = p["dimensions"]
    t, ri, k = d["sheet_t"], d["bend_radius_inside"], d["k_factor"]
    ba = bend_allowance(90.0, ri, t, k)
    bd = bend_deduction(90.0, ri, t, k)
    common = {"angle_deg": 90, "inside_radius_mm": ri, "material_t_mm": t, "k_factor": k,
              "bend_allowance_mm": round(ba, 3), "bend_deduction_mm": round(bd, 3)}
    rows = []
    if variant in model.METAL_VARIANTS:
        s = model.channel_stations(p)
        for i, (side, w) in enumerate(model.walls_for(p, variant).items(), 1):
            sg = 1 if side == "+X" else -1
            what = {"bulkhead_shelf": {"-X": "shelf -> bulkhead flange", "+X": "shelf -> far web"},
                    "deck_tray": {"-X": "pan -> -X wall", "+X": "pan -> +X wall"}}[variant][side]
            u0, u1 = sg * s["x_tan"], sg * (s["x_tan"] + ba)
            rows.append({**common, "bend": f"B{i} {what}",
                         "line_part_frame": f"X = {u0:+.1f} (pan tangent); "
                                            f"blank u = {u0:+.1f}..{u1:+.2f}",
                         "leg_length_mm": w["h"],
                         "runs": f"Y {w['y'][0]:.1f}..{w['y'][1]:.1f}",
                         "direction": "up (+Z), wall outboard of the pan",
                         "note": ("full length, no slits" if abs(w["y"][0] - d["pan_y"][0]) < 1e-6
                                  else f"{d['bend_relief_w']} mm relief slits at both ends")})
    elif variant == "side_tab":
        s = model.tab_stations(p)
        v = p["variants"]["side_tab"]
        u1 = s["foot_tan"]
        rows.append({**common, "bend": "B1 foot -> leg",
                     "line_part_frame": f"X = {u1:+.1f} (foot tangent); "
                                        f"blank u = {u1 - ba:+.2f}..{u1:+.1f}",
                     "leg_length_mm": v["leg_h"],
                     "runs": f"full width, {v['width']} mm",
                     "direction": "leg up (+Z), foot OUTWARD from the unit",
                     "note": "the leg's unit-facing face is the convex skin; its flat starts "
                             f"at Z = {s['leg_tan']}"})
    elif variant == "bulkhead_strap":
        s = model.channel_stations(p)
        v = p["variants"]["bulkhead_strap"]
        rows.append({**common, "bend": "B1 shelf -> flange",
                     "line_part_frame": f"X = {-s['x_tan']:+.1f} (shelf tangent); "
                                        f"blank u = {-s['x_tan'] - ba:+.2f}..{-s['x_tan']:+.1f}",
                     "leg_length_mm": v["flange_depth"],
                     "runs": f"full width, {v['width']} mm",
                     "direction": "flange DOWN (-Z), on the bulkhead",
                     "note": "the shelf top and the flange's bulkhead face are the convex skin"})
    return rows


# ---------------------------------------------------------------------------
# Fastener schedule
# ---------------------------------------------------------------------------
def _row(kit, id_, into, at, thread, screw, under, grip, eng, limit, torque, optional, note):
    return {"kit": kit, "id": id_, "into": into, "at_xyz": at, "thread": thread,
            "screw": screw, "under_head": under, "grip_mm": grip, "engagement_mm": eng,
            "max_penetration_mm": limit, "torque_nm": torque, "optional": optional, "note": note}


def fastener_schedule(params: dict | None = None) -> list[dict]:
    """Every screw in every kit, with the engagement arithmetic spelled out."""
    p = params or model.load_params()
    f = p["fasteners"]
    rows: list[dict] = []
    hw = iface.HALF_W

    def station(y: float) -> str:
        return "terminal_end" if y > -100 else "fan_end"

    # --- v2 tab kits -------------------------------------------------------
    tab = p["variants"]["side_tab"]
    for kit in ("deck_tab_kit", "bulkhead_strap_kit"):
        for y, z in iface.SIDE_M4_YZ:
            for side in tab["sides"][kit]:
                sg = 1 if side == "+X" else -1
                rows.append(_row(
                    kit, f"M4_tab_{side}_{station(y)}", "NSP-1600 side wall",
                    f"({sg * hw:+.1f}, {y:.1f}, {z:.1f})", iface.SIDE_M4_THREAD,
                    f["side_m4_tab"]["screw"], f"{f['side_m4_tab']['washer']} + 3.0 tab, flush",
                    f["side_m4_tab"]["grip"], f["side_m4_tab"]["engagement"],
                    iface.SIDE_M4_MAX_PENETRATION, f["side_m4_tab"]["torque_nm"], "no",
                    "threaded cross-tube, real in the vendor STEP" if y > -100 else
                    "NOT modelled in the vendor STEP (dia 5 clearance only) - verify on a unit"))
                host = "host deck" if kit == "deck_tab_kit" else "bulkhead_strap shelf (nut below)"
                rows.append(_row(
                    kit, f"M5_tab_foot_{side}_{station(y)}", host,
                    f"({sg * tab['slot_x']:+.1f}, {y:.1f}, 0)", f["tab_to_host"]["thread"],
                    f["tab_to_host"]["screw"], "washer on the tab's foot",
                    p["dimensions"]["sheet_t"], "", "", f["tab_to_host"]["torque_nm"], "no",
                    "slot +/-2.25 across the unit: tighten the M4 flush first, this second"))
    v = p["variants"]["bulkhead_strap"]
    for y in model.strap_stations(p):
        for z in v["bolt_z"]:
            rows.append(_row(
                "bulkhead_strap_kit", f"M5_strap_{station(y)}_Z{z:.0f}", "host bulkhead",
                f"(-48.5, {y:.1f}, {z:.1f})", f["strap_to_bulkhead"]["thread"],
                f["strap_to_bulkhead"]["screw"],
                "washer on the flange's inner face, below the shelf",
                p["dimensions"]["sheet_t"], "", "", f["strap_to_bulkhead"]["torque_nm"], "no",
                "reachable with the unit fitted"))
    box = p["variants"]["terminal_box"]
    for kit in ("deck_tab_kit", "bulkhead_strap_kit"):
        for i, (x, y) in enumerate(box["floor_screws_xy"], 1):
            on_strap = kit == "bulkhead_strap_kit"
            used = (not on_strap) or y < 20
            rows.append(_row(
                kit, f"M3_box_floor_{i}", "terminal strap (tapped)" if on_strap else "host deck",
                f"({x:+.1f}, {y:.1f}, 0)", f["box_m3"]["thread"], f["box_m3"]["screw"],
                "2.5 mm printed floor", 2.5, 3.0 if on_strap else "", "",
                0.5, "no" if used else "unused (beyond the strap)",
                "through-tapped: 3.0 mm of thread, tip 0.5 mm proud on the strap's free "
                "underside" if on_strap else "tap M3 in the deck, or clearance + nut"))
    for i, (hy, hz) in enumerate(box["ears"]["hole_yz"], 1):
        rows.append(_row(
            "bulkhead_strap_kit", f"M5_box_ear_{i}", "host bulkhead",
            f"(-48.5, {hy:.1f}, {hz:.1f})", f["box_ears"]["thread"], f["box_ears"]["screw"],
            "printed ear, head reached from +X", 6.5, "", "", 2.0, "no",
            "past the box's far wall"))

    # --- v1 channel kits ---------------------------------------------------
    for kit, variant, sides in (("bulkhead_shelf_kit", "bulkhead_shelf", ("+X",)),
                                ("deck_tray_kit", "deck_tray", ("-X", "+X"))):
        for side in sides:
            sg = 1 if side == "+X" else -1
            for y, z in iface.SIDE_M4_YZ:
                rows.append(_row(
                    kit, f"M4_side_{side}_{station(y)}", "NSP-1600 side wall",
                    f"({sg * hw:+.1f}, {y:.1f}, {z:.1f})", iface.SIDE_M4_THREAD,
                    f["side_m4"]["screw"], f"{f['side_m4']['washer']} + 3.0 wall + 3.0 spacer_ring",
                    f["side_m4"]["grip"], f["side_m4"]["engagement"], iface.SIDE_M4_MAX_PENETRATION,
                    f["side_m4"]["torque_nm"], "no",
                    "threaded cross-tube, real in the vendor STEP" if y > -100 else
                    "NOT modelled in the vendor STEP (dia 5 clearance only) - verify on a unit"))
        for i, (x, y) in enumerate(iface.BOTTOM_M3_XY, 1):
            rows.append(_row(
                kit, f"M3_bottom_{i}", "NSP-1600 bottom face", f"({x:+.1f}, {y:.1f}, 0)",
                iface.BOTTOM_M3_THREAD, f["bottom_m3"]["screw"], "countersunk, head fully sunk",
                f["bottom_m3"]["grip"], f["bottom_m3"]["engagement"],
                iface.BOTTOM_M3_MAX_PENETRATION, f["bottom_m3"]["torque_nm"],
                "yes" if variant == "deck_tray" else "no",
                "enters from below the pan; bench operation on the deck tray"))
        for i, (x, y) in enumerate(p["dimensions"]["hood_tap_xy"], 1):
            rows.append(_row(
                kit, f"M3_hood_{i}", f"{variant} pan (tapped)", f"({x:+.1f}, {y:.1f}, 0)",
                f["hood_m3"]["thread"], f["hood_m3"]["screw"], "3.0 mm printed foot", 3.0, 3.0, 3.0,
                0.5, "no", "tip flush with the pan underside"))
    dv = p["variants"]["deck_tray"]
    for i, (x, y) in enumerate(dv["host_holes"], 1):
        rows.append(_row(
            "deck_tray_kit", f"M5_deck_{i}", "host deck", f"({x:+.1f}, {y:.1f}, 0)",
            f["host_deck"]["thread"], f["host_deck"]["screw"], "countersunk flush in the pan",
            p["dimensions"]["sheet_t"], "", "", "", "no",
            "beyond the unit's ends - reachable with the unit fitted"))
    bv = p["variants"]["bulkhead_shelf"]
    for i, (y, z) in enumerate(bv["bulkhead_holes"] + bv["bulkhead_keyholes"], 1):
        key = i > len(bv["bulkhead_holes"])
        rows.append(_row(
            "bulkhead_shelf_kit", f"M5_bulkhead_{i}{'_keyhole' if key else ''}", "host bulkhead",
            f"(-48.5, {y:.1f}, {z:.1f})", f["host_bulkhead"]["thread"], f["host_bulkhead"]["screw"],
            "washer on the flange's inner face", p["dimensions"]["sheet_t"], "", "", "", "no",
            "keyhole - pre-fit, hang the bracket, then tighten" if key else
            "above the unit or beyond its ends; head clears the unit"))

    # --- the lugs, every kit -------------------------------------------------
    for blade, b in iface.BLADES.items():
        rows.append(_row(
            "all", f"M6_lug_{blade}_blade", f"{blade} DC blade, dia 6.5 hole",
            f"({b['x'][1]:.1f}, {b['hole_yz'][0]:.1f}, {b['hole_yz'][1]:.1f})", "M6",
            f["lug_bolts"]["spec"], "lug on the +X face", "", "", "",
            f["lug_bolts"]["torque_nm"], "no", f["lug_bolts"]["note"]))

    for row in rows:
        lim, eng = row["max_penetration_mm"], row["engagement_mm"]
        if lim != "" and eng != "" and eng > lim:
            raise ValueError(f"{row['id']} engages {eng} mm into a {lim} mm limit")
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    default_out = os.environ.get("EVAL_ATTEMPT_DIR") or str(PART_DIR / "exports")
    ap.add_argument("--out", default=default_out,
                    help="output directory (use a short path for SolidWorks)")
    ap.add_argument("--verbose", action="store_true", help="list every leg's station")
    args = ap.parse_args(argv)
    out = Path(args.out)
    (out / "plates").mkdir(parents=True, exist_ok=True)
    p = model.load_params()
    d = p["dimensions"]
    ba = bend_allowance(90.0, d["bend_radius_inside"], d["sheet_t"], d["k_factor"])
    print(f"  90 deg bend allowance {ba:.3f} mm   (Ri {d['bend_radius_inside']}, "
          f"t {d['sheet_t']}, K {d['k_factor']} - ASSUMED, confirm on a coupon)")
    failures = 0

    for variant in model.FOLDED_VARIANTS:
        try:
            blank, legs = develop(variant, p)
            face = blank.faces("<Z").val()
            path = out / "plates" / f"{variant}_flat.dxf"
            cq.exporters.export(cq.Workplane(obj=face), str(path), exportType="DXF")
            bb = face.BoundingBox()
            print(f"  ok {variant:<16} blank {bb.xlen:6.1f} x {bb.ylen:6.1f} mm, "
                  f"{len(face.innerWires())} holes -> {path.name}")
            if args.verbose:
                for leg in legs:
                    print(f"       {leg}")
        except Exception as e:
            failures += 1
            print(f"  !! {variant:<16} development failed: {e}")

    ring = model.create_spacer_ring(p)
    path = out / "plates" / "spacer_ring.dxf"
    cq.exporters.export(cq.Workplane(obj=ring.faces("<Z").val()), str(path), exportType="DXF")
    q = p["variants"]["spacer_ring"]["qty"]
    print(f"  ok {'spacer_ring':<16} dia {p['variants']['spacer_ring']['od']} / "
          f"{p['variants']['spacer_ring']['id']}, v1 only: {q['deck_tray']} per deck tray, "
          f"{q['bulkhead_shelf']} per bulkhead shelf -> {path.name}")

    rows = [dict(variant=v, **b) for v in model.FOLDED_VARIANTS for b in bend_table(v, p)]
    path = out / "bend_table.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  ok bend table       {len(rows)} bends -> {path.name}")

    fr = fastener_schedule(p)
    path = out / "fastener_schedule.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fr[0]))
        w.writeheader()
        w.writerows(fr)
    print(f"  ok fastener schedule {len(fr)} rows -> {path.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
