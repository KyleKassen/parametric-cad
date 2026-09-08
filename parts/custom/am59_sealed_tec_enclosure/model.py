"""
AM59 sealed thermoelectric enclosure, V3
=========================================

Standalone CadQuery concept for a welded dry enclosure containing one exact
AM59-3S-64-64 amplifier and four exact Seifert 3050303 thermoelectric coolers.

The cooler banks are recessed symmetrically into the two long walls. In normal
operation the populated enclosure has an IP66/IP6X/IPX6 *design target* because
the complete Seifert cooler is rated IP66 / Type 4X. For planned, unpowered
temporary immersion, removable gasketed caps create a secondary pressure
boundary around both cooler banks. Neither target becomes a product claim
until the complete production-equivalent enclosure passes the stated tests.

Coordinate system
-----------------
X : AM59 airflow, factory fan inlet (-X) to RF output (+X)
Y : across the amplifier and between opposed cooler banks
Z : vertical
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
SEIFERT_STEP = PROJECT_ROOT / "parts" / "vendor" / "seifert" / "Seifert - 3050303.STEP"


def load_params(path: Path = PARAMS_FILE) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=4)
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


def _box(
    length_x: float,
    width_y: float,
    height_z: float,
    center: tuple[float, float, float],
) -> cq.Workplane:
    return cq.Workplane("XY").box(length_x, width_y, height_z).translate(center)


def _cylinder_x(
    diameter: float,
    length: float,
    start: tuple[float, float, float],
    direction: int = 1,
) -> cq.Workplane:
    return cq.Workplane(
        obj=cq.Solid.makeCylinder(
            diameter / 2,
            length,
            cq.Vector(*start),
            cq.Vector(direction, 0, 0),
        )
    )


def _cylinder_y(
    diameter: float,
    length: float,
    start: tuple[float, float, float],
    direction: int = 1,
) -> cq.Workplane:
    return cq.Workplane(
        obj=cq.Solid.makeCylinder(
            diameter / 2,
            length,
            cq.Vector(*start),
            cq.Vector(0, direction, 0),
        )
    )


def _rect_ring_x(
    thickness_x: float,
    outer_width_y: float,
    outer_height_z: float,
    ring_width: float,
    center: tuple[float, float, float],
) -> cq.Workplane:
    outer = _box(
        thickness_x,
        outer_width_y,
        outer_height_z,
        center,
    )
    inner = _box(
        thickness_x + 2.0,
        outer_width_y - 2 * ring_width,
        outer_height_z - 2 * ring_width,
        center,
    )
    return outer.cut(inner)


def _rect_ring_y(
    outer_width_x: float,
    thickness_y: float,
    outer_height_z: float,
    inner_width_x: float,
    inner_height_z: float,
    center: tuple[float, float, float],
) -> cq.Workplane:
    outer = _box(
        outer_width_x,
        thickness_y,
        outer_height_z,
        center,
    )
    inner = _box(
        inner_width_x,
        thickness_y + 2.0,
        inner_height_z,
        center,
    )
    return outer.cut(inner)


def cooler_mount_locations(
    params: dict | None = None,
) -> list[tuple[int, float, float]]:
    """Return side sign, X center, and Z center for all four coolers."""
    if params is None:
        params = load_params()
    s = params["seifert_3050303"]
    return [
        (side_sign, center_x, s["center_z"]) for side_sign in (-1, 1) for center_x in s["center_x"]
    ]


def cooler_mount_hole_locations(
    params: dict | None = None,
) -> list[tuple[int, float, float]]:
    """Return side sign and X/Z locations for the sixteen cooler studs."""
    if params is None:
        params = load_params()
    s = params["seifert_3050303"]
    locations: list[tuple[int, float, float]] = []
    for side_sign, center_x, center_z in cooler_mount_locations(params):
        for x_sign in (-1, 1):
            for z_sign in (-1, 1):
                locations.append(
                    (
                        side_sign,
                        center_x + x_sign * s["mount_hole_spacing_x"] / 2,
                        center_z + z_sign * s["mount_hole_spacing_z"] / 2,
                    )
                )
    return locations


def cooler_mount_cutout_references(
    params: dict | None = None,
) -> cq.Workplane:
    """Return the four supplier-controlled rectangular wall cutouts."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    s = params["seifert_3050303"]
    wall_y = e["outer_width_y"] / 2
    cutters = [
        _box(
            s["cutout_width_x"],
            e["wall_thickness"] + e["cooler_doubler_thickness_y"] + 12.0,
            s["cutout_height_z"],
            (center_x, side_sign * wall_y, center_z),
        )
        for side_sign, center_x, center_z in cooler_mount_locations(params)
    ]
    return _compound(cutters)


