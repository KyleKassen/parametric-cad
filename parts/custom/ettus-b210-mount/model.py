"""
Ettus USRP B210 mount family
============================
Three mounts for one radio, built in one shared frame.

    flat_plate     unit lying flat, bolted through its four M3 bores to a
                   plate that is also its heat spreader.  The default.
    edge_bracket   unit on edge, bolted to a vertical web with one folded
                   flange to the panel.  Trades enclosure depth for panel area.
    clamp_cradle   unit lying flat, located by its OWN four rubber feet
                   dropping into pockets and held by two folded bridges.
                   Touches none of the four M3 bores.

THE MOUNT FRAME
---------------
Origin is the centre of the unit's four-hole pattern, on the plane its bottom
pan seats against.  +Y points at the RF front panel, +Z points up out of the
pan into the body, +X completes a right-handed set.

In this frame the hole pattern is symmetric about BOTH axes — the four bores
sit at (+/-46.7995, +/-60.0075) — and the only asymmetry left in the whole
problem is where the body sits relative to them: 82.3115 mm of overhang toward
the front, 76.2055 toward the rear.  Every trap in this part reduces to that
one number, and it is written down once, in params.json.

Getting there from the vendor STEP's own frame is a PROPER ROTATION: +90 about
X, then 180 about Z, then translate by (58.5005, 80.6355, 1.210).  The
obvious-looking map (x, z, y) is a REFLECTION — using it would have silently
mirrored the vendor solid in every fit check.

BEND MODELLING
--------------
Folded parts are built as flat legs plus explicit annular bend quadrants, not
as unions with late fillets.  Every bend runs at an inside radius of one
thickness (R4 on the 4 mm bracket, R3 on the 3 mm bridges), so the STEP carries
the same bend the brake will actually make — and flat_pattern() develops the
blank from those same two numbers, so the blank cannot disagree with the part.

Units: mm.
"""

import json
import math
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"

# Derived from the directory name on purpose: lib.export and lib.evaluate both
# name a part's accepted artifact "<part_dir.name>_<version>.step", so taking
# it from the same place means the CLI's canonical export cannot drift from
# theirs if the folder is ever renamed.
PART_NAME = PART_DIR.name

