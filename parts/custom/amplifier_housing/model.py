"""
AM10-231A Amplifier Housing — v3
=================================
Two-piece mounting system for outdoor antenna rotator head installation.

v3 fixes identified in v2 design review:
  - Thermal: standoffs decouple amp from sun-heated baseplate/rotator plate;
    rain hood replaced with raised sun shade that doesn't trap convective heat
  - Airflow: louvers repositioned to upper wall zone, aligned with heatsink fins
  - EMI: ground bonding stud with bare-aluminum contact zone callout
  - Mechanical: cable clamp bosses moved to 15mm from connectors (was ~50mm)
    to prevent SMA flex fatigue during rotator cycles
  - Weight: baseplate pocketed from underside, saving ~150g

Pieces:
  1. **Base Plate** — bolts permanently to rotator head via slotted holes.
     Has dovetail rails for the cradle to slide onto.
  2. **Cradle** — holds the amplifier on thermal standoffs, slides onto the
     base plate, locks with two M6 thumb screws.

Units: mm (all dimensions)
"""

import json
import math
import sys
from pathlib import Path

import cadquery as cq

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"


def load_params(path: Path = PARAMS_FILE) -> dict:
    """Load the part parameters from its JSON engineering brief."""
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Amplifier ghost (for assembly visualization)
# ---------------------------------------------------------------------------
def create_amplifier_ghost(params: dict) -> cq.Workplane:
    """
    Simplified amplifier body for assembly visualization.
    Positioned on top of thermal standoffs (bottom face at Z = standoff_h).
    """
    amp = params["amplifier"]
    standoff_h = params["housing"]["thermal_standoffs"]["height"]
    return (
        cq.Workplane("XY")
        .box(amp["length"], amp["width"], amp["height"],
             centered=(True, True, False))
        .translate((0, 0, standoff_h))
    )


# ---------------------------------------------------------------------------
# Helper: amplifier mounting hole positions (housing-centered coords)
# ---------------------------------------------------------------------------
def _amp_hole_positions(params: dict) -> list[tuple[float, float]]:
    """
    Return (x, y) positions of all 13 amplifier mounting holes,
    in housing-centered coordinates (origin at center of amp footprint).
    """
    amp = params["amplifier"]
    mount = amp["mounting_holes"]
    ox = -amp["length"] / 2
    oy = -amp["width"] / 2

    positions = []
    for x in mount["x_positions_edge"]:
        positions.append((ox + x, oy + mount["bottom_row_y"]))
    for x in mount["x_positions_middle"]:
        positions.append((ox + x, oy + mount["middle_row_y"]))
    for x in mount["x_positions_edge"]:
        positions.append((ox + x, oy + mount["top_row_y"]))

    return positions


