"""
MEAN WELL NSP-1600 mount family
===============================

One qualified attitude (horizontal, bottom face down). Two generations of
hardware for it, all still buildable:

v2 - the tab kits (the default)
    side_tab         one small L-tab, flush on the side wall over one M4, foot
                     bent OUTWARD with a slot. Four per unit on a deck - MEAN
                     WELL's own bracket pattern. One bend. The default.
    bulkhead_strap   a 45 mm L strip: shelf under the unit, flange DOWN the
                     bulkhead. Two per unit, plus two side tabs bolted to
                     them. One bend.
    terminal_box     printed, vented, floored box over the terminal face with
                     grommet exits - finger-safe with nothing under it.

v1 - the channel kits
    bulkhead_shelf   full-length folded channel off a vertical bulkhead.
    deck_tray        full-length folded channel on a deck.
    busbar_hood      open-bottom hood that sits on a channel's pan.
    spacer_ring      3.0 mm ring filling the channel's bend clearance at each M4.

THE MOUNT FRAME
---------------
The vendor frame translated by (-66.787, -354.15, -1.5) - a pure translation, so
the vendor solid drops in with no handedness question. Origin on the unit's
bottom face, centred on its width, at the terminal face. +Y along the blades
(the body is at Y <= 0), +Z up. See interface.py.

THE ONE GEOMETRIC IDEA
----------------------
Both channels stand the unit 3.0 mm off each wall - exactly one sheet thickness.
A 90 degree bend in 3 mm sheet has a 3 mm inside radius, and that radius lands
its pan tangent exactly at X = +/-42.5, the unit's bottom corner. So the unit
bears on flat pan over its whole footprint, the fillet never lifts it, and the
gap at each side M4 is filled by a ring cut from the same sheet. Any other gap
either puts the unit up on the fillet or needs a spacer of a second thickness.

Folded parts are built as flat legs plus explicit annular bend quadrants, so the
STEP carries the bend the brake will make and flat_patterns.py develops the
blank from the same two numbers.

    C:/venvs/cadquery/Scripts/python.exe parts/custom/nsp1600-mount/model.py --out DIR [--stl]

Units: mm.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"
PART_NAME = PART_DIR.name           # what lib.export / lib.evaluate call the artifact

if str(PART_DIR) not in sys.path:
    sys.path.insert(0, str(PART_DIR))

import interface as iface  # noqa: E402  - path-dependent by design

VARIANT_NAMES = ("side_tab", "bulkhead_strap", "terminal_box",
                 "bulkhead_shelf", "deck_tray", "busbar_hood", "spacer_ring")
METAL_VARIANTS = ("bulkhead_shelf", "deck_tray")                 # the v1 channels
FOLDED_VARIANTS = ("side_tab", "bulkhead_strap", "bulkhead_shelf", "deck_tray")
KITS = ("deck_tab_kit", "bulkhead_strap_kit", "deck_tray_kit", "bulkhead_shelf_kit")


def load_params(path: Path = PARAMS_FILE) -> dict:
    """Load the part's engineering brief."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _var(p: dict, name: str) -> dict:
    return p["variants"][name]


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def _box(x0, x1, y0, y1, z0, z1) -> cq.Workplane:
    """Axis-aligned box; bounds are sorted so mirrored calls need no bookkeeping."""
    x0, x1 = sorted((x0, x1))
    y0, y1 = sorted((y0, y1))
    z0, z1 = sorted((z0, z1))
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def _cyl(axis: str, at: tuple, d: float, lo: float, hi: float) -> cq.Workplane:
    """A cylinder on an axis between two stations. `at` is the off-axis pair."""
    lo, hi = sorted((lo, hi))
    plane = {"X": "YZ", "Y": "XZ", "Z": "XY"}[axis]
    wp = cq.Workplane(plane).circle(d / 2).extrude(hi - lo)
    if axis == "X":
        return wp.translate((lo, at[0], at[1]))
    if axis == "Y":
        return wp.translate((at[0], hi, at[1]))        # XZ extrudes along -Y
    return wp.translate((at[0], at[1], lo))


def _quadrant(cx: float, cz: float, ir: float, orr: float, sx: int, sz: int,
              y0: float, y1: float) -> cq.Workplane:
    """
    One 90 degree bend: the annulus between radii `ir` and `orr` about (cx, cz)
    in the XZ plane, kept in the quadrant lying `sx` in X and `sz` in Z from the
    centre, extruded along Y from y0 to y1. Built explicitly rather than by
    filleting a union so the bend is the bend the brake makes.
    """
    ylen = y1 - y0
    outer = (cq.Workplane("XZ").center(cx, cz).circle(orr)
             .extrude(ylen).translate((0, y1, 0)))
    inner = (cq.Workplane("XZ").center(cx, cz).circle(ir)
             .extrude(ylen).translate((0, y1, 0)))
    quad = _box(cx, cx + sx * orr, y0, y1, cz, cz + sz * orr)
    return outer.cut(inner).intersect(quad)