VARIANTS = ("flat_plate", "edge_bracket", "clamp_cradle")
K_FACTOR = 0.42          # 5052-H32 at inside radius = 1t


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
def load_params(path: Path = PARAMS_FILE) -> dict:
    """Load the part's engineering brief."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _iface(params: dict) -> dict:
    return params["b210_interface"]


def _var(params: dict, name: str) -> dict:
    return params["variants"][name]


# ---------------------------------------------------------------------------
# Sheet-metal arithmetic
# ---------------------------------------------------------------------------
def bend_allowance(ir: float, t: float, k: float = K_FACTOR) -> float:
    """Arc length of a 90-degree bend along the neutral axis."""
    return (math.pi / 2) * (ir + k * t)


def bend_deduction(ir: float, t: float, k: float = K_FACTOR) -> float:
    """
    Subtract one of these per bend from the sum of the OUTSIDE leg lengths to
    get the flat blank length.
    """
    return 2 * (ir + t) - bend_allowance(ir, t, k)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def _rounded_plate(width: float, length: float, thickness: float,
                   radius: float, corners: str = "all") -> cq.Workplane:
    """
    A flat plate centred on the origin in X and Y, occupying z in
    [-thickness, 0], with its plan corners radiused.

    Radii go into the base solid before any boolean work — the repo's rule for
    keeping the kernel happy (DESIGN_LANGUAGE.md).

    corners="all" rounds all four.  corners="+x" rounds only the two at +X,
    which is what a folded leg wants: the corners on the bend line stay square
    because the material carries on around the bend.
    """
    plate = cq.Workplane("XY").box(width, length, thickness,
                                   centered=(True, True, False))
    plate = plate.translate((0, 0, -thickness))
    if radius <= 0:
        return plate
    if corners == "all":
        return plate.edges("|Z").fillet(radius)
    sel = cq.selectors.BoxSelector(
        (width / 2 - 0.5, -length, -thickness - 1),
        (width / 2 + 0.5, length, 1),
    )
    return plate.edges("|Z").edges(sel).fillet(radius)


def _slot(length: float, width: float, thickness: float, angle: float) -> cq.Workplane:
    """A rounded-end slot cutter, centred on the origin, tall enough to cut through."""
    return (
        cq.Workplane("XY")
        .slot2D(length, width, angle=angle)
        .extrude(thickness + 2)
        .translate((0, 0, -thickness - 1))
    )


def _slot_pocket(length: float, width: float, depth: float,
                 angle: float, z_bottom: float) -> cq.Workplane:
    """A slot-shaped counterbore, cut upward from z_bottom by `depth`."""
    return (
        cq.Workplane("XY")
        .slot2D(length, width, angle=angle)
        .extrude(depth + 1)
        .translate((0, 0, z_bottom - 1))
    )


def _bend_quadrant(cx: float, cz: float, ir: float, orr: float,
                   sx: int, sz: int, y0: float, y1: float) -> cq.Workplane:
    """
    One 90-degree bend: the annular quadrant between radii `ir` and `orr`
    about (cx, cz), taken in the quadrant that lies `sx` in X and `sz` in Z
    from the centre, extruded along Y from y0 to y1.

    Building the bend explicitly, rather than filleting a union, is what keeps
    these parts off the kernel's failure list — and it means the modelled bend
    is the bend the brake makes, not an approximation of it.
    """
    ylen = y1 - y0
    outer = (cq.Workplane("XZ").center(cx, cz).circle(orr)
             .extrude(ylen).translate((0, y1, 0)))
    inner = (cq.Workplane("XZ").center(cx, cz).circle(ir)
             .extrude(ylen).translate((0, y1, 0)))
    quad = (cq.Workplane("XY")
            .box(orr, ylen, orr, centered=(False, False, False))
            .translate((cx if sx > 0 else cx - orr, y0,
                        cz if sz > 0 else cz - orr)))
    return outer.cut(inner).intersect(quad)


def _drill(solid: cq.Workplane, points: list, diameter: float,
           z_top: float, depth: float) -> cq.Workplane:
    """Cut plain vertical holes at (x, y) points. No workplane gymnastics."""
    cutter = cq.Workplane("XY").circle(diameter / 2).extrude(depth + 2)
    for x, y in points:
        solid = solid.cut(cutter.translate((x, y, z_top - depth - 1)))
    return solid


def _countersink(hole_dia: float, head_dia: float, angle_deg: float,
                 z_bottom: float) -> cq.Workplane:
    """
    A countersink cutter opening downward from z_bottom: `head_dia` at the
    face, closing to `hole_dia` at the cone's top.
    """
    depth = (head_dia - hole_dia) / (2 * math.tan(math.radians(angle_deg / 2)))
    cone = (cq.Workplane("XY")
            .circle(head_dia / 2).workplane(offset=depth).circle(hole_dia / 2)
            .loft())
    # a short skirt below the face so the cut is clean through the surface
    skirt = cq.Workplane("XY").circle(head_dia / 2).extrude(-1.0)
    return (cone.union(skirt)).translate((0, 0, z_bottom))


def _m3_holes(solid: cq.Workplane, params: dict, variant: dict,
              thickness: float, positions: list) -> cq.Workplane:
    """
    The four M3 clearance holes, relieved from the UNDERSIDE so the head never
    stands proud of the face that mates to the panel.

    The radio allows only 3.575 mm of screw travel past its pan before the tip
    meets the internal PCB screw, so engagement is pinned at 3.0 mm and the
    relief is what absorbs plate thickness:

      countersunk  head sits fully in the cone, so
                   engagement = screw length - plate thickness
      socket       counterbore until exactly `screw_grip` of material is left
                   under the head, so engagement = screw length - screw_grip

    Either way the same M3x6 works, whatever the plate is.
    """
    clearance = variant["m3_clearance"]
    solid = _drill(solid, positions, clearance, 0.0, thickness)

    if variant.get("m3_head") == "countersunk":
        csk = _countersink(clearance, variant["m3_countersink_diameter"],
                           variant["m3_countersink_angle"], -thickness)
        for x, y in positions:
            solid = solid.cut(csk.translate((x, y, 0)))
        return solid

    grip = _iface(params)["screw_grip"]["value"]
    cbore_depth = round(thickness - grip, 4)
    if cbore_depth > 0.01:
        cutter = (cq.Workplane("XY")
                  .circle(variant["m3_counterbore_diameter"] / 2)
                  .extrude(cbore_depth + 1))
        for x, y in positions:
            solid = solid.cut(cutter.translate((x, y, -thickness - 1)))
    return solid


# ---------------------------------------------------------------------------
# Variant 1 — flat conduction plate
# ---------------------------------------------------------------------------
def create_flat_plate(params: dict | None = None) -> cq.Workplane:
    """
    Unit lying flat, bolted down through its four M3 bores.

    The plate is symmetric about both axes on purpose.  The hole pattern
    already is; only the body is offset.  Sizing the plate to the LONGER
    overhang costs 6.1 mm of length and buys a plate that cannot be fitted
    backwards — rotate the radio 180 degrees and all four bores still line up,
    so the integrator picks which end meets the cable entry.
    """
    if params is None:
        params = load_params()
    v = _var(params, "flat_plate")
    t = v["thickness"]

    plate = _rounded_plate(2 * v["half_width"], 2 * v["half_length"], t,
                           v["corner_radius"])
    plate = _m3_holes(plate, params, v, t,
                      _iface(params)["mount_holes"]["positions_xy"])

    # Panel bolts, outboard of the radio so a driver still reaches them with
    # the unit fitted.  The four M3s underneath are a bench operation.
    panel_pts = [(sx * v["panel_hole_x"], y)
                 for sx in (-1, 1) for y in v["panel_hole_y"]]
    plate = _drill(plate, panel_pts, v["panel_hole_diameter"], 0.0, t)

    # Cable-tie slots, so the pigtails are anchored to the plate and the
    # connectors never take a pull.
    ts = v["tie_slot"]
    for sx in (-1, 1):
        for y in ts["y"]:
            plate = plate.cut(
                _slot(ts["length_x"], ts["width_y"], t, 0)
                .translate((sx * ts["x"], y, 0))
            )
    return plate


# ---------------------------------------------------------------------------
# Variant 2 — on-edge folded bracket
# ---------------------------------------------------------------------------
def create_edge_bracket(params: dict | None = None) -> cq.Workplane:
    """
    Unit on edge: bottom pan bolted to a vertical web, one folded flange to
    the panel.

    Two dimensions here are not free choices and both are worth reading.

    * The bend line sits at x = -72, not hard against the radio at -61.17.
      That 10.8 mm of standoff keeps the flange outside the 10 mm keep-out on
      the rear vent slot, which is why this part needs no relief notch and has
      no handedness.
    * The part runs 206 mm against a 158.5 mm radio.  The extra length puts
      four flange bolts BEYOND both ends of the unit, where a driver reaches
      them along the door axis with the radio fitted.  Everything else on this
      bracket is a bench operation.
    """
    if params is None:
        params = load_params()
    v = _var(params, "edge_bracket")
    t = v["thickness"]
    ir = v["bend_inside_radius"]
    orr = ir + t
    x_bend, x_free = v["web_x"]                # -72 (bend line), +63 (free edge)
    half_l = v["half_length"]
    fw = v["flange_width"]

    web_x0 = x_bend + ir                       # -69, inner bend tangent
    flange_z0 = ir                             # +3, outer bend tangent
    flange_z1 = -t + fw                        # +29, flange tip
    cx, cz = web_x0, flange_z0                 # both arcs share this centre

    # --- web: flat leg, plan radii on the free end only -------------------
    web = _rounded_plate(x_free - web_x0, 2 * half_l, t,
                         v["corner_radius"], corners="+x")
    web = web.translate(((web_x0 + x_free) / 2, 0, 0))

    # --- flange: vertical leg, plan radii on its tip only -----------------
    flange = cq.Workplane("XY").box(t, 2 * half_l, flange_z1 - flange_z0,
                                    centered=(True, True, False))
    flange = flange.translate((x_bend - t / 2, 0, flange_z0))
    sel = cq.selectors.BoxSelector(
        (x_bend - t - 1, -half_l - 1, flange_z1 - 0.5),
        (x_bend + 1, half_l + 1, flange_z1 + 0.5),
    )
    flange = flange.edges("|X").edges(sel).fillet(v["corner_radius"])

    bend = _bend_quadrant(cx, cz, ir, orr, -1, -1, -half_l, half_l)
    bracket = web.union(bend).union(flange)

    # --- the four M3 through the web --------------------------------------
    # Two round, two slotted along the bend direction.  A press brake places
    # the bend line to about +/-0.5 mm relative to the holes; the slots absorb
    # that instead of arguing with it on the bench.
    holes = _iface(params)["mount_holes"]["positions_xy"]
    round_holes = [p for p in holes if p[0] < 0]
    slot_holes = [p for p in holes if p[0] > 0]
    slot_len = v["m3_clearance"] + v["m3_slot_travel"]

    bracket = _drill(bracket, round_holes, v["m3_clearance"], 0.0, t)
    for x, y in slot_holes:
        bracket = bracket.cut(
            _slot(slot_len, v["m3_clearance"], t, 0).translate((x, y, 0)))

    # A 4 mm web would eat the thread engagement, since the radio caps total
    # screw travel at 3.575 mm.  Counterboring from the underside puts exactly
    # `screw_grip` of material under the head and keeps the same M3x6.
    cb_depth = round(t - _iface(params)["screw_grip"]["value"], 4)
    if cb_depth > 0.01:
        cb = v["m3_counterbore_diameter"]
        cutter = cq.Workplane("XY").circle(cb / 2).extrude(cb_depth + 1)
        for x, y in round_holes:
            bracket = bracket.cut(cutter.translate((x, y, -t - 1)))
        for x, y in slot_holes:
            bracket = bracket.cut(
                _slot_pocket(slot_len - v["m3_clearance"] + cb, cb, cb_depth,
                             0, -t).translate((x, y, 0)))

    # --- flange bolts ------------------------------------------------------
    cutter = (cq.Workplane("YZ").circle(v["flange_hole_diameter"] / 2)
              .extrude(t + 4))
    for y in v["flange_hole_y"]:
        for z in v["flange_hole_z"]:
            bracket = bracket.cut(cutter.translate((x_bend - t - 2, y, z)))

    # --- cable-tie slots down the web's free edge --------------------------
    ts = v["tie_slot"]
    for y in ts["y"]:
        bracket = bracket.cut(
            _slot(ts["length_y"], ts["width_x"], t, 90).translate((ts["x"], y, 0))
        )
    return bracket


# ---------------------------------------------------------------------------
# Variant 3 — no-drill clamp cradle
# ---------------------------------------------------------------------------
def create_cradle_tray(params: dict | None = None) -> cq.Workplane:
    """
    The cradle's tray.

    The four rubber feet are the locating feature, not an obstruction.
    Ø13.5 pockets in a 4 mm tray swallow the Ø12.7 x 3.556 feet whole, the pan
    seats flat on the tray, and the radio is positively located in X and Y
    without a single hole being put in it.
    """
    if params is None:
        params = load_params()
    v = _var(params, "clamp_cradle")
    t = v["tray_thickness"]

    tray = _rounded_plate(2 * v["tray_half_width"], 2 * v["tray_half_length"], t,
                          v["corner_radius"])
    tray = _drill(tray, _iface(params)["mount_holes"]["positions_xy"],
                  v["foot_pocket_diameter"], 0.0, t)

    panel_pts = [(sx * v["panel_hole_x"], y)
                 for sx in (-1, 1) for y in v["panel_hole_y"]]
    tray = _drill(tray, panel_pts, v["panel_hole_diameter"], 0.0, t)

    # Tapped M4 for the two bridges, modelled at tap-drill size.
    tap_pts = [(sx * v["bridge_bolt_x"], y)
               for sx in (-1, 1) for y in v["bridge_y"]]
    tray = _drill(tray, tap_pts, v["bridge_tap_drill"], 0.0, t)
    return tray


def _bridge_stations(params: dict) -> dict:
    """Every X/Z station on the bridge's folded section, derived once."""
    v = _var(params, "clamp_cradle")
    t = v["bridge_thickness"]
    ir = v["bend_inside_radius"]
    orr = ir + t
    near = v["bridge_leg_x"]                       # 72.5  leg face nearest radio
    far = near + t                                 # 75.5  leg's other face
    beam_hi = _iface(params)["top_cover_z"] + v["pad_thickness"] + t   # 39.7
    beam_lo = beam_hi - t                          # 36.7
    return {
        "t": t, "ir": ir, "orr": orr, "w": v["bridge_width"],
        "near": near, "far": far,
        "beam_hi": beam_hi, "beam_lo": beam_lo,
        "foot_tan": near + orr,                    # 78.5  foot flat starts here
        "foot_end": near + orr + v["bridge_foot_flat"],   # 91.5
        "beam_tan": far - orr,                     # 69.5  beam flat ends here
        "leg_z0": orr,                             # 6.0
        "leg_z1": beam_hi - orr,                   # 33.7
        "bolt_x": v["bridge_bolt_x"],
        "hole": v["bridge_hole_diameter"],
    }


