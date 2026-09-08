"""
Develop each folded mount into the flat blank a shop actually cuts.

A STEP of a bent part is not a shop pack. What gets ordered is a flat blank with
every hole in it, a bend table, and a fastener schedule. All three are built here
from the same solids `model.py` produces, so the blank cannot drift from the
part: each leg's outer face is lifted straight off the solid — holes, slots and
countersink mouths included — rotated into the blank plane and slid to its
developed station. The strips between them are the bend allowances.

Bend allowance uses the standard sheet formula

    BA = (pi/180) * angle * (Ri + K*t)

with Ri, t and K from params.json. At Ri = t = 3.0 and K = 0.42 a 90 degree bend
develops 6.692 mm against a 12.000 mm outside dimension — a bend deduction of
5.308 mm. **Confirm K against the shop's own test coupon before cutting a
batch.** It is the one number in this part that belongs to their tooling rather
than to this design, and if it is wrong every hole in every leg past the first
bend is wrong with it. The bend table is emitted alongside the blanks precisely
so a shop can re-develop from the folded STEP with their own constant instead.

    uv run python parts/custom/bedrock-v3000-mount/flat_patterns.py --out C:/work/bdrk

Units: mm.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent


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


def bend_allowance(angle_deg: float, ri: float, t: float, k: float) -> float:
    """Developed length of the bend region, tangent to tangent."""
    return math.radians(angle_deg) * (ri + k * t)


# ---------------------------------------------------------------------------
# Lifting a leg's outer face off the solid
# ---------------------------------------------------------------------------
_ROT = {
    # the leg's face normal -> (rotation axis, angle) that lays it into XY
    "Z": (None, 0.0),
    "Y": ((1, 0, 0), -90.0),
    "X": ((0, 1, 0), 90.0),
}


def leg_face(solid: cq.Workplane, axis: str, plane: float, box: tuple) -> cq.Face:
    """
    The outer face of one leg, taken from the built solid.

    `box` is (xmin, xmax, ymin, ymax, zmin, zmax) bounding that leg's FLAT region
    — tangent to tangent, excluding the bend arcs. Cutting the solid to that box
    and picking the largest face on `plane` gives the true blank outline for the
    leg with every hole already in it, which is the point: nothing about the
    blank is retyped from the model.
    """
    piece = solid.intersect(model._slab(*box))
    best, best_area = None, 0.0
    idx = "XYZ".index(axis)
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


def to_blank(face: cq.Face, axis: str, u_ref: float, v_ref: float,
             u_at: float, v_at: float, u_flip: bool = False,
             v_flip: bool = False, swap: float = 0.0) -> cq.Workplane:
    """
    Rotate a leg face into the XY blank plane and pin one of its points to
    (u_at, v_at).

    Laying a face down gives in-plane coordinates (u, v) = (X, Y) for a Z-normal
    leg, (X, Z) for a Y-normal leg and (Z, Y) for an X-normal leg. A leg that
    folds off an edge running the other way needs those two axes exchanged, which
    is what `swap` — a rotation about the blank normal, in degrees — is for.
    Flips put a leg on the far side of its fold line. `u_ref`/`v_ref` are the
    leg's own coordinates of the pinned point, always its bend tangent, read in
    the frame that exists after the swap and before the flips.
    """
    shp = face
    rot, ang = _ROT[axis]
    if rot is not None:
        shp = shp.rotate(cq.Vector(0, 0, 0), cq.Vector(*rot), ang)
    if swap:
        shp = shp.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), swap)
    wp = cq.Workplane(obj=shp)
    su, sv = (-1 if u_flip else 1), (-1 if v_flip else 1)
    if u_flip:
        wp = wp.mirror("YZ")
    if v_flip:
        wp = wp.mirror("XZ")
    bb = wp.val().BoundingBox()
    wp = wp.translate((0, 0, -bb.zmin))          # land it on Z = 0
    return wp.translate((u_at - su * u_ref, v_at - sv * v_ref, 0))


STRIP_OVERLAP = 0.05   # mm the bend strip reaches into each leg it joins


def _strip(u0: float, u1: float, v0: float, v1: float) -> cq.Workplane:
    """
    A bend-allowance strip, as a 1 mm slab in the blank plane.

    Grown by STRIP_OVERLAP along the fold direction only (the short axis, the one
    whose length is the bend allowance). Legs and strips that merely touch fuse
    into a compound rather than one solid, and a compound is not a blank; growing
    across the fold instead would put a 0.05 mm tab on the outline.
    """
    u0, u1 = sorted((u0, u1))
    v0, v1 = sorted((v0, v1))
    if (u1 - u0) < (v1 - v0):
        u0, u1 = u0 - STRIP_OVERLAP, u1 + STRIP_OVERLAP
    else:
        v0, v1 = v0 - STRIP_OVERLAP, v1 + STRIP_OVERLAP
    return (cq.Workplane("XY").box(u1 - u0, v1 - v0, 1.0, centered=False)
            .translate((u0, v0, 0.0)))


def _blank(pieces: list[cq.Workplane], cuts: list[tuple] | None = None) -> cq.Workplane:
    """
    Fuse the laid-down faces and the bend strips into one blank slab.

    `cuts` are (u0, u1, v0, v1) regions to remove afterwards — used where a leg's
    face had to be lifted past a bend tangent because its own outline is not a
    rectangle, so the arc projection has to come off again.
    """
    slabs = []
    for w in pieces:
        if w.val().Solids():
            slabs.append(w)
        else:
            slabs.append(cq.Workplane(obj=w.val()).wires().toPending().extrude(1.0))
    out = slabs[0]
    for s in slabs[1:]:
        out = out.union(s)
    for u0, u1, v0, v1 in (cuts or ()):
        u0, u1 = sorted((u0, u1))
        v0, v1 = sorted((v0, v1))
        out = out.cut(cq.Workplane("XY").box(u1 - u0, v1 - v0, 3.0, centered=False)
                      .translate((u0, v0, -1.0)))
    if len(out.val().Solids()) != 1:
        raise RuntimeError(
            f"the blank came out as {len(out.val().Solids())} disconnected solids — "
            "a leg or a bend strip is not reaching its neighbour")
    return out


# ---------------------------------------------------------------------------
# Per-variant fold chains
# ---------------------------------------------------------------------------
def develop(variant: str, params: dict | None = None) -> tuple[cq.Workplane, list[str]]:
    """
    The flat blank for one folded variant, plus a description of each leg's
    place in it.

    The root leg lands in the blank plane unmoved; every other leg is pinned by
    its own bend tangent to the developed station of the leg it folds off, with a
    bend-allowance strip bridging the gap.
    """
    p = params or model.load_params()
    d = p["dimensions"]
    t, ri, k = d["sheet_t"], d["bend_radius_inside"], d["k_factor"]
    ba = bend_allowance(90.0, ri, t, k)
    tan = ri + t                      # tangent inset from a bend's outer corner
    solid = model.BUILDERS[variant](p)
    v = p["variants"][variant]
    pieces: list[cq.Workplane] = []
    cuts: list[tuple] = []
    legs: list[str] = []

    holes = [0]

    def add(name, axis, plane, box, u_ref, v_ref, u_at, v_at,
            u_flip=False, v_flip=False, swap=0.0, subtract=()):
        """
        Lift one leg's face, lay it flat and pin it. `subtract` trims blank-plane
        regions off THIS leg before it is unioned — needed where a leg's outline
        is not a rectangle, so its box had to run past a bend tangent and picked
        up the arc projection that the bend strip already accounts for.
        """
        face = leg_face(solid, axis, plane, box)
        holes[0] += len(face.Wires()) - 1
        piece = to_blank(face, axis, u_ref, v_ref, u_at, v_at, u_flip, v_flip, swap)
        if subtract:
            piece = cq.Workplane(obj=piece.val()).wires().toPending().extrude(1.0)
            for su0, su1, sv0, sv1 in subtract:
                su0, su1 = sorted((su0, su1))
                sv0, sv1 = sorted((sv0, sv1))
                piece = piece.cut(
                    cq.Workplane("XY").box(su1 - su0, sv1 - sv0, 3.0, centered=False)
                    .translate((su0, sv0, -1.0)))
        pieces.append(piece)
        bb = pieces[-1].val().BoundingBox()
        legs.append(f"{name:<22} u {bb.xmin:7.1f}..{bb.xmax:7.1f}   "
                    f"v {bb.ymin:7.1f}..{bb.ymax:7.1f}")

    # Every leg's box is clipped at ITS OWN bend tangents. A box that runs past a
    # tangent lifts the bend arc's projection as well as the flat, and that region
    # then gets counted twice — once in the leg, once in the bend-allowance strip
    # — silently lengthening the blank by (Ri + t) per bend.
    if variant == "upright_deck":
        ear, pan_x = v["rear_ear_x"], v["pan_x"]
        y_free, y_tan = v["pan_y_front"], v["pan_y_rear"] + t - tan   # 62.0
        x_tan = pan_x + t - tan                                       # 35.5
        z_lo, z_hi = ri, v["spine_z_top"] - tan                       # 3.0, 130.0
        fl_lo = v["pan_y_rear"] + t + ri                              # 71.0
        fl_hi = fl_lo + v["spine_return_flange"]
        wy0, wy1 = v["wall_y"]

        # root: the pan, on its underside, in true position. (u, v) = (X, Y).
        # Two boxes: the shock walls fold off the main span so it stops at their
        # tangent, but the rear ears are past the walls and stay full width.
        # The pan is not a rectangle — its rear ears run out past the shock walls —
        # so it is lifted whole and the two wall-arc projections are trimmed off it
        # before anything else joins the blank.
        add("pan", "Z", -t, (-ear - 1, ear + 1, y_free - 1, y_tan, -t - 1, -t + 1),
            0.0, 0.0, 0.0, 0.0,
            subtract=[(x_tan, ear + 2, y_free - 2, wy1 + 1.0),
                      (-x_tan, -ear - 2, y_free - 2, wy1 + 1.0)])
        # spine, folded up off the pan's rear tangent
        pieces.append(_strip(-ear, ear, y_tan, y_tan + ba))
        add("spine", "Y", v["pan_y_rear"] + t,
            (-ear - 1, ear + 1, v["pan_y_rear"] + t - 1, v["pan_y_rear"] + t + 1,
             z_lo, z_hi),
            0.0, z_lo, 0.0, y_tan + ba)
        v_end = y_tan + ba + (z_hi - z_lo)
        # top return flange, folded back off the spine's top tangent
        pieces.append(_strip(-ear, ear, v_end, v_end + ba))
        add("top return flange", "Z", v["spine_z_top"],
            (-ear - 1, ear + 1, fl_lo, fl_hi + 1,
             v["spine_z_top"] - 1, v["spine_z_top"] + 1),
            0.0, fl_lo, 0.0, v_end + ba)
        # shock walls, folded sideways off the pan's own edges. An X-normal leg
        # lays down as (Z, Y) and the pan's frame is (X, Y), so the wall's fold
        # direction is already u — no swap, just a flip for the -X side.
        for sign in (1, -1):
            u_tan = sign * x_tan
            pieces.append(_strip(u_tan, u_tan + sign * ba, wy0, wy1))
            add(f"shock wall {'+X' if sign > 0 else '-X'}", "X", sign * (pan_x + t),
                (sign * (pan_x + t) - 1, sign * (pan_x + t) + 1, wy0 - 1, wy1 + 1,
                 ri, v["wall_h"]),
                ri, 0.0, u_tan + sign * ba, 0.0, u_flip=(sign < 0))

    elif variant == "low_profile_side":
        x_base, ex = v["base_x"], v["end_wall_x"]
        by0 = v["base_y"][0]
        bz1 = v["base_z"][1]
        ey0, ey1 = v["end_wall_y"]
        bwz0, bwz1 = v["back_wall_z"]
        x_tan = x_base + ri                              # -43.0, both bends
        y_tan = iface.BACKWALL_Y + t - tan               # 62.0

        # root: the base, on its outside face. An X-normal leg lays down as
        # (u, v) = (Z, Y), so the blank runs along the unit's long axis.
        add("base", "X", x_base - t,
            (x_base - t - 1, x_base - t + 1, by0 - 1, y_tan, ri, bz1 + 1),
            0.0, 0.0, 0.0, 0.0)
        # end wall, folded up off the base's Z = ri edge. Z-normal leg -> (X, Y);
        # the fold runs along X and the blank's u is Z, so no swap, just a flip.
        pieces.append(_strip(ri - ba, ri, ey0, ey1))
        add("end wall", "Z", -t,
            (x_tan, ex + 1, ey0 - 1, ey1 + 1, -t - 1, -t + 1),
            x_tan, 0.0, ri - ba, 0.0, u_flip=True)
        # back wall, folded up off the base's Y = y_tan edge. A Y-normal leg lays
        # down as (X, Z), but here the fold runs along X while the cross axis is
        # Z — so swap the two, then flip.
        pieces.append(_strip(bwz0, bwz1, y_tan, y_tan + ba))
        add("back wall", "Y", iface.BACKWALL_Y + t,
            (x_tan, v["back_wall_x"] + 1, iface.BACKWALL_Y + t - 1,
             iface.BACKWALL_Y + t + 1, bwz0, bwz1),
            0.0, -x_tan, 0.0, y_tan + ba, v_flip=True, swap=-90.0)

    elif variant == "upright_bulkhead":
        web_x, fl = v["web_x"], v["return_flange_w"]
        y_wall = iface.BACKWALL_Y
        y_bulk = y_wall + t + v["side_flange_depth"]
        y_lip = v["shelf_y_front"]
        lip_tan = y_lip + t + ri                          # -16.0
        y_tan = y_wall + t - tan                          # 62.0
        z_lo, z_hi = ri, v["web_z"][1] - tan              # 3.0, 137.0
        tf_lo = y_wall + t + ri                           # 71.0
        x_tan = web_x - tan                               # 39.0
        sf0, sf1 = y_wall + tan, y_bulk - tan             # 71.0, 92.0 side-flange flat
        rf0 = (web_x - t) + tan                           # 48.0 return-flange tangent
        fz0, fz1 = v["side_flange_z"]

        # root: the shelf, on its underside. (u, v) = (X, Y).
        add("shelf", "Z", -t,
            (-web_x - 1, web_x + 1, lip_tan, y_tan, -t - 1, -t + 1), 0.0, 0.0, 0.0, 0.0)
        # front lip, folded down off the shelf's front tangent
        pieces.append(_strip(-web_x, web_x, lip_tan - ba, lip_tan))
        add("front lip", "Y", y_lip,
            (-web_x - 1, web_x + 1, y_lip - 1, y_lip + 1,
             -v["shelf_lip_h"] - 1, -tan), 0.0, -tan, 0.0, lip_tan - ba, v_flip=True)
        # web, folded up off the shelf's rear tangent. Clipped at the side-flange
        # tangents in X as well as at its own bends in Z.
        pieces.append(_strip(-web_x, web_x, y_tan, y_tan + ba))
        add("web", "Y", y_wall + t,
            (-x_tan, x_tan, y_wall + t - 1, y_wall + t + 1, z_lo, z_hi),
            0.0, z_lo, 0.0, y_tan + ba)
        v_web0 = y_tan + ba
        v_web1 = v_web0 + (z_hi - z_lo)
        # top return flange off the web's top tangent
        pieces.append(_strip(-web_x, web_x, v_web1, v_web1 + ba))
        add("top return flange", "Z", v["web_z"][1],
            (-web_x - 1, web_x + 1, tf_lo, tf_lo + v["top_flange_w"] + 1,
             v["web_z"][1] - 1, v["web_z"][1] + 1),
            0.0, tf_lo, 0.0, v_web1 + ba)
        # side flanges fold off the web's X edges, inside the web's own v band.
        # X-normal legs lay down as (Z, Y); here the fold runs along Y and the
        # cross axis is Z, so swap them.
        for sign in (1, -1):
            u_tan = sign * x_tan
            v0, v1 = v_web0 + (fz0 - z_lo), v_web0 + (fz1 - z_lo)
            pieces.append(_strip(u_tan, u_tan + sign * ba, v0, v1))
            add(f"side flange {'+X' if sign > 0 else '-X'}", "X", sign * web_x,
                (sign * web_x - 1, sign * web_x + 1, sf0, sf1, fz0, fz1),
                -sf0, fz0, u_tan + sign * ba, v0, u_flip=(sign > 0), swap=90.0)
            # return flange folds off the side flange's bulkhead edge. A Y-normal
            # leg lays down as (X, Z) — u already runs along X, so no swap.
            u_end = u_tan + sign * (ba + (sf1 - sf0))
            pieces.append(_strip(u_end, u_end + sign * ba, v0, v1))
            lo = rf0 - 1 if sign > 0 else -(rf0 + fl + 2)
            hi = rf0 + fl + 2 if sign > 0 else -(rf0 - 1)
            add(f"return flange {'+X' if sign > 0 else '-X'}", "Y", y_bulk,
                (lo, hi, y_bulk - 1, y_bulk + 1, fz0, fz1),
                sign * rf0, fz0, u_end + sign * ba, v0)

    else:
        raise ValueError(f"{variant} is flat already — export its face directly")

    blank = _blank(pieces, cuts)
    got = len(blank.faces("<Z").val().Wires()) - 1
    if got != holes[0]:
        raise RuntimeError(
            f"{variant}: the legs carry {holes[0]} holes but the blank shows {got}. "
            "Fewer in the blank means a hole reached a leg's outline and became a bite "
            "out of it; more means a slot or window ran off a leg into its bend tangent, "
            "which the blank then closes up again and a press brake cannot form across. "
            "Either way, move the feature inboard of the tangent.")
    return blank, legs


# ---------------------------------------------------------------------------
# Bend table
# ---------------------------------------------------------------------------
def bend_table(variant: str, params: dict | None = None) -> list[dict]:
    """Every bend in a variant: line, direction, radius and the developed maths."""
    p = params or model.load_params()
    d = p["dimensions"]
    t, ri, k = d["sheet_t"], d["bend_radius_inside"], d["k_factor"]
    ba = bend_allowance(90.0, ri, t, k)
    bd = 2 * (ri + t) - ba
    v = p["variants"].get(variant, {})
    common = {"angle_deg": 90, "inside_radius_mm": ri, "material_t_mm": t,
              "k_factor": k, "bend_allowance_mm": round(ba, 3),
              "bend_deduction_mm": round(bd, 3)}

    if variant == "upright_deck":
        return [
            {**common, "bend": "B1 pan -> spine", "line": "Y = 65.0 (part frame)",
             "direction": "up (+Z)",
             "note": "the relief notch removes |X| <= 30 at this line, so only the "
                     "two rear ears fold here"},
            {**common, "bend": "B2 spine -> top return flange",
             "line": f"Z = {v['spine_z_top']}", "direction": "back (+Y), reverse of B1",
             "note": "stiffens the spine top and removes the raw edge"},
            {**common, "bend": "B3 pan -> +X shock wall", "line": f"X = +{v['pan_x']}",
             "direction": "up (+Z)",
             "note": f"{v['wall_h']} mm flange, 2.0 mm clear of the fin tips"},
            {**common, "bend": "B4 pan -> -X shock wall", "line": f"X = -{v['pan_x']}",
             "direction": "up (+Z)", "note": "mirror of B3"},
        ]
    if variant == "upright_bulkhead":
        return [
            {**common, "bend": "B1 shelf -> web", "line": "Y = 65.0",
             "direction": "up (+Z)", "note": "relief notch at |X| <= 30"},
            {**common, "bend": "B2 shelf -> front lip",
             "line": f"Y = {v['shelf_y_front']}", "direction": "down (-Z)",
             "note": "closes the shelf into a channel; doubles as the drip edge"},
            {**common, "bend": "B3 web -> top return flange",
             "line": f"Z = {v['web_z'][1]}", "direction": "back (+Y)"},
            {**common, "bend": "B4/B5 web -> side flanges",
             "line": f"X = +/-{v['web_x']}", "direction": "back (+Y)",
             "note": f"sets the {v['side_flange_depth']} mm bulkhead standoff"},
            {**common, "bend": "B6/B7 side flange -> bulkhead return flange",
             "line": "Y = 98.0", "direction": "outboard (+/-X)",
             "note": "the convex corner of this bend is on the flange's INBOARD "
                     "face (|X| = 42), not its outboard face"},
        ]
    if variant == "low_profile_side":
        return [
            {**common, "bend": "B1 base -> end wall", "line": "Z = 0.0",
             "direction": "up (+X)",
             "note": "bears on the -Z end cap; carries the optional M4"},
            {**common, "bend": "B2 base -> back wall", "line": "Y = 65.0",
             "direction": "up (+X)",
             "note": "bears on the +Y land; carries the 2x M3. Corner relief "
                     "between B1 and B2."},
        ]
    return []


# ---------------------------------------------------------------------------
# Fastener / hole schedule
# ---------------------------------------------------------------------------
def fastener_schedule(params: dict | None = None) -> list[dict]:
    """Every screw in the family, with the engagement arithmetic spelled out."""
    p = params or model.load_params()
    f = p["fasteners"]
    general = "upright_deck / upright_bulkhead / low_profile_side"
    rows = []
    for z in iface.BACKWALL_M3_Z:
        rows.append({
            "variant": general, "id": f"M3_backwall_Z{z:.0f}",
            "into": "Bedrock +Y back wall", "at_xyz": f"(0, 65, {z:.0f})",
            "thread": iface.BACKWALL_M3_THREAD, "screw": f["backwall_m3"]["screw"],
            "bracket_grip_mm": f["backwall_m3"]["grip"],
            "engagement_mm": f["backwall_m3"]["engagement"],
            "max_penetration_mm": iface.BACKWALL_M3_MAX_PENETRATION,
            "torque_nm": f["backwall_m3"]["torque_nm"], "optional": "no",
            "note": "the 0.5 mm spotface sets the grip; M3x6 here bottoms out and "
                    "jacks the bracket off the land",
        })
    rows.append({
        "variant": general, "id": "M4_bottom", "into": "Bedrock -Z end cap",
        "at_xyz": f"({iface.BOTTOM_M4_XY[0]:g}, {iface.BOTTOM_M4_XY[1]:g}, 0)",
        "thread": iface.BOTTOM_M4_THREAD, "screw": f["bottom_m4"]["screw"],
        "bracket_grip_mm": f["bottom_m4"]["grip"],
        "engagement_mm": f["bottom_m4"]["engagement"],
        "max_penetration_mm": iface.BOTTOM_M4_MAX_PENETRATION,
        "torque_nm": f["bottom_m4"]["torque_nm"], "optional": "YES",
        "note": "probably a vendor bottom-cover screw - confirm with SolidRun. "
                "Every mount stands up without it.",
    })
    for i, (y, z) in enumerate(iface.TILE_M4_YZ, 1):
        rows.append({
            "variant": "tile_side_plate", "id": f"TILE_M4_{i}",
            "into": "Bedrock Tile -X side flat", "at_xyz": f"(-14.5, {y:g}, {z:g})",
            "thread": "M4x0.7", "screw": f["tile_m4"]["screw"],
            "bracket_grip_mm": f["tile_m4"]["grip"],
            "engagement_mm": f["tile_m4"]["engagement"],
            "max_penetration_mm": iface.TILE_M4_MAX_PENETRATION,
            "torque_nm": f["tile_m4"]["torque_nm"], "optional": "no",
            "note": "Tile chassis only - this pattern does not exist on 30 W or 60 W",
        })
    hm4 = f["hybrid_m4"]
    for i, (y, z) in enumerate(iface.TILE_M4_YZ, 1):
        rows.append({
            "variant": "hybrid_cold_plate", "id": f"HYB_M4_{i}",
            "into": "Bedrock hybrid flat side (Tile core)",
            "at_xyz": f"({iface.flat_side_x('hybrid_posx'):g}, {y:g}, {z:g})",
            "thread": "M4x0.7", "screw": hm4["screw"],
            "bracket_grip_mm": hm4["grip"], "engagement_mm": hm4["engagement"],
            "max_penetration_mm": iface.TILE_M4_MAX_PENETRATION,
            "torque_nm": hm4["torque_nm"], "optional": "no",
            "note": "the core's bores are tapped from both ends - a fin-bank screw "
                    "on the other side uses the same bore and never meets this one",
        })
    bolt = f["hybrid_border"]
    for i, (hy, hz) in enumerate(
            sorted(p["variants"]["hybrid_cold_plate"]["border_holes"],
                   key=lambda h: (h[1], h[0])), 1):
        rows.append({
            "variant": "hybrid_cold_plate", "id": f"BORDER_M6_{i}",
            "into": "host plate", "at_xyz": f"(border, Y {hy:g}, Z {hz:g})",
            "thread": bolt["thread"], "screw": bolt["screw"],
            "bracket_grip_mm": p["variants"]["hybrid_cold_plate"]["plate_t"],
            "engagement_mm": "", "max_penetration_mm": "", "torque_nm": "",
            "optional": "no",
            "note": "through the border, head on the UNIT side - the bolts you can "
                    "still reach once the Bedrock is on the plate",
        })
    for name in ("upright_deck", "upright_bulkhead", "low_profile_side"):
        for i, hole in enumerate(p["variants"][name]["host_holes"], 1):
            rows.append({
                "variant": name, "id": f"HOST_{i}", "into": "host deck / bulkhead",
                "at_xyz": str(tuple(hole)), "thread": f["host"]["thread"],
                "screw": f["host"]["screw"],
                "bracket_grip_mm": p["dimensions"]["sheet_t"], "engagement_mm": "",
                "max_penetration_mm": "", "torque_nm": "", "optional": "no",
                "note": "countersunk flush so the head may sit under the chassis "
                        "footprint",
            })
    return rows


def machining_ops(params: dict | None = None) -> list[dict]:
    """
    Every feature a flat pattern cannot carry: spotfaces, countersinks, tapped
    holes. A DXF is the laser file — it shows an outline and through holes. Ship
    only that and the countersinks never get cut, the spotfaces never get cut,
    and the first bracket built jacks itself off the chassis because its M3 grip
    is 3.0 mm instead of 2.5.
    """
    p = params or model.load_params()
    f = p["fasteners"]
    t = p["dimensions"]["sheet_t"]
    rows = []

    for name in ("upright_deck", "upright_bulkhead", "low_profile_side"):
        m3 = f["backwall_m3"]
        for z in iface.BACKWALL_M3_Z:
            rows.append({
                "variant": name, "op": "spotface", "face": "back-wall plate, OUTER face",
                "at": f"(X 0, Z {z:g}) on the +Y web", "tool_d": m3["spotface_d"],
                "depth": round(t - m3["grip"], 2), "thread": "",
                "why": (f"sets the grip to {m3['grip']} mm so an {m3['screw'].split()[0]} "
                        "engages 2.5 mm and stops short of the 3.000 mm hole bottom"),
            })
        m4 = f["bottom_m4"]
        rows.append({
            "variant": name, "op": "countersink 90deg", "face": "underside of the -Z pad",
            "at": f"({iface.BOTTOM_M4_XY[0]:g}, {iface.BOTTOM_M4_XY[1]:g})",
            "tool_d": m4["csk_d"], "depth": round((m4["csk_d"] - m4["clearance_d"]) / 2, 2),
            "thread": "", "why": "head must finish flush - it sits against the host",
        })
        host = f["host"]
        for i, (hx, hy) in enumerate(p["variants"][name]["host_holes"], 1):
            rows.append({
                "variant": name, "op": "countersink 90deg", "face": "host-side face",
                "at": f"HOST_{i} ({hx:g}, {hy:g})", "tool_d": host["csk_d"],
                "depth": round((host["csk_d"] - host["clearance_d"]) / 2, 2), "thread": "",
                "why": "flush so the head may sit under the chassis footprint",
            })

    v = p["variants"]["hybrid_cold_plate"]
    hm4, hh = f["hybrid_m4"], f["hybrid_host"]
    for i, (hy, hz) in enumerate(iface.TILE_M4_YZ, 1):
        rows.append({
            "variant": "hybrid_cold_plate", "op": "countersink 90deg",
            "face": "OUTER face (host side)", "at": f"M4_{i} (Y {hy:g}, Z {hz:g})",
            "tool_d": hm4["csk_d"],
            "depth": round((hm4["csk_d"] - hm4["clearance_d"]) / 2, 2), "thread": "",
            "why": "flush - this face is the one that beds against the host",
        })
    zc = v["vesa_centre_z"]
    for pitch in v["vesa_pattern"]:
        for sy in (-1, 1):
            for sz in (-1, 1):
                rows.append({
                    "variant": "hybrid_cold_plate", "op": "drill + tap BLIND",
                    "face": "OUTER face (host side)",
                    "at": f"VESA{pitch:g} (Y {sy * pitch / 2:g}, Z {zc + sz * pitch / 2:g})",
                    "tool_d": hh["m4_tap_drill"], "depth": hh["tap_drill_depth"],
                    "thread": f"M4x0.7, {hh['min_thread_depth']} mm min full thread",
                    "why": "must NOT break through - a long host screw would jack the "
                           "plate off the chassis",
                })
    return rows


def host_drilling(params: dict | None = None) -> list[dict]:
    """
    The pattern to put in the plate the cold plate bolts TO.

    Six M6 clearance or tapped holes on a 148 x 180 rectangle, in the cold
    plate's own frame (Y across, Z up the unit's long axis), origin on the
    chassis centreline. Every one of them sits outboard of the chassis flat, so
    the bolt is reachable with the Bedrock already fitted — which is the whole
    reason the border exists.
    """
    p = params or model.load_params()
    v = p["variants"]["hybrid_cold_plate"]
    bolt = p["fasteners"]["hybrid_border"]
    ys = sorted({hy for hy, _ in v["border_holes"]})
    zs = sorted({hz for _, hz in v["border_holes"]})
    rows = []
    for i, (hy, hz) in enumerate(sorted(v["border_holes"], key=lambda h: (h[1], h[0])), 1):
        rows.append({
            "id": f"HOST_{i}", "y_mm": hy, "z_mm": hz,
            "clearance_d_mm": bolt["clearance_d"],
            "or_tapped": bolt["thread"],
            "pattern": f"{ys[-1] - ys[0]:g} x {zs[-1] - zs[0]:g} mm, "
                       f"{len(ys)} columns x {len(zs)} rows",
            "note": "outboard of the chassis flat (|Y| <= 64.49) - reachable with "
                    "the unit fitted",
        })
    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", default=str(PART_DIR / "exports"),
                    help="output directory (use a short path for SolidWorks)")
    ap.add_argument("--verbose", action="store_true", help="list every leg's station")
    args = ap.parse_args(argv)
    out = Path(args.out)
    (out / "plates").mkdir(parents=True, exist_ok=True)
    p = model.load_params()
    d = p["dimensions"]
    ba = bend_allowance(90.0, d["bend_radius_inside"], d["sheet_t"], d["k_factor"])
    print(f"  90 deg bend allowance {ba:.3f} mm   "
          f"(Ri {d['bend_radius_inside']}, t {d['sheet_t']}, K {d['k_factor']})")
    failures = 0

    for variant in model.VARIANT_NAMES:
        if variant in model.FLAT_VARIANTS:
            solid = model.BUILDERS[variant](p)
            face = max((f for f in solid.val().Faces()
                        if abs(abs(f.normalAt().x) - 1) < 1e-3), key=lambda f: f.Area())
            flat = face.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 90)
            path = out / "plates" / f"{variant}.dxf"
            # the biggest X-normal face is the bearing face, which carries the
            # outline and the through holes and nothing else — i.e. exactly the
            # laser file. Countersinks and tapped holes are secondary ops and
            # live in machining_ops.csv, not here.
            cq.exporters.export(cq.Workplane(obj=flat), str(path), exportType="DXF")
            bb = flat.BoundingBox()
            print(f"  ok {variant:<18} flat plate {bb.xlen:6.1f} x {bb.ylen:6.1f} mm, "
                  f"{len(flat.Wires()) - 1} holes -> {path.name}")
            continue
        try:
            blank, legs = develop(variant, p)
            face = blank.faces("<Z").val()
            path = out / "plates" / f"{variant}_flat.dxf"
            cq.exporters.export(cq.Workplane(obj=face), str(path), exportType="DXF")
            bb = face.BoundingBox()
            print(f"  ok {variant:<18} blank {bb.xlen:6.1f} x {bb.ylen:6.1f} mm, "
                  f"{len(face.Wires()) - 1} holes -> {path.name}")
            if args.verbose:
                for leg in legs:
                    print(f"       {leg}")
        except Exception as e:
            failures += 1
            print(f"  !! {variant:<18} development failed: {e}")

    rows = [dict(variant=v, **b) for v in model.VARIANT_NAMES for b in bend_table(v, p)]
    path = out / "bend_table.csv"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"  ok bend table          {len(rows)} bends -> {path.name}")

    ops = machining_ops(p)
    path = out / "machining_ops.csv"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ops[0]))
        w.writeheader()
        w.writerows(ops)
    print(f"  ok secondary ops       {len(ops)} features -> {path.name}")

    hd = host_drilling(p)
    path = out / "host_drilling.csv"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(hd[0]))
        w.writeheader()
        w.writerows(hd)
    print(f"  ok host drilling       {len(hd)} holes -> {path.name}")

    fr = fastener_schedule(p)
    path = out / "fastener_schedule.csv"
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fr[0]))
        w.writeheader()
        w.writerows(fr)
    print(f"  ok fastener schedule   {len(fr)} screws -> {path.name}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
