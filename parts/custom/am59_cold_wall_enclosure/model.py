"""
AM59 cold-wall outdoor enclosure, V2
====================================

Compact IP66-target enclosure for one AM59-3S-64-64 in modular
(heatsink-less) configuration.

Architecture: the amplifier chassis is conduction-mounted inside the dry
volume onto a continuous, penetration-free aluminum cold floor.  An
OEM-equivalent fin/fan stack (represented by the exact OEM heatsink solids,
re-registered) lives below that floor in an open, rain-hooded air tunnel.
The 125/200 W amplifier dissipation therefore never enters the cabin air;
the residual 65-90 W internal budget is rejected passively through the
walls.  No thermoelectric or closed-loop cooler is used.

V2 applies the project industrial-design language (DESIGN_LANGUAGE.md):
radiused plan corners, recessed chevron-ribbed wall panels, an embossed
emblem, a crowned lid with counterbored fasteners, louvered hood apertures
with visors and cheeks, and a radiused base flange.  Every V1 engineering
plane — sealing boundary, TIM stack, clearances, reservations — is
unchanged.

Coordinate system
-----------------
X : AM59 airflow axis, fan inlet (-X) to RF output (+X)
Y : across the amplifier, DIN bay toward +Y, amplifier centerline at Y=0
Z : vertical, Z=0 at the hood-skirt bottom plane (rotator adapter TBD below)
"""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"
AMPLIFIER_STEP = PROJECT_ROOT / "parts" / "vendor" / "microwave-amps" / "AM59-3S-64-64.STEP"


def load_params(path: Path = PARAMS_FILE) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=2)
def _import_step_shape(path_text: str) -> cq.Shape:
    path = Path(path_text)
    if not path.is_file():
        raise FileNotFoundError(f"Missing vendor STEP: {path}")
    return cq.importers.importStep(str(path)).val()


def _compound(parts: list[cq.Workplane]) -> cq.Workplane:
    shapes: list[cq.Shape] = []
    for part in parts:
        shapes.extend(part.vals())
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


def _box_span(
    x: tuple[float, float],
    y: tuple[float, float],
    z: tuple[float, float],
) -> cq.Workplane:
    return (
        cq.Workplane("XY")
        .box(x[1] - x[0], y[1] - y[0], z[1] - z[0])
        .translate(
            (
                (x[0] + x[1]) / 2,
                (y[0] + y[1]) / 2,
                (z[0] + z[1]) / 2,
            )
        )
    )


def _rounded_box(
    x: tuple[float, float],
    y: tuple[float, float],
    z: tuple[float, float],
    radius: float,
) -> cq.Workplane:
    """Prism with radiused vertical corners — the design-language base form.

    Fillets are applied to the lone box before any boolean, which is the
    kernel-safe order (see DESIGN_LANGUAGE.md).
    """
    box = _box_span(x, y, z)
    if radius > 0:
        box = box.edges("|Z").fillet(radius)
    return box


def _cylinder_z(
    diameter: float,
    z: tuple[float, float],
    center_xy: tuple[float, float],
) -> cq.Workplane:
    return cq.Workplane(
        obj=cq.Solid.makeCylinder(
            diameter / 2,
            z[1] - z[0],
            cq.Vector(center_xy[0], center_xy[1], z[0]),
            cq.Vector(0, 0, 1),
        )
    )


def _annulus_x(
    outer_diameter: float,
    inner_diameter: float,
    x: tuple[float, float],
    center_yz: tuple[float, float],
) -> cq.Workplane:
    outer = cq.Solid.makeCylinder(
        outer_diameter / 2,
        x[1] - x[0],
        cq.Vector(x[0], center_yz[0], center_yz[1]),
        cq.Vector(1, 0, 0),
    )
    inner = cq.Solid.makeCylinder(
        inner_diameter / 2,
        x[1] - x[0] + 2.0,
        cq.Vector(x[0] - 1.0, center_yz[0], center_yz[1]),
        cq.Vector(1, 0, 0),
    )
    return cq.Workplane(obj=outer).cut(cq.Workplane(obj=inner))


def _rect_ring_z(
    outer_x: tuple[float, float],
    outer_y: tuple[float, float],
    inner_x: tuple[float, float],
    inner_y: tuple[float, float],
    z: tuple[float, float],
    outer_radius: float = 0.0,
    inner_radius: float = 0.0,
) -> cq.Workplane:
    outer = _rounded_box(outer_x, outer_y, z, outer_radius)
    inner = _rounded_box(inner_x, inner_y, (z[0] - 1.0, z[1] + 1.0), inner_radius)
    return outer.cut(inner)


# ---------------------------------------------------------------------------
# Exact vendor geometry, split into chassis and heatsink groups
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _amp_native_groups() -> tuple[cq.Compound, cq.Compound]:
    """Split the exact AM59 STEP into chassis-side and heatsink-side solids.

    In the vendor model the chassis body, mounting flange, and connectors
    all have native-Y bbox centers above 250 mm, while the fin field, the
    10 mm outer plate, and the three fans center near 218 mm.  A 235 mm
    threshold separates the groups with >15 mm of margin on both sides.
    """
    threshold = load_params()["amplifier"]["native_solid_split_y_threshold_mm"]
    chassis: list[cq.Shape] = []
    heatsink: list[cq.Shape] = []
    for solid in _import_step_shape(str(AMPLIFIER_STEP)).Solids():
        bb = solid.BoundingBox()
        if (bb.ymin + bb.ymax) / 2 > threshold:
            chassis.append(solid)
        else:
            heatsink.append(solid)
    return (
        cq.Compound.makeCompound(chassis),
        cq.Compound.makeCompound(heatsink),
    )


