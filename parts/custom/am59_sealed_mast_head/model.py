"""
AM59 sealed mast head, V2
=========================

Concept-level CadQuery definition for a welded IP66/IP67-target dry enclosure,
closed internal air/liquid thermal loop, floodable external wet cooling bay,
and independent rotator load-bypass frame.

This model establishes packaging and environmental boundaries. Heat exchangers,
pumps, fans, feedthroughs, gasket details, welds, fasteners, and mast interfaces
remain qualification or supplier-controlled items unless explicitly released.

Coordinate system
-----------------
X : AM59 airflow, factory fan inlet (-X) to RF output / thermal bay (+X)
Y : across the amplifier mounting flange
Z : mast axis, upward
"""

from __future__ import annotations

import json
import sys
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
) -> cq.Workplane:
    return cq.Workplane(
        obj=cq.Solid.makeCylinder(
            diameter / 2,
            length,
            cq.Vector(*start),
            cq.Vector(1, 0, 0),
        )
    )


def _tube_post(
    outer: float,
    wall: float,
    height: float,
    center_x: float,
    center_y: float,
    bottom_z: float,
) -> cq.Workplane:
    outer_shape = (
        cq.Workplane("XY")
        .box(outer, outer, height, centered=(True, True, False))
        .translate((center_x, center_y, bottom_z))
    )
    inner_shape = (
        cq.Workplane("XY")
        .box(
            outer - 2 * wall,
            outer - 2 * wall,
            height + 2.0,
            centered=(True, True, False),
        )
        .translate((center_x, center_y, bottom_z - 1.0))
    )
    return outer_shape.cut(inner_shape)


def create_structural_frame(params: dict | None = None) -> cq.Workplane:
    """Create the independent antenna/rotator load path and pod cradle."""
    if params is None:
        params = load_params()
    f = params["frame"]

    def interface_plate(bottom_z: float, thickness: float) -> cq.Workplane:
        plate = (
            cq.Workplane("XY")
            .box(
                f["interface_core_size"],
                f["interface_core_size"],
                thickness,
                centered=(True, True, False),
            )
            .translate((0, 0, bottom_z))
        )
        for x_sign in (-1, 1):
            for y_sign in (-1, 1):
                pad = (
                    cq.Workplane("XY")
                    .box(
                        f["post_pad_size"],
                        f["post_pad_size"],
                        thickness,
                        centered=(True, True, False),
                    )
                    .translate(
                        (
                            x_sign * f["post_center_x"],
                            y_sign * f["post_center_y"],
                            bottom_z,
                        )
                    )
                )
                neck = (
                    cq.Workplane("XY")
                    .box(
                        f["post_pad_neck_size"],
                        f["post_pad_neck_size"],
                        thickness,
                        centered=(True, True, False),
                    )
                    .translate(
                        (
                            x_sign * (f["interface_core_size"] / 2 - f["post_pad_neck_size"] / 4),
                            y_sign * (f["interface_core_size"] / 2 + f["post_pad_neck_size"] / 4),
                            bottom_z,
                        )
                    )
                )
                plate = plate.union(neck).union(pad)
        return plate

    lower = interface_plate(0.0, f["lower_plate_thickness"])
    upper = interface_plate(
        f["upper_plate_bottom_z"],
        f["upper_plate_thickness"],
    )
    result = lower.union(upper)

    post_height = f["upper_plate_bottom_z"] - f["lower_plate_thickness"]
    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            result = result.union(
                _tube_post(
                    f["post_outer_size"],
                    f["post_wall"],
                    post_height,
                    x_sign * f["post_center_x"],
                    y_sign * f["post_center_y"],
                    f["lower_plate_thickness"],
                )
            )

    for x_sign in (-1, 1):
        crossbar = (
            cq.Workplane("XY")
            .box(
                f["cradle_crossbar_width_x"],
                f["cradle_crossbar_length_y"],
                f["cradle_crossbar_height"],
                centered=(True, True, False),
            )
            .translate(
                (
                    x_sign * f["post_center_x"],
                    0,
                    f["lower_plate_thickness"],
                )
            )
        )
        result = result.union(crossbar)

    for y_sign in (-1, 1):
        rail_length = f["cradle_rail_x_max"] - f["cradle_rail_x_min"]
        rail_center_x = (f["cradle_rail_x_min"] + f["cradle_rail_x_max"]) / 2
        rail = (
            cq.Workplane("XY")
            .box(
                rail_length,
                f["cradle_rail_width_y"],
                f["cradle_rail_height"],
                centered=(True, True, False),
            )
            .translate(
                (
                    rail_center_x,
                    y_sign * f["cradle_rail_center_y"],
                    f["lower_plate_thickness"],
                )
            )
        )
        result = result.union(rail)

    return result