def create_cooler_doubler_frames(
    params: dict | None = None,
) -> cq.Workplane:
    """Create four welded internal frames restoring stiffness at the cutouts."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    wall_y = e["outer_width_y"] / 2
    t = e["cooler_doubler_thickness_y"]
    frames: list[cq.Workplane] = []
    for side_sign, center_x, center_z in cooler_mount_locations(params):
        frame = _rect_ring_y(
            e["cooler_doubler_outer_width_x"],
            t,
            e["cooler_doubler_outer_height_z"],
            e["cooler_doubler_inner_width_x"],
            e["cooler_doubler_inner_height_z"],
            (
                center_x,
                side_sign * (wall_y - e["wall_thickness"] - t / 2),
                center_z,
            ),
        )
        frames.append(frame)
    result = _compound(frames)

    # The supplier studs pass through the wall and the internal doublers.
    start_y = wall_y - e["wall_thickness"] - t - 2.0
    for side_sign, x, z in cooler_mount_hole_locations(params):
        cutter = _cylinder_y(
            params["seifert_3050303"]["mount_hole_diameter"],
            e["wall_thickness"] + t + 5.0,
            (x, side_sign * start_y, z),
            direction=side_sign,
        )
        result = result.cut(cutter)
    return result


def create_immersion_coamings(
    params: dict | None = None,
) -> cq.Workplane:
    """Create welded rings that receive the two removable immersion caps."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    cap = params["immersion_caps"]
    wall_y = e["outer_width_y"] / 2
    parts: list[cq.Workplane] = []
    for side_sign in (-1, 1):
        parts.append(
            _rect_ring_y(
                cap["coaming_outer_width_x"],
                cap["coaming_projection_y"],
                cap["coaming_outer_height_z"],
                cap["coaming_inner_width_x"],
                cap["coaming_inner_height_z"],
                (
                    cap["center_x"],
                    side_sign * (wall_y + cap["coaming_projection_y"] / 2),
                    cap["center_z"],
                ),
            )
        )
    return _compound(parts)


def create_cartridge_support_structure(
    params: dict | None = None,
) -> cq.Workplane:
    """Create the two welded floor rails and fixed +X cartridge stops."""
    if params is None:
        params = load_params()
    c = params["cartridge"]
    rail_length = c["support_rail_x_max"] - c["support_rail_x_min"]
    rail_height = c["support_rail_top_z"] - c["support_rail_bottom_z"]
    stop_length = c["fixed_stop_x_max"] - c["fixed_stop_x_min"]
    stop_height = c["stop_z_max"] - c["stop_z_min"]
    parts: list[cq.Workplane] = []
    for side_sign in (-1, 1):
        parts.append(
            _box(
                rail_length,
                c["support_rail_width_y"],
                rail_height,
                (
                    (c["support_rail_x_min"] + c["support_rail_x_max"]) / 2,
                    side_sign * c["support_rail_center_abs_y"],
                    (c["support_rail_bottom_z"] + c["support_rail_top_z"]) / 2,
                ),
            )
        )
        parts.append(
            _box(
                stop_length,
                c["stop_width_y"],
                stop_height,
                (
                    (c["fixed_stop_x_min"] + c["fixed_stop_x_max"]) / 2,
                    side_sign * c["support_rail_center_abs_y"],
                    (c["stop_z_min"] + c["stop_z_max"]) / 2,
                ),
            )
        )
    return _compound(parts)