# ---------------------------------------------------------------------------
# CRADLE — the main housing piece
# ---------------------------------------------------------------------------
def create_cradle(params: dict | None = None) -> cq.Workplane:
    """
    Build the amplifier cradle — holds the amplifier on thermal standoffs
    and slides onto the base plate.
    """
    if params is None:
        params = load_params()

    # --- Unpack amplifier dimensions -----------------------------------------
    amp = params["amplifier"]
    amp_length = amp["length"]
    amp_width = amp["width"]
    amp_height = amp["height"]
    mount_hole_d = amp["mounting_holes"]["hole_diameter"]

    # --- Unpack housing parameters -------------------------------------------
    h = params["housing"]
    wall_t = h["wall_thickness"]
    base_t = h["baseplate_thickness"]
    overhang_x = h["overhang_x"]
    overhang_y = h["overhang_y"]
    hs_clearance = h["heatsink_clearance"]

    standoffs = h["thermal_standoffs"]
    standoff_h = standoffs["height"]
    standoff_d = standoffs["diameter"]

    sw = h["side_walls"]
    gusset_count = sw["gusset_count"]
    gusset_t = sw["gusset_thickness"]
    gusset_h = sw["gusset_height"]
    gusset_base_l = sw["gusset_base_length"]
    flare_angle = sw["flare_angle"]
    flare_h = sw["flare_height"]

    louvers = h["airflow_louvers"]
    louver_count = louvers["slot_count_per_row"]
    louver_w = louvers["slot_width"]
    louver_h = louvers["slot_height"]
    louver_pitch = louvers["slot_pitch"]
    louver_start_x = louvers["slot_start_x"]
    row_ratios = louvers["row_z_ratios"]

    shade = h["sun_shade"]
    shade_overhang = shade["overhang_width"]
    shade_t = shade["thickness"]
    shade_above = shade["height_above_wall"]
    shade_post_w = shade["post_width"]
    shade_post_d = shade["post_depth"]
    shade_post_inset_x = shade["post_inset_x"]

    ground = h["ground_bonding"]
    ground_stud_d = ground["stud_diameter"]
    ground_stud_h = ground["stud_height"]
    ground_stud_hole_d = ground["stud_hole_diameter"]

    pockets = h["baseplate_pockets"]
    pocket_depth = pockets["pocket_depth"]
    pocket_margin = pockets["edge_margin"]
    pocket_r = pockets["pocket_corner_radius"]

    ribs = h["stiffening_ribs"]
    rib_h = ribs["rib_height"]
    rib_t = ribs["rib_thickness"]
    rib_count_w = ribs["count_across_width"]

    drains = h["drain_slots"]
    drain_w = drains["width"]
    drain_h = drains["height"]
    drain_count = drains["count_per_side"]
    drain_spacing = drains["spacing"]

    cable = h["cable_management"]
    clamp_dist = cable["clamp_distance_from_end"]
    td_boss_d = cable["tiedown_boss_diameter"]
    td_boss_hole = cable["tiedown_boss_hole"]
    td_boss_h = cable["tiedown_boss_height"]
    td_boss_count = cable["tiedown_boss_count"]
    td_boss_spacing = cable["tiedown_boss_spacing"]

    fillets = h["edge_fillets"]
    outer_r = fillets["outer_radius"]

    lock = h["cradle_mounting"]
    lock_d = lock["lock_screw_diameter"]
    lock_inset_x = lock["lock_screw_inset_x"]

    # --- Derived dimensions --------------------------------------------------
    housing_length = amp_length + 2 * overhang_x
    housing_width = amp_width + 2 * (overhang_y + wall_t)
    # Wall height accounts for standoff raising the amplifier
    wall_height = standoff_h + amp_height + hs_clearance
    flare_offset = flare_h * math.tan(math.radians(flare_angle))
    total_wall_h = wall_height + flare_h

    # =========================================================================
    # Step 1: Baseplate
    # =========================================================================
    result = (
        cq.Workplane("XY")
        .box(housing_length, housing_width, base_t,
             centered=(True, True, False))
        .translate((0, 0, -base_t))
    )

    # =========================================================================
    # Step 2: Side walls (taller to account for standoffs)
    # =========================================================================
    for sign in [-1, 1]:
        wall_y = sign * (housing_width / 2 - wall_t / 2)
        wall = (
            cq.Workplane("XY")
            .box(housing_length, wall_t, wall_height,
                 centered=(True, True, False))
            .translate((0, wall_y, 0))
        )
        result = result.union(wall)

    # =========================================================================
    # Step 3: Wind-scoop flare at top of side walls
    # =========================================================================
    for sign in [-1, 1]:
        wall_inner_y = sign * (housing_width / 2 - wall_t)
        wall_outer_y = sign * (housing_width / 2)
        flare_outer_y = wall_outer_y + sign * flare_offset

        pts = [
            (wall_inner_y, wall_height),
            (wall_outer_y, wall_height),
            (flare_outer_y, wall_height + flare_h),
            (wall_inner_y, wall_height + flare_h),
        ]
        flare = (
            cq.Workplane("YZ")
            .polyline(pts)
            .close()
            .extrude(housing_length)
        )
        flare = flare.translate((-housing_length / 2, 0, 0))
        result = result.union(flare)

    # =========================================================================
    # Step 4: Thermal standoffs at 13 mounting hole positions
    # =========================================================================
    amp_holes = _amp_hole_positions(params)

    for hx, hy in amp_holes:
        standoff_body = (
            cq.Workplane("XY")
            .workplane(offset=0)
            .center(hx, hy)
            .circle(standoff_d / 2)
            .extrude(standoff_h)
        )
        result = result.union(standoff_body)

    # =========================================================================
    # Step 5: Gussets (triangular stiffeners)
    # =========================================================================
    gusset_spacing = housing_length / (gusset_count + 1)

    for sign in [-1, 1]:
        wall_inner_face_y = sign * (housing_width / 2 - wall_t)

        for i in range(gusset_count):
            gx = -housing_length / 2 + (i + 1) * gusset_spacing

            if sign == -1:
                tri_pts = [
                    (wall_inner_face_y, 0),
                    (wall_inner_face_y, gusset_h),
                    (wall_inner_face_y + gusset_base_l, 0),
                ]
            else:
                tri_pts = [
                    (wall_inner_face_y, 0),
                    (wall_inner_face_y, gusset_h),
                    (wall_inner_face_y - gusset_base_l, 0),
                ]

            gusset = (
                cq.Workplane("YZ")
                .polyline(tri_pts)
                .close()
                .extrude(gusset_t)
                .translate((gx - gusset_t / 2, 0, 0))
            )
            result = result.union(gusset)

    # =========================================================================
    # Step 6: Airflow louvers (3 rows in upper wall zone)
    # =========================================================================
    amp_left = -amp_length / 2

    for ratio in row_ratios:
        louver_z = wall_height * ratio

        for i in range(louver_count):
            slot_x = amp_left + louver_start_x + i * louver_pitch + louver_w / 2

            for sign in [-1, 1]:
                wall_y = sign * (housing_width / 2 - wall_t / 2)
                slot_cut = (
                    cq.Workplane("XY")
                    .box(louver_w, wall_t + 2, louver_h,
                         centered=(True, True, True))
                    .translate((slot_x, wall_y, louver_z))
                )
                result = result.cut(slot_cut)

    # =========================================================================
    # Step 7: Drain slots at base of side walls
    # =========================================================================
    drain_start_x = -(drain_count - 1) * drain_spacing / 2

    for i in range(drain_count):
        dx = drain_start_x + i * drain_spacing
        for sign in [-1, 1]:
            wall_y = sign * (housing_width / 2 - wall_t / 2)
            drain_cut = (
                cq.Workplane("XY")
                .box(drain_w, wall_t + 2, drain_h,
                     centered=(True, True, True))
                .translate((dx, wall_y, drain_h / 2))
            )
            result = result.cut(drain_cut)

    # =========================================================================
    # Step 8: Sun shade (raised plate on 4 posts — replaces v2 rain hood)
    # =========================================================================
    shade_z = total_wall_h + shade_above
    shade_length = housing_length - 30  # Margin from ends
    shade_width = housing_width + 2 * flare_offset + 2 * shade_overhang

    # Shade plate
    shade_plate = (
        cq.Workplane("XY")
        .box(shade_length, shade_width, shade_t,
             centered=(True, True, False))
        .translate((0, 0, shade_z))
    )
    result = result.union(shade_plate)

    # 4 support posts (2 per side)
    for sign_x in [-1, 1]:
        for sign_y in [-1, 1]:
            px = sign_x * (housing_length / 2 - shade_post_inset_x)
            py = sign_y * (housing_width / 2 + flare_offset)
            post_height = shade_above

            post = (
                cq.Workplane("XY")
                .box(shade_post_w, shade_post_d, post_height,
                     centered=(True, True, False))
                .translate((px, py, total_wall_h))
            )
            result = result.union(post)

    # =========================================================================
    # Step 9: End drip lips (top edge overhang on open ends)
    # =========================================================================
    drip_lip_depth = 8.0
    drip_lip_t = 2.5

    for sign_x in [-1, 1]:
        lip_x = sign_x * (housing_length / 2)
        lip = (
            cq.Workplane("XY")
            .box(drip_lip_t, housing_width + 2 * flare_offset, drip_lip_depth,
                 centered=(True, True, False))
            .translate((lip_x, 0, total_wall_h - drip_lip_depth))
        )
        result = result.union(lip)

    # =========================================================================
    # Step 10: Ground bonding stud
    # =========================================================================
    # Positioned on baseplate top, near output end (+X), in overhang zone
    ground_x = housing_length / 2 - 20
    ground_y = amp_width / 2 + overhang_y / 2  # Between amp edge and wall

    ground_boss = (
        cq.Workplane("XY")
        .workplane(offset=0)
        .center(ground_x, ground_y)
        .circle(ground_stud_d / 2)
        .extrude(ground_stud_h)
    )
    result = result.union(ground_boss)

    # Hole through the ground stud (M5 tapped)
    ground_hole = (
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .center(ground_x, ground_y)
        .circle(ground_stud_hole_d / 2)
        .extrude(ground_stud_h + 1)
    )
    result = result.cut(ground_hole)

    # =========================================================================
    # Step 11: Cable clamp bosses (close to connectors — 15mm from end)
    # =========================================================================
    boss_x = housing_length / 2 - clamp_dist
    td_start_y = -(td_boss_count - 1) * td_boss_spacing / 2

    for i in range(td_boss_count):
        by = td_start_y + i * td_boss_spacing

        boss = (
            cq.Workplane("XY")
            .workplane(offset=0)
            .center(boss_x, by)
            .circle(td_boss_d / 2)
            .extrude(td_boss_h)
        )
        boss_hole = (
            cq.Workplane("XY")
            .workplane(offset=-0.5)
            .center(boss_x, by)
            .circle(td_boss_hole / 2)
            .extrude(td_boss_h + 1)
        )
        result = result.union(boss)
        result = result.cut(boss_hole)

    # =========================================================================
    # Step 12: Amplifier mounting holes (through standoffs + baseplate)
    # =========================================================================
    for hx, hy in amp_holes:
        hole_cut = (
            cq.Workplane("XY")
            .workplane(offset=-base_t - 0.5)
            .center(hx, hy)
            .circle(mount_hole_d / 2)
            .extrude(base_t + standoff_h + 1)
        )
        result = result.cut(hole_cut)

    # =========================================================================
    # Step 13: Lock screw holes (M6 through baseplate flanges)
    # =========================================================================
    for sign_x in [-1, 1]:
        lx = sign_x * (housing_length / 2 - lock_inset_x)
        for sign_y in [-1, 1]:
            ly = sign_y * (housing_width / 2 - wall_t / 2)
            lock_hole = (
                cq.Workplane("XY")
                .workplane(offset=-base_t - 0.5)
                .center(lx, ly)
                .circle(lock_d / 2)
                .extrude(base_t + 1)
            )
            result = result.cut(lock_hole)

    # =========================================================================
    # Step 14: Stiffening ribs on baseplate underside
    # =========================================================================
    rib_positions_x = []
    for i in range(rib_count_w):
        rx = -housing_length / 2 + (i + 1) * housing_length / (rib_count_w + 1)
        rib_positions_x.append(rx)

    for rx in rib_positions_x:
        rib_body = (
            cq.Workplane("XY")
            .box(rib_t, housing_width - 2 * wall_t, rib_h,
                 centered=(True, True, False))
            .translate((rx, 0, -base_t - rib_h))
        )
        result = result.union(rib_body)

    # =========================================================================
    # Step 15: Baseplate pockets (weight reduction from underside)
    # =========================================================================
    # Cut pockets between the stiffening ribs, from the bottom of the baseplate.
    # With 2 ribs, we get 3 zones along X.
    rib_positions_sorted = sorted(rib_positions_x)

    # Define pocket zone boundaries along X
    pocket_zones_x = []
    # Zone 1: left edge to first rib
    pocket_zones_x.append((
        -housing_length / 2 + pocket_margin,
        rib_positions_sorted[0] - rib_t / 2 - 2
    ))
    # Zone 2: between ribs
    for j in range(len(rib_positions_sorted) - 1):
        pocket_zones_x.append((
            rib_positions_sorted[j] + rib_t / 2 + 2,
            rib_positions_sorted[j + 1] - rib_t / 2 - 2
        ))
    # Zone 3: last rib to right edge
    pocket_zones_x.append((
        rib_positions_sorted[-1] + rib_t / 2 + 2,
        housing_length / 2 - pocket_margin
    ))

    pocket_y_extent = housing_width - 2 * (wall_t + pocket_margin)

    for (px_start, px_end) in pocket_zones_x:
        pocket_lx = px_end - px_start
        if pocket_lx < 20:
            continue  # Skip pockets that are too small

        pocket_cx = (px_start + px_end) / 2
        pocket_cut = (
            cq.Workplane("XY")
            .box(pocket_lx, pocket_y_extent, pocket_depth,
                 centered=(True, True, False))
            .translate((pocket_cx, 0, -base_t))
        )
        # Round pocket corners for machinability
        try:
            pocket_cut = pocket_cut.edges("|Z").fillet(pocket_r)
        except Exception:
            pass
        result = result.cut(pocket_cut)

    # =========================================================================
    # Step 16: Fillet outer edges
    # =========================================================================
    try:
        result = result.edges("|Z").fillet(outer_r)
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# BASE PLATE — the rotator mounting piece
# ---------------------------------------------------------------------------
def create_base_plate(params: dict | None = None) -> cq.Workplane:
    """
    Build the base plate that bolts permanently to the rotator head.
    Features dovetail rails and slotted mounting holes.
    """
    if params is None:
        params = load_params()

    amp = params["amplifier"]
    h = params["housing"]
    wall_t = h["wall_thickness"]
    overhang_x = h["overhang_x"]
    overhang_y = h["overhang_y"]
    base_t = h["baseplate_thickness"]
    rib_h = h["stiffening_ribs"]["rib_height"]

    bp = h["base_plate"]
    bp_t = bp["thickness"]
    bp_extra = bp["length_extra"]
    rail_h = bp["rail_height"]
    rail_w = bp["rail_width"]
    rail_top_w = bp["rail_top_width"]

    bm = bp["mounting_holes"]
    bm_hole_d = bm["hole_diameter"]
    bm_slot_l = bm["slot_length"]
    bm_inset_x = bm["inset_x"]
    bm_inset_y = bm["inset_y"]
    bm_count_x = bm["count_x"]
    bm_count_y = bm["count_y"]

    # --- Derived dimensions --------------------------------------------------
    housing_length = amp["length"] + 2 * overhang_x
    housing_width = amp["width"] + 2 * (overhang_y + wall_t)

    bp_length = housing_length + bp_extra
    bp_width = housing_width + 10

    # Base plate top meets cradle bottom (below baseplate + ribs)
    bp_z_top = -(base_t + rib_h)

    # =========================================================================
    # Step 1: Flat plate
    # =========================================================================
    result = (
        cq.Workplane("XY")
        .box(bp_length, bp_width, bp_t, centered=(True, True, False))
        .translate((bp_extra / 2, 0, bp_z_top - bp_t))
    )

    # =========================================================================
    # Step 2: Dovetail rails
    # =========================================================================
    for sign in [-1, 1]:
        rail_y = sign * (housing_width / 2 - wall_t / 2)

        half_base = rail_w / 2
        half_top = rail_top_w / 2

        rail_pts = [
            (-half_base, 0),
            (half_base, 0),
            (half_top, rail_h),
            (-half_top, rail_h),
        ]

        rail = (
            cq.Workplane("XZ")
            .polyline(rail_pts)
            .close()
            .extrude(bp_length)
            .translate((-bp_length / 2 + bp_extra / 2, rail_y, bp_z_top))
        )
        result = result.union(rail)

    # =========================================================================
    # Step 3: Slotted mounting holes
    # =========================================================================
    x_positions = []
    for i in range(bm_count_x):
        x_positions.append(
            -bp_length / 2 + bp_extra / 2 + bm_inset_x
            + i * (bp_length - 2 * bm_inset_x) / max(bm_count_x - 1, 1)
        )

    y_positions = []
    for i in range(bm_count_y):
        y_positions.append(
            -bp_width / 2 + bm_inset_y
            + i * (bp_width - 2 * bm_inset_y) / max(bm_count_y - 1, 1)
        )

    for mx in x_positions:
        for my in y_positions:
            slot = (
                cq.Workplane("XY")
                .workplane(offset=bp_z_top - bp_t - 0.5)
                .center(mx, my)
                .slot2D(bm_slot_l, bm_hole_d)
                .extrude(bp_t + 1)
            )
            result = result.cut(slot)

    # =========================================================================
    # Step 4: Chamfered lead-in on rails
    # =========================================================================
    chamfer_len = 15.0
    for sign in [-1, 1]:
        rail_y = sign * (housing_width / 2 - wall_t / 2)

        wedge_pts = [
            (0, 0),
            (0, rail_h),
            (chamfer_len, 0),
        ]
        wedge = (
            cq.Workplane("XZ")
            .polyline(wedge_pts)
            .close()
            .extrude(rail_w + 2, both=True)
            .translate((-bp_length / 2 + bp_extra / 2, rail_y, bp_z_top))
        )
        result = result.cut(wedge)

    # =========================================================================
    # Step 5: Fillet outer edges
    # =========================================================================
    try:
        result = result.edges("|Z").fillet(1.5)
    except Exception:
        pass

    return result


