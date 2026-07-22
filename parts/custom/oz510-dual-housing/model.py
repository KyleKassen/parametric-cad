"""
OZ510 Dual-Module Housing
=========================
A two-bay enclosure that holds one OZ510 Receiver and one OZ510 Transmitter
side by side, with all I/O (SMA coax + 0.1" pin header) on a common front panel
and an SC/APC fiber port per module on the back panel.

Design (see params.json for every dimension):
  - Base tray with two module bays separated by a central rib.
  - Each module sits plate-down on four pilot-less support studs (inboard of
    the plate corners — the corner holes are filled by vendor press-fit
    standoffs whose hardware protrudes below the plate) and is retained by
    two M3 screws through the module's free 1/8" plate holes (front inner +
    back center) into screw-boss pilots. The front hole is TX-mirrored.
  - Front panel (the -Y face) has an SMA clearance hole and a wiring slot per bay.
  - Behind the module bays, a full-width fiber plenum stores each module's
    factory SC/APC pigtail. The partition between bays and plenum has a
    top-open pass-slot above each fiber exit (top-open so a module drops in
    with its pigtail attached). Slack coils around a central spool whose
    radius enforces the fiber's minimum bend radius; the spool doubles as a
    lid-screw post.
  - Back panel (+Y face) has one flanged SC/APC simplex adapter mount per bay:
    a rectangular cutout plus two M2 pilot holes. The pigtail plugs into the
    adapter from inside; the external fiber plugs in from outside.
  - Removable lid with an access opening directly above each pin-header block,
    retained by screws into three rib posts, the spool, and two back corners.

Handedness: the TX module is a MIRROR of the RX across X (SMA and header swap
sides). The module geometry in params.json is receiver-handed; each entry in
params["bays"] carries a mirror_x flag that flips that bay's handed cutouts
(SMA hole, wiring slot, lid opening). The mounting-hole pattern is symmetric,
so the bosses are shared. EXCEPTION: the fiber exit on the can's back is NOT
mirrored — both modules exit at module-local x = +fiber_exit_x (verified
per-file in the vendor analyses), so fiber features never use mirror_x.
Run fit_check.py after any change to re-verify against the real vendor STEPs.

This model is the SHARED BUILDER for the whole OZ51x housing family — the
dual-TX and dual-RX variants (parts/custom/oz51x-dual-tx-housing and
oz51x-dual-rx-housing) are thin wrappers that call these functions with their
own params.json. REQUIREMENTS.md in this directory is the family's
dimension-free spec: design intent, constraints, discovered traps, and the
verification obligations every variant must pass. Everything variant-specific is parametric: bays[] set each
bay's handedness (mirror_x) and vendor STEP (step); housing.front_wiring_slots
gates the front slots; panel_connector (optional) adds a rear signal
connector (e.g. DE-9); fiber_bay.spool_setback front-biases the spool.

Coordinate frame (CadQuery-natural, Z up):
    X = width  (modules side by side)
    Y = depth  (front panel at -Y, back wall at +Y)
    Z = up     (floor at Z=0)

A module's own STEP frame (plate centered in X, plate center in Z, plate BOTTOM
at Y=0, can up +Y, I/O at +Z) maps into this frame by:
    rotate +90 deg about X, then translate to (bay_center_x, 0, plate_bottom_z)

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


def load_params(path: Path = PARAMS_FILE) -> dict:
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Derived layout — everything the geometry needs, computed from params
# ---------------------------------------------------------------------------
def layout(params: dict) -> dict:
    m = params["module"]
    h = params["housing"]

    # One entry per bay; mirror_x flags a mirrored (transmitter-handed) module
    bays = params.get("bays", [{"label": "left", "mirror_x": False},
                               {"label": "right", "mirror_x": False}])
    n = len(bays)

    plate_w = m["plate_width_x"]
    plate_l = m["plate_length_z"]

    bay_w = plate_w + 2 * h["clearance_side"]          # interior width of one bay
    bay_d = plate_l + 2 * h["clearance_end"]           # interior depth of one bay
    bay_pitch = bay_w + h["bay_gap"]
    bay_cx = [(i - (n - 1) / 2.0) * bay_pitch for i in range(n)]

    plate_bottom_z = h["floor"] + h["standoff_height"]
    interior_top_z = plate_bottom_z + m["can_height_y"] + h["clearance_top"]

    interior_half_x = (n - 1) / 2.0 * bay_pitch + plate_w / 2.0 + h["clearance_side"]
    interior_half_y = plate_l / 2.0 + h["clearance_end"]
    outer_half_x = interior_half_x + h["wall"]
    outer_half_y = interior_half_y + h["wall"]

    # Fiber plenum behind the module bays. The old back wall (thickness =
    # wall) survives as the partition; the plenum runs from its outer face
    # to the new back wall. Modules stay centered on y=0, so the outer box
    # is asymmetric in Y: from -outer_half_y to +back_outer_y.
    fb = params["fiber_bay"]
    plenum_y0 = outer_half_y                      # partition outer face
    plenum_y1 = plenum_y0 + fb["depth"]           # back wall inner face
    back_outer_y = plenum_y1 + h["wall"]

    # Fiber exits: bay-local +fiber_exit_x on BOTH modules (NOT mirrored)
    m_fx = m["fiber_exit_x"]
    fiber_x = [cx + m_fx for cx in bay_cx]
    fiber_z = plate_bottom_z + m["fiber_exit_y"]

    # Spool: centered in the plenum by default; spool_setback front-biases it
    # (gap to the partition) to free depth at the back wall, e.g. for a
    # panel connector's rear shell and wiring.
    setback = fb.get("spool_setback")
    if setback is None:
        spool_y = (plenum_y0 + plenum_y1) / 2.0
    else:
        spool_y = plenum_y0 + setback + fb["spool_dia"] / 2.0

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
    }


def _y_cylinder(r: float, x: float, z: float, y_start: float, length: float) -> cq.Solid:
    """A cylinder whose axis runs along +Y (used for front-panel holes)."""
    return cq.Solid.makeCylinder(r, length, cq.Vector(x, y_start, z), cq.Vector(0, 1, 0))


# ---------------------------------------------------------------------------
# Base tray
# ---------------------------------------------------------------------------
def create_base(params: dict) -> cq.Workplane:
    m = params["module"]
    h = params["housing"]
    L = layout(params)

    # --- Outer block, bottom on Z=0, asymmetric in Y (plenum at +Y) ---------
    base = (
        cq.Workplane("XY")
        .box(2 * L["outer_half_x"], L["total_depth"], L["base_height"],
             centered=(True, False, False))
        .translate((0, -L["outer_half_y"], 0))
    )

    # --- Hollow out the two module bays (open top), leaving the central rib --
    cav_h = L["base_height"] - h["floor"] + 1.0  # +1 so the cut clears the top
    for cx in L["bay_cx"]:
        cavity = (
            cq.Workplane("XY")
            .box(L["bay_w"], L["bay_d"], cav_h, centered=(True, True, False))
            .translate((cx, 0, h["floor"]))
        )
        base = base.cut(cavity)

    # --- Fiber plenum: full-width open-top cavity behind the partition ------
    fb = params["fiber_bay"]
    plenum = (
        cq.Workplane("XY")
        .box(2 * L["interior_half_x"], fb["depth"], cav_h,
             centered=(True, False, False))
        .translate((0, L["plenum_y0"], h["floor"]))
    )
    base = base.cut(plenum)

    # --- Partition pass-slots: top-open, one per bay, NOT mirrored ----------
    # (both modules' pigtails exit at bay-local +fiber_exit_x; a module is
    # dropped in with its pigtail attached, so the slot opens to the top)
    slot_z0 = L["plate_bottom_z"]
    for fx in L["fiber_x"]:
        slot = (
            cq.Workplane("XY")
            .box(fb["pass_slot_width"], h["wall"] + 2.0,
                 L["base_height"] - slot_z0 + 1.0, centered=(True, False, False))
            .translate((fx, L["interior_half_y"] - 1.0, slot_z0))
        )
        base = base.cut(slot)

    # --- Slack spool: center of the plenum, radius = min fiber bend radius --
    # Full height, so it also supports the lid; pilot makes it a screw post.
    spool_r = fb["spool_dia"] / 2.0
    spool = (
        cq.Workplane("XY")
        .circle(spool_r).extrude(L["base_height"])
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

    # --- Back-corner lid posts (the lid spans much further now) -------------
    post_r = h["corner_post_dia"] / 2.0
    post_pilot_r = h["corner_post_pilot_dia"] / 2.0
    corner_y = L["plenum_y1"] - post_r - 1.0
    for px in (-(L["interior_half_x"] - post_r - 1.0),
               +(L["interior_half_x"] - post_r - 1.0)):
        post = (
            cq.Workplane("XY")
            .circle(post_r).extrude(L["base_height"])
            .translate((px, corner_y, 0))
        )
        base = base.union(post)
        pilot = (
            cq.Workplane("XY")
            .circle(post_pilot_r).extrude(L["base_height"] - h["floor"] + 0.5)
            .translate((px, corner_y, h["floor"]))
        )
        base = base.cut(pilot)

    # --- Back-panel SC/APC adapter mounts (one per bay) ---------------------
    # Rectangular cutout for the adapter body (long axis horizontal — the
    # 22mm flange would not fit vertically in the wall height) plus two M2
    # pilot holes for the flange screws. Adapter inserted from outside.
    ad = params["sc_adapter"]
    cut_w = ad["body_long"] + 2 * ad["cutout_clearance"]
    cut_h = ad["body_short"] + 2 * ad["cutout_clearance"]
    for ax in L["adapter_x"]:
        cutout = (
            cq.Workplane("XY")
            .box(cut_w, h["wall"] + 2.0, cut_h, centered=(True, True, True))
            .translate((ax, L["plenum_y1"] + h["wall"] / 2.0, L["fiber_z"]))
        )
        base = base.cut(cutout)
        for sx in (-ad["screw_spacing"] / 2.0, +ad["screw_spacing"] / 2.0):
            pilot = _y_cylinder(ad["screw_pilot_dia"] / 2.0, ax + sx, L["fiber_z"],
                                y_start=L["plenum_y1"] - 1.0, length=h["wall"] + 2.0)
            base = base.cut(pilot)

    # --- Support studs: 4 per bay, pilot-less, under BARE plate -------------
    # The module's corner holes are occupied by vendor press-fit standoffs
    # whose hardware protrudes 1.5mm below the plate, so the studs sit ~6mm
    # inboard of the corners (stud_z) where the underside is clean. They only
    # carry the plate; retention comes from the two screw bosses below.
    stud_r = h["stud_dia"] / 2.0
    boss_top = L["plate_bottom_z"]
    for cx in L["bay_cx"]:
        for sx in (-h["stud_dx"], +h["stud_dx"]):
            for sz in h["stud_z"]:
                stud = (
                    cq.Workplane("XY")
                    .circle(stud_r).extrude(boss_top)
                    .translate((cx + sx, -sz, 0))
                )
                base = base.union(stud)

    # --- Screw bosses: M3 through the module's two FREE 3.175mm holes -------
    # (front inner + back center). The front hole is handed (TX mirrored);
    # the back hole sits on the bay centerline.
    sb_r = h["screw_boss_dia"] / 2.0
    sb_pilot_r = h["screw_boss_pilot_dia"] / 2.0
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1.0 if bay.get("mirror_x") else 1.0
        for hole in (m["screw_hole_front"], m["screw_hole_back"]):
            x = cx + sign * hole["x"]
            y = -hole["z"]  # module +Z -> housing -Y
            boss = (
                cq.Workplane("XY")
                .circle(sb_r).extrude(boss_top)
                .translate((x, y, 0))
            )
            base = base.union(boss)
            # thread-forming pilot, boss top down into the floor (0.5 web
            # left) — an M3x6 needs ~4.4mm of engagement below the plate
            pilot = (
                cq.Workplane("XY")
                .circle(sb_pilot_r).extrude(boss_top)
                .translate((x, y, 0.5))
            )
            base = base.cut(pilot)

    # --- Lid-screw posts: three along the central rib -----------------------
    post_r = h["corner_post_dia"] / 2.0
    post_pilot_r = h["corner_post_pilot_dia"] / 2.0
    post_ys = [-(L["interior_half_y"] - post_r - 1.0), 0.0,
               +(L["interior_half_y"] - post_r - 1.0)]
    for py in post_ys:
        post = cq.Workplane("XY").circle(post_r).extrude(L["base_height"]).translate((0, py, 0))
        base = base.union(post)
        pilot = (
            cq.Workplane("XY")
            .circle(post_pilot_r).extrude(L["base_height"] - h["floor"] + 0.5)
            .translate((0, py, h["floor"]))
        )
        base = base.cut(pilot)

    # --- Front-panel SMA clearance holes (one per bay, handed) ---------------
    # The round hole passes the barrel; the shallow relief pocket in the wall's
    # interior face clears the SMA's square base block, which sticks out
    # sma_base_beyond_plate (1.65) past the plate edge — more than the bay's
    # clearance_end (1.5). Without the pocket the base bears on the wall.
    sma_r = h["sma_hole_dia"] / 2.0
    relief_d = (m["sma_base_beyond_plate"] - h["clearance_end"]
                + h["sma_relief_margin"])
    relief_w = m["sma_base_w"] + 2 * h["sma_relief_margin"]
    relief_h = m["sma_base_h"] + 2 * h["sma_relief_margin"]
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        sign = -1.0 if bay.get("mirror_x") else 1.0
        x = cx + sign * m["sma_axis_x"]
        z = L["plate_bottom_z"] + m["sma_axis_y"]
        hole = _y_cylinder(sma_r, x, z,
                           y_start=-L["outer_half_y"] - 1.0, length=h["wall"] + 2.0)
        base = base.cut(hole)
        if relief_d > 0:
            pocket = (
                cq.Workplane("XY")
                .box(relief_w, relief_d + 0.1, relief_h, centered=(True, False, True))
                .translate((x, -L["interior_half_y"] - relief_d, z))
            )
            base = base.cut(pocket)

    # --- Front-panel wiring slots (one per bay, over the header block, handed)
    # Housings with a rear panel connector route the header wires over the can
    # tops into the plenum instead — no front slots (front_wiring_slots false).
    if h.get("front_wiring_slots", True):
        slot_x0 = m["header_x_min"] - h["header_slot_margin"]
        slot_x1 = m["header_x_max"] + h["header_slot_margin"]
        slot_w = slot_x1 - slot_x0
        slot_z0 = L["plate_bottom_z"]
        slot_z1 = L["plate_bottom_z"] + m["header_top_y"] + h["header_slot_top_clear"]
        slot_h = slot_z1 - slot_z0
        for bay, cx in zip(L["bays"], L["bay_cx"]):
            bx0 = -slot_x1 if bay.get("mirror_x") else slot_x0
            slot = (
                cq.Workplane("XY")
                .box(slot_w, h["wall"] + 2.0, slot_h, centered=(False, True, False))
                .translate((cx + bx0, -L["outer_half_y"] + h["wall"] / 2.0, slot_z0))
            )
            base = base.cut(slot)

    # --- Back-panel signal connector (optional, e.g. a DE-9) -----------------
    # Rectangular cutout + two jackscrew holes through the back wall. The
    # rear shell / solder-cup keep-out behind it is verified in the tests.
    pc = params.get("panel_connector")
    if pc:
        cutout = (
            cq.Workplane("XY")
            .box(pc["cutout_w"], h["wall"] + 2.0, pc["cutout_h"],
                 centered=(True, True, True))
            .translate((pc["x"], L["plenum_y1"] + h["wall"] / 2.0, pc["z"]))
        )
        base = base.cut(cutout)
        for sx in (-pc["screw_spacing"] / 2.0, +pc["screw_spacing"] / 2.0):
            hole = _y_cylinder(pc["screw_hole_dia"] / 2.0, pc["x"] + sx, pc["z"],
                               y_start=L["plenum_y1"] - 1.0, length=h["wall"] + 2.0)
            base = base.cut(hole)

    return base


# ---------------------------------------------------------------------------
# Lid
# ---------------------------------------------------------------------------
def create_lid(params: dict) -> cq.Workplane:
    m = params["housing"]
    mm = params["module"]
    L = layout(params)

    z0 = L["base_height"]
    lid = (
        cq.Workplane("XY")
        .box(2 * L["outer_half_x"], L["total_depth"], m["lid_thickness"],
             centered=(True, False, False))
        .translate((0, -L["outer_half_y"], z0))
    )

    # Registration lip: one pad per module bay, nesting inside that bay's
    # cavity. (A single full-interior box — the v2 approach — overlapped the
    # central rib, its screw posts, and now the partition/spool, so the lid
    # could never seat.) The plenum gets no lip: a 0.3mm-gap edge there could
    # pinch a stray fiber wrap against the wall, and the bay pads already
    # register the lid in X and Y.
    #
    # Variants that route the header harness internally (front_wiring_slots
    # false) get a perimeter RING lip instead of a solid pad — a solid pad
    # would leave only ~1mm over the can top and pinch the wires — with a gap
    # in its rear segment over the partition pass-slot where the wires and
    # fiber climb into the plenum.
    lip_depth = 2.0
    lip_gap = 0.3
    lip_ring_w = 3.0
    internal_wiring = not m.get("front_wiring_slots", True)
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        lip = (
            cq.Workplane("XY")
            .box(L["bay_w"] - 2 * lip_gap, L["bay_d"] - 2 * lip_gap,
                 lip_depth, centered=(True, True, False))
            .translate((cx, 0, z0 - lip_depth))
        )
        if internal_wiring:
            core = (
                cq.Workplane("XY")
                .box(L["bay_w"] - 2 * lip_gap - 2 * lip_ring_w,
                     L["bay_d"] - 2 * lip_gap - 2 * lip_ring_w,
                     lip_depth + 1.0, centered=(True, True, False))
                .translate((cx, 0, z0 - lip_depth - 0.5))
            )
            lip = lip.cut(core)
            slot_gap = (
                cq.Workplane("XY")
                .box(params["fiber_bay"]["pass_slot_width"],
                     lip_ring_w + lip_gap + 1.0, lip_depth + 1.0,
                     centered=(True, False, False))
                .translate((cx + mm["fiber_exit_x"],
                            L["bay_d"] / 2.0 - lip_gap - lip_ring_w - 0.5,
                            z0 - lip_depth - 0.5))
            )
            lip = lip.cut(slot_gap)
        lid = lid.union(lip)

    # The rib screw posts bulge past the bay-cavity edge (post radius > half
    # the bay gap) — scallop the lip pads around them so the lid can seat
    post_r = m["corner_post_dia"] / 2.0
    for py in [-(L["interior_half_y"] - post_r - 1.0), 0.0,
               +(L["interior_half_y"] - post_r - 1.0)]:
        scallop = (
            cq.Workplane("XY")
            .circle(post_r + lip_gap).extrude(lip_depth + 0.5)
            .translate((0, py, z0 - lip_depth - 0.5))
        )
        lid = lid.cut(scallop)

    # Header access openings, directly above each pin-header block (handed)
    op_x0 = mm["header_x_min"] - m["header_slot_margin"]
    op_x1 = mm["header_x_max"] + m["header_slot_margin"]
    op_w = op_x1 - op_x0
    op_y0 = -mm["header_z_max"]  # module +Z -> housing -Y
    op_y1 = -mm["header_z_min"]
    op_d = op_y1 - op_y0
    for bay, cx in zip(L["bays"], L["bay_cx"]):
        bx0 = -op_x1 if bay.get("mirror_x") else op_x0
        opening = (
            cq.Workplane("XY")
            .box(op_w, op_d, m["lid_thickness"] + lip_depth + 2.0, centered=(False, False, False))
            .translate((cx + bx0, op_y0, z0 - lip_depth - 1.0))
        )
        lid = lid.cut(opening)

    # Lid screw clearance holes: three rib posts, the spool, two back corners
    clr_r = m["lid_screw_clear_dia"] / 2.0
    head_r = m["lid_screw_head_dia"] / 2.0
    post_r = m["corner_post_dia"] / 2.0
    screw_xy = [(0.0, -(L["interior_half_y"] - post_r - 1.0)),
                (0.0, 0.0),
                (0.0, +(L["interior_half_y"] - post_r - 1.0)),
                (0.0, L["spool_y"]),
                (-(L["interior_half_x"] - post_r - 1.0), L["plenum_y1"] - post_r - 1.0),
                (+(L["interior_half_x"] - post_r - 1.0), L["plenum_y1"] - post_r - 1.0)]
    for px, py in screw_xy:
        # counterbored so the screw head sits flush in the lid top
        cbore = (
            cq.Workplane("XY")
            .circle(clr_r).extrude(m["lid_thickness"] + lip_depth + 1.0)
            .translate((px, py, z0 - lip_depth))
        )
        head = (
            cq.Workplane("XY")
            .circle(head_r).extrude(1.6)
            .translate((px, py, z0 + m["lid_thickness"] - 1.6))
        )
        lid = lid.cut(cbore).cut(head)

    return lid


# ---------------------------------------------------------------------------
# Assembly (base + lid) as a single compound, matching create_part() convention
# ---------------------------------------------------------------------------
def create_part(params: dict | None = None) -> cq.Workplane:
    if params is None:
        params = load_params()

    base = create_base(params)
    lid = create_lid(params)

    explode = params["housing"].get("explode_gap", 0.0)
    if explode:
        lid = lid.translate((0, 0, explode))

    compound = cq.Compound.makeCompound([base.val(), lid.val()])
    return cq.Workplane("XY").newObject([compound])


def export_part(result, name="oz510-dual-housing", version="v1", formats=None):
    if formats is None:
        formats = ["step"]
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
    print(f"  Outer envelope: {2*L['outer_half_x']:.1f} (W) × "
          f"{L['total_depth']:.1f} (D) × "
          f"{L['base_height'] + params['housing']['lid_thickness']:.1f} (H) mm\n")

    fmts = ["step"] + (["stl"] if "--stl" in sys.argv else [])
    export_part(part, version=params.get("version", "v1"), formats=fmts)

    try:
        from ocp_vscode import show

        show(part)
        print("\n  📐 Model displayed in OCP CAD Viewer")
    except Exception:
        # No viewer running (e.g. headless) — export already succeeded.
        pass