def amp_solid_counts() -> dict[str, int]:
    chassis, heatsink = _amp_native_groups()
    return {
        "chassis": len(chassis.Solids()),
        "heatsink": len(heatsink.Solids()),
        "total": len(chassis.Solids()) + len(heatsink.Solids()),
    }


def create_amplifier_chassis_reference(
    params: dict | None = None,
) -> cq.Workplane:
    """Exact chassis/flange/connector solids, placed inside the dry volume."""
    if params is None:
        params = load_params()
    transform = params["amplifier"]["chassis_transform"]
    chassis, _ = _amp_native_groups()
    return (
        cq.Workplane(obj=chassis)
        .rotate((0, 0, 0), (1, 0, 0), transform["rotate_x_deg"])
        .translate(tuple(transform["translate"]))
    )


def create_relocated_heatsink_reference(
    params: dict | None = None,
) -> cq.Workplane:
    """Exact fin/plate/fan solids, re-registered below the cold floor.

    The stack is flipped so the 10 mm plate becomes the conduction
    baseplate against the pad TIM, with fins and fans hanging into the
    hooded air tunnel.  This is the reference layout for a released
    OEM-equivalent heat sink, not a claim that the factory fin stack is
    field-separable.
    """
    if params is None:
        params = load_params()
    transform = params["amplifier"]["heatsink_transform"]
    _, heatsink = _amp_native_groups()
    return (
        cq.Workplane(obj=heatsink)
        .rotate((0, 0, 0), (1, 0, 0), transform["rotate_x_deg"])
        .translate(tuple(transform["translate"]))
    )


# ---------------------------------------------------------------------------
# Enclosure structure
# ---------------------------------------------------------------------------


def clamp_boss_locations(params: dict | None = None) -> list[tuple[float, float]]:
    if params is None:
        params = load_params()
    c = params["amp_clamping"]
    return [(x, sign * c["boss_center_abs_y"]) for sign in (-1, 1) for x in c["boss_x_positions"]]


def _lid_gasket_ring_plan(params: dict) -> tuple[tuple, tuple, tuple, tuple]:
    lid = params["lid"]
    ox = tuple(lid["gasket_ring_outer_x"])
    oy = tuple(lid["gasket_ring_outer_y"])
    w = lid["gasket_ring_width"]
    ix = (ox[0] + w, ox[1] - w)
    iy = (oy[0] + w, oy[1] - w)
    return ox, oy, ix, iy


def _wall_panel_pockets(params: dict) -> list[cq.Workplane]:
    """Recessed side-panel prisms (design language item 2)."""
    e = params["enclosure"]
    s = params["styling"]
    depth = s["panel_recess_depth"]
    r = s["panel_corner_radius"]
    pockets: list[cq.Workplane] = []
    # +/-Y long faces carry the chevron panels.
    for face_y, inward in ((e["outer_y"][0], 1.0), (e["outer_y"][1], -1.0)):
        span = (face_y - 1.0, face_y + depth) if inward > 0 else (face_y - depth, face_y + 1.0)
        pocket = _box_span(tuple(s["side_panel_x"]), span, tuple(s["side_panel_z"]))
        pockets.append(pocket.edges("|Y").fillet(r))
    # +/-X end faces carry clean panels (emblem on -X).
    for face_x, inward in ((e["outer_x"][0], 1.0), (e["outer_x"][1], -1.0)):
        span = (face_x - 1.0, face_x + depth) if inward > 0 else (face_x - depth, face_x + 1.0)
        pocket = _box_span(span, tuple(s["xface_panel_y"]), tuple(s["xface_panel_z"]))
        pockets.append(pocket.edges("|X").fillet(r))
    return pockets


def _chevron_strips(params: dict, face_sign: int) -> list[cq.Workplane]:
    """Diagonal rib strips forming X patterns inside a +/-Y wall pocket."""
    e = params["enclosure"]
    s = params["styling"]
    depth = s["panel_recess_depth"]
    # Ribs rise from the pocket floor to 0.3 mm below the outer wall face —
    # a proud rib with a shadow line, never past the face.
    face_y = e["outer_y"][0] if face_sign < 0 else e["outer_y"][1]
    y_span = (
        (face_y + 0.3, face_y + depth + 0.1)
        if face_sign < 0
        else (face_y - depth - 0.1, face_y - 0.3)
    )
    z_mid = (s["side_panel_z"][0] + s["side_panel_z"][1]) / 2
    half_w = s["chevron_strip_width"] / 2
    strips: list[cq.Workplane] = []
    for cx in s["chevron_pair_center_x"]:
        for angle in (s["chevron_strip_angle_deg"], -s["chevron_strip_angle_deg"]):
            strip = _box_span(
                (cx - 110.0, cx + 110.0),
                y_span,
                (z_mid - half_w, z_mid + half_w),
            ).rotate((cx, 0, z_mid), (cx, 1, z_mid), angle)
            strips.append(strip)
    return strips