def create_pressure_body(params: dict | None = None) -> cq.Workplane:
    """Create the open-service-end welded shell with cooler interfaces."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    s = params["seifert_3050303"]

    length = e["x_max"] - e["x_min"]
    width = e["outer_width_y"]
    height = e["z_max"] - e["z_min"]
    wall = e["wall_thickness"]
    center_x = (e["x_min"] + e["x_max"]) / 2
    center_z = (e["z_min"] + e["z_max"]) / 2
    wall_y = width / 2

    outer = _box(length, width, height, (center_x, 0, center_z))

    # Extend the void 1 mm beyond -X so that the service end remains open;
    # retain exact wall thickness at +X, both sides, roof, and floor.
    inner_x_min = e["x_min"] - 1.0
    inner_x_max = e["x_max"] - wall
    inner = _box(
        inner_x_max - inner_x_min,
        width - 2 * wall,
        height - 2 * wall,
        (
            (inner_x_min + inner_x_max) / 2,
            0,
            center_z,
        ),
    )
    shell = outer.cut(inner)

    flange_outer = _box(
        e["flange_thickness_x"],
        e["flange_outer_width_y"],
        e["flange_outer_height_z"],
        (
            e["x_min"] + e["flange_thickness_x"] / 2,
            0,
            e["flange_outer_center_z"],
        ),
    )
    flange_opening = _box(
        e["flange_thickness_x"] + 2.0,
        e["flange_opening_width_y"],
        e["flange_opening_height_z"],
        (
            e["x_min"] + e["flange_thickness_x"] / 2,
            0,
            e["flange_opening_center_z"],
        ),
    )
    shell = shell.union(flange_outer.cut(flange_opening))

    # Cut the four 170 x 120 supplier-defined recessed-mount openings.
    for side_sign, cut_x, cut_z in cooler_mount_locations(params):
        shell = shell.cut(
            _box(
                s["cutout_width_x"],
                wall + 4.0,
                s["cutout_height_z"],
                (cut_x, side_sign * wall_y, cut_z),
            )
        )

    shell = shell.union(create_cooler_doubler_frames(params))
    shell = shell.union(create_immersion_coamings(params))
    shell = shell.union(create_cartridge_support_structure(params))

    # Cut all mounting-stud holes through the finished wall/doubler stack.
    for side_sign, x, z in cooler_mount_hole_locations(params):
        shell = shell.cut(
            _cylinder_y(
                s["mount_hole_diameter"],
                wall + e["cooler_doubler_thickness_y"] + 6.0,
                (
                    x,
                    side_sign * (wall_y - wall - e["cooler_doubler_thickness_y"] - 2.0),
                    z,
                ),
                direction=side_sign,
            )
        )

    # Blind interior lands for supplier-selected +X feedthroughs. These do
    # not pierce the pressure wall in the concept model.
    connector_pad = _box(
        7.0,
        185.0,
        82.0,
        (e["x_max"] - 3.5, -42.5, 72.0),
    )
    control_pad = _box(
        7.0,
        105.0,
        82.0,
        (e["x_max"] - 3.5, -147.5, 72.0),
    )
    return shell.union(connector_pad).union(control_pad)


def service_fastener_locations(
    params: dict | None = None,
) -> list[tuple[float, float]]:
    """Return Y/Z locations for the captive service-cover fasteners."""
    if params is None:
        params = load_params()
    lid = params["service_lid"]
    locations: list[tuple[float, float]] = []
    for y in lid["fastener_y_top_bottom"]:
        locations.append((y, lid["fastener_edge_z_bottom"]))
        locations.append((y, lid["fastener_edge_z_top"]))
    for z in lid["fastener_z_sides"]:
        locations.append((-lid["fastener_edge_y"], z))
        locations.append((lid["fastener_edge_y"], z))
    return locations


def create_service_lid(params: dict | None = None) -> cq.Workplane:
    """Create the removable -X lid with hydrostatic stiffening ribs."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    lid = params["service_lid"]
    thickness = lid["plate_thickness_x"]
    center_z = (e["z_min"] + e["z_max"]) / 2
    result = _box(
        thickness,
        lid["outer_width_y"],
        lid["outer_height_z"],
        (e["x_min"] - thickness / 2, 0, center_z),
    )

    for y, z in service_fastener_locations(params):
        result = result.cut(
            _cylinder_x(
                lid["fastener_diameter"],
                thickness + 2.0,
                (e["x_min"] - thickness - 1.0, y, z),
            )
        )

    # External vertical ribs drain rather than creating horizontal shelves.
    for y in (-135.0, -45.0, 45.0, 135.0):
        result = result.union(
            _box(
                4.0,
                16.0,
                lid["outer_height_z"] - 66.0,
                (e["x_min"] - thickness - 2.0, y, center_z),
            )
        )
    return result


def create_service_gasket(params: dict | None = None) -> cq.Workplane:
    """Create a continuous proxy ring for the selected environmental seal."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    lid = params["service_lid"]
    return _rect_ring_x(
        lid["seal_proxy_thickness_x"],
        lid["seal_ring_outer_width_y"],
        lid["seal_ring_outer_height_z"],
        lid["seal_ring_width"],
        (
            e["x_min"],
            0,
            lid["seal_ring_center_z"],
        ),
    )


def create_internal_cartridge(params: dict | None = None) -> cq.Workplane:
    """Create the removable AM59 tray using all twelve OEM mounting points."""
    if params is None:
        params = load_params()
    c = params["cartridge"]
    a = params["amplifier"]
    z0 = c["bottom_z"]
    result = _box(
        c["outer_length_x"],
        c["outer_width_y"],
        c["thickness"],
        (
            c["center_x"],
            0,
            z0 + c["thickness"] / 2,
        ),
    )
    result = result.cut(
        _box(
            c["inner_opening_length_x"],
            c["inner_opening_width_y"],
            c["thickness"] + 2.0,
            (
                c["center_x"],
                0,
                z0 + c["thickness"] / 2,
            ),
        )
    )
    for x in a["mount_hole_x"]:
        for y in a["mount_hole_y"]:
            result = result.cut(
                cq.Workplane(
                    obj=cq.Solid.makeCylinder(
                        c["mount_hole_diameter"] / 2,
                        c["thickness"] + 2.0,
                        cq.Vector(x, y, z0 - 1.0),
                        cq.Vector(0, 0, 1),
                    )
                )
            )
    return result


def create_cartridge_retainers(
    params: dict | None = None,
) -> cq.Workplane:
    """Create the two removable -X cartridge retention blocks."""
    if params is None:
        params = load_params()
    c = params["cartridge"]
    length = c["retainer_x_max"] - c["retainer_x_min"]
    height = c["retainer_z_max"] - c["retainer_z_min"]
    return _compound(
        [
            _box(
                length,
                c["retainer_width_y"],
                height,
                (
                    (c["retainer_x_min"] + c["retainer_x_max"]) / 2,
                    side_sign * c["support_rail_center_abs_y"],
                    (c["retainer_z_min"] + c["retainer_z_max"]) / 2,
                ),
            )
            for side_sign in (-1, 1)
        ]
    )


def create_cartridge_service_sweep_reference(
    params: dict | None = None,
) -> cq.Workplane:
    """Return the conservative clear passage needed to start tray extraction."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    c = params["cartridge"]
    a = params["amplifier"]["placed_bbox_mm"]
    x_min = e["x_min"] - 20.0
    x_max = c["center_x"] - c["outer_length_x"] / 2
    y_half = c["outer_width_y"] / 2 + c["service_sweep_clearance_y_each_side"]
    z_min = c["bottom_z"] - c["service_sweep_clearance_z"]
    z_max = a["z"][1] + c["service_sweep_clearance_z"]
    return _box(
        x_max - x_min,
        2 * y_half,
        z_max - z_min,
        (
            (x_min + x_max) / 2,
            0,
            (z_min + z_max) / 2,
        ),
    )