def create_dry_enclosure(params: dict | None = None) -> cq.Workplane:
    """Create the welded dry pressure body, open only at the -X service end."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]

    length = e["x_max"] - e["x_min"]
    width = e["outer_width_y"]
    height = e["z_max"] - e["z_min"]
    wall = e["wall_thickness"]
    center_x = (e["x_min"] + e["x_max"]) / 2
    center_z = (e["z_min"] + e["z_max"]) / 2

    outer = _box(length, width, height, (center_x, 0, center_z))
    inner = _box(
        length - wall + 2.0,
        width - 2 * wall,
        height - 2 * wall,
        (
            e["x_min"] - 1.0 + (length - wall + 2.0) / 2,
            0,
            center_z,
        ),
    )
    shell = outer.cut(inner)

    flange_outer = _box(
        e["flange_thickness_x"],
        width,
        height,
        (e["x_min"] + e["flange_thickness_x"] / 2, 0, center_z),
    )
    flange_opening = _box(
        e["flange_thickness_x"] + 2.0,
        e["flange_opening_width_y"],
        e["flange_opening_height_z"],
        (e["x_min"] + e["flange_thickness_x"] / 2, 0, center_z),
    )
    flange = flange_outer.cut(flange_opening)
    shell = shell.union(flange)

    # Blind internal pads reserve machined lands without piercing the boundary.
    connector_pad = _box(7.0, 190.0, 58.0, (e["x_max"] - 6.5, 0, 57.0))
    coolant_pad = _box(7.0, 190.0, 45.0, (e["x_max"] - 6.5, 0, 112.5))
    shell = shell.union(connector_pad).union(coolant_pad)
    return shell


def service_fastener_locations(
    params: dict | None = None,
) -> list[tuple[float, float]]:
    """Return Y/Z locations for blind service-cover fasteners."""
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
    """Create the removable -X lid with outside-of-seal captive screw holes."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    lid = params["service_lid"]

    thickness = lid["plate_thickness_x"]
    result = _box(
        thickness,
        lid["outer_width_y"],
        lid["outer_height_z"],
        (e["x_min"] - thickness / 2, 0, (e["z_min"] + e["z_max"]) / 2),
    )

    for y, z in service_fastener_locations(params):
        cutter = _cylinder_x(
            lid["fastener_diameter"],
            thickness + 2.0,
            (e["x_min"] - thickness - 1.0, y, z),
        )
        result = result.cut(cutter)

    # Shallow external ribs reduce lid deflection and drain vertically.
    for y in (-65.0, 65.0):
        rib = _box(4.0, 18.0, 190.0, (e["x_min"] - thickness - 2.0, y, 150.0))
        result = result.union(rib)
    return result


