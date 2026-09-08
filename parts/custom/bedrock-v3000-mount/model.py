"""
SolidRun Bedrock V3000 mount family
===================================

Five mounts across two interfaces.

On the 30 W and 60 W chassis the entire external fixing set is two M3x0.5 blind
tappings 3.000 mm deep on a 20 mm wide back-wall land, plus one M4x0.7 on the
bottom end cap whose twin is already occupied. Everything else is fin bank, I/O
panel or antenna. Three of the mounts work those two faces and differ only in
which way the unit points and what it bolts to:

  upright_deck       +Z up, bolts down to a deck. Full chimney. One folded part.
  upright_bulkhead   +Z up, bolts back to a vertical bulkhead 30 mm behind the
                     unit. Full chimney. One folded part.
  low_profile_side   -X down: 89 mm of stack instead of 173. Costs convection
                     and says so. One folded part, touching no fin.

The Tile core has a far better interface: a 20410 mm2 flat side carrying six
M4x0.7 tapped from BOTH ends. Two mounts use it:

  tile_side_plate    Tile chassis - a light skeletal plate on a side flat.
  hybrid_cold_plate  Hybrid chassis (Tile core + ONE fin bank): the flat side
                     bolts to the plate, the plate bolts to a host through a
                     border that stays reachable with the unit fitted. Solid, not
                     skeletal - it is the heat path the missing bank used to be.

Design target for the folded three is the 60 W chassis (|X| = 36.5), the widest
of the three variants superimposed in the vendor STEP. Because they touch only
the +Y back wall and the -Z end cap, they fit the 30 W, the Tile and either
handedness of hybrid unchanged.

Folded parts are built by extruding an exact 2D bend profile - inside radius,
outside radius and both tangent points - rather than by filleting a union, so
the bend geometry is right by construction and the flat pattern developed in
`flat_patterns.py` matches the solid.

Frame: the vendor's own, so a mount drops straight into an assembly with the
unit at the origin. Units: mm.

    uv run python parts/custom/bedrock-v3000-mount/model.py [--stl] [--out DIR]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"

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

VARIANT_NAMES = ("upright_deck", "upright_bulkhead", "low_profile_side",
                 "tile_side_plate", "hybrid_cold_plate")
FLAT_VARIANTS = ("tile_side_plate", "hybrid_cold_plate")   # no bends to develop


def load_params(path: Path = PARAMS_FILE) -> dict:
    """Load the part's engineering brief."""
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Folded-sheet primitives
# ---------------------------------------------------------------------------
def _arc_mid(p1: tuple, p2: tuple, centre: tuple) -> tuple:
    """Midpoint of the minor arc from p1 to p2 about `centre` — for threePointArc."""
    r = math.hypot(p1[0] - centre[0], p1[1] - centre[1])
    mx = (p1[0] + p2[0]) / 2 - centre[0]
    my = (p1[1] + p2[1]) / 2 - centre[1]
    n = math.hypot(mx, my)
    if n < 1e-9:
        raise ValueError("p1 and p2 are diametrically opposite — arc is ambiguous")
    return (centre[0] + r * mx / n, centre[1] + r * my / n)


def bend_centre(outer_a: float, sign_a: int, outer_b: float, sign_b: int,
                r_outer: float) -> tuple:
    """
    Centre of a 90 deg bend from its two OUTER surface coordinates.

    A 90 degree bend in sheet is fully described by where its two outside faces
    are and which way the material lies from each: the arc centre sits `r_outer`
    inboard of both. Deriving it this way (rather than typing a centre) is what
    keeps the inside radius, the outside radius and all four tangent points
    consistent — get one wrong by hand and the flat pattern stops matching.

    `sign_a` / `sign_b` are +1 if the material lies in the increasing direction
    from that outer face, -1 otherwise.
    """
    return (outer_a + sign_a * r_outer, outer_b + sign_b * r_outer)


def profile_solid(ops: list, plane: str, extrude: float,
                  offset: tuple = (0, 0, 0)) -> cq.Workplane:
    """
    Extrude a closed 2D bend profile into a folded-sheet solid.

    `ops` is a list of ("line", (u, v)) and ("arc", (u, v), (cu, cv)) steps in the
    workplane's own 2D coordinates, starting from the first op's point. `plane` is
    a CadQuery named plane ("YZ" extrudes along +X, "XZ" along -Y, "XY" along +Z).
    """
    cur = ops[0][1]
    wp = cq.Workplane(plane).moveTo(*cur)
    for op in ops[1:]:
        if op[0] == "line":
            wp = wp.lineTo(*op[1])
        elif op[0] == "arc":
            _, end, centre = op
            wp = wp.threePointArc(_arc_mid(cur, end, centre), end)
        else:
            raise ValueError(f"unknown profile op {op[0]!r}")
        cur = op[1]
    solid = wp.close().extrude(extrude)
    return solid.translate(offset) if any(offset) else solid


def rounded_prism(x0: float, x1: float, y0: float, y1: float,
                  z0: float, z1: float, r: float = 0.0) -> cq.Workplane:
    """An axis-aligned prism with rounded plan (Z-parallel) corners."""
    wp = cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
    if r > 0:
        wp = wp.edges("|Z").fillet(r)
    return wp.translate((x0, y0, z0))


def csk_hole(wp: cq.Workplane, x: float, y: float, through_d: float, head_d: float,
             plate_z0: float, plate_z1: float, from_below: bool = True,
             angle: float = 90.0) -> cq.Workplane:
    """
    A countersunk hole through a Z-normal plate, cut as a cylinder plus a cone.

    Countersinks go on flat lands only (DESIGN_LANGUAGE) and are cut as plain
    primitives rather than with `.cskHole()` so the depth arithmetic is explicit:
    a 90 deg head of diameter `head_d` sinks (head_d - through_d)/2.
    """
    depth = (head_d - through_d) / 2 / math.tan(math.radians(angle / 2))
    cyl = (cq.Workplane("XY").circle(through_d / 2)
           .extrude(plate_z1 - plate_z0 + 4).translate((x, y, plate_z0 - 2)))
    if from_below:
        cone = cq.Solid.makeCone(head_d / 2, through_d / 2, depth,
                                 cq.Vector(x, y, plate_z0))
    else:
        cone = cq.Solid.makeCone(head_d / 2, through_d / 2, depth,
                                 cq.Vector(x, y, plate_z1), cq.Vector(0, 0, -1))
    return wp.cut(cyl).cut(cq.Workplane(obj=cone))


