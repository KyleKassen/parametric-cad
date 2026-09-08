"""
OZ51x Dual Vertical Housing — Fable 5 Extra Edition (shared builder)
====================================================================
Production-refined redesign of the vertical-stack OZ51x housings, authored by
Claude (Fable 5 extra). This file is the SHARED BUILDER for the redesigned
vertical family: this directory (dual-RX) hosts the geometry, and
parts/custom/oz51x-dual-tx-housing-vertical-fable5-extra is a thin wrapper
with transmitter-handed params.

Every critical interface of the verified v1 vertical housings is preserved
exactly — bay positions, stud/boss patterns, SMA holes + relief pockets,
fiber pass-slots, SC/APC adapter cutouts + pilots, DE-9 cutout + jackscrews,
mated-connector corridors, DE-9 rear keep-out, spool radius, and the lid's
perimeter-ring lip with wire headroom. The same canonical coordinate frame
and layout() API are kept so the family's tests and fit checks run unchanged
against this builder.

What the redesign adds (all parametric via params["industrial"]):

  Structure & mounting
  - Integral wall-mount flanges on the finished top and bottom faces, flush
    with the mount face, with rounded corners, slotted screw holes (lateral
    print-tolerance take-up) and triangular gusset roots (support-free print).
  - Harness tie-down anchors (post pairs) on the plenum floor near the DE-9
    so the solder-cup harness gets strain relief — clear of the rear keep-out
    and both SC connector corridors.

  Edge treatment / industrial design
  - The extruded-profile edge language: the four canonical vertical edges and
    the mount-side long edges are filleted, so in the finished attitude the
    front and back faces blend into the top, bottom, and mount faces. The
    service-cover perimeter is chamfered — a crisp, deliberate panel, like an
    extruded-aluminium enclosure's bolted end plate.
  - A matched 0.6 mm reveal chamfer on both sides of the parting line turns
    the lid seam into an intentional V-groove instead of a print artifact.
  - Engraved panel text: per-bay "RF"/"TTL" port labels beside each SMA, an
    "RX"/"TX" identity centered on the front face, and a maker/version mark
    on the cover. All engraving is oriented to read horizontally in the
    finished (vertical) mounting attitude.

  Manufacturability & serviceability
  - Entry chamfers on every thread-forming pilot (lid posts, spool, module
    bosses) and on the lid screw counterbores — screws start square, no
    elephant-foot jams.
  - Exterior cone chamfers on the SMA clearance holes (cleaner look, easier
    connector start, better FDM bridging).
  - SC/APC adapter flanges seat in shallow recessed pockets (locates the
    adapter, flush look); pocket depth is limited so the M2 flange-screw
    pilots keep >2 mm of engagement. The DE-9 stays surface-mounted: its
    30.8 mm flange spans the lid parting line, so a recess is impossible —
    documented, not accidental.
  - The DE-9's TOP jackscrew hole is opened into a deliberate capture slot to
    the parting face: in v1 only a 0.12 mm ligament separated hole from seam
    (it would break unpredictably in print). The cover edge closes the slot
    and captures the jackscrew standoff — deterministic geometry instead of a
    random break-out. The bottom jackscrew is a normal closed hole.
  - Lip pads get lead-in chamfers so the side-mounted cover self-aligns when
    fitted blind; support studs get top chamfers so modules seat smoothly.

  Ventilation & environment
  - Louver groups sized ≤2 mm (probe-safe) give each bay a convection path in
    the finished attitude: downward-facing intake/weep slots in the bottom
    face (nothing can fall in; they double as drainage), a low intake louver
    group on the cover over the lower bay, and a high exhaust group over the
    upper bay. The top face and the fiber plenum stay unvented — no
    upward-facing openings, and dust stays out of the optics.

Coordinate frame, module mapping, and handedness rules are identical to
parts/custom/oz510-dual-housing/model.py (the family's canonical builder) —
see that file and REQUIREMENTS.md for the underlying rationale and traps.
Units: mm throughout.
"""

import json
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge parameter dictionaries without mutating either input."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_params_file(path: Path) -> dict:
    """Load params, optionally inheriting another variant via ``_extends``."""
    with open(path, encoding="utf-8") as f:
        params = json.load(f)
    parent = params.pop("_extends", None)
    if parent:
        parent_path = (path.parent / parent).resolve()
        params = _deep_merge(load_params_file(parent_path), params)
    return params


def load_params(path: Path = PARAMS_FILE) -> dict:
    return load_params_file(path)