def create_cradle_bridge(params: dict | None = None) -> cq.Workplane:
    """
    One hold-down bridge: a folded channel that steps over the radio and bolts
    into the tray on both sides.  Built at y = 0; create_clamp_cradle() places
    the pair.

    The legs stand at x = +/-72.5, which is 11.33 mm clear of the side walls.
    That is what lets a bridge sit anywhere along the unit even though one of
    them passes directly over a vent slot — and it is asserted in spec.json
    rather than trusted.
    """
    if params is None:
        params = load_params()
    s = _bridge_stations(params)
    t, w = s["t"], s["w"]
    y0, y1 = -w / 2, w / 2

    def _box(x0, x1, z0, z1):
        return (cq.Workplane("XY")
                .box(x1 - x0, w, z1 - z0, centered=(False, True, False))
                .translate((x0, 0, z0)))

    # beam across the top
    part = _box(-s["beam_tan"], s["beam_tan"], s["beam_lo"], s["beam_hi"])

    for sx in (-1, 1):
        # vertical leg
        lo, hi = sorted((sx * s["near"], sx * s["far"]))
        part = part.union(_box(lo, hi, s["leg_z0"], s["leg_z1"]))
        # foot flat on the tray
        f0, f1 = sorted((sx * s["foot_tan"], sx * s["foot_end"]))
        part = part.union(_box(f0, f1, 0.0, t))
        # bend at the foot: outer arc tangent to z=0 and to the leg's near face
        part = part.union(
            _bend_quadrant(sx * s["foot_tan"], s["orr"], s["ir"], s["orr"],
                           -sx, -1, y0, y1))
        # bend at the beam: outer arc tangent to the leg's far face and z=beam_hi
        part = part.union(
            _bend_quadrant(sx * s["beam_tan"], s["leg_z1"], s["ir"], s["orr"],
                           sx, 1, y0, y1))

    # foot bolt holes
    cutter = cq.Workplane("XY").circle(s["hole"] / 2).extrude(t + 4)
    for sx in (-1, 1):
        part = part.cut(cutter.translate((sx * s["bolt_x"], 0, -2)))
    return part