def fuse(base: cq.Workplane, add: cq.Workplane, what: str) -> cq.Workplane:
    """
    Union that refuses to lose a part.

    A self-intersecting bend profile makes a face the kernel will not fuse, and
    `Workplane.union` reports that by quietly returning the base solid — the
    flange simply is not in the model, and every downstream check still passes
    because there is nothing there to interfere with anything. Assert the volume
    actually went up.
    """
    before = base.val().Volume()
    out = base.union(add)
    gained = out.val().Volume() - before
    # The material a correct union must add is exactly what `add` has that `base`
    # does not — profiles here deliberately share stock (both of the side-lying
    # bends carry the whole base plate), so comparing against `add` alone would
    # cry wolf every time.
    expected = sum(abs(s.Volume()) for s in add.val().cut(base.val()).Solids())
    if gained < expected - max(1.0, 0.01 * expected):
        raise RuntimeError(
            f"union of {what} added {gained:.1f} mm3 where {expected:.1f} mm3 was new — "
            "the profile is probably self-intersecting. Check that its bend centre was "
            "read off the two faces that form the bend's CONVEX corner.")
    return out


def check_feature_spacing(features: list[tuple], min_gap: float, where: str) -> None:
    """
    Refuse a face whose features run into one another.

    `features` are (u, v, radius) in the face's own plane. Two holes closer than
    r1 + r2 + min_gap share metal that is not there: a tapped hole breaks into a
    countersink, the tap has nothing to cut on one flank, and the screw that goes
    in it holds nothing. This is the same failure as a countersink reaching a
    blank's outline, and just as invisible in a render — the first version of the
    cold plate put two M5 taps 4.5 mm from an 8.4 mm countersink and it took a
    rendered view of the far face to notice.
    """
    for i, (u1, v1, r1) in enumerate(features):
        for u2, v2, r2 in features[i + 1:]:
            need = r1 + r2 + min_gap
            got = math.hypot(u2 - u1, v2 - v1)
            if got < need:
                raise ValueError(
                    f"on {where}, features at ({u1:g}, {v1:g}) r{r1:g} and "
                    f"({u2:g}, {v2:g}) r{r2:g} are {got:.2f} mm apart but need "
                    f"{need:.2f} mm — they overlap or leave no land between them.")