# ---------------------------------------------------------------------------
# Industrial-refinement parameters (all additive; defaults keep the part sane
# even if params.json omits the section)
# ---------------------------------------------------------------------------
_INDUSTRIAL_DEFAULTS = {
    # Edge language: verticals rounded, mount-side long edges rounded smaller
    # (limited by the SC adapter flange reaching within 0.24 mm of the floor
    # plane on the back panel), cover perimeter chamfered, parting-line reveal.
    "corner_fillet": 2.5,
    "mount_edge_fillet": 1.2,
    "reveal_chamfer": 0.6,
    "cover_chamfer": 1.2,
    "pilot_entry_chamfer": 0.5,
    "counterbore_entry_chamfer": 0.4,
    "sma_face_chamfer": 0.6,
    "stud_top_chamfer": 0.4,
    "lip_lead_in": 0.8,
    "spool_top_fillet": 1.5,
    "mount_flanges": {
        "enabled": True,
        "protrusion": 11.0,  # beyond the finished top/bottom faces
        "thickness": 3.0,  # flush with the mount face
        "end_inset": 3.0,  # stay clear of the rounded body corners
        "corner_radius": 4.0,
        "embed": 2.0,  # overlap into the wall for a robust union
        "gusset": 3.0,  # triangular root blend, support-free print
        "slot_width": 4.5,  # M4 / #8 pan head clearance
        "slot_length": 9.0,
        "slot_from_ends": 16.0,  # slot centers, measured from front/back faces
    },
    "vents": {
        "enabled": True,
        "slot_width": 2.0,  # <=2 mm: finger/debris safe
        "cover_slot_length": 30.0,
        "cover_slot_y": -7.0,  # clear of the header access openings
        "cover_slot_x": [31.5, 36.0],  # |x| centers, inside the lip ring
        "wall_slot_length": 28.0,
        "wall_slot_y": -10.0,
        "wall_slot_z": [9.0, 13.5, 18.0],  # above the flange gusset (z=6)
    },
    "connector_recess": {
        "sc_depth": 0.8,  # keeps >2 mm of M2 pilot engagement
        "clearance": 0.4,
        "corner_radius": 1.5,
    },
    "harness_anchors": {
        "enabled": True,
        "x": [-16.0, 16.0],  # clear of DE-9 keep-out (|x|<7) and SC
        "y_from_back_wall": 8.0,  # corridors (|x| 23.4..32.7)
        "post_dia": 3.0,
        "post_gap": 4.0,
        "height": 6.0,
    },
    "labels": {
        "enabled": True,
        "depth": 0.5,
        "font": "Arial",
        "bay_size": 4.5,
        "bay_z": 10.5,
        "bay_offset_from_sma": 9.0,  # toward the bay center, clear of the SMA
        "identity_size": 7.0,
        "identity_z": 20.0,
        "identity_text": "RX",
        "maker_text": "FABLE-5X V1",
        "maker_size": 3.2,
    },
}


def _industrial(params: dict) -> dict:
    return _deep_merge(_INDUSTRIAL_DEFAULTS, params.get("industrial", {}))


# ---------------------------------------------------------------------------
# Derived layout — same keys and meanings as the canonical family builder,
# plus flange-aware envelope numbers
# ---------------------------------------------------------------------------
def layout(params: dict) -> dict:
    m = params["module"]
    h = params["housing"]
    ind = _industrial(params)

    bays = params.get(
        "bays",
        [
            {"label": "left", "mirror_x": False},
            {"label": "right", "mirror_x": False},
        ],
    )
    n = len(bays)

    plate_w = m["plate_width_x"]
    plate_l = m["plate_length_z"]

    bay_w = plate_w + 2 * h["clearance_side"]
    bay_d = plate_l + 2 * h["clearance_end"]
    bay_pitch = bay_w + h["bay_gap"]
    bay_cx = [(i - (n - 1) / 2.0) * bay_pitch for i in range(n)]

    plate_bottom_z = h["floor"] + h["standoff_height"]
    interior_top_z = plate_bottom_z + m["can_height_y"] + h["clearance_top"]

    interior_half_x = (n - 1) / 2.0 * bay_pitch + plate_w / 2.0 + h["clearance_side"]
    interior_half_y = plate_l / 2.0 + h["clearance_end"]
    outer_half_x = interior_half_x + h["wall"]
    outer_half_y = interior_half_y + h["wall"]

    fb = params["fiber_bay"]
    plenum_y0 = outer_half_y
    plenum_y1 = plenum_y0 + fb["depth"]
    back_outer_y = plenum_y1 + h["wall"]

    m_fx = m["fiber_exit_x"]
    fiber_x = [cx + m_fx for cx in bay_cx]
    fiber_z = plate_bottom_z + m["fiber_exit_y"]

    setback = fb.get("spool_setback")
    if setback is None:
        spool_y = (plenum_y0 + plenum_y1) / 2.0
    else:
        spool_y = plenum_y0 + setback + fb["spool_dia"] / 2.0

    mounting_orientation = h.get("mounting_orientation", "horizontal")
    lid_thickness = h["lid_thickness"]

    fl = ind["mount_flanges"]
    flanges = bool(fl["enabled"]) and mounting_orientation == "vertical"
    flange_ext = fl["protrusion"] if flanges else 0.0

    if mounting_orientation == "vertical":
        envelope_width = interior_top_z + lid_thickness
        envelope_height = 2 * outer_half_x + 2 * flange_ext
    elif mounting_orientation == "horizontal":
        envelope_width = 2 * outer_half_x
        envelope_height = interior_top_z + lid_thickness
    else:
        raise ValueError("housing.mounting_orientation must be 'horizontal' or 'vertical'")

    pc = params.get("panel_connector")
    panel_connector_z = None
    if pc:
        panel_connector_z = interior_top_z / 2.0 if pc.get("center_z") else pc["z"]

    return {
        "plate_w": plate_w,
        "plate_l": plate_l,
        "bay_w": bay_w,
        "bay_d": bay_d,
        "bay_pitch": bay_pitch,
        "bay_cx": bay_cx,
        "bays": bays,
        "plate_bottom_z": plate_bottom_z,
        "interior_top_z": interior_top_z,
        "interior_half_x": interior_half_x,
        "interior_half_y": interior_half_y,
        "outer_half_x": outer_half_x,
        "outer_half_y": outer_half_y,
        "base_height": interior_top_z,
        "plenum_y0": plenum_y0,
        "plenum_y1": plenum_y1,
        "back_outer_y": back_outer_y,
        "spool_y": spool_y,
        "fiber_x": fiber_x,
        "fiber_z": fiber_z,
        "adapter_x": [b["adapter_x"] for b in bays],
        "total_depth": outer_half_y + back_outer_y,
        "mounting_orientation": mounting_orientation,
        "envelope_width": envelope_width,
        "envelope_depth": outer_half_y + back_outer_y,
        "envelope_height": envelope_height,
        "panel_connector_z": panel_connector_z,
        "has_flanges": flanges,
        "flange_ext": flange_ext,
        "industrial": ind,
    }