def _cone(x: float, y: float, head_d: float, through_d: float, z_face: float,
          direction: int, angle: float = 90.0) -> cq.Workplane:
    """A countersink cone opening on the plane z_face, closing `direction` (+1 up)."""
    import math

    depth = (head_d - through_d) / 2 / math.tan(math.radians(angle / 2))
    cone = cq.Solid.makeCone(head_d / 2, through_d / 2, depth,
                             cq.Vector(x, y, z_face), cq.Vector(0, 0, direction))
    return cq.Workplane(obj=cone)


def _slot(cx: float, cy: float, length: float, width: float, angle: float,
          z0: float, z1: float) -> cq.Workplane:
    """
    A rounded-end slot cutter through Z: a box plus two end cylinders. Built
    from primitives rather than slot2D().extrude() - the latter's seam leaves
    an invalid B-rep after the cut.
    """
    half = (length - width) / 2
    if angle == 90:
        body = _box(cx - width / 2, cx + width / 2, cy - half, cy + half, z0, z1)
        ends = [(cx, cy - half), (cx, cy + half)]
    else:
        body = _box(cx - half, cx + half, cy - width / 2, cy + width / 2, z0, z1)
        ends = [(cx - half, cy), (cx + half, cy)]
    for ex, ey in ends:
        body = body.union(_cyl("Z", (ex, ey), width, z0, z1))
    return body


def fuse(base: cq.Workplane, add: cq.Workplane, what: str) -> cq.Workplane:
    """
    Union that refuses to lose a piece.

    `Workplane.union` reports a face it cannot fuse by quietly returning the base
    solid - the flange is simply not in the model and every downstream check
    passes because there is nothing there to interfere. Assert the volume went
    up by what was new, and that the result is still one solid.
    """
    before = base.val().Volume()
    out = base.union(add)
    gained = out.val().Volume() - before
    expected = sum(abs(s.Volume()) for s in add.val().cut(base.val()).Solids())
    if gained < expected - max(1.0, 0.01 * expected):
        raise RuntimeError(f"union of {what} added {gained:.1f} mm3 where {expected:.1f} "
                           "mm3 was new - a piece was dropped")
    if len(out.val().Solids()) != 1:
        raise RuntimeError(f"union of {what} left {len(out.val().Solids())} solids - "
                           "the pieces do not share a face")
    return out


# ---------------------------------------------------------------------------
# The channel section both metal variants are made of
# ---------------------------------------------------------------------------
def channel_stations(p: dict) -> dict:
    """Every X station of the section, derived once from three numbers."""
    d = p["dimensions"]
    t, ri = d["sheet_t"], d["bend_radius_inside"]
    x_in = iface.HALF_W + d["side_gap"]          # 45.5  wall inner face
    return {
        "t": t, "ri": ri, "orr": ri + t,
        "x_in": x_in,                               # 45.5
        "x_out": x_in + t,                          # 48.5  wall outer face / pan edge
        "x_tan": x_in - ri,                         # 42.5  pan tangent = unit's corner
        "z_tan": ri,                                # 3.0   wall tangent above the pan top
    }


def walls_for(p: dict, variant: str) -> dict:
    """Which walls a metal variant bends up, and how tall and how long they run."""
    v = _var(p, variant)
    if variant == "bulkhead_shelf":
        return {"-X": {"h": v["flange_h"], "y": tuple(p["dimensions"]["pan_y"])},
                "+X": {"h": v["web_h"], "y": tuple(v["web_y"])}}
    if variant == "deck_tray":
        return {"-X": {"h": v["wall_h"], "y": tuple(v["wall_y"])},
                "+X": {"h": v["wall_h"], "y": tuple(v["wall_y"])}}
    raise ValueError(f"{variant} is not a folded variant")


def _channel(p: dict, walls: dict) -> cq.Workplane:
    """
    Pan plus up to two walls bent up from its +/-X edges.

    walls = {"+X": {"h": height, "y": (y0, y1)}, "-X": {...}}. Where a wall does
    not run, the pan stays flat and full width, separated from the wall's end by
    a bend-relief slit one sheet thickness wide - the brake cannot fold across
    flat material, and a slit is the unambiguous way to tell it so.
    """
    d = p["dimensions"]
    s = channel_stations(p)
    t, ri, orr = s["t"], s["ri"], s["orr"]
    y0, y1 = d["pan_y"]
    relief = d["bend_relief_w"]
    cr = d["corner_r"]

    part = _box(-s["x_out"], s["x_out"], y0, y1, -t, 0).edges("|Z").fillet(cr)

    for side, w in walls.items():
        sg = 1 if side == "+X" else -1
        wy0, wy1 = w["y"]
        h = w["h"]
        # clear the pan beyond the tangent over the wall band plus both slits
        part = part.cut(_box(sg * s["x_tan"], sg * (s["x_out"] + 1),
                             wy0 - relief, wy1 + relief, -t - 1, 1))
        bend = _quadrant(sg * s["x_tan"], ri, ri, orr, sg, -1, wy0, wy1)
        wall = _box(sg * s["x_in"], sg * s["x_out"], wy0, wy1, s["z_tan"], h)
        top_edges = cq.selectors.BoxSelector(
            (min(sg * s["x_in"], sg * s["x_out"]) - 1, wy0 - 1, h - 0.5),
            (max(sg * s["x_in"], sg * s["x_out"]) + 1, wy1 + 1, h + 0.5))
        wall = wall.edges("|X").edges(top_edges).fillet(cr)
        part = fuse(part, bend, f"{side} bend")
        part = fuse(part, wall, f"{side} wall")
    return part