def _slab(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    """Plain cutting box. Bounds are sorted, so mirrored calls need no bookkeeping."""
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def _cyl(axis: str, at: tuple, d: float, lo: float, hi: float) -> cq.Workplane:
    """A cutting cylinder on an axis. `at` is the pair of off-axis coordinates."""
    plane = {"X": "YZ", "Y": "XZ", "Z": "XY"}[axis]
    wp = cq.Workplane(plane).circle(d / 2).extrude(abs(hi - lo))
    if axis == "X":
        return wp.translate((lo, at[0], at[1]))
    if axis == "Y":
        # the XZ plane extrudes along -Y
        return wp.translate((at[0], hi, at[1]))
    return wp.translate((at[0], at[1], lo))


# ---------------------------------------------------------------------------
# Shared interface features — the two faces every variant works
# ---------------------------------------------------------------------------
def backwall_screw_holes(wp: cq.Workplane, plate_y0: float, plate_y1: float,
                         p: dict) -> cq.Workplane:
    """
    The 2x M3 clearance holes and their spotfaces in a Y-normal plate.

    The spotface is not cosmetic. It sets the grip: 3.0 mm of plate less a
    0.5 mm spotface is a 2.5 mm grip, so an M3x5 engages 2.5 mm and stops
    0.5 mm short of the 3.000 mm hole bottom. Take the spotface away and the
    same screw bottoms out.
    """
    f = p["fasteners"]["backwall_m3"]
    screw_len = float(f["screw"].split("x")[1].split()[0])
    iface.check_backwall_screw(screw_len, f["grip"])   # raises if the schedule is wrong
    sf_depth = (plate_y1 - plate_y0) - f["grip"]
    if sf_depth < 0:
        raise ValueError(f"plate is thinner than the {f['grip']} mm grip it must provide")
    for z in iface.BACKWALL_M3_Z:
        wp = wp.cut(_cyl("Y", (iface.BACKWALL_M3_X, z), f["clearance_d"],
                         plate_y0 - 2, plate_y1 + 2))
        wp = wp.cut(_cyl("Y", (iface.BACKWALL_M3_X, z), f["spotface_d"],
                         plate_y1 - sf_depth, plate_y1 + 2))
    return wp


def backwall_relief_slots(wp: cq.Workplane, plate_y0: float, plate_y1: float,
                          z0: float, z1: float, p: dict) -> cq.Workplane:
    """
    Two through-slots that turn a wide plate into a 19 mm bearing tongue.

    The back wall's continuous flat is only X -10..+10. Just outboard of it the
    surface rolls away into two blend ridges that sit 0.1 mm low at Y = 64.9, so a
    flat plate wider than the land rocks on those ridges instead of bearing. A
    through-slot is an unambiguous relief: material exists on the land, and again
    only where the chassis has fallen at least 0.7 mm away.
    """
    x0, x1 = p["clearances"]["relief_slot_x_inner"], p["clearances"]["relief_slot_outer_x"]
    for s in (1, -1):
        lo, hi = sorted((s * x0, s * x1))
        wp = wp.cut(_slab(lo, hi, plate_y0 - 2, plate_y1 + 2, z0, z1)
                    .edges("|Y").fillet(2.0))
    return wp


# ---------------------------------------------------------------------------
# Variant 1 — upright_deck
# ---------------------------------------------------------------------------
def create_upright_deck(params: dict | None = None) -> cq.Workplane:
    """
    Unit upright on a horizontal deck: open pan, side shock walls, rear spine.

    Load path. Weight goes straight down the -Z end cap into the pan's bearing
    land (|X| <= 15, so both fin-channel inlet bands stay open). Fore-and-aft and
    tipping about X are taken by the spine in tension through the 2x M3. Sideways
    shock and roll about Z hit the two side walls, which stand 1.5 mm off the fin
    tips and never touch in normal service. The optional M4 into the bottom cap
    adds anti-prying; nothing here depends on it.
    """
    p = params or load_params()
    v = p["variants"]["upright_deck"]
    d = p["dimensions"]
    t = d["sheet_t"]
    ro = d["bend_radius_inside"] + t

    y_rear = v["pan_y_rear"]              # 65.0 — spine front face, on the land
    y_front = v["pan_y_front"]
    z_top = v["spine_z_top"]
    fl = v["spine_return_flange"]

    # Bend 1, pan -> spine: outer faces are the pan underside (Z = -t, material up)
    # and the spine rear (Y = y_rear + t, material forward).
    c1 = bend_centre(y_rear + t, -1, -t, +1, ro)          # (62, 3)
    # Bend 2, spine -> top return flange: outer faces are the spine front
    # (Y = y_rear, material rearward) and the flange top (Z = z_top, material down).
    c2 = bend_centre(y_rear, +1, z_top, -1, ro)           # (71, 133+3)

    ops = [
        ("line", (y_front, -t)),
        ("line", (c1[0], -t)),
        ("arc", (y_rear + t, c1[1]), c1),
        ("line", (y_rear + t, c2[1])),
        ("arc", (c2[0], z_top - t), c2),
        ("line", (c2[0] + fl, z_top - t)),
        ("line", (c2[0] + fl, z_top)),
        ("line", (c2[0], z_top)),
        ("arc", (y_rear, c2[1]), c2),
        ("line", (y_rear, c1[1])),
        ("arc", (c1[0], 0.0), c1),
        ("line", (y_front, 0.0)),
        ("line", (y_front, -t)),
    ]
    body = profile_solid(ops, "YZ", 2 * v["rear_ear_x"], (-v["rear_ear_x"], 0, 0))

    # Plan outline: pan proper, plus a wider rear ear that carries the spine bend.
    # The ear starts ABOVE the shock walls' rear end — flat material outboard of a
    # bend line is not a thing you can fold, so the two must not share a Y band.
    pan_x, ear_x, ear_y = v["pan_x"], v["rear_ear_x"], v["ear_y_start"]
    if ear_y <= v["wall_y"][1]:
        raise ValueError("the rear ear overlaps the shock-wall bend line — "
                         f"ear starts at Y={ear_y}, walls end at Y={v['wall_y'][1]}")
    plan = (rounded_prism(-pan_x, pan_x, y_front, ear_y + 2,
                          -t - 1, z_top + 1, d["corner_r"])
            .union(rounded_prism(-ear_x, ear_x, ear_y, y_rear + fl + 20,
                                 -t - 1, z_top + 1, d["corner_r"])))
    part = body.intersect(plan)

    # Side shock walls, bent up at |X| = pan_x. Outer faces: the pan underside
    # (Z = -t, material up) and the wall outside (|X| = pan_x + t, material inboard).
    wy0, wy1 = v["wall_y"]
    wh = v["wall_h"]
    cw = bend_centre(pan_x + t, -1, -t, +1, ro)
    wall_ops = [
        ("line", (pan_x - 12.0, -t)),
        ("line", (cw[0], -t)),
        ("arc", (pan_x + t, cw[1]), cw),
        ("line", (pan_x + t, wh)),
        ("line", (pan_x, wh)),
        ("line", (pan_x, cw[1])),
        ("arc", (cw[0], 0.0), cw),
        ("line", (pan_x - 12.0, 0.0)),
        ("line", (pan_x - 12.0, -t)),
    ]
    wall = profile_solid(wall_ops, "XZ", wy1 - wy0, (0, wy1, 0))
    part = fuse(part, wall, "left shock wall")
    part = fuse(part, wall.mirror("YZ"), "right shock wall")

    # Bend relief: the pan->spine bend fillet would sit inside the chassis over
    # Y 62..65, Z 0..3 wherever the bottom cap reaches (|X| <= 29.5). Cut it away
    # so the bend survives only in the two ears outboard of the chassis.
    brx = v["bend_relief_x"]
    part = part.cut(_slab(-brx, brx, c1[0] - 0.01, y_rear + t + 1, -t - 1, c1[1] - 0.001))

    # Fin-channel inlet windows — the pan must bear on the core only.
    wx0, wx1 = v["window_x"]
    wyy0, wyy1 = v["window_y"]
    for s in (1, -1):
        lo, hi = sorted((s * wx0, s * wx1))
        part = part.cut(_slab(lo, hi, wyy0, wyy1, -t - 1, 1.0)
                        .edges("|Z").fillet(v["window_r"]))

    # Spine: bearing tongue, relief slots, M3 holes.
    part = backwall_relief_slots(part, y_rear, y_rear + t,
                                 v["relief_slot_z"][0], v["relief_slot_z"][1], p)
    part = backwall_screw_holes(part, y_rear, y_rear + t, p)

    # Bottom cap fasteners: the optional M4, and clearance over the vendor's
    # fitted screw so a proud head can never jack the pan.
    m4 = p["fasteners"]["bottom_m4"]
    iface.check_bottom_screw(8.0, m4["grip"])
    part = csk_hole(part, *iface.BOTTOM_M4_XY, m4["clearance_d"], m4["csk_d"], -t, 0.0)
    part = part.cut(_cyl("Z", iface.BOTTOM_M4_OCCUPIED_XY, 8.0, -t - 1, 1.0))

    # Host bolts, countersunk flush so heads may live under the chassis footprint.
    host = p["fasteners"]["host"]
    for hx, hy in v["host_holes"]:
        part = csk_hole(part, hx, hy, host["clearance_d"], host["csk_d"], -t, 0.0)

    # Wall lightening / drain slots: air in at the fin inlets, water out.
    half = v["wall_slot_half"]
    sz0, sz1 = v["wall_slot_z"]
    for s in (1, -1):
        for sy in v["wall_slots"]:
            part = part.cut(
                _slab(s * (pan_x - 1), s * (pan_x + t + 1), sy - half, sy + half,
                      sz0, sz1).edges("|X").fillet(2.5))
    return part


# ---------------------------------------------------------------------------
# Variant 2 — upright_bulkhead
# ---------------------------------------------------------------------------
def create_upright_bulkhead(params: dict | None = None) -> cq.Workplane:
    """
    Unit upright against a vertical bulkhead, standing 30 mm off it.

    A top hat: the web carries the bearing tongue and the 2x M3, two side flanges
    take it back to the bulkhead, and two return flanges bolt to it. The 30 mm
    standoff is the point — a mount that pins the unit flat to a bulkhead puts a
    steel plate one millimetre from a live fin bank. Weight sits on a short shelf
    bent forward under the -Z cap, stiffened into a channel by a down-turned front
    lip that doubles as the drip edge.
    """
    p = params or load_params()
    v = p["variants"]["upright_bulkhead"]
    d = p["dimensions"]
    t, ro = d["sheet_t"], d["bend_radius_inside"] + d["sheet_t"]

    y_wall = iface.BACKWALL_Y                     # 65.0, the bearing plane
    z_top = v["web_z"][1]
    y_lip = v["shelf_y_front"]
    lip_h = v["shelf_lip_h"]
    fl = v["return_flange_w"]
    tfl = v["top_flange_w"]
    web_x = v["web_x"]
    depth = v["side_flange_depth"]
    y_bulk = y_wall + t + depth                   # bulkhead plane

    # shelf -> web bend, and web -> top return flange bend
    c_web = bend_centre(y_wall + t, -1, -t, +1, ro)
    c_top = bend_centre(y_wall, +1, z_top, -1, ro)
    # shelf -> down-turned front lip: outer faces are the shelf top (Z = 0,
    # material down) and the lip front (Y = y_lip, material rearward).
    c_lip = bend_centre(y_lip, +1, 0.0, -1, ro)

    ops = [
        ("line", (y_lip, -lip_h)),
        ("line", (y_lip, c_lip[1])),
        ("arc", (c_lip[0], 0.0), c_lip),
        ("line", (c_web[0], 0.0)),
        ("arc", (y_wall, c_web[1]), c_web),
        ("line", (y_wall, c_top[1])),
        ("arc", (c_top[0], z_top), c_top),
        ("line", (c_top[0] + tfl, z_top)),
        ("line", (c_top[0] + tfl, z_top - t)),
        ("line", (c_top[0], z_top - t)),
        ("arc", (y_wall + t, c_top[1]), c_top),
        ("line", (y_wall + t, c_web[1])),
        ("arc", (c_web[0], -t), c_web),
        ("line", (c_lip[0], -t)),
        ("arc", (y_lip + t, c_lip[1]), c_lip),
        ("line", (y_lip + t, -lip_h)),
        ("line", (y_lip, -lip_h)),
    ]
    body = profile_solid(ops, "YZ", 2 * web_x, (-web_x, 0, 0))
    body = body.intersect(rounded_prism(-web_x, web_x, y_lip - 1, y_bulk,
                                        -lip_h - 1, z_top + 1, d["corner_r"]))

    # Side flanges + bulkhead return flanges, bent about Z-parallel lines.
    # web -> side flange: outer faces are the web front (Y = y_wall, material
    # rearward) and the flange outside (X = web_x, material inboard).
    cs = bend_centre(web_x, -1, y_wall, +1, ro)
    # side flange -> return flange. The return flange runs OUTBOARD, so the convex
    # corner of this bend is on the flange's INBOARD face (X = web_x - t), not on
    # its outboard face. Reading that corner off the wrong face puts the arc centre
    # 9 mm out of place, and the profile self-intersects into a face the kernel
    # will not fuse — which shows up as flanges silently missing from the union,
    # not as an error.
    fx = web_x - t
    cr = bend_centre(fx, +1, y_bulk, -1, ro)
    flange_ops = [
        ("line", (web_x - 14.0, y_wall)),
        ("line", (cs[0], y_wall)),
        ("arc", (web_x, cs[1]), cs),
        ("line", (web_x, cr[1])),
        ("arc", (cr[0], y_bulk - t), cr),
        ("line", (cr[0] + fl, y_bulk - t)),
        ("line", (cr[0] + fl, y_bulk)),
        ("line", (cr[0], y_bulk)),
        ("arc", (fx, cr[1]), cr),
        ("line", (fx, cs[1])),
        ("arc", (cs[0], y_wall + t), cs),
        ("line", (web_x - 14.0, y_wall + t)),
        ("line", (web_x - 14.0, y_wall)),
    ]
    fz0, fz1 = v["side_flange_z"]
    flange = profile_solid(flange_ops, "XY", fz1 - fz0, (0, 0, fz0))
    body = fuse(body, flange, "left side flange")
    body = fuse(body, flange.mirror("YZ"), "right side flange")

    # Same bend relief as the deck variant: keep the shelf->web fillet outboard
    # of the chassis footprint.
    brx = v["bend_relief_x"]
    body = body.cut(_slab(-brx, brx, c_web[0] - 0.01, y_wall + t + 1,
                          -t - 1, c_web[1] - 0.001))

    # Shelf: bear on the core only, leave the inlet bands open.
    wx0, wx1 = v["window_x"]
    wy0, wy1 = v["window_y"]
    for s in (1, -1):
        lo, hi = sorted((s * wx0, s * wx1))
        body = body.cut(_slab(lo, hi, wy0, wy1, -t - 1, 1.0).edges("|Z").fillet(5.0))

    body = backwall_relief_slots(body, y_wall, y_wall + t,
                                 v["relief_slot_z"][0], v["relief_slot_z"][1], p)
    body = backwall_screw_holes(body, y_wall, y_wall + t, p)

    m4 = p["fasteners"]["bottom_m4"]
    body = csk_hole(body, *iface.BOTTOM_M4_XY, m4["clearance_d"], m4["csk_d"], -t, 0.0)
    body = body.cut(_cyl("Z", iface.BOTTOM_M4_OCCUPIED_XY, 8.0, -t - 1, 1.0))

    # Bulkhead bolts through the return flanges (Y-normal plates).
    host = p["fasteners"]["host"]
    for hx, hz in v["host_holes"]:
        body = body.cut(_cyl("Y", (hx, hz), host["clearance_d"], y_bulk - t - 2, y_bulk + 2))
        cone = cq.Solid.makeCone(host["csk_d"] / 2, host["clearance_d"] / 2,
                                 (host["csk_d"] - host["clearance_d"]) / 2,
                                 cq.Vector(hx, y_bulk, hz), cq.Vector(0, -1, 0))
        body = body.cut(cq.Workplane(obj=cone))

    # Web lightening windows — the web is 90 mm wide and only ever loaded through
    # the tongue, so the corners are dead metal. Removing them also lets air past
    # the back of the unit instead of trapping it against the plate.
    for s in (1, -1):
        for wz0, wz1 in v["web_windows"]:
            lo, hi = sorted((s * v["web_window_x"][0], s * v["web_window_x"][1]))
            body = body.cut(_slab(lo, hi, y_wall - 1, y_wall + t + 1, wz0, wz1)
                            .edges("|Y").fillet(v["web_window_r"]))
    return body


# ---------------------------------------------------------------------------
# Variant 3 — low_profile_side
# ---------------------------------------------------------------------------
def create_low_profile_side(params: dict | None = None) -> cq.Workplane:
    """
    Unit on its side, -X face down: 85 mm of stack instead of 173.

    There is no fin-free bearing surface anywhere on +/-X — the flare below Z = 7
    that looks like solid skin is still a comb of fin ramps — so this variant does
    not try to rest the unit on anything. It bolts to the two faces that are
    fin-free (the +Y back wall and the -Z end cap) and carries the weight the way
    any bolted joint carries shear: through preload friction, with the screw shanks
    as the backstop. 1.6 kg at 20 g is 314 N against roughly 1.4 kN of friction
    capacity from three screws.

    The base is a guard, not a seat: it sits 9.5 mm below the fin tips and never
    touches. If the joint ever slipped the unit would drop onto a broad frame
    instead of hanging on screw threads, and in normal service the lower fin bank
    still has a 9.5 mm plenum and an open window to convect into.

    Thermal cost is real and stated: fin channels run along Z, so on its side they
    are horizontal. See DESIGN_NOTES.md.
    """
    p = params or load_params()
    v = p["variants"]["low_profile_side"]
    d = p["dimensions"]
    t, ro = d["sheet_t"], d["bend_radius_inside"] + d["sheet_t"]

    x_base = v["base_x"]                     # -46.0, inner face of the base
    y_wall = iface.BACKWALL_Y
    ey0, ey1 = v["end_wall_y"]
    bz0, bz1 = v["base_z"]
    by0, by1 = v["base_y"]

    # base -> end wall (bent up about a Y-parallel line at Z = 0). Outer faces:
    # base outside (X = x_base - t, material inboard) and the end wall's -Z face.
    ce = bend_centre(x_base - t, +1, -t, +1, ro)
    end_ops = [
        ("line", (x_base - t, bz1)),
        ("line", (x_base - t, ce[1])),
        ("arc", (ce[0], -t), ce),
        ("line", (v["end_wall_x"], -t)),
        ("line", (v["end_wall_x"], 0.0)),
        ("line", (ce[0], 0.0)),
        ("arc", (x_base, ce[1]), ce),
        ("line", (x_base, bz1)),
        ("line", (x_base - t, bz1)),
    ]
    part = profile_solid(end_ops, "XZ", ey1 - ey0, (0, ey1, 0))

    # base -> back wall (bent up about a Z-parallel line at Y = 65). Outer faces:
    # base outside (X = x_base - t) and the back wall's rear (Y = y_wall + t).
    cb = bend_centre(x_base - t, +1, y_wall + t, -1, ro)
    back_ops = [
        ("line", (x_base - t, by0)),
        ("line", (x_base - t, cb[1])),
        ("arc", (cb[0], y_wall + t), cb),
        ("line", (v["back_wall_x"], y_wall + t)),
        ("line", (v["back_wall_x"], y_wall)),
        ("line", (cb[0], y_wall)),
        ("arc", (x_base, cb[1]), cb),
        ("line", (x_base, by0)),
        ("line", (x_base - t, by0)),
    ]
    bz_lo, bz_hi = v["back_wall_z"]
    part = fuse(part, profile_solid(back_ops, "XY", bz_hi - bz_lo, (0, 0, bz_lo)),
                "back wall")

    # Trim the base to its plan and round it.
    part = part.intersect(
        rounded_prism(x_base - t - 1, v["end_wall_x"] + 1, by0, by1, bz0, bz1, 0.0)
        .union(rounded_prism(x_base - t - 1, v["back_wall_x"] + 1, by0, y_wall + t + 1,
                             bz_lo - 1, bz_hi + 1, 0.0)))

    # Base windows: the down-facing bank is nearly dead lying on its side, but
    # nearly dead is not dead — leave it open to ambient rather than boxing it in.
    for wz0, wz1 in v["base_windows"]:
        part = part.cut(_slab(x_base - t - 1, x_base + 1, v["base_window_y"][0],
                              v["base_window_y"][1], wz0, wz1)
                        .edges("|X").fillet(8.0))

    # Back wall: bearing tongue + 2x M3.
    part = backwall_relief_slots(part, y_wall, y_wall + t,
                                 v["relief_slot_z"][0], v["relief_slot_z"][1], p)
    part = backwall_screw_holes(part, y_wall, y_wall + t, p)

    # End wall: the M4 into the bottom cap, countersunk on the outside, plus
    # clearance over the vendor's fitted screw.
    m4 = p["fasteners"]["bottom_m4"]
    part = csk_hole(part, *iface.BOTTOM_M4_XY, m4["clearance_d"], m4["csk_d"], -t, 0.0)
    part = part.cut(_cyl("Z", iface.BOTTOM_M4_OCCUPIED_XY, 8.0, -t - 1, 1.0))

    # Host bolts through the base (a X-normal plate), countersunk on the outside.
    host = p["fasteners"]["host"]
    for hy, hz in v["host_holes"]:
        part = part.cut(_cyl("X", (hy, hz), host["clearance_d"], x_base - t - 2, x_base + 2))
        cone = cq.Solid.makeCone(host["csk_d"] / 2, host["clearance_d"] / 2,
                                 (host["csk_d"] - host["clearance_d"]) / 2,
                                 cq.Vector(x_base - t, hy, hz), cq.Vector(1, 0, 0))
        part = part.cut(cq.Workplane(obj=cone))
    return part


# ---------------------------------------------------------------------------
# Variant 4 — tile_side_plate
# ---------------------------------------------------------------------------
def create_tile_side_plate(params: dict | None = None) -> cq.Workplane:
    """
    Tile chassis only: a flat plate on one of its two 20410 mm2 side flats.

    The Tile is the one variant whose sides are worth bolting to, and it has a
    six-point M4 pattern there. Six fixings on a big flat beat two shallow M3 in
    every direction that matters, the plate lands full-contact so it is a real
    conduction path off a fanless unit, and because the load is spread the plate
    can be flat stock with no bends at all. It carries VESA 75 and 100 so the unit
    can go on any standard arm or wall plate.

    This pattern does NOT exist on the 30 W or 60 W chassis. Do not carry it over.
    """
    p = params or load_params()
    v = p["variants"]["tile_side_plate"]
    t = v["plate_t"]
    x1 = -iface.TILE_FACE_X          # the plate's bearing face, on the Tile flat
    x0 = x1 - t

    y0, y1 = v["plate_y"]
    z0, z1 = v["plate_z"]
    plate = (cq.Workplane("YZ").rect(y1 - y0, z1 - z0)
             .extrude(t).translate((x0, (y0 + y1) / 2, (z0 + z1) / 2)))
    plate = plate.edges("|X").fillet(v["plate_r"])

    f = p["fasteners"]["tile_m4"]
    eng = float(f["screw"].split("x")[1].split()[0]) - f["grip"]
    if eng > iface.TILE_M4_MAX_PENETRATION:
        raise ValueError(
            f"{f['screw']} through {f['grip']} mm of plate penetrates {eng:.1f} mm; "
            f"the Tile bores take {iface.TILE_M4_MAX_PENETRATION} mm per side.")
    for y, z in iface.TILE_M4_YZ:
        plate = plate.cut(_cyl("X", (y, z), f["clearance_d"], x0 - 2, x1 + 2))

    # VESA 75 and 100, centred on the plate.
    host = p["fasteners"]["host"]
    zc = (z0 + z1) / 2
    for pitch in v["vesa_pattern"]:
        for sy in (-1, 1):
            for sz in (-1, 1):
                plate = plate.cut(_cyl("X", (sy * pitch / 2, zc + sz * pitch / 2),
                                       host["clearance_d"], x0 - 2, x1 + 2))

    # Lightening windows between the fixing columns — the plate is a spreader,
    # not a shield, and the Tile has no fins to protect.
    for wy0, wy1, wz0, wz1 in v["windows"]:
        plate = plate.cut(_slab(x0 - 1, x1 + 1, wy0, wy1, wz0, wz1)
                          .edges("|X").fillet(6.0))
    return plate


# ---------------------------------------------------------------------------
# Entry points expected by lib/evaluate.py and lib/fit.py
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Variant 5 — hybrid_cold_plate
# ---------------------------------------------------------------------------
def create_hybrid_cold_plate(params: dict | None = None) -> cq.Workplane:
    """
    Hybrid chassis: the flat side bolts to a structure, the fin bank stays in air.

    The 60 W chassis is a Tile core with two identical fin banks on it, separable
    at |X| = 14.5. Take one bank off and the unit gains what none of the other
    configurations have: a 20 410 mm2 flat face carrying six M4 on a 120 x 140 mm
    spread. That is a better fixing than the 2x M3 back-wall pair by every
    measure, and it is the reason this variant exists.

    But it is not free. Half the fin area went with the bank, so this plate is not
    a bracket that happens to touch — it is the replacement heat path, and it is
    solid on purpose. No lightening windows: `tile_side_plate` can be skeletal
    because a fanless Tile has little to shed, and this cannot. 5 mm of 6082-T6
    spreads across the whole plate (sqrt(k*t/h) ~ 290 mm against a 168 mm plate),
    so the useful question is what the plate is bolted TO. Bolt it to a bulkhead
    that conducts and the trade is a good one; bolt it to a plastic panel and you
    have simply thrown away a fin bank.

    Fastener direction sets the whole design. The unit is a closed box, so the
    six M4 can only come from the outer face — which is the face that has to sit
    flat against the host — so they are countersunk.

    That leaves the question of how the plate itself gets mounted, and inside the
    chassis footprint there is only one answer: BLIND tapped holes, because a
    through hole there has no accessible end. A screw into it would have to come
    from behind the host plate, and an over-length one in a through-tapped hole
    would stand proud on the bearing face and jack the plate off the chassis. The
    VESA patterns are exactly that, and they are the right answer for an arm.

    They are the wrong answer for bolting this flat to another plate you cannot
    reach behind — so the plate carries a **border** that stands 19.5 mm outboard
    of the chassis flat on every side, with six M6 straight through it. Those
    bolt heads land on the unit side of the plate, in fresh air outboard of the
    chassis, which is what makes them reachable with the Bedrock already fitted.
    """
    p = params or load_params()
    v = p["variants"]["hybrid_cold_plate"]
    t = v["plate_t"]
    side = v["fin_side"]
    variant = "hybrid_posx" if side == "+X" else "hybrid_negx"
    x_bear = iface.flat_side_x(variant)          # the face we clamp against
    sgn = -1 if side == "+X" else 1              # the plate lies away from the fins
    x_outer = x_bear + sgn * t
    lo, hi = sorted((x_bear, x_outer))

    y0, y1 = v["plate_y"]
    z0, z1 = v["plate_z"]
    plate = (cq.Workplane("YZ").rect(y1 - y0, z1 - z0)
             .extrude(t).translate((lo, (y0 + y1) / 2, (z0 + z1) / 2)))
    plate = plate.edges("|X").fillet(v["plate_r"])

    # The border has to clear the chassis flat, or its bolt heads land on the unit
    # and the whole point of it is gone.
    border = min(-y0 - iface.TILE_SIDE_FLAT_Y, y1 - iface.TILE_SIDE_FLAT_Y)
    if border < 12.0:
        raise ValueError(
            f"the plate reaches only {border:.1f} mm past the chassis flat at "
            f"|Y| = {iface.TILE_SIDE_FLAT_Y} — there is nowhere to put a through "
            "bolt you can still reach with the unit fitted.")

    # Six M4 into the chassis, countersunk flush in the outer face.
    f = p["fasteners"]["hybrid_m4"]
    screw_len = float(f["screw"].split("x")[1].split()[0])
    engagement = screw_len - t
    if engagement > iface.TILE_M4_MAX_PENETRATION:
        raise ValueError(
            f"{f['screw']} through {t} mm of plate penetrates {engagement:.1f} mm; "
            f"the core's side bores give {iface.TILE_M4_MAX_PENETRATION} mm per side.")
    if engagement < 2.5:
        raise ValueError(
            f"{f['screw']} through {t} mm of plate engages only {engagement:.1f} mm.")
    csk_depth = (f["csk_d"] - f["clearance_d"]) / 2
    for hy, hz in iface.TILE_M4_YZ:
        plate = plate.cut(_cyl("X", (hy, hz), f["clearance_d"], lo - 2, hi + 2))
        cone = cq.Solid.makeCone(f["csk_d"] / 2, f["clearance_d"] / 2, csk_depth,
                                 cq.Vector(x_outer, hy, hz), cq.Vector(-sgn, 0, 0))
        plate = plate.cut(cq.Workplane(obj=cone))

    # Host interfaces: blind tapping-drill holes in the outer face only.
    host = p["fasteners"]["hybrid_host"]
    depth = host["tap_drill_depth"]
    if depth >= t:
        raise ValueError(
            f"a {depth} mm tapped hole in a {t} mm plate breaks through onto the "
            "bearing face — an over-length host screw would then jack the plate "
            "off the chassis.")
    zc = v["vesa_centre_z"]
    taps = [(sy * pitch / 2, zc + sz * pitch / 2, host["m4_tap_drill"] / 2)
            for pitch in v["vesa_pattern"] for sy in (-1, 1) for sz in (-1, 1)]

    # Six M6 straight through the border — the ones you can reach with the unit on.
    bolt = p["fasteners"]["hybrid_border"]
    through = [(hy, hz, bolt["clearance_d"] / 2) for hy, hz in v["border_holes"]]
    for hy, hz in v["border_holes"]:
        head_r = bolt["head_d"] / 2
        if abs(hy) - head_r < iface.TILE_SIDE_FLAT_Y and \
                -1.0 < hz < iface.TILE_SIDE_FLAT_Z[1] + 1.0:
            raise ValueError(
                f"border bolt at (Y {hy:g}, Z {hz:g}) puts a {bolt['head_d']:g} mm head "
                f"over the chassis flat (|Y| <= {iface.TILE_SIDE_FLAT_Y}) — it cannot be "
                "reached once the unit is fitted, which is the only reason it exists.")

    check_feature_spacing(
        [(hy, hz, f["csk_d"] / 2) for hy, hz in iface.TILE_M4_YZ] + taps + through,
        v["min_feature_gap"], "the cold plate's outer face")

    for hy, hz, r in taps:
        plate = plate.cut(_cyl("X", (hy, hz), 2 * r,
                               *sorted((x_outer, x_outer - sgn * depth))))
    for hy, hz, r in through:
        plate = plate.cut(_cyl("X", (hy, hz), 2 * r, lo - 2, hi + 2))
    return plate


BUILDERS = {
    "upright_deck": create_upright_deck,
    "upright_bulkhead": create_upright_bulkhead,
    "low_profile_side": create_low_profile_side,
    "tile_side_plate": create_tile_side_plate,
    "hybrid_cold_plate": create_hybrid_cold_plate,
}


def create_part(params: dict | None = None) -> cq.Workplane:
    """The primary fabrication concept: the upright deck mount."""
    return create_upright_deck(params)


# Vendor solids exposed as builders so spec.json's declarative "fit" block can
# place them. They ignore `params` — the geometry is SolidRun's, not ours.
def bedrock_60w(params: dict | None = None) -> cq.Workplane:
    """The 60 W unit (chassis + connectors) in its own frame."""
    return iface.bedrock_unit("60w")


def bedrock_30w(params: dict | None = None) -> cq.Workplane:
    """The 30 W unit (chassis + connectors) in its own frame."""
    return iface.bedrock_unit("30w")


def bedrock_tile(params: dict | None = None) -> cq.Workplane:
    """The Tile unit (chassis + connectors) in its own frame."""
    return iface.bedrock_unit("tile")


def bedrock_hybrid_posx(params: dict | None = None) -> cq.Workplane:
    """The hybrid unit with its fin bank on +X (flat face at X = -14.5)."""
    return iface.bedrock_unit("hybrid_posx")


def bedrock_hybrid_negx(params: dict | None = None) -> cq.Workplane:
    """The hybrid unit with its fin bank on -X (flat face at X = +14.5)."""
    return iface.bedrock_unit("hybrid_negx")


def hybrid_fin_bank(params: dict | None = None) -> cq.Workplane:
    """The +X fin volume of the hybrid, root to tip over the tip Z band."""
    return iface.keepout_solid("fin_bank_pos_x", "hybrid_posx")


def io_cable_envelope(params: dict | None = None) -> cq.Workplane:
    """The 55 mm service volume in front of the I/O panel."""
    return iface.keepout_solid("io_cables")


def sma_cable_envelope(params: dict | None = None) -> cq.Workplane:
    """The 45 mm service volume above the antenna bulkheads."""
    return iface.keepout_solid("sma_cables")


def fin_bank_pos_x(params: dict | None = None) -> cq.Workplane:
    """The +X fin volume, root to tip over the Z band the tips span."""
    return iface.keepout_solid("fin_bank_pos_x")


def fin_bank_neg_x(params: dict | None = None) -> cq.Workplane:
    """The -X fin volume."""
    return iface.keepout_solid("fin_bank_neg_x")


def create_assembly(params: dict | None = None, variant: str = "upright_deck",
                    with_unit: bool = True) -> cq.Assembly:
    """The mount with the vendor unit dropped into it, for renders and fit views."""
    p = params or load_params()
    asm = cq.Assembly()
    asm.add(BUILDERS[variant](p), name=variant, color=cq.Color(0.18, 0.19, 0.21))
    if with_unit:
        unit = {"tile_side_plate": "tile",
                "hybrid_cold_plate": ("hybrid_posx"
                                      if p["variants"]["hybrid_cold_plate"]["fin_side"] == "+X"
                                      else "hybrid_negx")}.get(variant, p["target_variant"])
        asm.add(iface.bedrock_unit(unit), name=f"bedrock_{unit}",
                color=cq.Color(0.55, 0.16, 0.13))
    return asm


def build_stages(params: dict | None = None):
    """Stage-by-stage build of the primary variant for `lib.debug_build`."""
    p = params or load_params()
    v = p["variants"]["upright_deck"]
    d = p["dimensions"]
    t, ro = d["sheet_t"], d["bend_radius_inside"] + d["sheet_t"]
    y_rear, y_front, z_top = v["pan_y_rear"], v["pan_y_front"], v["spine_z_top"]
    fl = v["spine_return_flange"]
    c1 = bend_centre(y_rear + t, -1, -t, +1, ro)
    c2 = bend_centre(y_rear, +1, z_top, -1, ro)
    ops = [
        ("line", (y_front, -t)), ("line", (c1[0], -t)),
        ("arc", (y_rear + t, c1[1]), c1), ("line", (y_rear + t, c2[1])),
        ("arc", (c2[0], z_top - t), c2), ("line", (c2[0] + fl, z_top - t)),
        ("line", (c2[0] + fl, z_top)), ("line", (c2[0], z_top)),
        ("arc", (y_rear, c2[1]), c2), ("line", (y_rear, c1[1])),
        ("arc", (c1[0], 0.0), c1), ("line", (y_front, 0.0)), ("line", (y_front, -t)),
    ]
    result = profile_solid(ops, "YZ", 2 * v["rear_ear_x"], (-v["rear_ear_x"], 0, 0))
    yield "bend_profile_extrusion", result

    plan = (rounded_prism(-v["pan_x"], v["pan_x"], y_front, v["window_y"][1] + 4,
                          -t - 1, z_top + 1, d["corner_r"])
            .union(rounded_prism(-v["rear_ear_x"], v["rear_ear_x"], v["window_y"][1] - 2,
                                 y_rear + fl + 20, -t - 1, z_top + 1, d["corner_r"])))
    result = result.intersect(plan)
    yield "plan_outline", result

    yield "complete", create_upright_deck(p)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_design(params: dict | None = None, out_dir: Path | None = None,
                  stl: bool = False) -> list[Path]:
    """Export every variant, plus the primary assembly, as STEP."""
    p = params or load_params()
    out = Path(out_dir) if out_dir else EXPORTS_DIR
    out.mkdir(parents=True, exist_ok=True)
    ver = p.get("version", "v1")
    written = []

    for name, builder in BUILDERS.items():
        solid = builder(p)
        stem = f"bdrk_mnt_{ver}_{name}"
        path = out / f"{stem}.step"
        _warn_long_path(path)
        cq.exporters.export(solid, str(path))
        written.append(path)
        print(f"  ok {path.name:<38} {solid.val().Volume() / 1000:8.1f} cm^3")
        if stl:
            cq.exporters.export(solid, str(out / f"{stem}.stl"))
    return written


MAX_WIN_PATH = 258


def _warn_long_path(path: Path) -> None:
    """SolidWorks still uses the legacy Win32 API — a 259-char path is unopenable."""
    if len(str(path.resolve())) > MAX_WIN_PATH:
        print(f"  !! {len(str(path.resolve()))} characters — SolidWorks will refuse this "
              f"file. Re-run with --out C:/some/short/dir")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", help="export directory (use a short path for SolidWorks)")
    ap.add_argument("--stl", action="store_true", help="also write STL")
    ap.add_argument("--variant", choices=VARIANT_NAMES, help="build just one variant")
    ap.add_argument("--show", action="store_true",
                    help="push the assembly to the OCP CAD Viewer (VS Code)")
    args = ap.parse_args()

    params = load_params()
    print(f"\n  {params['part_name']} ({params.get('version', 'v1')})")
    print(f"  Material: {params['material']}")
    print(f"  Process:  {params['process']}\n")

    if args.variant:
        solid = BUILDERS[args.variant](params)
        out = Path(args.out) if args.out else EXPORTS_DIR
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"bdrk_mnt_{params.get('version', 'v1')}_{args.variant}.step"
        _warn_long_path(path)
        cq.exporters.export(solid, str(path))
        print(f"  ok {path}")
    else:
        export_design(params, args.out, args.stl)

    # Opt-in: the viewer re-tessellates the vendor solids and prints a page of
    # "face NNN ignored" at every export otherwise.
    if args.show:
        try:
            from ocp_vscode import show

            show(create_assembly(params))
        except Exception as exc:
            print(f"  (OCP CAD Viewer unavailable: {exc})")