def create_environmental_gasket(params: dict | None = None) -> cq.Workplane:
    """Create a continuous ring proxy for the supplier-controlled EPDM seal."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    lid = params["service_lid"]
    thickness = lid["seal_proxy_thickness_x"]
    outer_w = lid["seal_ring_outer_width_y"]
    outer_h = lid["seal_ring_outer_height_z"]
    ring_w = lid["seal_ring_width"]
    center = (e["x_min"], 0, (e["z_min"] + e["z_max"]) / 2)

    outer = _box(thickness, outer_w, outer_h, center)
    inner = _box(
        thickness + 2.0,
        outer_w - 2 * ring_w,
        outer_h - 2 * ring_w,
        center,
    )
    return outer.cut(inner)


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
    opening = _box(
        c["inner_opening_length_x"],
        c["inner_opening_width_y"],
        c["thickness"] + 2.0,
        (
            c["center_x"],
            0,
            z0 + c["thickness"] / 2,
        ),
    )
    result = result.cut(opening)

    for x in a["mount_hole_x"]:
        for y in a["mount_hole_y"]:
            cutter = cq.Workplane(
                obj=cq.Solid.makeCylinder(
                    c["mount_hole_diameter"] / 2,
                    c["thickness"] + 2.0,
                    cq.Vector(x, y, z0 - 1.0),
                    cq.Vector(0, 0, 1),
                )
            )
            result = result.cut(cutter)
    return result


def create_amplifier_reference(params: dict | None = None) -> cq.Workplane:
    """Import and place the exact user-supplied AM59 STEP."""
    if params is None:
        params = load_params()
    if not AMPLIFIER_STEP.is_file():
        raise FileNotFoundError(f"Missing amplifier STEP: {AMPLIFIER_STEP}")
    transform = params["amplifier"]["step_transform"]
    return (
        cq.importers.importStep(str(AMPLIFIER_STEP))
        .rotate((0, 0, 0), (1, 0, 0), transform["rotate_x_deg"])
        .translate(tuple(transform["translate"]))
    )


def internal_air_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Return dry-side coil/blower envelopes and recirculation baffles."""
    if params is None:
        params = load_params()
    air = params["internal_air_loop"]

    coil = _box(
        air["coil_x_max"] - air["coil_x_min"],
        air["coil_y_max"] - air["coil_y_min"],
        air["coil_z_max"] - air["coil_z_min"],
        (
            (air["coil_x_min"] + air["coil_x_max"]) / 2,
            (air["coil_y_min"] + air["coil_y_max"]) / 2,
            (air["coil_z_min"] + air["coil_z_max"]) / 2,
        ),
    )

    divider = _box(
        air["roof_return_x_max"] - air["roof_return_x_min"],
        air["roof_return_width_y"],
        air["divider_z_max"] - air["divider_z_min"],
        (
            (air["roof_return_x_min"] + air["roof_return_x_max"]) / 2,
            0,
            (air["divider_z_min"] + air["divider_z_max"]) / 2,
        ),
    )
    cold_drop = _box(
        air["cold_drop_x_max"] - air["cold_drop_x_min"],
        air["roof_return_width_y"],
        air["divider_z_min"] - 82.0,
        (
            (air["cold_drop_x_min"] + air["cold_drop_x_max"]) / 2,
            0,
            82.0 + (air["divider_z_min"] - 82.0) / 2,
        ),
    )

    parts = {
        "dry_air_to_liquid_coil_REFERENCE": coil,
        "dry_return_divider": divider,
        "cold_drop_baffle": cold_drop,
    }
    for index, center_y in enumerate(air["blower_center_y"], start=1):
        blower = _box(
            air["blower_envelope_x"],
            air["blower_envelope_y"],
            air["blower_envelope_z"],
            (
                air["blower_center_x"],
                center_y,
                air["blower_center_z"],
            ),
        )
        parts[f"dry_recirculation_blower_{index}_REFERENCE"] = blower
    return parts


def create_internal_thermal_module(params: dict | None = None) -> cq.Workplane:
    """Return performance envelopes for the internal coil and dry blowers."""
    if params is None:
        params = load_params()
    components = internal_air_components(params)
    selected = [
        component
        for name, component in components.items()
        if name == "dry_air_to_liquid_coil_REFERENCE"
        or name.startswith("dry_recirculation_blower_")
    ]
    return _compound(selected)