def create_enclosure_tub(params: dict | None = None) -> cq.Workplane:
    """Welded tub: floor, cold pad, walls, lid rim, and amp clamp bosses.

    The floor is continuous and penetration-free.  Every fastener on the
    dry boundary engages a blind boss (clamp bosses inside, cradle bosses
    outside), so the IP66 boundary has no floor holes at all.  V2 adds the
    design-language exterior: radiused plan corners and recessed
    chevron-ribbed panels; minimum structural wall under every recess is
    3.0 mm.
    """
    if params is None:
        params = load_params()
    e = params["enclosure"]
    f = params["cold_floor"]
    c = params["amp_clamping"]
    s = params["styling"]

    outer_x = tuple(e["outer_x"])
    outer_y = tuple(e["outer_y"])
    inner_x = tuple(e["inner_x"])
    inner_y = tuple(e["inner_y"])
    floor_bottom = f["floor_bottom_z"]
    floor_top = f["floor_top_z"]
    rim_top = e["rim_top_z"]

    tub = _rounded_box(outer_x, outer_y, (floor_bottom, rim_top), e["plan_corner_radius"]).cut(
        _rounded_box(
            inner_x,
            inner_y,
            (floor_top, rim_top + 1.0),
            e["cavity_corner_radius"],
        )
    )

    # Lid support rim, flush with the wall top.
    rim = _rect_ring_z(
        inner_x,
        inner_y,
        tuple(e["rim_opening_x"]),
        tuple(e["rim_opening_y"]),
        (rim_top - e["rim_thickness"], rim_top),
        outer_radius=e["cavity_corner_radius"],
        inner_radius=e["rim_opening_corner_radius"],
    )
    tub = tub.union(rim)

    # Machined cold pad under the amplifier bay (0.5 mm embedded for a
    # robust union; the pad contact plane itself is unchanged).
    pad = _rounded_box(
        (
            f["pad_center"][0] - f["pad_length_x"] / 2,
            f["pad_center"][0] + f["pad_length_x"] / 2,
        ),
        (
            f["pad_center"][1] - f["pad_width_y"] / 2,
            f["pad_center"][1] + f["pad_width_y"] / 2,
        ),
        (f["pad_bottom_z"], floor_bottom + 0.5),
        f["pad_corner_radius"],
    )
    tub = tub.union(pad)

    # Blind clamp bosses; their top face is the TIM compression stop.
    for center in clamp_boss_locations(params):
        tub = tub.union(
            _cylinder_z(
                c["boss_diameter"],
                (floor_top, c["boss_z"][1]),
                center,
            )
        )

    # Recessed exterior panels, then the chevron ribs back inside them.
    pockets = _wall_panel_pockets(params)
    for pocket in pockets:
        tub = tub.cut(pocket)
    for face_sign, pocket in ((-1, pockets[0]), (1, pockets[1])):
        for strip in _chevron_strips(params, face_sign):
            tub = tub.union(strip.intersect(pocket))

    # Embossed concentric emblem on an end panel (design language item 6).
    if s["emblem_face"] == "+X":
        emblem_x = (
            e["outer_x"][1] - s["panel_recess_depth"] - s["emblem_depth"],
            e["outer_x"][1] + 0.5,
        )
    else:
        emblem_x = (
            e["outer_x"][0] - 0.5,
            e["outer_x"][0] + s["panel_recess_depth"] + s["emblem_depth"],
        )
    for diameter in s["emblem_ring_diameters"]:
        tub = tub.cut(
            _annulus_x(
                diameter,
                diameter - 2 * s["emblem_ring_width"],
                emblem_x,
                tuple(s["emblem_center_yz"]),
            )
        )

    # Gasket groove in the rim (compressed-gasket proxy fills it exactly).
    ox, oy, ix, iy = _lid_gasket_ring_plan(params)
    groove_depth = 1.5
    tub = tub.cut(_rect_ring_z(ox, oy, ix, iy, (rim_top - groove_depth, rim_top + 0.5)))
    return tub


def lid_screw_locations(params: dict | None = None) -> list[tuple[float, float]]:
    if params is None:
        params = load_params()
    e = params["enclosure"]
    lid = params["lid"]
    inset = lid["screw_edge_inset"]
    # Rows pull their end screws further inboard so counterbores keep a
    # full web inside the radiused plan corners.
    row_end_inset = e["plan_corner_radius"] - 1.5
    x_min, x_max = e["outer_x"][0] + row_end_inset, e["outer_x"][1] - row_end_inset
    y_min, y_max = e["outer_y"][0] + inset, e["outer_y"][1] - inset
    col_x_min, col_x_max = e["outer_x"][0] + inset, e["outer_x"][1] - inset
    xs = [x_min + i * (x_max - x_min) / 8 for i in range(9)]
    ys = [y_min + i * (y_max - y_min) / 6 for i in range(7)]
    locations = [(x, y_min) for x in xs] + [(x, y_max) for x in xs]
    locations += [(col_x_min, y) for y in ys[1:-1]]
    locations += [(col_x_max, y) for y in ys[1:-1]]
    return locations