def create_amplifier_reference(params: dict | None = None) -> cq.Workplane:
    """Import and place the exact user-supplied AM59 STEP."""
    if params is None:
        params = load_params()
    transform = params["amplifier"]["step_transform"]
    return (
        cq.Workplane(obj=_import_step_shape(str(AMPLIFIER_STEP)))
        .rotate((0, 0, 0), (1, 0, 0), transform["rotate_x_deg"])
        .translate(tuple(transform["translate"]))
    )


def seifert_cooler_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Import and place four exact Seifert STEP references."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    s = params["seifert_3050303"]
    wall_y = e["outer_width_y"] / 2
    native = s["native_step_bbox_mm"]
    native_center_x = (native["x"][0] + native["x"][1]) / 2
    native_center_z = (native["z"][0] + native["z"][1]) / 2
    native_mount_y = s["native_step_mounting_plane_y"]
    base_shape = _import_step_shape(str(SEIFERT_STEP))
    parts: dict[str, cq.Workplane] = {}

    for side_sign, center_x, center_z in cooler_mount_locations(params):
        cooler = cq.Workplane(obj=base_shape)
        if side_sign > 0:
            # Rotate so the ambient side faces +Y. This also reverses the
            # native X direction, which is accommodated by the translation.
            cooler = cooler.rotate((0, 0, 0), (0, 0, 1), 180.0)
            tx = center_x + native_center_x
        else:
            tx = center_x - native_center_x
        ty = side_sign * (wall_y + native_mount_y)
        tz = center_z - native_center_z
        cooler = cooler.translate((tx, ty, tz))
        side_name = "posY" if side_sign > 0 else "negY"
        index = s["center_x"].index(center_x) + 1
        parts[f"Seifert_3050303_{side_name}_{index}_REFERENCE"] = cooler
    return parts


def create_seifert_cooler_bank(
    params: dict | None = None,
) -> cq.Workplane:
    return _compound(list(seifert_cooler_components(params).values()))


def cooler_interface_gasket_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Create four gasket proxies at the Seifert mounting planes."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    s = params["seifert_3050303"]
    wall_y = e["outer_width_y"] / 2
    parts: dict[str, cq.Workplane] = {}
    for side_sign, center_x, center_z in cooler_mount_locations(params):
        gasket = _rect_ring_y(
            s["gasket_outer_width_x"],
            s["gasket_proxy_thickness_y"],
            s["gasket_outer_height_z"],
            s["gasket_inner_width_x"],
            s["gasket_inner_height_z"],
            (center_x, side_sign * wall_y, center_z),
        )
        side_name = "posY" if side_sign > 0 else "negY"
        index = s["center_x"].index(center_x) + 1
        parts[f"Seifert_preinstalled_gasket_{side_name}_{index}_REFERENCE"] = gasket
    return parts


def create_cooler_interface_gaskets(
    params: dict | None = None,
) -> cq.Workplane:
    return _compound(list(cooler_interface_gasket_components(params).values()))


