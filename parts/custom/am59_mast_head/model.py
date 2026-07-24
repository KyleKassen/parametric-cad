"""
AM59 centered bridge mast head
===============================

Preliminary CadQuery design for placing an AM59-3S-64-64 immediately below
an antenna rotator on a BlueSky AL2 mast.

The design deliberately does not reproduce the BlueSky castle geometry.
The user's existing castle-cut pipe and plate remain the lower interface.
Likewise, v1 leaves the lower and rotator bolt patterns undrilled until both
interfaces are surveyed.

Coordinate system
-----------------
X : AM59 airflow direction, fan end (-X) to output end (+X)
Y : across the 200 mm amplifier mounting flange
Z : mast axis, upward
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
EXPORTS_DIR = PART_DIR / "exports"
PARAMS_FILE = PART_DIR / "params.json"
AMPLIFIER_STEP = (
    PROJECT_ROOT / "parts" / "vendor" / "microwave-amps" / "AM59-3S-64-64.STEP"
)


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
    return (
        cq.Workplane("XY")
        .box(length_x, width_y, height_z)
        .translate(center)
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
    inner = (
        cq.Workplane("XY")
        .box(
            outer - 2 * wall,
            outer - 2 * wall,
            height + 2.0,
            centered=(True, True, False),
        )
        .translate((center_x, center_y, bottom_z - 1.0))
    )
    return outer_shape.cut(inner)


def create_structural_frame(params: dict | None = None) -> cq.Workplane:
    """Create the conceptual load-bypass frame as one fused validation body."""
    if params is None:
        params = load_params()
    f = params["frame"]

    lower_t = f["lower_plate_thickness"]
    upper_z = f["upper_plate_bottom_z"]
    upper_t = f["upper_plate_thickness"]

    result = (
        cq.Workplane("XY")
        .box(
            f["lower_plate_length_x"],
            f["lower_plate_width_y"],
            lower_t,
            centered=(True, True, False),
        )
    )

    upper = (
        cq.Workplane("XY")
        .box(
            f["upper_plate_length_x"],
            f["upper_plate_width_y"],
            upper_t,
            centered=(True, True, False),
        )
        .translate((0, 0, upper_z))
    )
    result = result.union(upper)

    post_height = upper_z - lower_t
    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            post = _tube_post(
                f["post_outer_size"],
                f["post_wall"],
                post_height,
                x_sign * f["post_center_x"],
                y_sign * f["post_center_y"],
                lower_t,
            )
            result = result.union(post)

    for x_sign in (-1, 1):
        support = (
            cq.Workplane("XY")
            .box(
                f["support_bar_width_x"],
                f["support_bar_length_y"],
                f["support_bar_height"],
                centered=(True, True, False),
            )
            .translate(
                (
                    x_sign * f["support_bar_center_x"],
                    0,
                    lower_t,
                )
            )
        )
        result = result.union(support)

    c = params["cartridge"]
    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            tap_hole = (
                cq.Workplane("XY")
                .workplane(offset=lower_t)
                .center(
                    x_sign * c["end_lock_hole_x"],
                    y_sign * c["end_lock_hole_y"],
                )
                .circle(f["cartridge_lock_tap_diameter"] / 2)
                .extrude(f["support_bar_height"] + 0.1)
            )
            result = result.cut(tap_hole)

    return result


def create_cartridge(params: dict | None = None) -> cq.Workplane:
    """Create the removable amplifier mounting cartridge."""
    if params is None:
        params = load_params()
    c = params["cartridge"]
    a = params["amplifier"]

    z0 = c["bottom_z"]
    t = c["thickness"]
    result = (
        cq.Workplane("XY")
        .box(
            c["outer_length_x"],
            c["outer_width_y"],
            t,
            centered=(True, True, False),
        )
        .translate((0, 0, z0))
    )
    core_outer_y = c["outer_width_y"] / 2
    ear_width_y = c["lock_ear_outer_y"] - core_outer_y
    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            ear = (
                cq.Workplane("XY")
                .box(
                    c["lock_ear_length_x"],
                    ear_width_y,
                    t,
                    centered=(True, True, False),
                )
                .translate(
                    (
                        x_sign * c["end_lock_hole_x"],
                        y_sign * (core_outer_y + ear_width_y / 2),
                        z0,
                    )
                )
            )
            result = result.union(ear)
    opening = (
        cq.Workplane("XY")
        .box(
            c["inner_opening_length_x"],
            c["inner_opening_width_y"],
            t + 2.0,
            centered=(True, True, False),
        )
        .translate((0, 0, z0 - 1.0))
    )
    result = result.cut(opening)

    for x in a["mount_hole_x"]:
        for y in a["mount_hole_y"]:
            cutter = (
                cq.Workplane("XY")
                .workplane(offset=z0 - 1.0)
                .center(x, y)
                .circle(c["mount_hole_diameter"] / 2)
                .extrude(t + 2.0)
            )
            result = result.cut(cutter)
            countersink_depth = (
                c["mount_countersink_diameter"]
                - c["mount_hole_diameter"]
            ) / (
                2
                * math.tan(
                    math.radians(c["mount_countersink_angle_deg"] / 2)
                )
            )
            countersink = cq.Workplane(
                obj=cq.Solid.makeCone(
                    c["mount_countersink_diameter"] / 2,
                    c["mount_hole_diameter"] / 2,
                    countersink_depth,
                    cq.Vector(x, y, z0),
                    cq.Vector(0, 0, 1),
                )
            )
            result = result.cut(countersink)

    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            cutter = (
                cq.Workplane("XY")
                .workplane(offset=z0 - 1.0)
                .center(
                    x_sign * c["end_lock_hole_x"],
                    y_sign * c["end_lock_hole_y"],
                )
                .circle(c["end_lock_hole_diameter"] / 2)
                .extrude(t + 2.0)
            )
            result = result.cut(cutter)

    return result


def weather_components(params: dict | None = None) -> dict[str, cq.Workplane]:
    """Return separately addressable non-structural rain/sun shield panels."""
    if params is None:
        params = load_params()
    s = params["weather_shell"]
    f = params["frame"]

    t = s["sheet_thickness"]
    length = s["outer_length_x"]
    width = s["outer_width_y"]
    x_edge = length / 2
    y_edge = width / 2
    roof_z = s["roof_bottom_z"]

    roof = (
        cq.Workplane("XY")
        .box(length, width, t, centered=(True, True, False))
        .translate((0, 0, roof_z))
    )
    post_cut = f["post_outer_size"] + 2 * s["post_roof_clearance"]
    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            cutter = (
                cq.Workplane("XY")
                .box(post_cut, post_cut, t + 3.0, centered=(True, True, False))
                .translate(
                    (
                        x_sign * f["post_center_x"],
                        y_sign * f["post_center_y"],
                        roof_z - 1.0,
                    )
                )
            )
            roof = roof.cut(cutter)

    side_height = roof_z - s["side_wall_bottom_z"]
    side_parts: dict[str, cq.Workplane] = {}
    for side_name, sign in (("service_side", 1), ("fixed_side", -1)):
        panel = (
            cq.Workplane("XY")
            .box(length, t, side_height, centered=(True, True, False))
            .translate(
                (
                    0,
                    sign * (y_edge - t / 2),
                    s["side_wall_bottom_z"],
                )
            )
        )
        win_len = (
            s["side_exhaust_window_x_max"]
            - s["side_exhaust_window_x_min"]
        )
        window = (
            cq.Workplane("XY")
            .box(
                win_len,
                t + 3.0,
                s["side_exhaust_window_height_z"],
                centered=(True, True, False),
            )
            .translate(
                (
                    (
                        s["side_exhaust_window_x_min"]
                        + s["side_exhaust_window_x_max"]
                    )
                    / 2,
                    sign * (y_edge - t / 2),
                    s["side_exhaust_window_bottom_z"],
                )
            )
        )
        side_parts[side_name] = panel.cut(window)

    inlet_height = roof_z - s["inlet_baffle_bottom_z"]
    inlet = (
        cq.Workplane("XY")
        .box(t, width, inlet_height, centered=(True, True, False))
        .translate(
            (
                -x_edge + t / 2,
                0,
                s["inlet_baffle_bottom_z"],
            )
        )
    )
    for center_y in s["inlet_window_centers_y"]:
        window = (
            cq.Workplane("XY")
            .box(
                t + 3.0,
                s["inlet_window_width_y"],
                s["inlet_window_height_z"],
                centered=(True, True, False),
            )
            .translate(
                (
                    -x_edge + t / 2 + 1.0,
                    center_y,
                    s["inlet_window_bottom_z"],
                )
            )
        )
        inlet = inlet.cut(window)

    exhaust_height = roof_z - s["exhaust_baffle_bottom_z"]
    exhaust = (
        cq.Workplane("XY")
        .box(t, width, exhaust_height, centered=(True, True, False))
        .translate(
            (
                x_edge - t / 2,
                0,
                s["exhaust_baffle_bottom_z"],
            )
        )
    )
    for y_sign in (-1, 1):
        window = (
            cq.Workplane("XY")
            .box(
                t + 3.0,
                s["exhaust_window_width_y"],
                s["exhaust_window_height_z"],
                centered=(True, True, False),
            )
            .translate(
                (
                    x_edge - t / 2 - 1.0,
                    y_sign * s["exhaust_window_center_y"],
                    s["exhaust_window_bottom_z"],
                )
            )
        )
        exhaust = exhaust.cut(window)

    louver_parts: list[cq.Workplane] = []
    blade_count = s["louver_blade_count_per_window"]
    blade_pitch = s["exhaust_window_height_z"] / blade_count
    for y_sign in (-1, 1):
        for index in range(blade_count):
            z = (
                s["exhaust_window_bottom_z"]
                + (index + 0.65) * blade_pitch
            )
            blade = (
                cq.Workplane("XY")
                .box(
                    s["louver_blade_projection"],
                    s["exhaust_window_width_y"] - 6.0,
                    1.2,
                )
                .rotate(
                    (0, 0, 0),
                    (0, 1, 0),
                    s["louver_blade_angle_deg"],
                )
                .translate(
                    (
                        x_edge + s["louver_blade_projection"] / 2 - 2.0,
                        y_sign * s["exhaust_window_center_y"],
                        z,
                    )
                )
            )
            louver_parts.append(blade)

    inlet_louver_parts: list[cq.Workplane] = []
    inlet_blade_count = s["inlet_louver_blade_count_per_window"]
    inlet_blade_pitch = s["inlet_window_height_z"] / inlet_blade_count
    for center_y in s["inlet_window_centers_y"]:
        for index in range(inlet_blade_count):
            z = (
                s["inlet_window_bottom_z"]
                + (index + 0.65) * inlet_blade_pitch
            )
            blade = (
                cq.Workplane("XY")
                .box(
                    s["louver_blade_projection"],
                    s["inlet_window_width_y"] - 6.0,
                    1.2,
                )
                .rotate(
                    (0, 0, 0),
                    (0, 1, 0),
                    -s["louver_blade_angle_deg"],
                )
                .translate(
                    (
                        -x_edge - s["louver_blade_projection"] / 2 + 2.0,
                        center_y,
                        z,
                    )
                )
            )
            inlet_louver_parts.append(blade)

    parts = {
        "roof": roof,
        "service_side": side_parts["service_side"],
        "fixed_side": side_parts["fixed_side"],
        "inlet_baffle": inlet,
        "exhaust_baffle": exhaust,
    }
    for index, blade in enumerate(louver_parts):
        parts[f"exhaust_louver_{index + 1}"] = blade
    for index, blade in enumerate(inlet_louver_parts):
        parts[f"inlet_louver_{index + 1}"] = blade
    return parts


def create_weather_shell(params: dict | None = None) -> cq.Workplane:
    return _compound(list(weather_components(params).values()))


def doghouse_components(params: dict | None = None) -> dict[str, cq.Workplane]:
    """Return the dry output-connector vestibule as removable sheet panels."""
    if params is None:
        params = load_params()
    d = params["connector_doghouse"]
    t = params["weather_shell"]["sheet_thickness"]

    length = d["x_max"] - d["x_min"]
    height = d["z_max"] - d["z_min"]
    center_x = (d["x_min"] + d["x_max"]) / 2
    y_edge = d["width_y"] / 2

    roof = (
        cq.Workplane("XY")
        .box(length, d["width_y"], t, centered=(True, True, False))
        .translate((center_x, 0, d["z_max"] - t))
    )
    floor = (
        cq.Workplane("XY")
        .box(length, d["width_y"], t, centered=(True, True, False))
        .translate((center_x, 0, d["z_min"]))
    )

    sides: dict[str, cq.Workplane] = {}
    for name, sign in (("doghouse_side_pos", 1), ("doghouse_side_neg", -1)):
        sides[name] = (
            cq.Workplane("XY")
            .box(length, t, height, centered=(True, True, False))
            .translate(
                (
                    center_x,
                    sign * (y_edge - t / 2),
                    d["z_min"],
                )
            )
        )

    bulkhead_side_width = (
        d["width_y"] - d["bulkhead_inner_width_y"]
    ) / 2
    bulkhead_height = d["z_max"] - d["bulkhead_open_bottom_z"]
    bulkhead_parts: dict[str, cq.Workplane] = {}
    for name, sign in (
        ("doghouse_bulkhead_side_pos", 1),
        ("doghouse_bulkhead_side_neg", -1),
    ):
        bulkhead_parts[name] = (
            cq.Workplane("XY")
            .box(
                t,
                bulkhead_side_width,
                bulkhead_height,
                centered=(True, True, False),
            )
            .translate(
                (
                    d["x_min"] + t / 2,
                    sign
                    * (
                        d["bulkhead_inner_width_y"] / 2
                        + bulkhead_side_width / 2
                    ),
                    d["bulkhead_open_bottom_z"],
                )
            )
        )
    bulkhead_parts["doghouse_bulkhead_top"] = (
        cq.Workplane("XY")
        .box(
            t,
            d["bulkhead_inner_width_y"],
            d["z_max"] - d["bulkhead_inner_top_z"],
            centered=(True, True, False),
        )
        .translate(
            (
                d["x_min"] + t / 2,
                0,
                d["bulkhead_inner_top_z"],
            )
        )
    )

    end_panel = (
        cq.Workplane("XY")
        .box(t, d["width_y"], height, centered=(True, True, False))
        .translate((d["x_max"] - t / 2, 0, d["z_min"]))
    )
    gland_specs = (
        (
            d["coax_gland_center_y"],
            d["coax_gland_center_z"],
            d["coax_gland_diameter"],
        ),
        (
            d["power_gland_center_y"],
            d["power_gland_center_z"],
            d["power_gland_diameter"],
        ),
        (
            d["fan_gland_center_y"],
            d["fan_gland_center_z"],
            d["fan_gland_diameter"],
        ),
    )
    for y, z, diameter in gland_specs:
        cutter = cq.Workplane(
            obj=cq.Solid.makeCylinder(
                diameter / 2,
                t + 3.0,
                cq.Vector(d["x_max"] - t - 1.0, y, z),
                cq.Vector(1, 0, 0),
            )
        )
        end_panel = end_panel.cut(cutter)

    result = {
        "doghouse_roof": roof,
        "doghouse_floor": floor,
        **sides,
        **bulkhead_parts,
        "doghouse_end": end_panel,
    }
    return result


def create_connector_doghouse(params: dict | None = None) -> cq.Workplane:
    return _compound(list(doghouse_components(params).values()))


def create_amplifier_reference(params: dict | None = None) -> cq.Workplane:
    """Import and place the exact vendor STEP in the horizontal cartridge pose."""
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


def create_mast_reference(params: dict | None = None) -> cq.Workplane:
    """Simplified context only; deliberately omits the castle geometry."""
    if params is None:
        params = load_params()
    r = params["reference_geometry"]
    plate = (
        cq.Workplane("XY")
        .box(
            r["existing_plate_length_x"],
            r["existing_plate_width_y"],
            r["existing_plate_thickness"],
            centered=(True, True, False),
        )
        .translate((0, 0, -r["existing_plate_thickness"]))
    )
    pole = cq.Workplane(
        obj=cq.Solid.makeCylinder(
            r["mast_od"] / 2,
            r["mast_reference_length"],
            cq.Vector(0, 0, -r["existing_plate_thickness"] - r["mast_reference_length"]),
            cq.Vector(0, 0, 1),
        )
    )
    return plate.union(pole)


def create_rotator_reference(params: dict | None = None) -> cq.Workplane:
    """Generic keep-out, not a model of the user's unknown rotator."""
    if params is None:
        params = load_params()
    f = params["frame"]
    r = params["reference_geometry"]
    z0 = f["upper_plate_bottom_z"] + f["upper_plate_thickness"]
    body = cq.Workplane(
        obj=cq.Solid.makeCylinder(
            r["rotator_keepout_diameter"] / 2,
            r["rotator_keepout_height"],
            cq.Vector(0, 0, z0),
            cq.Vector(0, 0, 1),
        )
    )
    flange = cq.Workplane(
        obj=cq.Solid.makeCylinder(
            r["rotator_keepout_diameter"] / 2 + 10.0,
            8.0,
            cq.Vector(0, 0, z0),
            cq.Vector(0, 0, 1),
        )
    )
    return body.union(flange)