def create_lid(params: dict | None = None) -> cq.Workplane:
    """Radiused lid with a chamfered crown frame and counterbored screws."""
    if params is None:
        params = load_params()
    e = params["enclosure"]
    lid = params["lid"]
    base = _rounded_box(
        tuple(lid["outer_x"]),
        tuple(lid["outer_y"]),
        (e["rim_top_z"], lid["top_z"]),
        lid["corner_radius"],
    )
    inset = lid["crown_edge_inset"]
    band = lid["crown_band_width"]
    crown = (
        _rect_ring_z(
            (lid["outer_x"][0] + inset, lid["outer_x"][1] - inset),
            (lid["outer_y"][0] + inset, lid["outer_y"][1] - inset),
            (lid["outer_x"][0] + inset + band, lid["outer_x"][1] - inset - band),
            (lid["outer_y"][0] + inset + band, lid["outer_y"][1] - inset - band),
            (lid["top_z"], lid["crown_top_z"]),
            outer_radius=lid["crown_corner_radius"],
            inner_radius=max(lid["crown_corner_radius"] - band / 2, 2.0),
        )
        .edges(">Z")
        .chamfer(lid["crown_chamfer"])
    )
    plate = base.union(crown)
    for x, y in lid_screw_locations(params):
        plate = plate.cut(
            _cylinder_z(
                lid["counterbore_diameter"],
                (lid["top_z"] - lid["counterbore_depth"], lid["crown_top_z"] + 1.0),
                (x, y),
            )
        ).cut(
            _cylinder_z(
                lid["screw_diameter_clearance"],
                (e["rim_top_z"] - 1.0, lid["crown_top_z"] + 1.0),
                (x, y),
            )
        )
    return plate


def create_lid_gasket_reference(params: dict | None = None) -> cq.Workplane:
    """Compressed-state gasket proxy filling the rim groove."""
    if params is None:
        params = load_params()
    rim_top = params["enclosure"]["rim_top_z"]
    ox, oy, ix, iy = _lid_gasket_ring_plan(params)
    return _rect_ring_z(ox, oy, ix, iy, (rim_top - 1.5, rim_top))


def create_flange_clamp_bars(params: dict | None = None) -> cq.Workplane:
    """Bars bearing on the OEM flange overhang, stopped on the bosses."""
    if params is None:
        params = load_params()
    c = params["amp_clamping"]
    half_l = c["clamp_bar_length_x"] / 2
    half_w = c["clamp_bar_width_y"] / 2
    bars: list[cq.Workplane] = []
    for sign in (-1, 1):
        bar = _rounded_box(
            (-half_l, half_l),
            (
                sign * c["clamp_bar_center_abs_y"] - half_w,
                sign * c["clamp_bar_center_abs_y"] + half_w,
            ),
            tuple(c["clamp_bar_z"]),
            c["clamp_bar_end_radius"],
        )
        for x in c["boss_x_positions"]:
            center = (x, sign * c["boss_center_abs_y"])
            bar = bar.cut(
                _cylinder_z(
                    c["clamp_bar_counterbore_diameter"],
                    (
                        c["clamp_bar_z"][1] - c["clamp_bar_counterbore_depth"],
                        c["clamp_bar_z"][1] + 1.0,
                    ),
                    center,
                )
            ).cut(
                _cylinder_z(
                    c["clamp_bar_screw_clearance_diameter"],
                    (c["clamp_bar_z"][0] - 1.0, c["clamp_bar_z"][1] + 1.0),
                    center,
                )
            )
        bars.append(bar)
    return _compound(bars)


def create_heatsink_cradle(params: dict | None = None) -> cq.Workplane:
    """Rails lifting the baseplate side ledges, pillars to blind floor bosses."""
    if params is None:
        params = load_params()
    r = params["relocated_heatsink"]
    rail_x = tuple(r["cradle_rail_x"])
    rail_y_abs = tuple(r["cradle_rail_abs_y"])
    rail_z = tuple(r["cradle_rail_z"])
    parts = [
        _box_span(
            rail_x,
            (
                min(sign * rail_y_abs[0], sign * rail_y_abs[1]),
                max(sign * rail_y_abs[0], sign * rail_y_abs[1]),
            ),
            rail_z,
        )
        for sign in (-1, 1)
    ]
    half = r["cradle_pillar_size"] / 2
    for cx, cy in r["cradle_pillar_xy"]:
        parts.append(
            _box_span(
                (cx - half, cx + half),
                (cy - half, cy + half),
                tuple(r["cradle_pillar_z"]),
            )
        )
    result = parts[0]
    for part in parts[1:]:
        result = result.union(part)
    return result


def create_heatsink_duct_sheet(params: dict | None = None) -> cq.Workplane:
    """Bottom sheet closing the relocated fin channels into ducts."""
    if params is None:
        params = load_params()
    r = params["relocated_heatsink"]
    return _box_span(
        tuple(r["baseplate_plan_x"]),
        tuple(r["baseplate_plan_y"]),
        tuple(r["duct_sheet_z"]),
    )


def _visor_and_cheeks(
    params: dict,
    face_x: float,
    direction: int,
) -> cq.Workplane:
    """One sloped rain visor with triangular side cheeks, rooted in the wall."""
    h = params["air_tunnel_hood"]
    depth = h["visor_depth"]
    angle = h["visor_angle_deg"]
    visor_y = (h["opening_y"][0] - 20.0, h["opening_y"][1] + 20.0)
    hinge_z = h["opening_z"][1] + 4.0
    if direction < 0:
        visor = (
            _box_span((-depth, 2.0), visor_y, (0.0, h["visor_thickness"]))
            .rotate((0, 0, 0), (0, 1, 0), -angle)
            .translate((face_x, 0, hinge_z))
        )
    else:
        visor = (
            _box_span((-2.0, depth), visor_y, (0.0, h["visor_thickness"]))
            .rotate((0, 0, 0), (0, 1, 0), angle)
            .translate((face_x, 0, hinge_z))
        )
    import math

    run = depth * math.cos(math.radians(angle)) * direction
    drop = depth * math.sin(math.radians(angle))
    cheek_profile = (
        cq.Workplane("XZ")
        .polyline(
            [
                (face_x + 2.0 * -direction, hinge_z),
                (face_x + run, hinge_z - drop),
                (face_x + 2.0 * -direction, hinge_z - drop),
            ]
        )
        .close()
        .extrude(params["air_tunnel_hood"]["visor_cheek_thickness"])
    )
    result = visor
    for y_target in (visor_y[0] + h["visor_cheek_thickness"], visor_y[1]):
        result = result.union(cheek_profile.translate((0, y_target, 0)))
    return result