def air_management_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Return low-pressure baffle envelopes for the closed cabinet-air loop."""
    if params is None:
        params = load_params()
    air = params["internal_air_management"]
    t = air["baffle_thickness"]

    roof_divider = _box(
        air["roof_divider_x_max"] - air["roof_divider_x_min"],
        air["roof_divider_width_y"],
        t,
        (
            (air["roof_divider_x_min"] + air["roof_divider_x_max"]) / 2,
            0,
            air["roof_divider_z"],
        ),
    )
    parts: dict[str, cq.Workplane] = {
        "roof_hot_return_divider": roof_divider,
    }

    for side_sign in (-1, 1):
        parts[f"side_cold_supply_baffle_{'posY' if side_sign > 0 else 'negY'}"] = _box(
            air["side_baffle_x_max"] - air["side_baffle_x_min"],
            t,
            air["side_baffle_z_max"] - air["side_baffle_z_min"],
            (
                (air["side_baffle_x_min"] + air["side_baffle_x_max"]) / 2,
                side_sign * air["side_baffle_center_abs_y"],
                (air["side_baffle_z_min"] + air["side_baffle_z_max"]) / 2,
            ),
        )

    parts["hot_discharge_riser_baffle"] = _box(
        air["hot_riser_x_max"] - air["hot_riser_x_min"],
        air["hot_riser_width_y"],
        air["hot_riser_z_max"] - air["hot_riser_z_min"],
        (
            (air["hot_riser_x_min"] + air["hot_riser_x_max"]) / 2,
            0,
            (air["hot_riser_z_min"] + air["hot_riser_z_max"]) / 2,
        ),
    )
    parts["cold_inlet_drop_baffle"] = _box(
        air["cold_drop_x_max"] - air["cold_drop_x_min"],
        air["cold_drop_width_y"],
        air["cold_drop_z_max"] - air["cold_drop_z_min"],
        (
            (air["cold_drop_x_min"] + air["cold_drop_x_max"]) / 2,
            0,
            (air["cold_drop_z_min"] + air["cold_drop_z_max"]) / 2,
        ),
    )
    return parts


def create_internal_air_management(
    params: dict | None = None,
) -> cq.Workplane:
    return _compound(list(air_management_components(params).values()))


def condensate_tray_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Create four sealed catch-pan proxies; there is intentionally no drain."""
    if params is None:
        params = load_params()
    s = params["seifert_3050303"]
    c = params["condensation_management"]
    outer_w = c["tray_outer_width_x"]
    outer_d = c["tray_outer_depth_y"]
    outer_h = c["tray_outer_height_z"]
    bottom_z = c["tray_bottom_z"]
    parts: dict[str, cq.Workplane] = {}

    for side_sign, center_x, _ in cooler_mount_locations(params):
        center_y = side_sign * c["tray_center_abs_y"]
        outer = _box(
            outer_w,
            outer_d,
            outer_h,
            (center_x, center_y, bottom_z + outer_h / 2),
        )
        # Remove an upward-open cavity, retaining 3 mm bottom and side walls.
        inner = _box(
            outer_w - 6.0,
            outer_d - 6.0,
            outer_h - 2.0,
            (
                center_x,
                center_y,
                bottom_z + 3.0 + (outer_h - 2.0) / 2,
            ),
        )
        tray = outer.cut(inner)
        side_name = "posY" if side_sign > 0 else "negY"
        index = s["center_x"].index(center_x) + 1
        parts[f"sealed_condensate_tray_{side_name}_{index}"] = tray
    return parts


def create_condensation_management(
    params: dict | None = None,
) -> cq.Workplane:
    return _compound(list(condensate_tray_components(params).values()))


def create_controller_reference(params: dict | None = None) -> cq.Workplane:
    """Return the branch controller/safety I/O packaging envelope."""
    if params is None:
        params = load_params()
    box = params["controller"]["reference_envelope_mm"]
    return _box(
        box["x"][1] - box["x"][0],
        box["y"][1] - box["y"][0],
        box["z"][1] - box["z"][0],
        (
            sum(box["x"]) / 2,
            sum(box["y"]) / 2,
            sum(box["z"]) / 2,
        ),
    )


def create_feedthrough_references(
    params: dict | None = None,
) -> cq.Workplane:
    """Show non-released connector keep-outs aligned on the fixed +X wall."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    rf = params["feedthroughs"]["high_power_rf_axis_mm"]
    ports = [
        (42.0, rf["y"], rf["z"]),
        (34.0, -72.0, 72.0),
        (34.0, -132.0, 72.0),
        (18.0, 82.0, 72.0),
    ]
    return _compound(
        [
            _cylinder_x(
                diameter,
                42.0,
                (e["x_max"] - 5.0, y, z),
            )
            for diameter, y, z in ports
        ]
    )


def create_pressure_vent_reference(
    params: dict | None = None,
) -> cq.Workplane:
    """Show a sheltered IP68/IP69K ePTFE vent envelope."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    return _cylinder_x(
        18.0,
        22.0,
        (e["x_max"] - 5.0, 155.0, 304.0),
    )


def immersion_cap_fastener_locations(
    params: dict | None = None,
) -> list[tuple[int, float, float]]:
    """Return side sign and global X/Z locations for both cap fastener sets."""
    if params is None:
        params = load_params()
    cap = params["immersion_caps"]
    local: list[tuple[float, float]] = []
    for x in cap["fastener_x_top_bottom"]:
        local.append((x, -cap["fastener_edge_abs_z"]))
        local.append((x, cap["fastener_edge_abs_z"]))
    for z in cap["fastener_z_sides"]:
        local.append((-cap["fastener_edge_abs_x"], z))
        local.append((cap["fastener_edge_abs_x"], z))
    return [
        (side_sign, cap["center_x"] + x, cap["center_z"] + z)
        for side_sign in (-1, 1)
        for x, z in local
    ]