# --- shared features --------------------------------------------------------
def _side_m4_holes(part: cq.Workplane, p: dict, sides: tuple) -> cq.Workplane:
    s = channel_stations(p)
    f = p["fasteners"]["side_m4"]
    screw_len = float(f["screw"].split("x")[1].split()[0])
    iface.check_side_screw(screw_len, f["grip"])      # raises if the schedule is wrong
    for side in sides:
        sg = 1 if side == "+X" else -1
        for y, z in iface.SIDE_M4_YZ:
            part = part.cut(_cyl("X", (y, z), f["clearance_d"],
                                 sg * (s["x_in"] - 1), sg * (s["x_out"] + 1)))
    return part


def _bottom_m3_csk(part: cq.Workplane, p: dict) -> cq.Workplane:
    """Three M3 clearance holes, countersunk from the pan's underside."""
    t = p["dimensions"]["sheet_t"]
    f = p["fasteners"]["bottom_m3"]
    screw_len = float(f["screw"].split("x")[1].split()[0])
    iface.check_bottom_screw(screw_len, f["grip"])
    for x, y in iface.BOTTOM_M3_XY:
        part = part.cut(_cyl("Z", (x, y), f["clearance_d"], -t - 1, 1))
        part = part.cut(_cone(x, y, f["csk_d"], f["clearance_d"], -t, +1, f["csk_angle"]))
    return part


def _hood_taps(part: cq.Workplane, p: dict) -> cq.Workplane:
    t = p["dimensions"]["sheet_t"]
    td = p["fasteners"]["hood_m3"]["tap_drill"]
    for x, y in p["dimensions"]["hood_tap_xy"]:
        part = part.cut(_cyl("Z", (x, y), td, -t - 1, 1))
    return part


def _pan_slots(part: cq.Workplane, p: dict) -> cq.Workplane:
    """Drain slots under the unit's edges, cable-tie slots past the hood."""
    d = p["dimensions"]
    t = d["sheet_t"]
    sl, sw = d["drain_slot"]
    for sg in (1, -1):
        for y in d["drain_slot_y"]:
            part = part.cut(_slot(sg * d["drain_slot_x"], y, sl, sw, 90, -t - 1, 1))
    tl, tw = d["tie_slot"]
    for x, y in d["tie_slots_xy"]:
        part = part.cut(_slot(x, y, tl, tw, 0, -t - 1, 1))
    return part


# ---------------------------------------------------------------------------
# Variant 1 - bulkhead_shelf (the default)
# ---------------------------------------------------------------------------
def create_bulkhead_shelf(params: dict | None = None) -> cq.Workplane:
    """
    Unit horizontal on a shelf off a vertical bulkhead.

    Load path. Weight goes straight down into the shelf over the unit's whole
    85 x 300 footprint. Sideways and fore-aft shock go through the two +X M4s in
    shear (with their spacer rings clamped metal-to-metal) and the three M3s.
    Tip-over about the M4 line is a couple between the shelf and the M4s in
    tension - 353 N at 20 g against roughly 1 kN of preload. The flange takes
    all of it into the bulkhead through seven M5, every one reachable with the
    unit fitted because every one is above it or beyond its ends.
    """
    p = params or load_params()
    v = _var(p, "bulkhead_shelf")
    f = p["fasteners"]["host_bulkhead"]
    s = channel_stations(p)

    part = _channel(p, walls_for(p, "bulkhead_shelf"))
    part = _side_m4_holes(part, p, sides=("+X",))
    part = _bottom_m3_csk(part, p)
    part = _hood_taps(part, p)
    part = _pan_slots(part, p)

    # Bulkhead bolts through the -X flange: round holes plus two keyholes. The
    # keyhole's round end sits BELOW the slot: lift the bracket, pass two bolt
    # heads through the rounds, lower it 8 mm so the shanks ride up the slots,
    # then fit the rest.
    x0, x1 = -s["x_out"] - 1, -s["x_in"] + 1
    for y, z in v["bulkhead_holes"]:
        part = part.cut(_cyl("X", (y, z), f["clearance_d"], x0, x1))
    for y, z in v["bulkhead_keyholes"]:
        part = part.cut(_cyl("X", (y, z - f["keyhole_slot_len"]), f["keyhole_d"], x0, x1))
        part = part.cut(_box(x0, x1, y - f["keyhole_slot_w"] / 2, y + f["keyhole_slot_w"] / 2,
                             z - f["keyhole_slot_len"], z))
    return part