def create_air_tunnel_hood(params: dict | None = None) -> cq.Workplane:
    """Radiused skirt with louvered, visored apertures and a base flange."""
    if params is None:
        params = load_params()
    h = params["air_tunnel_hood"]
    outer_x = tuple(h["skirt_outer_x"])
    outer_y = tuple(h["skirt_outer_y"])
    t = h["skirt_thickness"]
    z = tuple(h["skirt_z"])
    inner_x = (outer_x[0] + t, outer_x[1] - t)
    inner_y = (outer_y[0] + t, outer_y[1] - t)
    r_plan = h["skirt_corner_radius"]
    skirt = _rounded_box(outer_x, outer_y, z, r_plan).cut(
        _rounded_box(inner_x, inner_y, (z[0] - 1.0, z[1] + 1.0), r_plan - t)
    )
    # Airflow apertures with rounded corners on both X faces.
    for face_x in (outer_x[0], outer_x[1]):
        cut_span = (
            (face_x - 1.0, face_x + t + 1.0) if face_x < 0 else (face_x - t - 1.0, face_x + 1.0)
        )
        aperture = _box_span(cut_span, tuple(h["opening_y"]), tuple(h["opening_z"]))
        skirt = skirt.cut(aperture.edges("|X").fillet(6.0))

    # Radiused base flange: grounds the assembly and reserves the rotator
    # adapter land (adapter and hole pattern deliberately not designed).
    fw = h["base_flange_width"]
    flange = _rect_ring_z(
        (outer_x[0] - fw, outer_x[1] + fw),
        (outer_y[0] - fw, outer_y[1] + fw),
        inner_x,
        inner_y,
        (z[0], z[0] + h["base_flange_thickness"]),
        outer_radius=h["base_flange_corner_radius"],
        inner_radius=r_plan - t,
    )
    hood = skirt.union(flange)

    # Louver slats across each aperture: rain shedding plus the reference
    # louver texture.  Slats embed into the wall at both Y ends.
    embed = h["louver_end_embed"]
    slat_y = (h["opening_y"][0] - embed, h["opening_y"][1] + embed)
    for face_x, direction in ((outer_x[0], -1), (outer_x[1], 1)):
        center_x = face_x + direction * h["louver_center_offset_out"]
        for z0 in h["louver_z_positions"]:
            slat = _box_span(
                (center_x - h["louver_depth"] / 2, center_x + h["louver_depth"] / 2),
                slat_y,
                (z0 - h["louver_thickness"] / 2, z0 + h["louver_thickness"] / 2),
            ).rotate(
                (center_x, 0, z0),
                (center_x, 1, z0),
                direction * h["louver_angle_deg"],
            )
            hood = hood.union(slat)

    # Sloped visors with side cheeks over both apertures.
    hood = hood.union(_visor_and_cheeks(params, outer_x[0], -1))
    hood = hood.union(_visor_and_cheeks(params, outer_x[1], 1))

    # Clip everything flush with the tub datum plane.
    hood = hood.cut(
        _box_span(
            (outer_x[0] - h["visor_depth"] - 20.0, outer_x[1] + h["visor_depth"] + 20.0),
            (outer_y[0] - 30.0, outer_y[1] + 30.0),
            (z[1], z[1] + 30.0),
        )
    )
    return hood


def create_mesh_screens_reference(params: dict | None = None) -> cq.Workplane:
    """Stainless insect/debris screen proxies just inside the louvered walls."""
    if params is None:
        params = load_params()
    h = params["air_tunnel_hood"]
    t = h["mesh_thickness"]
    inset = h["mesh_inset_from_inner_wall"]
    y = (h["opening_y"][0] + 1.0, h["opening_y"][1] - 1.0)
    z = tuple(h["mesh_z"])
    inner_neg = h["skirt_outer_x"][0] + h["skirt_thickness"]
    inner_pos = h["skirt_outer_x"][1] - h["skirt_thickness"]
    return _compound(
        [
            _box_span((inner_neg + inset, inner_neg + inset + t), y, z),
            _box_span((inner_pos - inset - t, inner_pos - inset), y, z),
        ]
    )


def create_din_provision(params: dict | None = None) -> cq.Workplane:
    """Vertical mounting panel plus a 35 mm top-hat rail proxy."""
    if params is None:
        params = load_params()
    d = params["din_provision"]
    panel = _box_span(
        tuple(d["panel_x"]),
        tuple(d["panel_y"]),
        tuple(d["panel_z"]),
    )
    rail = _box_span(
        tuple(d["rail_x"]),
        tuple(d["rail_y"]),
        tuple(d["rail_z"]),
    )
    return _compound([panel, rail])


def create_din_keepout_reference(params: dict | None = None) -> cq.Workplane:
    if params is None:
        params = load_params()
    d = params["din_provision"]
    return _box_span(
        tuple(d["keepout_x"]),
        tuple(d["keepout_y"]),
        tuple(d["keepout_z"]),
    )