def immersion_cap_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Create two hollow, wall-facing secondary immersion caps."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    cap = params["immersion_caps"]
    wall_y = e["outer_width_y"] / 2
    face_y = wall_y + cap["coaming_projection_y"]
    depth = cap["cap_depth_y"]
    t = cap["cap_wall_thickness"]
    gasket_t = cap["gasket_proxy_thickness_y"]
    flange_t = cap["cap_flange_thickness_y"]
    flange_inner_face = face_y + gasket_t
    flange_center = flange_inner_face + flange_t / 2
    pan_near = flange_inner_face + flange_t
    pan_far = pan_near + depth
    parts: dict[str, cq.Workplane] = {}

    for side_sign in (-1, 1):
        outer_center_y = side_sign * ((pan_near + pan_far) / 2)
        outer = _box(
            cap["cap_outer_width_x"],
            depth,
            cap["cap_outer_height_z"],
            (cap["center_x"], outer_center_y, cap["center_z"]),
        )

        # Cavity extends 1 mm through the wall-facing side and stops t mm
        # before the closed outer wall.
        inner_near = pan_near - 1.0
        inner_far = pan_far - t
        inner_center_y = side_sign * ((inner_near + inner_far) / 2)
        inner = _box(
            cap["cap_outer_width_x"] - 2 * t,
            inner_far - inner_near,
            cap["cap_outer_height_z"] - 2 * t,
            (cap["center_x"], inner_center_y, cap["center_z"]),
        )
        pan = outer.cut(inner)

        flange = _rect_ring_y(
            cap["cap_flange_outer_width_x"],
            flange_t,
            cap["cap_flange_outer_height_z"],
            cap["cap_flange_inner_width_x"],
            cap["cap_flange_inner_height_z"],
            (
                cap["center_x"],
                side_sign * flange_center,
                cap["center_z"],
            ),
        )
        ribbed_pan = pan.union(flange)

        # Only the removable flange is drilled. The mating coaming uses
        # welded blind studs/bosses so no fastener pierces the dry wall.
        for fastener_side, x, z in immersion_cap_fastener_locations(params):
            if fastener_side != side_sign:
                continue
            ribbed_pan = ribbed_pan.cut(
                _cylinder_y(
                    cap["fastener_hole_diameter"],
                    flange_t + 2.0,
                    (
                        x,
                        side_sign * (flange_inner_face - 1.0),
                        z,
                    ),
                    direction=side_sign,
                )
            )

        for x_offset in cap["cap_external_rib_x_offsets"]:
            ribbed_pan = ribbed_pan.union(
                _box(
                    cap["cap_external_rib_width_x"],
                    cap["cap_external_rib_depth_y"],
                    cap["cap_external_rib_height_z"],
                    (
                        cap["center_x"] + x_offset,
                        side_sign * (pan_far + cap["cap_external_rib_depth_y"] / 2),
                        cap["center_z"],
                    ),
                )
            )
        parts[f"immersion_cap_{'posY' if side_sign > 0 else 'negY'}"] = ribbed_pan
    return parts


def create_immersion_caps(params: dict | None = None) -> cq.Workplane:
    return _compound(list(immersion_cap_components(params).values()))


def immersion_cap_gasket_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Create the two continuous secondary-boundary gasket proxies."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    cap = params["immersion_caps"]
    face_y = e["outer_width_y"] / 2 + cap["coaming_projection_y"]
    gasket_center = face_y + cap["gasket_proxy_thickness_y"] / 2
    parts: dict[str, cq.Workplane] = {}
    for side_sign in (-1, 1):
        gasket = _rect_ring_y(
            cap["gasket_outer_width_x"],
            cap["gasket_proxy_thickness_y"],
            cap["gasket_outer_height_z"],
            cap["gasket_inner_width_x"],
            cap["gasket_inner_height_z"],
            (
                cap["center_x"],
                side_sign * gasket_center,
                cap["center_z"],
            ),
        )
        parts[f"immersion_cap_gasket_{'posY' if side_sign > 0 else 'negY'}_REFERENCE"] = gasket
    return parts


def create_immersion_cap_gaskets(
    params: dict | None = None,
) -> cq.Workplane:
    return _compound(list(immersion_cap_gasket_components(params).values()))


def sun_shield_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Return freely ventilated solar shields; none is an ingress barrier."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    shield = params["sun_shields"]
    center_x = (e["x_min"] + e["x_max"]) / 2
    parts: dict[str, cq.Workplane] = {
        "central_white_solar_shield": _box(
            shield["central_length_x"],
            shield["central_width_y"],
            shield["thickness"],
            (
                center_x,
                0,
                shield["central_bottom_z"] + shield["thickness"] / 2,
            ),
        )
    }
    bank_center_y = e["outer_width_y"] / 2 + shield["side_bank_width_y"] / 2
    for side_sign in (-1, 1):
        parts[f"cooler_bank_solar_shield_{'posY' if side_sign > 0 else 'negY'}"] = _box(
            shield["side_bank_length_x"],
            shield["side_bank_width_y"],
            shield["thickness"],
            (
                params["immersion_caps"]["center_x"],
                side_sign * bank_center_y,
                shield["side_bottom_z"] + shield["thickness"] / 2,
            ),
        )
    return parts


def create_sun_shields(params: dict | None = None) -> cq.Workplane:
    return _compound(list(sun_shield_components(params).values()))


def thermal_capacity_per_unit_w(
    enclosure_air_c: float,
    params: dict | None = None,
) -> float:
    """Interpolate the supplied 3050 curve at 45 C ambient."""
    if params is None:
        params = load_params()
    raw = params["seifert_3050303"]["capacity_at_45c_ambient_w_per_unit"]
    points = sorted((float(key), float(value)) for key, value in raw.items())
    if enclosure_air_c < points[0][0] or enclosure_air_c > points[-1][0]:
        raise ValueError(
            f"Enclosure air {enclosure_air_c} C is outside the digitized "
            f"{points[0][0]} to {points[-1][0]} C curve range"
        )
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= enclosure_air_c <= x1:
            ratio = (enclosure_air_c - x0) / (x1 - x0)
            return y0 + ratio * (y1 - y0)
    return points[-1][1]