def wet_cooling_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Return floodable external radiator, pump, fan, and shroud envelopes."""
    if params is None:
        params = load_params()
    wet = params["wet_cooling_bay"]

    radiator = _box(
        wet["radiator_x_max"] - wet["radiator_x_min"],
        wet["radiator_width_y"],
        wet["radiator_z_max"] - wet["radiator_z_min"],
        (
            (wet["radiator_x_min"] + wet["radiator_x_max"]) / 2,
            0,
            (wet["radiator_z_min"] + wet["radiator_z_max"]) / 2,
        ),
    )
    parts: dict[str, cq.Workplane] = {
        "external_liquid_to_air_radiator_REFERENCE": radiator,
    }

    for index, center_y in enumerate(wet["fan_center_y"], start=1):
        fan = _cylinder_x(
            wet["fan_diameter"],
            wet["fan_depth"],
            (
                wet["fan_center_x"] - wet["fan_depth"] / 2,
                center_y,
                wet["fan_center_z"],
            ),
        )
        parts[f"external_IP68_fan_{index}_REFERENCE"] = fan

    pump_length = wet["pump_tray_x_max"] - wet["pump_tray_x_min"] - 15.0
    for index, center_y in enumerate((-55.0, 55.0), start=1):
        pump = _cylinder_x(
            34.0,
            pump_length,
            (
                wet["pump_tray_x_min"] + 7.5,
                center_y,
                53.0,
            ),
        )
        parts[f"external_brushless_pump_{index}_REFERENCE"] = pump

    # Open-sided shroud: the pressure boundary is the fixed enclosure wall.
    shroud_length = wet["x_max"] - wet["x_min"]
    shroud_height = wet["z_max"] - wet["z_min"]
    t = 2.0
    parts["wet_shroud_roof"] = _box(
        shroud_length,
        wet["outer_width_y"],
        t,
        (
            (wet["x_min"] + wet["x_max"]) / 2,
            0,
            wet["z_max"] - t / 2,
        ),
    )
    for sign, name in ((-1, "negative"), (1, "positive")):
        parts[f"wet_shroud_side_{name}"] = _box(
            shroud_length,
            t,
            shroud_height - wet["drain_slot_height"],
            (
                (wet["x_min"] + wet["x_max"]) / 2,
                sign * (wet["outer_width_y"] / 2 - t / 2),
                wet["z_min"]
                + wet["drain_slot_height"]
                + (shroud_height - wet["drain_slot_height"]) / 2,
            ),
        )

    tray_t = 2.0
    parts["wet_hydraulic_drip_tray"] = _box(
        wet["pump_tray_x_max"] - wet["pump_tray_x_min"],
        wet["pump_tray_width_y"],
        tray_t,
        (
            (wet["pump_tray_x_min"] + wet["pump_tray_x_max"]) / 2,
            0,
            wet["pump_tray_z_min"] + tray_t / 2,
        ),
    )
    return parts


def create_wet_cooling_module(params: dict | None = None) -> cq.Workplane:
    return _compound(list(wet_cooling_components(params).values()))


def create_coolant_bulkhead_references(
    params: dict | None = None,
) -> cq.Workplane:
    """Show the two welded/brazed tube-penetration qualification envelopes."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    liquid = params["liquid_loop"]
    tubes: list[cq.Workplane] = []
    for center_y in (-55.0, 55.0):
        tubes.append(
            _cylinder_x(
                liquid["tube_penetration_diameter_keepout"],
                24.0,
                (e["x_max"] - 8.0, center_y, 112.0),
            )
        )
    return _compound(tubes)