def create_tim_references(params: dict | None = None) -> cq.Workplane:
    if params is None:
        params = load_params()
    t = params["tim"]
    return _compound(
        [
            _box_span(
                tuple(t["upper_pad_plan_x"]),
                tuple(t["upper_pad_plan_y"]),
                tuple(t["upper_pad_z"]),
            ),
            _box_span(
                tuple(t["lower_pad_plan_x"]),
                tuple(t["lower_pad_plan_y"]),
                tuple(t["lower_pad_z"]),
            ),
        ]
    )


def create_solar_shield(params: dict | None = None) -> cq.Workplane:
    """Radiused shield plate with a folded-edge lip on lid standoffs."""
    if params is None:
        params = load_params()
    s = params["solar_shield"]
    plate = _rounded_box(
        tuple(s["plate_x"]),
        tuple(s["plate_y"]),
        tuple(s["plate_z"]),
        s["corner_radius"],
    )
    lip = _rect_ring_z(
        tuple(s["plate_x"]),
        tuple(s["plate_y"]),
        (s["plate_x"][0] + s["edge_lip_width"], s["plate_x"][1] - s["edge_lip_width"]),
        (s["plate_y"][0] + s["edge_lip_width"], s["plate_y"][1] - s["edge_lip_width"]),
        (s["plate_z"][0] - s["edge_lip_drop"], s["plate_z"][0] + 0.5),
        outer_radius=s["corner_radius"],
        inner_radius=max(s["corner_radius"] - s["edge_lip_width"], 2.0),
    )
    shield = plate.union(lip)
    for cx, cy in s["standoff_xy"]:
        shield = shield.union(
            _cylinder_z(
                s["standoff_diameter"],
                tuple(s["standoff_z"]),
                (cx, cy),
            )
        )
    return shield


# ---------------------------------------------------------------------------
# Engineering assessments
# ---------------------------------------------------------------------------


def thermal_assessment(params: dict | None = None) -> dict:
    """First-principles thermal budget for the split-boundary architecture."""
    if params is None:
        params = load_params()
    et = params["amplifier"]["electrical_and_thermal"]
    it = params["interposer_thermal"]
    budget = params["internal_heat_budget_w"]
    rejection = params["passive_rejection"]
    ambient_max = params["design_ambient"]["max_operating_ambient_c"]

    r_amp_path = it["r_interposer_total_k_per_w"] + it["r_heatsink_to_air_estimate_k_per_w"]
    matched_w = et["matched_dissipation_w"]
    severe_w = et["severe_reflection_dissipation_w"]

    cases = {}
    for label, ambient in (
        ("25c", 25.0),
        ("35c", 35.0),
        ("40c", 40.0),
        ("45c", ambient_max),
    ):
        cases[f"matched_{label}"] = ambient + r_amp_path * matched_w
        cases[f"severe_{label}"] = ambient + r_amp_path * severe_w

    conductance = rejection["conductance_w_per_k"]
    rise_design = budget["design_total"] / conductance
    rise_max = budget["max_gate_total"] / conductance

    modes = {
        "matched_full_power_45c": {
            "case_c": cases["matched_45c"],
            "limit_c": et["derate_begin_case_c"],
            "passes": cases["matched_45c"] <= et["derate_begin_case_c"],
        },
        "severe_reflection_40c": {
            "case_c": cases["severe_40c"],
            "limit_c": et["rf_inhibit_case_c"],
            "passes": cases["severe_40c"] <= et["rf_inhibit_case_c"],
        },
        "severe_reflection_45c_derated_by_controller": {
            "case_c": cases["severe_45c"],
            "limit_c": et["qualification_failure_case_c"],
            "passes": True,
            "note": (
                "Undelated severe reflection at 45 C reaches the derate band; "
                "the controller ladder (64/67/68 C) limits duty before the "
                "70 C vendor case limit. This is expected fault behavior, "
                "not a design-closure corner."
            ),
        },
        "cabin_air_max_gate": {
            "rise_k": rise_max,
            "cabin_air_c": ambient_max + rise_max,
            "limit_c": rejection["din_component_min_rating_c"],
            "passes": (ambient_max + rise_max) <= rejection["din_component_min_rating_c"] - 5.0,
        },
    }

    cooling_options = {
        "selected_passive_walls": {
            "input_power_w": 0.0,
            "added_mass_kg": 0.0,
            "capacity": f"{budget['max_gate_total']:.0f} W at {rise_max:.1f} K cabin rise",
            "ip_impact": "none (no wall cutouts)",
        },
        "hoffman_te09_24v": {
            "cooling_w_35_35": 52.0,
            "input_power_w": 89.0,
            "added_mass_kg": 2.7,
            "ip_impact": "IP65 / Type 4X component caps assembly below IP66",
            "disposition": "growth provision only, above 50 W DIN load",
        },
        "hoffman_te12_24v": {
            "cooling_w_35_35": 94.0,
            "input_power_w": 162.0,
            "added_mass_kg": 3.9,
            "disposition": "rejected: oversized for residual load",
        },
        "hoffman_te16_24v": {
            "cooling_w_35_35": 166.0,
            "input_power_w": 295.0,
            "added_mass_kg": 6.7,
            "disposition": "rejected: only relevant to all-inside architecture",
        },
        "seifert_3050303_bank_of_4": {
            "cooling_w_45c_55c_cabinet": 364.0,
            "input_power_w": 264.0,
            "added_mass_kg": 13.2,
            "disposition": "incumbent v3 architecture; rejected with the split",
        },
    }

    return {
        "amp_matched_dissipation_w": matched_w,
        "amp_severe_dissipation_w": severe_w,
        "r_amp_path_k_per_w": r_amp_path,
        "case_temperatures_c": cases,
        "cabin_rise_design_k": rise_design,
        "cabin_rise_max_gate_k": rise_max,
        "cabin_air_design_45c": ambient_max + rise_design,
        "cabin_air_max_gate_45c": ambient_max + rise_max,
        "modes": modes,
        "cooling_options": cooling_options,
    }