def orient_to_mounting(part: cq.Workplane, params: dict) -> cq.Workplane:
    """Transform canonical tray geometry into the requested mounting attitude.

    Identical to the canonical family builder: the vertical variant turns the
    tray +90 degrees about Y and re-centers so the BODY spans z = 0..2*outer_half_x
    (mount flanges deliberately protrude beyond both ends). Fit checks reuse
    this to transform module and probe geometry exactly like the housing.
    """
    L = layout(params)
    if L["mounting_orientation"] == "horizontal":
        return part
    x_shift = -L["envelope_width"] / 2.0
    z_shift = L["outer_half_x"]
    return part.rotate((0, 0, 0), (0, 1, 0), 90).translate((x_shift, 0, z_shift))


# ---------------------------------------------------------------------------
# Small geometric helpers
# ---------------------------------------------------------------------------
def _y_cylinder(r: float, x: float, z: float, y_start: float, length: float) -> cq.Solid:
    """A cylinder whose axis runs along +Y (front/back-panel holes)."""
    return cq.Solid.makeCylinder(r, length, cq.Vector(x, y_start, z), cq.Vector(0, 1, 0))


def _entry_cone_z(r: float, ch: float, x: float, y: float, z_top: float) -> cq.Solid:
    """Cut solid: 45-degree entry chamfer widening toward +Z at a pilot mouth.

    Overshoots the surface by 0.5 so the boolean cuts cleanly through the face.
    """
    return cq.Solid.makeCone(
        r,
        r + ch + 0.5,
        ch + 0.5,
        cq.Vector(x, y, z_top - ch),
        cq.Vector(0, 0, 1),
    )


def _face_cone_y(r: float, ch: float, x: float, z: float, y_face: float, inward: float) -> cq.Solid:
    """Cut solid: 45-degree cone chamfer on a Y-facing panel hole.

    ``inward`` is +1 for the front face (material toward +Y) and -1 for a
    back face. Starts 0.1 proud of the face for a clean boolean.
    """
    return cq.Solid.makeCone(
        r + ch + 0.1,
        r,
        ch + 0.1,
        cq.Vector(x, y_face - inward * 0.1, z),
        cq.Vector(0, inward, 0),
    )


def _rounded_pocket(w: float, h_: float, depth: float, r: float) -> cq.Workplane:
    """A rounded-corner pocket cut solid, centered at origin, cutting along -Y.

    Built as a box with its four Y-parallel edges filleted (safe on the
    primitive), spanning y in (-depth, +0.5) so it cuts in from a +Y face.
    """
    pocket = (
        cq.Workplane("XY")
        .box(w, depth + 0.5, h_, centered=(True, False, True))
        .translate((0, -depth, 0))
    )
    return pocket.edges("|Y").fillet(r)


def _panel_text_front(
    txt: str, size: float, depth: float, font: str, x: float, z: float, outer_half_y: float
) -> cq.Workplane:
    """Engraving solid for the FRONT (-Y) face, reading horizontally in the
    finished vertical attitude (glyph right = canonical +Z, up = canonical -X).
    """
    solid = cq.Workplane("XZ").text(
        txt,
        size,
        depth,
        combine=False,
        font=font,
        halign="center",
        valign="center",
    )
    # On XZ the text extrudes toward -Y (spans y in [-depth, 0]); rotate the
    # glyphs in-plane so they read correctly once the tray is stood vertical.
    solid = solid.rotate((0, 0, 0), (0, 1, 0), -90)
    return solid.translate((x, -outer_half_y + depth, z))