def create_clamp_cradle(params: dict | None = None) -> cq.Workplane:
    """Tray plus both bridges — three solids in one compound."""
    if params is None:
        params = load_params()
    v = _var(params, "clamp_cradle")
    bridge = create_cradle_bridge(params)
    solids = [create_cradle_tray(params).val()]
    solids += [bridge.translate((0, y, 0)).val() for y in v["bridge_y"]]
    return cq.Workplane(obj=cq.Compound.makeCompound(solids))


# ---------------------------------------------------------------------------
# The radio, and the volumes it forbids
# ---------------------------------------------------------------------------
def b210_transform() -> list:
    """The vendor STEP's frame -> the mount frame, as lib.fit transform steps."""
    return [
        {"rotate": {"axis": "X", "angle": 90}},
        {"rotate": {"axis": "Z", "angle": 180}},
        {"translate": [58.5005, 80.6355, 1.210]},
    ]


def create_b210(params: dict | None = None) -> cq.Workplane:
    """The vendor solid placed in the mount frame — for renders and fit checks."""
    if params is None:
        params = load_params()
    path = PROJECT_ROOT / _iface(params)["source_step"]
    wp = cq.importers.importStep(str(path))
    wp = wp.rotate((0, 0, 0), (1, 0, 0), 90)
    wp = wp.rotate((0, 0, 0), (0, 0, 1), 180)
    return wp.translate((58.5005, 80.6355, 1.210))