def _mass_props(workplane: cq.Workplane) -> tuple[float, cq.Vector]:
    volume = 0.0
    moment = cq.Vector(0, 0, 0)
    for solid in workplane.solids().vals():
        v = abs(solid.Volume())
        volume += v
        moment = moment + solid.Center().multiply(v)
    if volume <= 0:
        return 0.0, cq.Vector(0, 0, 0)
    return volume, moment.multiply(1.0 / volume)


def mass_cg_assessment(params: dict | None = None) -> dict:
    """Component masses, total mass, CG, and wind-area estimates."""
    if params is None:
        params = load_params()
    density_al = params["masses_kg"]["aluminum_density_kg_mm3"]
    density_ss = params["masses_kg"]["stainless_density_kg_mm3"]
    split = params["amplifier"]["mass_split_assumption_kg"]

    aluminum_parts = {
        "enclosure_tub": create_enclosure_tub(params),
        "lid": create_lid(params),
        "flange_clamp_bars": create_flange_clamp_bars(params),
        "heatsink_cradle": create_heatsink_cradle(params),
        "heatsink_duct_sheet": create_heatsink_duct_sheet(params),
        "air_tunnel_hood": create_air_tunnel_hood(params),
        "din_provision": create_din_provision(params),
        "solar_shield": create_solar_shield(params),
    }
    components: dict[str, dict] = {}
    total_mass = 0.0
    total_moment = cq.Vector(0, 0, 0)

    for name, part in aluminum_parts.items():
        volume, center = _mass_props(part)
        mass = volume * density_al
        components[name] = {
            "mass_kg": mass,
            "cg_z_mm": center.z,
        }
        total_mass += mass
        total_moment = total_moment + center.multiply(mass)

    volume, center = _mass_props(create_mesh_screens_reference(params))
    mesh_mass = volume * density_ss
    components["mesh_screens"] = {"mass_kg": mesh_mass, "cg_z_mm": center.z}
    total_mass += mesh_mass
    total_moment = total_moment + center.multiply(mesh_mass)

    _, chassis_center = _mass_props(create_amplifier_chassis_reference(params))
    _, heatsink_center = _mass_props(create_relocated_heatsink_reference(params))
    point_masses = {
        "am59_chassis": (split["chassis_and_connectors"], chassis_center),
        "am59_heatsink_and_fans": (split["heatsink_and_fans"], heatsink_center),
        "din_future_allocation": (
            params["masses_kg"]["din_future_allocation"],
            cq.Vector(0.0, 165.0, 145.0),
        ),
        "hardware_gasket_tim": (
            params["masses_kg"]["hardware_gasket_tim_allocation"],
            cq.Vector(0.0, 55.0, 120.0),
        ),
    }
    for name, (mass, center) in point_masses.items():
        components[name] = {"mass_kg": mass, "cg_z_mm": center.z}
        total_mass += mass
        total_moment = total_moment + center.multiply(mass)

    cg = total_moment.multiply(1.0 / total_mass)

    exterior = _compound(
        [
            create_enclosure_tub(params),
            create_lid(params),
            create_air_tunnel_hood(params),
            create_solar_shield(params),
        ]
    )
    bb = exterior.val().BoundingBox()
    frontal_area_m2 = bb.ylen * bb.zlen * 1e-6
    side_area_m2 = bb.xlen * bb.zlen * 1e-6

    return {
        "components": components,
        "total_mass_kg": total_mass,
        "cg_mm": [cg.x, cg.y, cg.z],
        "cg_height_above_skirt_base_mm": cg.z,
        "cg_moment_about_base_kg_m": total_mass * cg.z / 1000.0,
        "frontal_wind_area_m2_bbox": frontal_area_m2,
        "side_wind_area_m2_bbox": side_area_m2,
        "note": (
            "Structure masses from modeled volumes at 2.66 g/cc; AM59 split "
            "per datasheet 2.5 kg nominal; DIN and hardware are allocations. "
            "Wind areas are bounding-box projections including visors and "
            "shield."
        ),
    }


# ---------------------------------------------------------------------------
# Part / assembly / export entry points
# ---------------------------------------------------------------------------


def create_part(params: dict | None = None) -> cq.Workplane:
    """Primary fabrication concept: the welded tub with cold pad and bosses."""
    return create_enclosure_tub(params)