def _panel_text_lid_top(
    txt: str, size: float, depth: float, font: str, x: float, y: float, z_top: float
) -> cq.Workplane:
    """Engraving solid for the lid's outer face (finished right/service face),
    reading horizontally in the finished attitude (right = +Y, up = -X).
    """
    solid = cq.Workplane("XY").text(
        txt,
        size,
        depth,
        combine=False,
        font=font,
        halign="center",
        valign="center",
    )
    solid = solid.rotate((0, 0, 0), (0, 0, 1), 90)
    return solid.translate((x, y, z_top - depth))


# ---------------------------------------------------------------------------
# Base tray
# ---------------------------------------------------------------------------
def _create_base_canonical(params: dict) -> cq.Workplane:
    m = params["module"]
    h = params["housing"]
    L = layout(params)
    ind = L["industrial"]
    vertical = L["mounting_orientation"] == "vertical"

    # --- Outer block with the edge language applied while it is still a
    # simple prism (fillets/chamfers on primitives are robust; the interior
    # cuts below never touch the treated outer edges) ---------------------
    base = (
        cq.Workplane("XY")
        .box(
            2 * L["outer_half_x"], L["total_depth"], L["base_height"], centered=(True, False, False)
        )
        .translate((0, -L["outer_half_y"], 0))
    )
    base = base.edges("|Z").fillet(ind["corner_fillet"])
    base = base.edges("|X").edges("<Z").fillet(ind["mount_edge_fillet"])
    base = base.faces(">Z").edges().chamfer(ind["reveal_chamfer"])

    # --- Wall-mount flanges: flush with the mount face (canonical z=0), on
    # the finished top and bottom faces (canonical +/-X walls), with slotted
    # holes and a triangular gusset root ----------------------------------
    if L["has_flanges"]:
        fl = ind["mount_flanges"]
        yc = (-L["outer_half_y"] + L["back_outer_y"]) / 2.0
        f_depth = L["total_depth"] - 2 * fl["end_inset"]
        f_w = fl["protrusion"] + fl["embed"]
        for s in (-1.0, 1.0):
            plate = (
                cq.Workplane("XY")
                .box(f_w, f_depth, fl["thickness"], centered=(True, True, False))
                .edges("|Z")
                .fillet(fl["corner_radius"])
                .translate((s * (L["outer_half_x"] - fl["embed"] + f_w / 2.0), yc, 0))
            )
            slot_cx = s * (L["outer_half_x"] + fl["protrusion"] / 2.0)
            for sy in (
                -L["outer_half_y"] + fl["slot_from_ends"],
                L["back_outer_y"] - fl["slot_from_ends"],
            ):
                slot = (
                    cq.Workplane("XY")
                    .slot2D(fl["slot_length"], fl["slot_width"], 90)
                    .extrude(fl["thickness"] + 2.0)
                    .translate((slot_cx, sy, -1.0))
                )
                plate = plate.cut(slot)
            base = base.union(plate)
            # gusset: right-triangle prism blending flange top into the wall
            x0 = s * (L["outer_half_x"] - 0.5)
            xg = s * (L["outer_half_x"] + fl["gusset"])
            t = fl["thickness"]
            gusset = (
                cq.Workplane("XZ")
                .polyline([(x0, t), (x0, t + fl["gusset"]), (xg, t)])
                .close()
                .extrude(f_depth)
                .translate((0, yc + f_depth / 2.0, 0))
            )
            base = base.union(gusset)

    # --- Hollow out the module bays (open top), leaving the central rib ----
    cav_h = L["base_height"] - h["floor"] + 1.0
    for cx in L["bay_cx"]:
        cavity = (
            cq.Workplane("XY")
            .box(L["bay_w"], L["bay_d"], cav_h, centered=(True, True, False))
            .translate((cx, 0, h["floor"]))
        )
        base = base.cut(cavity)

    # --- Fiber plenum: full-width open-top cavity behind the partition -----
    fb = params["fiber_bay"]
    plenum = (
        cq.Workplane("XY")
        .box(2 * L["interior_half_x"], fb["depth"], cav_h, centered=(True, False, False))
        .translate((0, L["plenum_y0"], h["floor"]))
    )
    base = base.cut(plenum)

    # --- Partition pass-slots: top-open, one per bay, NOT mirrored ---------
    slot_z0 = L["plate_bottom_z"]
    for fx in L["fiber_x"]:
        slot = (
            cq.Workplane("XY")
            .box(
                fb["pass_slot_width"],
                h["wall"] + 2.0,
                L["base_height"] - slot_z0 + 1.0,
                centered=(True, False, False),
            )
            .translate((fx, L["interior_half_y"] - 1.0, slot_z0))
        )
        base = base.cut(slot)

    # --- Slack spool: doubles as a lid screw post. Top edge filleted so
    # fiber coils dress in over it without a sharp corner ------------------
    spool_r = fb["spool_dia"] / 2.0
    spool = (
        cq.Workplane("XY")
        .circle(spool_r)
        .extrude(L["base_height"])
        .edges(">Z")
        .fillet(ind["spool_top_fillet"])
        .translate((0, L["spool_y"], 0))
    )
    base = base.union(spool)
    spool_pilot = (
        cq.Workplane("XY")
        .circle(h["corner_post_pilot_dia"] / 2.0)
        .extrude(L["base_height"] - h["floor"] + 0.5)
        .translate((0, L["spool_y"], h["floor"]))
    )
    base = base.cut(spool_pilot)
    base = base.cut(
        cq.Workplane("XY").newObject(
            [
                _entry_cone_z(
                    h["corner_post_pilot_dia"] / 2.0,
                    ind["pilot_entry_chamfer"],
                    0,
                    L["spool_y"],
                    L["base_height"],
                )
            ]
        )
    )

    # --- Lid-screw posts: three along the central rib, two back corners ----
    post_r = h["corner_post_dia"] / 2.0
    post_pilot_r = h["corner_post_pilot_dia"] / 2.0
    corner_y = L["plenum_y1"] - post_r - 1.0
    post_xy = [
        (0.0, -(L["interior_half_y"] - post_r - 1.0)),
        (0.0, 0.0),
        (0.0, +(L["interior_half_y"] - post_r - 1.0)),
        (-(L["interior_half_x"] - post_r - 1.0), corner_y),
        (+(L["interior_half_x"] - post_r - 1.0), corner_y),
    ]
    for px, py in post_xy:
        post = cq.Workplane("XY").circle(post_r).extrude(L["base_height"]).translate((px, py, 0))
        base = base.union(post)
        pilot = (
            cq.Workplane("XY")
            .circle(post_pilot_r)
            .extrude(L["base_height"] - h["floor"] + 0.5)
            .translate((px, py, h["floor"]))
        )
        base = base.cut(pilot)
        base = base.cut(
            cq.Workplane("XY").newObject(
                [_entry_cone_z(post_pilot_r, ind["pilot_entry_chamfer"], px, py, L["base_height"])]
            )
        )

    # --- Back-panel SC/APC adapter mounts: recessed flange pocket, body
    # cutout, and M2 flange-screw pilots (counter-rotated when vertical so
    # the installed adapter's long axis and screws are horizontal) ----------
    ad = params["sc_adapter"]
    rc = ind["connector_recess"]
    cut_w = (ad["body_short"] if vertical else ad["body_long"]) + 2 * ad["cutout_clearance"]
    cut_h = (ad["body_long"] if vertical else ad["body_short"]) + 2 * ad["cutout_clearance"]
    pocket_w = (ad["flange_wide"] if vertical else ad["flange_len"]) + 2 * rc["clearance"]
    pocket_h = (ad["flange_len"] if vertical else ad["flange_wide"]) + 2 * rc["clearance"]
    for ax in L["adapter_x"]:
        cutout = (
            cq.Workplane("XY")
            .box(cut_w, h["wall"] + 2.0, cut_h, centered=(True, True, True))
            .translate((ax, L["plenum_y1"] + h["wall"] / 2.0, L["fiber_z"]))
        )
        base = base.cut(cutout)
        pocket = _rounded_pocket(pocket_w, pocket_h, rc["sc_depth"], rc["corner_radius"]).translate(
            (ax, L["back_outer_y"], L["fiber_z"])
        )
        base = base.cut(pocket)
        for offset in (-ad["screw_spacing"] / 2.0, +ad["screw_spacing"] / 2.0):
            px = ax if vertical else ax + offset
            pz = L["fiber_z"] + offset if vertical else L["fiber_z"]
            pilot = _y_cylinder(
                ad["screw_pilot_dia"] / 2.0,
                px,
                pz,
                y_start=L["plenum_y1"] - 1.0,
                length=h["wall"] + 2.0,
            )
            base = base.cut(pilot)

    # --- Support studs: 4 per bay, pilot-less, on verified-bare plate;
    # chamfered tops so a module (with pigtail attached) seats smoothly -----
    stud_r = h["stud_dia"] / 2.0
    boss_top = L["plate_bottom_z"]
    stud_proto = (
        cq.Workplane("XY")
        .circle(stud_r)
        .extrude(boss_top)
        .edges(">Z")
        .chamfer(ind["stud_top_chamfer"])
    )
    for cx in L["bay_cx"]:
        for sx in (-h["stud_dx"], +h["stud_dx"]):
            for sz in h["stud_z"]:
                base = base.union(stud_proto.translate((cx + sx, -sz, 0)))

    # --- Screw bosses: M3 through each module's two FREE plate holes -------
    sb_r = h["screw_boss_dia"] / 2.0
    sb_pilot_r = h["screw_boss_pilot_dia"] / 2.0
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1.0 if bay.get("mirror_x") else 1.0
        for hole in (m["screw_hole_front"], m["screw_hole_back"]):
            x = cx + sign * hole["x"]
            y = -hole["z"]  # module +Z -> housing -Y
            boss = cq.Workplane("XY").circle(sb_r).extrude(boss_top).translate((x, y, 0))
            base = base.union(boss)
            pilot = cq.Workplane("XY").circle(sb_pilot_r).extrude(boss_top).translate((x, y, 0.5))
            base = base.cut(pilot)
            base = base.cut(
                cq.Workplane("XY").newObject(
                    [_entry_cone_z(sb_pilot_r, ind["pilot_entry_chamfer"], x, y, boss_top)]
                )
            )

    # --- Front-panel SMA clearance holes: barrel hole + exterior cone
    # chamfer + interior relief pocket for the overhanging SMA base block ---
    sma_r = h["sma_hole_dia"] / 2.0
    relief_d = m["sma_base_beyond_plate"] - h["clearance_end"] + h["sma_relief_margin"]
    relief_w = m["sma_base_w"] + 2 * h["sma_relief_margin"]
    relief_h = m["sma_base_h"] + 2 * h["sma_relief_margin"]
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1.0 if bay.get("mirror_x") else 1.0
        x = cx + sign * m["sma_axis_x"]
        z = L["plate_bottom_z"] + m["sma_axis_y"]
        hole = _y_cylinder(sma_r, x, z, y_start=-L["outer_half_y"] - 1.0, length=h["wall"] + 2.0)
        base = base.cut(hole)
        base = base.cut(
            cq.Workplane("XY").newObject(
                [_face_cone_y(sma_r, ind["sma_face_chamfer"], x, z, -L["outer_half_y"], inward=1.0)]
            )
        )
        if relief_d > 0:
            pocket = (
                cq.Workplane("XY")
                .box(relief_w, relief_d + 0.1, relief_h, centered=(True, False, True))
                .translate((x, -L["interior_half_y"] - relief_d, z))
            )
            base = base.cut(pocket)

    # --- Front-panel wiring slots (only on variants that keep them) --------
    if h.get("front_wiring_slots", True):
        slot_x0 = m["header_x_min"] - h["header_slot_margin"]
        slot_x1 = m["header_x_max"] + h["header_slot_margin"]
        slot_w = slot_x1 - slot_x0
        wr_z0 = L["plate_bottom_z"]
        wr_z1 = L["plate_bottom_z"] + m["header_top_y"] + h["header_slot_top_clear"]
        for bay, cx in zip(L["bays"], L["bay_cx"]):
            bx0 = -slot_x1 if bay.get("mirror_x") else slot_x0
            slot = (
                cq.Workplane("XY")
                .box(slot_w, h["wall"] + 2.0, wr_z1 - wr_z0, centered=(False, True, False))
                .translate((cx + bx0, -L["outer_half_y"] + h["wall"] / 2.0, wr_z0))
            )
            base = base.cut(slot)

    # --- Back-panel signal connector (DE-9 class) --------------------------
    # Surface-mounted: the 30.8 mm flange spans the lid parting line, so a
    # recess pocket cannot exist on the base alone. The TOP jackscrew hole is
    # opened to the parting face as a deliberate capture slot (v1 left a
    # 0.12 mm ligament there that would break unpredictably in print); the
    # cover edge closes the slot and captures the jackscrew standoff.
    pc = params.get("panel_connector")
    if pc:
        pc_z = L["panel_connector_z"]
        cut_w = pc["cutout_h"] if vertical else pc["cutout_w"]
        cut_h = pc["cutout_w"] if vertical else pc["cutout_h"]
        cutout = (
            cq.Workplane("XY")
            .box(cut_w, h["wall"] + 2.0, cut_h, centered=(True, True, True))
            .translate((pc["x"], L["plenum_y1"] + h["wall"] / 2.0, pc_z))
        )
        base = base.cut(cutout)
        for offset in (-pc["screw_spacing"] / 2.0, +pc["screw_spacing"] / 2.0):
            px = pc["x"] if vertical else pc["x"] + offset
            pz = pc_z + offset if vertical else pc_z
            hole = _y_cylinder(
                pc["screw_hole_dia"] / 2.0,
                px,
                pz,
                y_start=L["plenum_y1"] - 1.0,
                length=h["wall"] + 2.0,
            )
            base = base.cut(hole)
            if vertical and pz + pc["screw_hole_dia"] / 2.0 > L["base_height"] - 1.0:
                capture = (
                    cq.Workplane("XY")
                    .box(
                        pc["screw_hole_dia"],
                        h["wall"] + 2.0,
                        L["base_height"] - pz + 1.0,
                        centered=(True, True, False),
                    )
                    .translate((px, L["plenum_y1"] + h["wall"] / 2.0, pz))
                )
                base = base.cut(capture)

    # --- Ventilation / drainage: downward-facing intake+weep slots in the
    # finished bottom face (canonical +X wall, lower bay). Nothing faces up;
    # the plenum stays unvented ---------------------------------------------
    vents = ind["vents"]
    if vents["enabled"] and vertical:
        for zc in vents["wall_slot_z"]:
            slot = (
                cq.Workplane("XY")
                .box(
                    h["wall"] + 2.0,
                    vents["wall_slot_length"],
                    vents["slot_width"],
                    centered=(True, True, True),
                )
                .translate(
                    ((L["interior_half_x"] + L["outer_half_x"]) / 2.0, vents["wall_slot_y"], zc)
                )
            )
            base = base.cut(slot)

    # --- Harness tie-down anchors: post pairs on the plenum floor near the
    # DE-9 so the solder-cup harness can be zip-tied (strain relief) --------
    ha = ind["harness_anchors"]
    if ha["enabled"] and pc:
        anchor_y = L["plenum_y1"] - ha["y_from_back_wall"]
        post_r = ha["post_dia"] / 2.0
        pitch = ha["post_gap"] + ha["post_dia"]
        proto = cq.Workplane("XY").circle(post_r).extrude(ha["height"]).edges(">Z").chamfer(0.3)
        for axc in ha["x"]:
            for dxp in (-pitch / 2.0, +pitch / 2.0):
                base = base.union(proto.translate((axc + dxp, anchor_y, h["floor"])))

    # --- Engraved panel text (reads horizontally in the finished attitude) -
    lab = ind["labels"]
    if lab["enabled"] and vertical:
        for bay, cx in zip(L["bays"], L["bay_cx"]):
            sign = -1.0 if bay.get("mirror_x") else 1.0
            txt = bay.get("panel_label", bay.get("label", "").split("-")[0].upper() or None)
            if not txt:
                continue
            label_x = cx + sign * (m["sma_axis_x"] + lab["bay_offset_from_sma"])
            base = base.cut(
                _panel_text_front(
                    txt,
                    lab["bay_size"],
                    lab["depth"],
                    lab["font"],
                    label_x,
                    lab["bay_z"],
                    L["outer_half_y"],
                )
            )
        if lab.get("identity_text"):
            base = base.cut(
                _panel_text_front(
                    lab["identity_text"],
                    lab["identity_size"],
                    lab["depth"],
                    lab["font"],
                    0.0,
                    lab["identity_z"],
                    L["outer_half_y"],
                )
            )

    return base