def create_keepouts(params: dict | None = None) -> cq.Workplane:
    """
    Every volume a mount solid is forbidden to enter, as one compound.

    Connector reach and cable bend, LED sight lines, driver swing for the
    eight case screws, and 10 mm around each of the two side vent slots.
    Asserted case-by-case in spec.json, so a bracket that fouls one fails the
    gate instead of failing on the bench.
    """
    if params is None:
        params = load_params()
    boxes = []
    for name, k in _iface(params)["connector_keepouts"].items():
        if name.startswith("_"):
            continue
        x0, x1 = k["x"]
        y0, y1 = k["y"]
        z0, z1 = k["z"]
        boxes.append(cq.Workplane("XY")
                     .box(x1 - x0, y1 - y0, z1 - z0, centered=(False, False, False))
                     .translate((x0, y0, z0)).val())
    return cq.Workplane(obj=cq.Compound.makeCompound(boxes))


# ---------------------------------------------------------------------------
# Flat patterns — what the shop actually cuts
# ---------------------------------------------------------------------------
def flat_pattern(params: dict, variant: str) -> tuple[cq.Workplane, dict]:
    """
    The developed blank for a variant as a 1 mm plate in XY, plus a bend table.
    Exported to DXF: outline and holes, 1:1, ready to nest.
    """
    if variant == "flat_plate":
        v = _var(params, "flat_plate")
        return create_flat_plate(params), {
            "blank_mm": [2 * v["half_width"], 2 * v["half_length"]],
            "thickness": v["thickness"], "bends": [],
            "note": "no bends — the blank is the part",
        }

    if variant == "edge_bracket":
        v = _var(params, "edge_bracket")
        t, ir = v["thickness"], v["bend_inside_radius"]
        x_bend, x_free = v["web_x"]
        half_l, fw = v["half_length"], v["flange_width"]
        ba, bd, setback = bend_allowance(ir, t), bend_deduction(ir, t), ir + t

        leg_flange = fw - setback                       # 26
        leg_web = (x_free - (x_bend - t)) - setback     # 132
        flat_len = leg_flange + ba + leg_web

        def u_web(x):
            return leg_flange + ba + (x - (x_bend + ir))

        def u_flange(z):
            return (fw - t) - z

        blank = _rounded_plate(flat_len, 2 * half_l, 1.0, v["corner_radius"])
        blank = blank.translate((flat_len / 2, 0, 0))

        holes = _iface(params)["mount_holes"]["positions_xy"]
        blank = _drill(blank, [(u_web(x), y) for x, y in holes if x < 0],
                       v["m3_clearance"], 0.0, 1.0)
        for x, y in [p for p in holes if p[0] > 0]:
            blank = blank.cut(
                _slot(v["m3_clearance"] + v["m3_slot_travel"], v["m3_clearance"],
                      1.0, 0).translate((u_web(x), y, 0)))
        blank = _drill(blank,
                       [(u_flange(z), y) for y in v["flange_hole_y"]
                        for z in v["flange_hole_z"]],
                       v["flange_hole_diameter"], 0.0, 1.0)
        ts = v["tie_slot"]
        for y in ts["y"]:
            blank = blank.cut(_slot(ts["length_y"], ts["width_x"], 1.0, 90)
                              .translate((u_web(ts["x"]), y, 0)))

        return blank, {
            "blank_mm": [round(flat_len, 2), 2 * half_l],
            "thickness": t,
            "bends": [{
                "id": "B1", "angle_deg": 90, "inside_radius": ir,
                "k_factor": K_FACTOR, "bend_allowance": round(ba, 3),
                "bend_deduction": round(bd, 3),
                "bend_line_u_mm": round(leg_flange + ba / 2, 2),
                "direction": "up, toward the radio",
            }],
        }

    if variant == "clamp_cradle":
        v = _var(params, "clamp_cradle")
        s = _bridge_stations(params)
        t, ir = s["t"], s["ir"]
        ba, bd, setback = bend_allowance(ir, t), bend_deduction(ir, t), ir + t

        # Outside leg lengths, measured to the virtual sharp corners.
        foot_out = s["foot_end"] - s["near"]
        leg_out = s["beam_hi"]
        beam_out = 2 * s["far"]
        outside = [foot_out, leg_out, beam_out, leg_out, foot_out]
        flat_len = sum(outside) - 4 * bd

        u, bends, segments = 0.0, [], []
        for i, leg in enumerate(outside):
            n = (1 if i > 0 else 0) + (1 if i < len(outside) - 1 else 0)
            flat_leg = leg - n * setback
            segments.append([round(u, 2), round(u + flat_leg, 2)])
            u += flat_leg
            if i < len(outside) - 1:
                bends.append({
                    "id": f"B{i + 1}", "angle_deg": 90, "inside_radius": ir,
                    "k_factor": K_FACTOR, "bend_allowance": round(ba, 3),
                    "bend_deduction": round(bd, 3),
                    "bend_line_u_mm": round(u + ba / 2, 2),
                    "direction": "up" if i in (0, 3) else "over",
                })
                u += ba

        blank = _rounded_plate(flat_len, s["w"], 1.0, 4.0)
        blank = blank.translate((flat_len / 2, 0, 0))
        d = s["foot_end"] - s["bolt_x"]                 # from each foot's free end
        blank = _drill(blank, [(d, 0), (flat_len - d, 0)], s["hole"], 0.0, 1.0)

        return blank, {
            "blank_mm": [round(flat_len, 2), s["w"]],
            "thickness": t, "bends": bends, "segments_u": segments,
            "note": "bridge only (x2) — the tray is flat and needs no development",
        }

    raise ValueError(f"unknown variant {variant!r}")