# ---------------------------------------------------------------------------
# Variant 2 - deck_tray
# ---------------------------------------------------------------------------
def create_deck_tray(params: dict | None = None) -> cq.Workplane:
    """
    Unit horizontal on a horizontal deck.

    The vendor's own mounting pattern - four side M4s - given a bearing floor.
    Weight into the pan; every other load into four M4 in shear through rings
    clamped metal-to-metal. The three M3 are optional insurance. Four M5 into
    the deck beyond the unit's ends, countersunk flush.
    """
    p = params or load_params()
    v = _var(p, "deck_tray")
    d = p["dimensions"]
    t = d["sheet_t"]
    host = p["fasteners"]["host_deck"]

    part = _channel(p, walls_for(p, "deck_tray"))
    part = _side_m4_holes(part, p, sides=("-X", "+X"))
    part = _bottom_m3_csk(part, p)
    part = _hood_taps(part, p)
    part = _pan_slots(part, p)
    for x, y in v["host_holes"]:
        part = part.cut(_cyl("Z", (x, y), host["clearance_d"], -t - 1, 1))
        part = part.cut(_cone(x, y, host["csk_d"], host["clearance_d"], 0.0, -1,
                              host["csk_angle"]))
    return part


# ---------------------------------------------------------------------------
# Variant 3 - busbar_hood (printed)
# ---------------------------------------------------------------------------
def hood_cavity(params: dict | None = None) -> cq.Workplane:
    """The volume the hood encloses, from the terminal plate to its far wall."""
    p = params or load_params()
    v = _var(p, "busbar_hood")
    wt, tt = v["wall_t"], v["top_t"]
    return _box(v["x"][0] + wt, v["x"][1] - wt, iface.TERMINAL_FACE_Y, v["y"][1] - wt,
                0.0, v["z_top"] - tt)


def create_busbar_hood(params: dict | None = None) -> cq.Workplane:
    """
    Vented hood over the terminal face. Open at the bottom (sits on the pan)
    and at the unit end (0.5 mm off the terminal plate); four walls otherwise.
    """
    p = params or load_params()
    v = _var(p, "busbar_hood")
    wt, tt = v["wall_t"], v["top_t"]
    x0, x1 = v["x"]
    y0, y1 = v["y"]
    zt = v["z_top"]

    outer = _box(x0, x1, y0, y1, 0.0, zt)
    far_corners = cq.selectors.BoxSelector((x0 - 1, y1 - 1, -1), (x1 + 1, y1 + 1, zt + 1))
    outer = outer.edges("|Z").edges(far_corners).fillet(v["corner_r"])
    outer = outer.faces(">Z").edges().fillet(v["top_r"])

    cav = _box(x0 + wt, x1 - wt, y0 - 5.0, y1 - wt, -5.0, zt - tt)
    far_inner = cq.selectors.BoxSelector((x0, y1 - wt - 1, -6), (x1, y1 - wt + 1, zt + 1))
    cav = cav.edges("|Z").edges(far_inner).fillet(v["corner_r"] - wt)
    hood = outer.cut(cav)

    # feet, inboard, along both side walls
    fy0, fy1 = v["foot_y"]
    fw, ft = v["foot_w"], v["foot_t"]
    hood = fuse(hood, _box(x0 + wt - 0.01, x0 + wt + fw, fy0, fy1, 0.0, ft), "-X foot")
    hood = fuse(hood, _box(x1 - wt - fw, x1 - wt + 0.01, fy0, fy1, 0.0, ft), "+X foot")
    for x, y in p["dimensions"]["hood_tap_xy"]:
        hood = hood.cut(_cyl("Z", (x, y), p["fasteners"]["hood_m3"]["clearance_d"], -1, ft + 1))

    # cable exits: U-slots up from the bottom edge of the far wall
    for name, cs in v["cable_slots"].items():
        sx0, sx1 = cs["x"]
        w = sx1 - sx0
        ztop = cs["z_top"]
        hood = hood.cut(_box(sx0, sx1, y1 - wt - 1, y1 + 1, -1.0, ztop - w / 2))
        hood = hood.cut(_cyl("Y", ((sx0 + sx1) / 2, ztop - w / 2), w, y1 - wt - 1, y1 + 1))
    # LED sight / trim-pot window in the far wall
    lw = v["led_window"]
    hood = hood.cut(_box(lw["x"][0], lw["x"][1], y1 - wt - 1, y1 + 1, lw["z"][0], lw["z"][1]))

    # louvres: top face, both side walls - rounded slots, 5 mm wide
    tl = v["top_louvres"]
    ly = (tl["y"][0] + tl["y"][1]) / 2
    for x in tl["x"]:
        hood = hood.cut(_slot(x, ly, tl["y"][1] - tl["y"][0], tl["w"], 90, zt - tt - 1, zt + 1))
    sl = v["side_louvres"]
    sy = (sl["y"][0] + sl["y"][1]) / 2
    for z in sl["z"]:
        cutter = (cq.Workplane("YZ").center(sy, z)
                  .slot2D(sl["y"][1] - sl["y"][0], sl["w"], angle=0).extrude(wt + 2))
        hood = hood.cut(cutter.translate((x0 - 1, 0, 0)))
        hood = hood.cut(cutter.translate((x1 - wt - 1, 0, 0)))
    return hood