def create_base(params: dict) -> cq.Workplane:
    """Build the base tray in its requested horizontal or vertical attitude."""
    return orient_to_mounting(_create_base_canonical(params), params)


# ---------------------------------------------------------------------------
# Lid — the finished right-side service cover
# ---------------------------------------------------------------------------
def _create_lid_canonical(params: dict) -> cq.Workplane:
    h = params["housing"]
    m = params["module"]
    L = layout(params)
    ind = L["industrial"]
    vertical = L["mounting_orientation"] == "vertical"

    z0 = L["base_height"]
    lid = (
        cq.Workplane("XY")
        .box(
            2 * L["outer_half_x"],
            L["total_depth"],
            h["lid_thickness"],
            centered=(True, False, False),
        )
        .translate((0, -L["outer_half_y"], z0))
    )
    # Plan profile matches the filleted base; outer perimeter chamfered like
    # an extruded enclosure's bolted end plate; matching parting-line reveal.
    lid = lid.edges("|Z").fillet(ind["corner_fillet"])
    lid = lid.faces(">Z").edges().chamfer(ind["cover_chamfer"])
    lid = lid.faces("<Z").edges().chamfer(ind["reveal_chamfer"])

    # Registration lip: perimeter RING per bay (internal-wiring variants) or
    # a solid pad, nesting in the bay cavities only — see the canonical
    # builder for the history behind every constraint here. New: lead-in
    # chamfer on each pad's bottom edges so the side-fitted cover self-aligns.
    lip_depth = 2.0
    lip_gap = 0.3
    lip_ring_w = 3.0
    internal_wiring = not h.get("front_wiring_slots", True)
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        lip = (
            cq.Workplane("XY")
            .box(
                L["bay_w"] - 2 * lip_gap,
                L["bay_d"] - 2 * lip_gap,
                lip_depth,
                centered=(True, True, False),
            )
            .edges("<Z")
            .chamfer(ind["lip_lead_in"])
            .translate((cx, 0, z0 - lip_depth))
        )
        if internal_wiring:
            core = (
                cq.Workplane("XY")
                .box(
                    L["bay_w"] - 2 * lip_gap - 2 * lip_ring_w,
                    L["bay_d"] - 2 * lip_gap - 2 * lip_ring_w,
                    lip_depth + 1.0,
                    centered=(True, True, False),
                )
                .translate((cx, 0, z0 - lip_depth - 0.5))
            )
            lip = lip.cut(core)
            slot_gap = (
                cq.Workplane("XY")
                .box(
                    params["fiber_bay"]["pass_slot_width"],
                    lip_ring_w + lip_gap + 1.0,
                    lip_depth + 1.0,
                    centered=(True, False, False),
                )
                .translate(
                    (
                        cx + m["fiber_exit_x"],
                        L["bay_d"] / 2.0 - lip_gap - lip_ring_w - 0.5,
                        z0 - lip_depth - 0.5,
                    )
                )
            )
            lip = lip.cut(slot_gap)
        lid = lid.union(lip)

    # Scallop the lip around the rib screw posts (they bulge past the bay edge)
    post_r = h["corner_post_dia"] / 2.0
    for py in [-(L["interior_half_y"] - post_r - 1.0), 0.0, +(L["interior_half_y"] - post_r - 1.0)]:
        scallop = (
            cq.Workplane("XY")
            .circle(post_r + lip_gap)
            .extrude(lip_depth + 0.5)
            .translate((0, py, z0 - lip_depth - 0.5))
        )
        lid = lid.cut(scallop)

    # Header access openings, directly above each pin-header block (handed)
    op_x0 = m["header_x_min"] - h["header_slot_margin"]
    op_x1 = m["header_x_max"] + h["header_slot_margin"]
    op_w = op_x1 - op_x0
    op_y0 = -m["header_z_max"]  # module +Z -> housing -Y
    op_y1 = -m["header_z_min"]
    op_d = op_y1 - op_y0
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        bx0 = -op_x1 if bay.get("mirror_x") else op_x0
        opening = (
            cq.Workplane("XY")
            .box(op_w, op_d, h["lid_thickness"] + lip_depth + 2.0, centered=(False, False, False))
            .translate((cx + bx0, op_y0, z0 - lip_depth - 1.0))
        )
        lid = lid.cut(opening)

    # Cover louvers: a low intake group over the (finished) lower bay and a
    # high exhaust group over the upper bay — inside the lip ring, clear of
    # the header openings, slots <=2 mm
    vents = ind["vents"]
    if vents["enabled"] and vertical:
        for s in (-1.0, 1.0):
            for xc in vents["cover_slot_x"]:
                slot = (
                    cq.Workplane("XY")
                    .box(
                        vents["slot_width"],
                        vents["cover_slot_length"],
                        h["lid_thickness"] + 2.0,
                        centered=(True, True, True),
                    )
                    .translate((s * xc, vents["cover_slot_y"], z0 + h["lid_thickness"] / 2.0))
                )
                lid = lid.cut(slot)

    # Lid screw clearance holes: three rib posts, the spool, two back corners
    clr_r = h["lid_screw_clear_dia"] / 2.0
    head_r = h["lid_screw_head_dia"] / 2.0
    screw_xy = [
        (0.0, -(L["interior_half_y"] - post_r - 1.0)),
        (0.0, 0.0),
        (0.0, +(L["interior_half_y"] - post_r - 1.0)),
        (0.0, L["spool_y"]),
        (-(L["interior_half_x"] - post_r - 1.0), L["plenum_y1"] - post_r - 1.0),
        (+(L["interior_half_x"] - post_r - 1.0), L["plenum_y1"] - post_r - 1.0),
    ]
    for px, py in screw_xy:
        cbore = (
            cq.Workplane("XY")
            .circle(clr_r)
            .extrude(h["lid_thickness"] + lip_depth + 1.0)
            .translate((px, py, z0 - lip_depth))
        )
        head = (
            cq.Workplane("XY")
            .circle(head_r)
            .extrude(1.6 + 0.5)
            .translate((px, py, z0 + h["lid_thickness"] - 1.6))
        )
        lid = lid.cut(cbore).cut(head)
        lid = lid.cut(
            cq.Workplane("XY").newObject(
                [
                    _entry_cone_z(
                        head_r, ind["counterbore_entry_chamfer"], px, py, z0 + h["lid_thickness"]
                    )
                ]
            )
        )

    # Maker / version mark, discreet, on the cover's outer face
    lab = ind["labels"]
    if lab["enabled"] and vertical and lab.get("maker_text"):
        lid = lid.cut(
            _panel_text_lid_top(
                lab["maker_text"],
                lab["maker_size"],
                min(lab["depth"], 0.4),
                lab["font"],
                40.0,
                25.0,
                z0 + h["lid_thickness"],
            )
        )

    return lid