def shop_pack(params: dict) -> dict:
    """Everything a fabricator needs that is not in the STEP."""
    pack = {"part_name": params["part_name"], "version": params.get("version", "v1"),
            "units": "mm", "variants": {}}
    for name in VARIANTS:
        v = _var(params, name)
        _, info = flat_pattern(params, name)
        blanks = [dict(info, part=name, qty=1)]
        if name == "clamp_cradle":
            # the bridge is the only developed part; there are two of them, and
            # the tray is flat so its blank is simply its outline
            blanks[0].update(part="bridge", qty=2)
            blanks.append({
                "part": "tray", "qty": 1,
                "blank_mm": [2 * v["tray_half_width"], 2 * v["tray_half_length"]],
                "thickness": v["tray_thickness"], "bends": [],
                "note": "flat — the blank is the part; M4 tapped for the bridges",
            })
        pack["variants"][name] = {
            "material": v["material"], "process": v["process"],
            "finish": params["finish"]["spec"],
            "blanks": blanks,
        }
    default = params.get("default_variant", "flat_plate")
    pack["default_variant"] = default
    pack["files"] = {
        f"{PART_NAME}_{pack['version']}.step":
            f"THE ONE TO BUILD — {default}, exported again under the bare part "
            f"name. Identical geometry to "
            f"{PART_NAME}-{default.replace('_', '-')}_{pack['version']}.step.",
        **{f"{PART_NAME}-{n.replace('_', '-')}_{pack['version']}.step":
           f"{n} — {_var(params, n)['summary']}" for n in VARIANTS},
        "plates/*.dxf": "1:1 flat blanks, outline and holes, one per fabricated "
                        "piece. Bend lines are in the bend table above, not in "
                        "the DXF.",
    }
    pack["fasteners"] = params["fasteners"]
    pack["assembly_notes"] = params["notes"]
    return pack