def create_feedthrough_references(params: dict | None = None) -> cq.Workplane:
    """Show reserved, non-released RF and electrical pressure-wall entries."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    ports = [
        (32.0, -70.0, 62.0),
        (24.0, 0.0, 62.0),
        (30.0, 70.0, 62.0),
    ]
    refs = [_cylinder_x(diameter, 28.0, (e["x_max"] - 8.0, y, z)) for diameter, y, z in ports]
    return _compound(refs)


def create_pressure_vent_reference(params: dict | None = None) -> cq.Workplane:
    """Show a sheltered screw-in ePTFE vent envelope on the fixed sidewall."""
    if params is None:
        params = load_params()
    e = params["sealed_enclosure"]
    return cq.Workplane(
        obj=cq.Solid.makeCylinder(
            9.0,
            18.0,
            cq.Vector(-275.0, -e["outer_width_y"] / 2 + 4.0, 246.0),
            cq.Vector(0, -1, 0),
        )
    )


def create_sun_shield(params: dict | None = None) -> cq.Workplane:
    """Create the ventilated white solar shield; it is not an ingress barrier."""
    if params is None:
        params = load_params()
    shield = params["sun_shield"]
    return (
        cq.Workplane("XY")
        .box(
            shield["length_x"],
            shield["width_y"],
            shield["thickness"],
            centered=(True, True, False),
        )
        .translate((-80.0, 0, shield["bottom_z"]))
    )


def create_mast_reference(params: dict | None = None) -> cq.Workplane:
    """Simplified context only; the proprietary castle interface is not copied."""
    if params is None:
        params = load_params()
    ref = params["reference_geometry"]
    plate = (
        cq.Workplane("XY")
        .box(
            ref["existing_plate_length_x"],
            ref["existing_plate_width_y"],
            ref["existing_plate_thickness"],
            centered=(True, True, False),
        )
        .translate((0, 0, -ref["existing_plate_thickness"]))
    )
    pole = cq.Workplane(
        obj=cq.Solid.makeCylinder(
            ref["mast_od"] / 2,
            ref["mast_reference_length"],
            cq.Vector(
                0,
                0,
                -ref["existing_plate_thickness"] - ref["mast_reference_length"],
            ),
            cq.Vector(0, 0, 1),
        )
    )
    return plate.union(pole)


def create_rotator_reference(params: dict | None = None) -> cq.Workplane:
    """Generic rotator keepout, not the user's unresolved rotator geometry."""
    if params is None:
        params = load_params()
    frame = params["frame"]
    ref = params["reference_geometry"]
    z0 = frame["upper_plate_bottom_z"] + frame["upper_plate_thickness"]
    body = cq.Workplane(
        obj=cq.Solid.makeCylinder(
            ref["rotator_keepout_diameter"] / 2,
            ref["rotator_keepout_height"],
            cq.Vector(0, 0, z0),
            cq.Vector(0, 0, 1),
        )
    )
    flange = cq.Workplane(
        obj=cq.Solid.makeCylinder(
            ref["rotator_keepout_diameter"] / 2 + 10.0,
            8.0,
            cq.Vector(0, 0, z0),
            cq.Vector(0, 0, 1),
        )
    )
    return body.union(flange)


def create_part(params: dict | None = None) -> cq.Workplane:
    """Release-gated primary part remains the structural load-bypass frame."""
    return create_structural_frame(params)