def create_lid(params: dict) -> cq.Workplane:
    """Build the removable side service cover in its mounting attitude."""
    return orient_to_mounting(_create_lid_canonical(params), params)


# ---------------------------------------------------------------------------
# Assembly (base + lid) as a single compound
# ---------------------------------------------------------------------------
def create_part(params: dict | None = None) -> cq.Workplane:
    if params is None:
        params = load_params()

    base = create_base(params)
    lid = create_lid(params)

    explode = params["housing"].get("explode_gap", 0.0)
    if explode:
        if layout(params)["mounting_orientation"] == "vertical":
            lid = lid.translate((explode, 0, 0))
        else:
            lid = lid.translate((0, 0, explode))

    compound = cq.Compound.makeCompound([base.val(), lid.val()])
    return cq.Workplane("XY").newObject([compound])


def export_part(result, name=None, version="v1", formats=None):
    name = PART_DIR.name if name is None else name
    formats = ["step"] if formats is None else formats
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for fmt in formats:
        p = EXPORTS_DIR / f"{name}_{version}.{fmt}"
        cq.exporters.export(result, str(p))
        print(f"  ✓ Exported {p.relative_to(PROJECT_ROOT)}")
        out.append(p)
    return out


if __name__ == "__main__":
    params = load_params()
    part = create_part(params)

    L = layout(params)
    print(f"\n  Building: {params['part_name']} ({params.get('version', 'v1')})")
    print(
        f"  Outer envelope: {L['envelope_width']:.1f} (W) × "
        f"{L['envelope_depth']:.1f} (D) × "
        f"{L['envelope_height']:.1f} (H) mm  (incl. mount flanges)\n"
    )

    fmts = ["step"] + (["stl"] if "--stl" in sys.argv else [])
    export_part(part, version=params.get("version", "v1"), formats=fmts)