# ---------------------------------------------------------------------------
# Entry points the pipeline expects
# ---------------------------------------------------------------------------
BUILDERS = {
    "flat_plate": create_flat_plate,
    "edge_bracket": create_edge_bracket,
    "clamp_cradle": create_clamp_cradle,
}


def create_part(params: dict | None = None) -> cq.Workplane:
    """The default variant — what lib.evaluate gates and make export-all writes."""
    if params is None:
        params = load_params()
    return BUILDERS[params.get("default_variant", "flat_plate")](params)


def build_stages(params: dict | None = None):
    """Stage-by-stage build of everything, for lib.debug_build bisection."""
    if params is None:
        params = load_params()
    yield "flat_plate", create_flat_plate(params)
    yield "edge_bracket", create_edge_bracket(params)
    yield "cradle_tray", create_cradle_tray(params)
    yield "cradle_bridge", create_cradle_bridge(params)
    yield "clamp_cradle", create_clamp_cradle(params)
    yield "keepouts", create_keepouts(params)
    yield "default", create_part(params)


def export_part(result, name: str, version: str = "v1",
                formats: list[str] | None = None,
                out_dir: Path | None = None) -> list[Path]:
    """Write a solid to exports/ — or to a short path, for SolidWorks."""
    formats = formats or ["step"]
    out_dir = Path(out_dir) if out_dir else EXPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for fmt in formats:
        p = out_dir / f"{name}_{version}.{fmt}"
        cq.exporters.export(result, str(p))
        print(f"  ok  {p}")
        written.append(p)
    return written