# ---------------------------------------------------------------------------
# Unified interface
# ---------------------------------------------------------------------------
def create_part(params: dict | None = None) -> cq.Workplane:
    """Build the amplifier housing cradle (primary part)."""
    return create_cradle(params)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
def create_assembly(params: dict | None = None) -> cq.Assembly:
    """Create assembly: cradle + base plate + amplifier ghost."""
    if params is None:
        params = load_params()

    cradle = create_cradle(params)
    base_plate = create_base_plate(params)
    amp_ghost = create_amplifier_ghost(params)

    assy = cq.Assembly()
    assy.add(cradle, name="cradle", color=cq.Color(0.75, 0.75, 0.75, 1.0))
    assy.add(base_plate, name="base_plate", color=cq.Color(0.5, 0.5, 0.55, 1.0))
    assy.add(amp_ghost, name="amplifier_ghost", color=cq.Color(0.2, 0.4, 0.8, 0.4))

    return assy


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def export_part(
    result: cq.Workplane,
    name: str = "amplifier_housing",
    version: str = "v3",
    formats: list[str] | None = None,
) -> list[Path]:
    """Export the part to the part's exports/ directory with version in filename."""
    if formats is None:
        formats = ["step"]

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    exported = []

    for fmt in formats:
        out_path = EXPORTS_DIR / f"{name}_{version}.{fmt}"
        cq.exporters.export(result, str(out_path))
        print(f"  ✓ Exported {out_path.relative_to(PROJECT_ROOT)}")
        exported.append(out_path)

    return exported


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    params = load_params()
    version = params.get("version", "v3")

    amp = params["amplifier"]
    h = params["housing"]
    sw = h["side_walls"]
    standoff_h = h["thermal_standoffs"]["height"]
    housing_length = amp["length"] + 2 * h["overhang_x"]
    housing_width = amp["width"] + 2 * (h["overhang_y"] + h["wall_thickness"])
    wall_height = standoff_h + amp["height"] + h["heatsink_clearance"]
    total_wall_h = wall_height + sw["flare_height"]
    shade_top = total_wall_h + h["sun_shade"]["height_above_wall"] + h["sun_shade"]["thickness"]

    print(f"\n  Building: {params['part_name']} ({version})")
    print(f"  Material: {params.get('material', 'N/A')}")
    print(f"  Process:  {params.get('process', 'N/A')}")
    print(f"  Cradle envelope: {housing_length:.0f} × {housing_width:.0f} × "
          f"{shade_top + h['baseplate_thickness']:.0f} mm")
    print(f"  Amplifier pocket: {amp['length']} × {amp['width']} × {amp['height']} mm")
    print(f"  Thermal standoffs: {standoff_h} mm (decouples amp from baseplate)")
    print(f"  Heatsink clearance: {h['heatsink_clearance']} mm")
    print(f"  Wall height: {wall_height:.0f} mm (incl. standoff)")
    print(f"  Sun shade gap: {h['sun_shade']['height_above_wall']} mm above flare top")
    print(f"  Louver rows: {len(h['airflow_louvers']['row_z_ratios'])} rows at "
          f"{h['airflow_louvers']['row_z_ratios']}")
    print(f"  Baseplate pocketing: {h['baseplate_pockets']['pocket_depth']} mm deep")
    print()

    export_formats = ["step"]
    if "--stl" in sys.argv:
        export_formats.append("stl")

    print("  [1/3] Building cradle...")
    cradle = create_cradle(params)
    export_part(cradle, name="amplifier_housing", version=version,
                formats=export_formats)

    print("\n  [2/3] Building base plate...")
    base_plate = create_base_plate(params)
    for fmt in export_formats:
        out_path = EXPORTS_DIR / f"amplifier_housing_{version}_base_plate.{fmt}"
        cq.exporters.export(base_plate, str(out_path))
        print(f"  ✓ Exported {out_path.relative_to(PROJECT_ROOT)}")

    print("\n  [3/3] Building assembly...")
    try:
        assy = create_assembly(params)
        assy_path = EXPORTS_DIR / f"amplifier_housing_{version}_assembly.step"
        assy.save(str(assy_path))
        print(f"  ✓ Exported {assy_path.relative_to(PROJECT_ROOT)} (with amplifier ghost)")
    except Exception as e:
        print(f"  ⚠ Assembly export failed: {e}")

    try:
        from ocp_vscode import show

        show(cradle)
        print(f"\n  📐 Model displayed in OCP CAD Viewer")
    except ImportError:
        print("\n  ℹ  Install ocp-vscode to preview in VS Code")