def thermal_assessment(params: dict | None = None) -> dict:
    """Return the design and degraded-mode thermal margins."""
    if params is None:
        params = load_params()
    amp = params["amplifier"]["electrical_and_thermal"]
    cooler = params["seifert_3050303"]
    air_c = cooler["design_enclosure_air_c"]
    per_unit = thermal_capacity_per_unit_w(air_c, params)
    margin = 1.0 + cooler["manufacturer_margin_percent_min"] / 100.0
    modes = {
        "four_healthy_300w": {
            "capacity_w": 4 * per_unit,
            "required_w": amp["enclosure_design_heat_w"] * margin,
        },
        "three_healthy_200w": {
            "capacity_w": 3 * per_unit,
            "required_w": amp["severe_reflection_heat_basis_w"] * margin,
        },
        "two_healthy_125w": {
            "capacity_w": 2 * per_unit,
            "required_w": amp["matched_heat_estimate_w"] * margin,
        },
        "one_healthy_125w": {
            "capacity_w": per_unit,
            "required_w": amp["matched_heat_estimate_w"] * margin,
        },
    }
    for mode in modes.values():
        mode["margin_w"] = mode["capacity_w"] - mode["required_w"]
        mode["passes"] = mode["margin_w"] >= 0
    return {
        "ambient_c": 45.0,
        "enclosure_air_c": air_c,
        "per_unit_capacity_w": per_unit,
        "modes": modes,
        "maximum_cooler_input_w": 4 * cooler["maximum_input_w"],
        "design_hot_side_rejection_w": (
            amp["enclosure_design_heat_w"] + 4 * cooler["maximum_input_w"]
        ),
        "maximum_curve_point_hot_side_rejection_w": (4 * per_unit + 4 * cooler["maximum_input_w"]),
    }


def mass_assessment(params: dict | None = None) -> dict:
    """Return preliminary known mass; AM59 and unreleased hardware are excluded."""
    if params is None:
        params = load_params()
    aluminum_density_kg_per_mm3 = 2.68e-6
    aluminum_parts = {
        "pressure_body_with_rails": create_pressure_body(params),
        "service_lid": create_service_lid(params),
        "cartridge": create_internal_cartridge(params),
        "cartridge_retainers": create_cartridge_retainers(params),
        "air_baffles": create_internal_air_management(params),
        "condensate_trays": create_condensation_management(params),
        "solar_shields": create_sun_shields(params),
        "immersion_caps": create_immersion_caps(params),
    }
    volumes_mm3 = {
        name: sum(abs(solid.Volume()) for solid in part.solids().vals())
        for name, part in aluminum_parts.items()
    }
    masses_kg = {name: volume * aluminum_density_kg_per_mm3 for name, volume in volumes_mm3.items()}
    cooler_mass = params["seifert_3050303"]["cooler_bank_mass_kg"]
    operating_aluminum_names = (
        "pressure_body_with_rails",
        "service_lid",
        "cartridge",
        "cartridge_retainers",
        "air_baffles",
        "condensate_trays",
        "solar_shields",
    )
    operating_known = sum(masses_kg[name] for name in operating_aluminum_names) + cooler_mass
    return {
        "aluminum_density_kg_per_mm3": aluminum_density_kg_per_mm3,
        "volumes_mm3": volumes_mm3,
        "aluminum_masses_kg": masses_kg,
        "cooler_bank_mass_kg": cooler_mass,
        "operating_known_mass_excluding_am59_gaskets_fasteners_wiring_kg": (operating_known),
        "immersion_known_mass_excluding_am59_gaskets_fasteners_wiring_kg": (
            operating_known + masses_kg["immersion_caps"]
        ),
        "single_immersion_cap_mass_kg_approx": (masses_kg["immersion_caps"] / 2),
        "system_cg_status": (
            "Not releasable until AM59 mass/CG, exact fasteners, connectors, "
            "wiring, controller, seals, and lifting hardware are known."
        ),
    }


def create_part(params: dict | None = None) -> cq.Workplane:
    """Primary fabrication concept: the welded pressure body."""
    return create_pressure_body(params)