# ---------------------------------------------------------------------------
# Variant 4 - spacer_ring
# ---------------------------------------------------------------------------
def create_spacer_ring(params: dict | None = None) -> cq.Workplane:
    """One ring, axis Z, sitting on Z = 0 - the blank as cut."""
    p = params or load_params()
    v = _var(p, "spacer_ring")
    t = p["dimensions"]["sheet_t"]
    return (cq.Workplane("XY").circle(v["od"] / 2).circle(v["id"] / 2).extrude(t))


def create_spacers(params: dict | None = None, variant: str = "deck_tray") -> cq.Workplane:
    """The rings placed on their M4 axes between the unit and the wall, as one compound."""
    p = params or load_params()
    v = _var(p, "spacer_ring")
    s = channel_stations(p)
    sides = ("-X", "+X") if variant == "deck_tray" else ("+X",)
    rings = []
    for side in sides:
        sg = 1 if side == "+X" else -1
        lo, hi = sorted((sg * iface.HALF_W, sg * s["x_in"]))
        for y, z in iface.SIDE_M4_YZ:
            ring = (_cyl("X", (y, z), v["od"], lo, hi)
                    .cut(_cyl("X", (y, z), v["id"], lo - 1, hi + 1)))
            rings.append(ring.val())
    return cq.Workplane(obj=cq.Compound.makeCompound(rings))


def spacers_bulkhead(params: dict | None = None) -> cq.Workplane:
    return create_spacers(params, "bulkhead_shelf")


def spacers_deck(params: dict | None = None) -> cq.Workplane:
    return create_spacers(params, "deck_tray")


# ---------------------------------------------------------------------------
# The unit and its keep-outs, as builders for spec.json's fit block
# ---------------------------------------------------------------------------
def create_nsp1600(params: dict | None = None) -> cq.Workplane:
    """The vendor solid in the mount frame (translation only)."""
    return iface.nsp1600_unit()


def keepout_fan_exhaust(params: dict | None = None) -> cq.Workplane:
    return iface.keepout_solid("fan_exhaust")


def keepout_terminal_face(params: dict | None = None) -> cq.Workplane:
    return iface.keepout_solid("terminal_face")


def keepout_led_svr(params: dict | None = None) -> cq.Workplane:
    return iface.keepout_solid("led_svr_access")


def lug_envelope_long(params: dict | None = None) -> cq.Workplane:
    return iface.keepout_solid("lug_long")


def lug_envelope_short(params: dict | None = None) -> cq.Workplane:
    return iface.keepout_solid("lug_short")


def ac_cable_envelope(params: dict | None = None) -> cq.Workplane:
    return iface.keepout_solid("ac_cable")


# ---------------------------------------------------------------------------
# v2 - side_tab: the vendor's pattern, one small L per M4
# ---------------------------------------------------------------------------
def tab_stations(p: dict) -> dict:
    """Every station of the tab's section, derived from the sheet and the unit."""
    d = p["dimensions"]
    t, ri = d["sheet_t"], d["bend_radius_inside"]
    return {
        "t": t, "ri": ri, "orr": ri + t,
        "leg_in": iface.HALF_W,             # 42.5  flush on the unit's side wall
        "leg_out": iface.HALF_W + t,        # 45.5
        "foot_tan": iface.HALF_W + t + ri,  # 48.5  the foot's flat starts here
        "leg_tan": ri + t,                  # 6.0   the leg's flat starts here (Z)
    }


def create_side_tab(params: dict | None = None) -> cq.Workplane:
    """
    One L-tab in its own frame: on the +X side, centred on its M4 station (Y = 0).

    The foot bends OUTWARD, away from the unit. So the bend's fillet lives in
    X 42.5..48.5, Z 0..6 - outside the unit's corner - and the leg's inner face
    is flat against the side wall from Z = 6 to the top. No gap, no spacer.
    The same tab serves both sides (an L is its own mirror image) and both
    stations.
    """
    p = params or load_params()
    v = _var(p, "side_tab")
    s = tab_stations(p)
    t, w, h = s["t"], v["width"], v["leg_h"]
    foot_end = s["leg_out"] + v["foot_len"]

    leg = _box(s["leg_in"], s["leg_out"], -w / 2, w / 2, s["leg_tan"], h)
    top = cq.selectors.BoxSelector((s["leg_in"] - 1, -w, h - 0.5), (s["leg_out"] + 1, w, h + 0.5))
    leg = leg.edges("|X").edges(top).fillet(v["top_r"])
    foot = _box(s["foot_tan"], foot_end, -w / 2, w / 2, 0.0, t)
    tip = cq.selectors.BoxSelector((foot_end - 0.5, -w, -1), (foot_end + 0.5, w, t + 1))
    foot = foot.edges("|Z").edges(tip).fillet(v["foot_r"])
    bend = _quadrant(s["foot_tan"], s["leg_tan"], s["ri"], s["orr"], -1, -1, -w / 2, w / 2)
    tab = fuse(leg, bend, "tab bend")
    tab = fuse(tab, foot, "tab foot")

    f = p["fasteners"]["side_m4_tab"]
    screw_len = float(f["screw"].split("x")[1].split()[0])
    iface.check_side_screw(screw_len, f["grip"])
    tab = tab.cut(_cyl("X", (0.0, iface.SIDE_M4_YZ[0][1]), f["clearance_d"],
                       s["leg_in"] - 1, s["leg_out"] + 1))
    hf = p["fasteners"]["tab_to_host"]
    tab = tab.cut(_slot(v["slot_x"], 0.0, hf["slot_len"], hf["clearance_d"], 0, -1, t + 1))
    return tab