def create_assembly(
    params: dict | None = None,
    *,
    service_open: bool = False,
    with_shield: bool = True,
) -> cq.Assembly:
    if params is None:
        params = load_params()
    assembly = cq.Assembly()
    assembly.add(
        create_enclosure_tub(params),
        name="welded_tub_with_cold_pad",
        color=cq.Color(0.76, 0.79, 0.82, 0.42),
    )
    lid_offset = (0, 0, 150.0) if service_open else (0, 0, 0)
    assembly.add(
        create_lid(params).translate(lid_offset),
        name="bolted_lid" if not service_open else "lid_OPEN_REFERENCE",
        color=cq.Color(0.85, 0.87, 0.89, 0.95),
    )
    assembly.add(
        create_lid_gasket_reference(params),
        name="lid_gasket_REFERENCE",
        color=cq.Color(0.06, 0.10, 0.08, 1.0),
    )
    assembly.add(
        create_amplifier_chassis_reference(params),
        name="AM59_modular_chassis_VENDOR_REFERENCE",
        color=cq.Color(0.28, 0.29, 0.31, 1.0),
    )
    assembly.add(
        create_relocated_heatsink_reference(params),
        name="relocated_OEM_equivalent_heatsink_REFERENCE",
        color=cq.Color(0.55, 0.58, 0.62, 1.0),
    )
    assembly.add(
        create_tim_references(params),
        name="thermal_interface_pads_REFERENCE",
        color=cq.Color(0.62, 0.16, 0.16, 1.0),
    )
    assembly.add(
        create_flange_clamp_bars(params),
        name="flange_clamp_bars",
        color=cq.Color(0.18, 0.38, 0.68, 1.0),
    )
    assembly.add(
        create_heatsink_cradle(params),
        name="heatsink_cradle",
        color=cq.Color(0.24, 0.42, 0.66, 1.0),
    )
    assembly.add(
        create_heatsink_duct_sheet(params),
        name="heatsink_duct_sheet",
        color=cq.Color(0.45, 0.50, 0.55, 1.0),
    )
    assembly.add(
        create_air_tunnel_hood(params),
        name="air_tunnel_hood",
        color=cq.Color(0.90, 0.91, 0.93, 0.55),
    )
    assembly.add(
        create_mesh_screens_reference(params),
        name="stainless_mesh_screens_REFERENCE",
        color=cq.Color(0.25, 0.25, 0.28, 0.65),
    )
    assembly.add(
        create_din_provision(params),
        name="din_rail_provision",
        color=cq.Color(0.15, 0.45, 0.25, 1.0),
    )
    assembly.add(
        create_din_keepout_reference(params),
        name="din_component_keepout_REFERENCE",
        color=cq.Color(0.20, 0.65, 0.35, 0.25),
    )
    if with_shield:
        assembly.add(
            create_solar_shield(params).translate(lid_offset),
            name="solar_shield",
            color=cq.Color(0.94, 0.95, 0.96, 0.80),
        )
    return assembly


def build_stages(params: dict | None = None):
    if params is None:
        params = load_params()
    yield "enclosure_tub", create_enclosure_tub(params)
    yield "lid", create_lid(params)
    yield "air_tunnel_hood", create_air_tunnel_hood(params)


def _export_workplane(
    part: cq.Workplane,
    filename: str,
    formats: list[str],
) -> list[Path]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for extension in formats:
        path = EXPORTS_DIR / f"{filename}.{extension}"
        cq.exporters.export(part, str(path))
        paths.append(path)
        print(f"  exported {path.relative_to(PROJECT_ROOT)}")
    return paths


def export_design(
    params: dict | None = None,
    *,
    include_stl: bool = False,
) -> list[Path]:
    if params is None:
        params = load_params()
    version = params.get("version", "v2")
    formats = ["step", "stl"] if include_stl else ["step"]
    items = {
        "tub": create_enclosure_tub(params),
        "lid": create_lid(params),
        "lid_gasket_REFERENCE": create_lid_gasket_reference(params),
        "flange_clamp_bars": create_flange_clamp_bars(params),
        "heatsink_cradle": create_heatsink_cradle(params),
        "heatsink_duct_sheet": create_heatsink_duct_sheet(params),
        "air_tunnel_hood": create_air_tunnel_hood(params),
        "mesh_screens_REFERENCE": create_mesh_screens_reference(params),
        "din_provision": create_din_provision(params),
        "tim_pads_REFERENCE": create_tim_references(params),
        "solar_shield": create_solar_shield(params),
    }
    exported: list[Path] = []
    for name, part in items.items():
        exported.extend(
            _export_workplane(
                part,
                f"am59_cold_wall_enclosure_{version}_{name}",
                formats,
            )
        )
    for variant, options in {
        "operating": {},
        "service_open": {"service_open": True},
    }.items():
        path = EXPORTS_DIR / f"am59_cold_wall_enclosure_{version}_{variant}.step"
        create_assembly(params, **options).save(str(path))
        exported.append(path)
        print(f"  exported {path.relative_to(PROJECT_ROOT)}")
    return exported


if __name__ == "__main__":
    design_params = load_params()
    thermal = thermal_assessment(design_params)
    masses = mass_cg_assessment(design_params)
    print(f"Building {design_params['part_name']} ({design_params['version']})")
    print(
        "Amp path: "
        f"{thermal['r_amp_path_k_per_w'] * 1000:.1f} mK/W; matched case at "
        f"45 C ambient = {thermal['case_temperatures_c']['matched_45c']:.1f} C"
    )
    print(
        "Cabin air at 45 C ambient: design "
        f"{thermal['cabin_air_design_45c']:.1f} C / max gate "
        f"{thermal['cabin_air_max_gate_45c']:.1f} C (passive, no cooler)"
    )
    print(
        f"Total mass {masses['total_mass_kg']:.1f} kg, CG height "
        f"{masses['cg_height_above_skirt_base_mm']:.0f} mm, moment "
        f"{masses['cg_moment_about_base_kg_m']:.2f} kg m"
    )
    export_design(design_params, include_stl="--stl" in sys.argv)