def create_assembly(
    params: dict | None = None,
    *,
    service_open: bool = False,
    thermal_exploded: bool = False,
) -> cq.Assembly:
    if params is None:
        params = load_params()
    assembly = cq.Assembly()
    assembly.add(
        create_mast_reference(params),
        name="existing_BlueSky_pipe_and_plate_REFERENCE",
        color=cq.Color(0.12, 0.12, 0.13, 1.0),
    )
    assembly.add(
        create_structural_frame(params),
        name="antenna_load_bypass_frame",
        color=cq.Color(0.34, 0.36, 0.39, 1.0),
    )
    assembly.add(
        create_dry_enclosure(params),
        name="continuously_welded_dry_pressure_body",
        color=cq.Color(0.76, 0.79, 0.82, 0.45),
    )

    if not service_open:
        assembly.add(
            create_environmental_gasket(params),
            name="continuous_EPDM_environmental_seal_REFERENCE",
            color=cq.Color(0.08, 0.12, 0.10, 1.0),
        )
        assembly.add(
            create_service_lid(params),
            name="bolted_blind_fastener_service_lid",
            color=cq.Color(0.82, 0.84, 0.86, 1.0),
        )

    assembly.add(
        create_internal_cartridge(params),
        name="removable_AM59_cartridge",
        color=cq.Color(0.18, 0.38, 0.68, 1.0),
    )
    assembly.add(
        create_amplifier_reference(params),
        name="AM59_3S_64_64_VENDOR_REFERENCE",
        color=cq.Color(0.29, 0.30, 0.32, 1.0),
    )

    thermal_offset = (55.0, 0, 0) if thermal_exploded else (0, 0, 0)
    for name, component in internal_air_components(params).items():
        assembly.add(
            component.translate(thermal_offset),
            name=name,
            color=(
                cq.Color(0.20, 0.55, 0.72, 0.42)
                if "coil" in name
                else cq.Color(0.25, 0.45, 0.58, 0.40)
            ),
        )
    assembly.add(
        create_coolant_bulkhead_references(params).translate(thermal_offset),
        name="two_welded_coolant_penetrations_REFERENCE",
        color=cq.Color(0.18, 0.50, 0.78, 0.72),
    )
    assembly.add(
        create_feedthrough_references(params),
        name="qualified_RF_power_control_feedthroughs_REFERENCE",
        color=cq.Color(0.72, 0.58, 0.18, 1.0),
    )
    assembly.add(
        create_pressure_vent_reference(params),
        name="IP68_IP69K_pressure_equalization_vent_REFERENCE",
        color=cq.Color(0.12, 0.12, 0.12, 1.0),
    )

    for name, component in wet_cooling_components(params).items():
        assembly.add(
            component.translate(thermal_offset),
            name=name,
            color=(
                cq.Color(0.15, 0.48, 0.72, 0.52)
                if "radiator" in name
                else cq.Color(0.18, 0.20, 0.22, 0.88)
                if "fan" in name or "pump" in name
                else cq.Color(0.64, 0.68, 0.72, 0.45)
            ),
        )

    assembly.add(
        create_sun_shield(params),
        name="white_ventilated_solar_shield",
        color=cq.Color(0.93, 0.94, 0.95, 0.75),
    )
    assembly.add(
        create_rotator_reference(params),
        name="rotator_KEEP_OUT_REFERENCE",
        color=cq.Color(0.18, 0.18, 0.20, 0.35),
    )
    return assembly


def build_stages(params: dict | None = None):
    if params is None:
        params = load_params()
    yield "structural_frame", create_structural_frame(params)


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
        "structural_frame": create_structural_frame(params),
        "dry_pressure_body": create_dry_enclosure(params),
        "service_lid": create_service_lid(params),
        "environmental_gasket_REFERENCE": create_environmental_gasket(params),
        "AM59_cartridge": create_internal_cartridge(params),
        "internal_thermal_module_REFERENCE": create_internal_thermal_module(params),
        "wet_cooling_module_REFERENCE": create_wet_cooling_module(params),
        "solar_shield": create_sun_shield(params),
    }
    exported: list[Path] = []
    for name, part in items.items():
        exported.extend(
            _export_workplane(
                part,
                f"am59_sealed_mast_head_{version}_{name}",
                formats,
            )
        )

    closed_path = EXPORTS_DIR / f"am59_sealed_mast_head_{version}_assembly.step"
    create_assembly(params).save(str(closed_path))
    exported.append(closed_path)
    print(f"  exported {closed_path.relative_to(PROJECT_ROOT)}")

    open_path = EXPORTS_DIR / f"am59_sealed_mast_head_{version}_service_open.step"
    create_assembly(params, service_open=True).save(str(open_path))
    exported.append(open_path)
    print(f"  exported {open_path.relative_to(PROJECT_ROOT)}")
    return exported


if __name__ == "__main__":
    design_params = load_params()
    print(f"Building {design_params['part_name']} ({design_params['version']})")
    print("Status: IP66/IP67 design target; verification/certification pending")
    export_design(design_params, include_stl="--stl" in sys.argv)