def place_tabs(params: dict | None = None, kit: str = "deck_tab_kit") -> cq.Workplane:
    """The tabs of a kit on their stations, as one compound."""
    p = params or load_params()
    tab = create_side_tab(p)
    solids = []
    for y, _ in iface.SIDE_M4_YZ:
        for side in _var(p, "side_tab")["sides"][kit]:
            one = tab.mirror("YZ") if side == "-X" else tab
            solids.append(one.translate((0, y, 0)).val())
    return cq.Workplane(obj=cq.Compound.makeCompound(solids))


def tabs_deck(params: dict | None = None) -> cq.Workplane:
    return place_tabs(params, "deck_tab_kit")


def tabs_bulkhead(params: dict | None = None) -> cq.Workplane:
    return place_tabs(params, "bulkhead_strap_kit")


# ---------------------------------------------------------------------------
# v2 - bulkhead_strap: the smallest shelf that holds the unit off a wall
# ---------------------------------------------------------------------------
def strap_stations(p: dict) -> list[float]:
    """Mount-frame Y of each strap's centre: 5.8 mm +Y of its M4 station."""
    off = _var(p, "bulkhead_strap")["station_offset_y"]
    return [y + off for y, _ in iface.SIDE_M4_YZ]


def create_bulkhead_strap(params: dict | None = None) -> cq.Workplane:
    """
    One strap in its own frame, centred at Y = 0; its M4 station is at Y = -5.8.

    Shelf on top (Z -3..0), flange DOWN the bulkhead (X -48.5..-45.5). The bend's
    outer arc is tangent to the shelf top at X = -42.5, the unit's corner, so the
    unit bears on the whole 45 x 85 of shelf. Holes: two M5 down the flange, the
    tab's M5 at the shelf tip, two M3 taps for the box.
    """
    p = params or load_params()
    v = _var(p, "bulkhead_strap")
    s = channel_stations(p)
    t, ri, orr, cr = s["t"], s["ri"], s["orr"], p["dimensions"]["corner_r"]
    w = v["width"]
    y0, y1 = -w / 2, w / 2
    x_bulk, x_fl_in, x_tan = -s["x_out"], -s["x_in"], -s["x_tan"]   # -48.5, -45.5, -42.5
    z_tan = -t - ri                                                 # -6.0
    z_bot = -v["flange_depth"]

    shelf = _box(x_tan, v["shelf_x_tip"], y0, y1, -t, 0.0)
    tip = cq.selectors.BoxSelector((v["shelf_x_tip"] - 0.5, -w, -t - 1),
                                   (v["shelf_x_tip"] + 0.5, w, 1))
    shelf = shelf.edges("|Z").edges(tip).fillet(cr)
    flange = _box(x_bulk, x_fl_in, y0, y1, z_bot, z_tan)
    bottom = cq.selectors.BoxSelector((x_bulk - 1, -w, z_bot - 0.5), (x_fl_in + 1, w, z_bot + 0.5))
    flange = flange.edges("|X").edges(bottom).fillet(cr)
    bend = _quadrant(x_tan, z_tan, ri, orr, -1, +1, y0, y1)
    strap = fuse(shelf, bend, "strap bend")
    strap = fuse(strap, flange, "strap flange")

    bf = p["fasteners"]["strap_to_bulkhead"]
    for z in v["bolt_z"]:
        strap = strap.cut(_cyl("X", (0.0, z), bf["clearance_d"], x_bulk - 1, x_fl_in + 1))
    hf = p["fasteners"]["tab_to_host"]
    strap = strap.cut(_cyl("Z", (v["tab_bolt_x"], -v["station_offset_y"]), hf["clearance_d"],
                           -t - 1, 1))
    td = p["fasteners"]["box_m3"]["tap_drill"]
    for x, y in v["box_tap_xy"]:
        strap = strap.cut(_cyl("Z", (x, y), td, -t - 1, 1))
    return strap


def straps_bulkhead(params: dict | None = None) -> cq.Workplane:
    """Both straps on their stations, as one compound."""
    p = params or load_params()
    strap = create_bulkhead_strap(p)
    solids = [strap.translate((0, y, 0)).val() for y in strap_stations(p)]
    return cq.Workplane(obj=cq.Compound.makeCompound(solids))