def create_assembly(
    params: dict | None = None,
    *,
    service_open: bool = False,
    immersion_ready: bool = False,
    airflow_exploded: bool = False,
) -> cq.Assembly:
    if params is None:
        params = load_params()
    assembly = cq.Assembly()
    assembly.add(
        create_pressure_body(params),
        name="continuously_welded_dry_pressure_body",
        color=cq.Color(0.76, 0.79, 0.82, 0.40),
    )
    assembly.add(
        create_service_gasket(params),
        name="continuous_service_lid_gasket_REFERENCE",
        color=cq.Color(0.06, 0.10, 0.08, 1.0),
    )
    # Park the removed lid beside the cabinet in the service-review assembly.
    # Translating it only along -X leaves it directly in front of the access
    # opening in an orthographic service-side view and hides the internals.
    lid_offset = (0, -470.0, 0) if service_open else (0, 0, 0)
    assembly.add(
        create_service_lid(params).translate(lid_offset),
        name=("service_lid_OPEN_REFERENCE" if service_open else "bolted_service_lid"),
        color=cq.Color(0.83, 0.85, 0.87, 1.0),
    )
    assembly.add(
        create_internal_cartridge(params),
        name="removable_AM59_cartridge",
        color=cq.Color(0.18, 0.38, 0.68, 1.0),
    )
    if not service_open:
        assembly.add(
            create_cartridge_retainers(params),
            name="removable_cartridge_retainers",
            color=cq.Color(0.24, 0.42, 0.66, 1.0),
        )
    assembly.add(
        create_amplifier_reference(params),
        name="AM59_3S_64_64_VENDOR_REFERENCE",
        color=cq.Color(0.28, 0.29, 0.31, 1.0),
    )

    for name, component in cooler_interface_gasket_components(params).items():
        assembly.add(
            component,
            name=name,
            color=cq.Color(0.08, 0.12, 0.10, 1.0),
        )
    for name, component in seifert_cooler_components(params).items():
        assembly.add(
            component,
            name=name,
            color=cq.Color(0.66, 0.69, 0.72, 1.0),
        )

    airflow_offset = (0, 0, 55.0) if airflow_exploded else (0, 0, 0)
    for name, component in air_management_components(params).items():
        component_offset = airflow_offset
        if service_open and name == "cold_inlet_drop_baffle":
            component_offset = lid_offset
        assembly.add(
            component.translate(component_offset),
            name=name,
            color=cq.Color(0.20, 0.55, 0.72, 0.38),
        )
    for name, component in condensate_tray_components(params).items():
        assembly.add(
            component,
            name=name,
            color=cq.Color(0.20, 0.42, 0.68, 0.72),
        )
    assembly.add(
        create_controller_reference(params),
        name="cooler_safety_controller_REFERENCE",
        color=cq.Color(0.15, 0.30, 0.18, 0.72),
    )
    assembly.add(
        create_feedthrough_references(params),
        name="qualified_feedthrough_keepouts_REFERENCE",
        color=cq.Color(0.72, 0.56, 0.16, 1.0),
    )
    assembly.add(
        create_pressure_vent_reference(params),
        name="IP68_IP69K_pressure_vent_REFERENCE",
        color=cq.Color(0.12, 0.12, 0.12, 1.0),
    )

    for name, component in sun_shield_components(params).items():
        assembly.add(
            component,
            name=name,
            color=cq.Color(0.94, 0.95, 0.96, 0.78),
        )

    if immersion_ready:
        for name, component in immersion_cap_gasket_components(params).items():
            assembly.add(
                component,
                name=name,
                color=cq.Color(0.06, 0.10, 0.08, 1.0),
            )
        for name, component in immersion_cap_components(params).items():
            assembly.add(
                component,
                name=name,
                color=cq.Color(0.86, 0.88, 0.90, 0.92),
            )
    return assembly


def build_stages(params: dict | None = None):
    if params is None:
        params = load_params()
    yield "pressure_body", create_pressure_body(params)


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
    version = params.get("version", "v3-tec")
    formats = ["step", "stl"] if include_stl else ["step"]
    items = {
        "pressure_body": create_pressure_body(params),
        "service_lid": create_service_lid(params),
        "service_gasket_REFERENCE": create_service_gasket(params),
        "AM59_cartridge": create_internal_cartridge(params),
        "cartridge_support_structure": create_cartridge_support_structure(params),
        "cartridge_retainers": create_cartridge_retainers(params),
        "cooler_doubler_frames": create_cooler_doubler_frames(params),
        "internal_air_management_REFERENCE": create_internal_air_management(params),
        "condensate_trays": create_condensation_management(params),
        "immersion_caps": create_immersion_caps(params),
        "immersion_cap_gaskets_REFERENCE": create_immersion_cap_gaskets(params),
        "solar_shields": create_sun_shields(params),
    }
    exported: list[Path] = []
    for name, part in items.items():
        exported.extend(
            _export_workplane(
                part,
                f"am59_sealed_tec_enclosure_{version}_{name}",
                formats,
            )
        )

    assembly_variants = {
        "operating": {},
        "service_open": {"service_open": True},
        "immersion_ready": {"immersion_ready": True},
    }
    for name, options in assembly_variants.items():
        path = EXPORTS_DIR / f"am59_sealed_tec_enclosure_{version}_{name}.step"
        create_assembly(params, **options).save(str(path))
        exported.append(path)
        print(f"  exported {path.relative_to(PROJECT_ROOT)}")
    return exported


if __name__ == "__main__":
    design_params = load_params()
    assessment = thermal_assessment(design_params)
    print(f"Building {design_params['part_name']} ({design_params['version']})")
    print(
        "Thermal design: "
        f"{assessment['per_unit_capacity_w']:.1f} W/unit at "
        f"{assessment['ambient_c']:.0f} C ambient and "
        f"{assessment['enclosure_air_c']:.0f} C enclosure air"
    )
    print(
        "Environmental status: operating IP66 target; unpowered IPX7 target "
        "only with both secondary immersion caps installed; all tests pending"
    )
    export_design(design_params, include_stl="--stl" in sys.argv)