def export_dxf(solid: cq.Workplane, path: Path) -> None:
    """Lay a flat blank into XY and write it 1:1 as DXF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    face = solid.faces(">Z").val()
    cq.exporters.export(cq.Workplane(obj=face), str(path), exportType="DXF")
    print(f"  ok  {path}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    params = load_params()
    version = params.get("version", "v1")

    out_dir = None
    if "--out" in sys.argv:
        out_dir = Path(sys.argv[sys.argv.index("--out") + 1])
    base = Path(out_dir) if out_dir else EXPORTS_DIR

    wanted = [a for a in sys.argv[1:] if a in VARIANTS] or list(VARIANTS)
    fmts = ["step"] + (["stl"] if "--stl" in sys.argv else [])
    default = params.get("default_variant", "flat_plate")

    print(f"\n  {params['part_name']}  ({version})")
    mh = _iface(params)["mount_holes"]
    print(f"  mount frame: origin at the four-hole pattern centre, "
          f"{mh['pattern_x']} x {mh['pattern_y']} mm\n")

    for name in wanted:
        solid = BUILDERS[name](params)
        bb = solid.val().BoundingBox()
        v = _var(params, name)
        flag = "  <- default" if name == default else ""
        print(f"  {name}: {len(solid.solids().vals())} solid(s), "
              f"envelope {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm{flag}")
        print(f"      {v['material']}")
        print(f"      {v['process']}")
        export_part(solid, f"{PART_NAME}-{name.replace('_', '-')}",
                    version, fmts, out_dir)

        # The default variant is ALSO written under the bare part name, with no
        # variant suffix.  That is the name lib.export and lib.evaluate use for
        # a part's accepted artifact, so `<part>_<version>.step` always means
        # "the one we went with" and the three suffixed files sit beside it as
        # the alternatives.  Change `default_variant` in params.json to move it.
        if name == default:
            export_part(solid, PART_NAME, version, fmts, out_dir)

        if "--dxf" in sys.argv:
            blank, info = flat_pattern(params, name)
            export_dxf(blank, base / "plates" / f"{name}_flat_{version}.dxf")
            print(f"      blank {info['blank_mm'][0]} x {info['blank_mm'][1]} "
                  f"x {info['thickness']} mm, {len(info['bends'])} bend(s)")
            if name == "clamp_cradle":
                # the tray is flat, so its blank is the part
                tv = _var(params, name)
                export_dxf(create_cradle_tray(params),
                           base / "plates" / f"clamp_cradle_tray_{version}.dxf")
                print(f"      tray blank {2 * tv['tray_half_width']} x "
                      f"{2 * tv['tray_half_length']} x {tv['tray_thickness']} mm, "
                      f"0 bend(s)")

    if "--shop-pack" in sys.argv:
        base.mkdir(parents=True, exist_ok=True)
        p = base / f"shop_pack_{version}.json"
        p.write_text(json.dumps(shop_pack(params), indent=2), encoding="utf-8")
        print(f"\n  ok  {p}")