# ---------------------------------------------------------------------------
# v2 - terminal_box: the hood with a floor and closed exits
# ---------------------------------------------------------------------------
def box_cavity(params: dict | None = None) -> cq.Workplane:
    """The volume the box encloses, from the terminal plate to its far wall."""
    p = params or load_params()
    v = _var(p, "terminal_box")
    wt, tt, ft = v["wall_t"], v["top_t"], v["floor_t"]
    return _box(v["x"][0] + wt, v["x"][1] - wt, iface.TERMINAL_FACE_Y, v["y"][1] - wt,
                ft, v["z_top"] - tt)


def create_terminal_box(params: dict | None = None) -> cq.Workplane:
    """
    Five walls, open toward the unit. Floor on the host (or the terminal
    strap), grommet holes and a harness slot in the far wall, LED / trim-pot
    window, louvres, and two ears past the far wall for a bulkhead.
    """
    p = params or load_params()
    v = _var(p, "terminal_box")
    wt, tt, ft = v["wall_t"], v["top_t"], v["floor_t"]
    x0, x1 = v["x"]
    y0, y1 = v["y"]
    zt = v["z_top"]

    outer = _box(x0, x1, y0, y1, 0.0, zt)
    far_corners = cq.selectors.BoxSelector((x0 - 1, y1 - 1, -1), (x1 + 1, y1 + 1, zt + 1))
    outer = outer.edges("|Z").edges(far_corners).fillet(v["corner_r"])
    outer = outer.faces(">Z").edges().fillet(v["top_r"])
    cav = _box(x0 + wt, x1 - wt, y0 - 5.0, y1 - wt, ft, zt - tt)
    far_inner = cq.selectors.BoxSelector((x0, y1 - wt - 1, ft - 1), (x1, y1 - wt + 1, zt + 1))
    cav = cav.edges("|Z").edges(far_inner).fillet(v["corner_r"] - wt)
    box = outer.cut(cav)

    for x, y in v["floor_screws_xy"]:
        box = box.cut(_cyl("Z", (x, y), p["fasteners"]["box_m3"]["clearance_d"], -1, ft + 1))

    for e in v["exits"].values():
        if "d" in e:
            box = box.cut(_cyl("Y", (e["xz"][0], e["xz"][1]), e["d"], y1 - wt - 1, y1 + 1))
        else:
            box = box.cut(_box(e["x"][0], e["x"][1], y1 - wt - 1, y1 + 1, e["z"][0], e["z"][1]))
    lw = v["led_window"]
    box = box.cut(_box(lw["x"][0], lw["x"][1], y1 - wt - 1, y1 + 1, lw["z"][0], lw["z"][1]))

    tl = v["top_louvres"]
    ly = (tl["y"][0] + tl["y"][1]) / 2
    for x in tl["x"]:
        box = box.cut(_slot(x, ly, tl["y"][1] - tl["y"][0], tl["w"], 90, zt - tt - 1, zt + 1))
    sl = v["side_louvres"]
    sy = (sl["y"][0] + sl["y"][1]) / 2
    for z in sl["z"]:
        cutter = (cq.Workplane("YZ").center(sy, z)
                  .slot2D(sl["y"][1] - sl["y"][0], sl["w"], angle=0).extrude(wt + 2))
        box = box.cut(cutter.translate((x0 - 1, 0, 0)))
        box = box.cut(cutter.translate((x1 - wt - 1, 0, 0)))

    # bulkhead ears: past the far wall, on the -X side, reaching the bulkhead plane
    x_bulk = -channel_stations(p)["x_out"]
    ey0, ey1 = v["ears"]["y"]
    ef = p["fasteners"]["box_ears"]
    for (z0, z1), (hy, hz) in zip(v["ears"]["z"], v["ears"]["hole_yz"]):
        box = fuse(box, _box(x_bulk, x0 + 0.01, ey0, ey1, z0, z1), "box ear")
        box = box.cut(_cyl("X", (hy, hz), ef["clearance_d"], x_bulk - 1, x0 + 1))
    return box


# ---------------------------------------------------------------------------
# Entry points the pipeline expects
# ---------------------------------------------------------------------------
BUILDERS = {
    "side_tab": create_side_tab,
    "bulkhead_strap": create_bulkhead_strap,
    "terminal_box": create_terminal_box,
    "bulkhead_shelf": create_bulkhead_shelf,
    "deck_tray": create_deck_tray,
    "busbar_hood": create_busbar_hood,
    "spacer_ring": create_spacer_ring,
}


def create_part(params: dict | None = None) -> cq.Workplane:
    """The default variant - what lib.evaluate gates and make export-all writes."""
    p = params or load_params()
    return BUILDERS[p.get("default_variant", "side_tab")](p)


def kit_solids(params: dict | None = None, kit: str = "deck_tab_kit") -> list[tuple]:
    """(name, workplane) for every fabricated piece of a kit, placed in the mount frame."""
    p = params or load_params()
    if kit == "deck_tab_kit":
        return [("tabs", tabs_deck(p)), ("terminal_box", create_terminal_box(p))]
    if kit == "bulkhead_strap_kit":
        return [("straps", straps_bulkhead(p)), ("tabs", tabs_bulkhead(p)),
                ("terminal_box", create_terminal_box(p))]
    if kit == "deck_tray_kit":
        return [("deck_tray", create_deck_tray(p)), ("spacers", spacers_deck(p)),
                ("busbar_hood", create_busbar_hood(p))]
    if kit == "bulkhead_shelf_kit":
        return [("bulkhead_shelf", create_bulkhead_shelf(p)), ("spacers", spacers_bulkhead(p)),
                ("busbar_hood", create_busbar_hood(p))]
    raise ValueError(f"unknown kit {kit!r} (one of {KITS})")