def create_part(params: dict | None = None) -> cq.Workplane:
    """Primary release-gated body: the structural load-bypass frame."""
    return create_structural_frame(params)


def create_assembly(
    params: dict | None = None,
    *,
    open_service_panels: bool = False,
) -> cq.Assembly:
    if params is None:
        params = load_params()

    assembly = cq.Assembly()
    assembly.add(
        create_mast_reference(params),
        name="existing_castle_pipe_and_plate_REFERENCE",
        color=cq.Color(0.12, 0.12, 0.13, 1.0),
    )
    assembly.add(
        create_structural_frame(params),
        name="load_bypass_frame",
        color=cq.Color(0.38, 0.40, 0.43, 1.0),
    )
    assembly.add(
        create_cartridge(params),
        name="removable_amplifier_cartridge",
        color=cq.Color(0.15, 0.35, 0.65, 1.0),
    )
    assembly.add(
        create_amplifier_reference(params),
        name="AM59_3S_64_64_VENDOR_REFERENCE",
        color=cq.Color(0.30, 0.31, 0.33, 1.0),
    )

    for name, component in weather_components(params).items():
        if open_service_panels and (
            name in {"service_side", "fixed_side"}
            or name == "exhaust_baffle"
            or name.startswith("exhaust_louver_")
        ):
            continue
        assembly.add(
            component,
            name=name,
            color=cq.Color(0.82, 0.84, 0.86, 0.42),
        )

    for name, component in doghouse_components(params).items():
        if open_service_panels:
            continue
        assembly.add(
            component,
            name=name,
            color=cq.Color(0.72, 0.75, 0.78, 0.72),
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


def export_design(params: dict | None = None, *, include_stl: bool = False) -> list[Path]:
    if params is None:
        params = load_params()
    version = params.get("version", "v1")
    formats = ["step", "stl"] if include_stl else ["step"]
    exported: list[Path] = []

    exported.extend(
        _export_workplane(
            create_structural_frame(params),
            f"am59_mast_head_{version}_structural_frame",
            formats,
        )
    )
    exported.extend(
        _export_workplane(
            create_cartridge(params),
            f"am59_mast_head_{version}_cartridge",
            formats,
        )
    )
    exported.extend(
        _export_workplane(
            create_weather_shell(params),
            f"am59_mast_head_{version}_weather_shell",
            formats,
        )
    )
    exported.extend(
        _export_workplane(
            create_connector_doghouse(params),
            f"am59_mast_head_{version}_connector_doghouse",
            formats,
        )
    )

    closed_path = EXPORTS_DIR / f"am59_mast_head_{version}_assembly.step"
    create_assembly(params).save(str(closed_path))
    exported.append(closed_path)
    print(f"  exported {closed_path.relative_to(PROJECT_ROOT)}")

    open_path = EXPORTS_DIR / f"am59_mast_head_{version}_assembly_open.step"
    create_assembly(params, open_service_panels=True).save(str(open_path))
    exported.append(open_path)
    print(f"  exported {open_path.relative_to(PROJECT_ROOT)}")
    return exported


if __name__ == "__main__":
    design_params = load_params()
    print(f"Building {design_params['part_name']} ({design_params['version']})")
    print("Status: preliminary; lower/upper interface survey still required")
    export_design(design_params, include_stl="--stl" in sys.argv)