def create_assembly(params: dict | None = None, kit: str = "deck_tab_kit",
                    with_unit: bool = True) -> cq.Assembly:
    """A kit with the unit in it, for renders."""
    p = params or load_params()
    asm = cq.Assembly()
    for name, wp in kit_solids(p, kit):
        rgb = (0.22, 0.22, 0.24) if name in ("terminal_box", "busbar_hood") else (0.18, 0.19, 0.21)
        asm.add(wp, name=name, color=cq.Color(*rgb))
    if with_unit:
        asm.add(iface.nsp1600_unit(), name="nsp1600", color=cq.Color(0.60, 0.60, 0.62))
    return asm


def build_stages(params: dict | None = None):
    """Stage-by-stage build of the default variant (the tab) for lib.debug_build."""
    p = params or load_params()
    v = _var(p, "side_tab")
    s = tab_stations(p)
    w, h = v["width"], v["leg_h"]
    leg = _box(s["leg_in"], s["leg_out"], -w / 2, w / 2, s["leg_tan"], h)
    yield "leg", leg
    bend = _quadrant(s["foot_tan"], s["leg_tan"], s["ri"], s["orr"], -1, -1, -w / 2, w / 2)
    tab = fuse(leg, bend, "tab bend")
    yield "leg_and_bend", tab
    tab = fuse(tab, _box(s["foot_tan"], s["leg_out"] + v["foot_len"], -w / 2, w / 2, 0.0, s["t"]),
               "tab foot")
    yield "leg_bend_foot", tab
    yield "complete", create_side_tab(p)


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
MAX_WIN_PATH = 258


def _warn_long_path(path: Path) -> None:
    """SolidWorks still uses the legacy Win32 API - a 259-char path is unopenable."""
    n = len(str(path.resolve()))
    if n > MAX_WIN_PATH:
        print(f"  !! {n} characters - SolidWorks will refuse this file. "
              "Re-run with --out C:/some/short/dir")


def export_design(params: dict | None = None, out_dir: Path | None = None,
                  stl: bool = False) -> list[Path]:
    """Every variant as STEP (short names), the default again under the part name,
    and the hood as STL for the printer."""
    p = params or load_params()
    out = Path(out_dir) if out_dir else EXPORTS_DIR
    out.mkdir(parents=True, exist_ok=True)
    ver = p.get("version", "v1")
    default = p.get("default_variant", "side_tab")
    written = []
    for name, builder in BUILDERS.items():
        solid = builder(p)
        path = out / f"nsp_mnt_{ver}_{name}.step"
        _warn_long_path(path)
        cq.exporters.export(solid, str(path))
        written.append(path)
        print(f"  ok {path.name:<36} {solid.val().Volume() / 1000:8.1f} cm^3"
              + ("   <- default" if name == default else ""))
        if name == default:
            canon = out / f"{PART_NAME}_{ver}.step"
            _warn_long_path(canon)
            cq.exporters.export(solid, str(canon))
            written.append(canon)
        if name in ("busbar_hood", "terminal_box") or stl:
            stl_path = out / f"nsp_mnt_{ver}_{name}.stl"
            cq.exporters.export(solid, str(stl_path), tolerance=0.02, angularTolerance=0.1)
            written.append(stl_path)
    return written


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", help="export directory (use a short path for SolidWorks)")
    ap.add_argument("--stl", action="store_true", help="also write STL for every variant")
    ap.add_argument("--variant", choices=VARIANT_NAMES, help="build just one variant")
    ap.add_argument("--show", action="store_true", help="push the assembly to the OCP CAD Viewer")
    args = ap.parse_args()

    params = load_params()
    print(f"\n  {params['part_name']} ({params.get('version', 'v1')})")
    print(f"  {iface.ATTITUDE_NOTE.split('.')[0]}.")
    print(f"  Design load: {iface.MASS_KG} kg x {iface.DESIGN_SHOCK_G} g = "
          f"{iface.DESIGN_LOAD_N:.0f} N\n")

    if args.variant:
        solid = BUILDERS[args.variant](params)
        out = Path(args.out) if args.out else EXPORTS_DIR
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"nsp_mnt_{params.get('version', 'v1')}_{args.variant}.step"
        _warn_long_path(path)
        cq.exporters.export(solid, str(path))
        print(f"  ok {path}")
    else:
        export_design(params, args.out, args.stl)

    if args.show:
        try:
            from ocp_vscode import show

            show(create_assembly(params, "deck_tab_kit"))
        except Exception as exc:
            print(f"  (OCP CAD Viewer unavailable: {exc})")
