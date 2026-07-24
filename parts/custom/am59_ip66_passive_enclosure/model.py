"""AM59 IP66 low-CG passive enclosure.

The exact supplied AM59 is placed through a welded vertical bulkhead.  Its
electronics section and all future DIN equipment are on the dry (+Y) side;
the OEM heatsink and fan bank remain in a drained wet (-Y) bay.  The wet rain
hood is secondary weather protection, not the pressure/dust boundary.

Coordinate system
-----------------
X : AM59 airflow, fan inlet (-X) to exhaust/connectors (+X)
Y : wet side (-Y) to dry service side (+Y)
Z : up; preliminary rotator reference plane is Z=0
"""

from __future__ import annotations

import json
import math
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
HOFFMAN_TE12_STEP = PROJECT_ROOT / "parts" / "vendor" / "Hoffman" / "te121024010.stp"
HOFFMAN_TE16_STEP = PROJECT_ROOT / "parts" / "vendor" / "Hoffman" / "te162024020.stp"


def load_params(path: Path = PARAMS_FILE) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=None)
def _import_step_shape(path: str) -> cq.Shape:
    return cq.importers.importStep(path).val()


def _box(
    length_x: float,
    depth_y: float,
    height_z: float,
    center: tuple[float, float, float],
) -> cq.Workplane:
    return cq.Workplane("XY").box(length_x, depth_y, height_z).translate(center)


def _compound(parts: list[cq.Workplane]) -> cq.Workplane:
    shapes: list[cq.Shape] = []
    for part in parts:
        shapes.extend(part.vals())
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


def _rect_ring_xz(
    outer_width_x: float,
    outer_height_z: float,
    inner_width_x: float,
    inner_height_z: float,
    y_min: float,
    y_max: float,
    center_z: float,
) -> cq.Workplane:
    depth = y_max - y_min
    center_y = (y_min + y_max) / 2
    outer = _box(
        outer_width_x,
        depth,
        outer_height_z,
        (0.0, center_y, center_z),
    )
    inner = _box(
        inner_width_x,
        depth + 2.0,
        inner_height_z,
        (0.0, center_y, center_z),
    )
    return outer.cut(inner)


def _volume_mm3(workplane: cq.Workplane) -> float:
    return sum(abs(solid.Volume()) for solid in workplane.solids().vals())


def _volume_centroid(workplane: cq.Workplane) -> tuple[float, float, float]:
    total = 0.0
    moments = [0.0, 0.0, 0.0]
    for solid in workplane.solids().vals():
        volume = abs(solid.Volume())
        center = solid.Center()
        total += volume
        moments[0] += volume * center.x
        moments[1] += volume * center.y
        moments[2] += volume * center.z
    if total <= 0.0:
        raise ValueError("Cannot calculate centroid of empty geometry")
    return tuple(moment / total for moment in moments)


def create_pressure_body(params: dict | None = None) -> cq.Workplane:
    """Create the continuously welded dry shell with both openings."""
    if params is None:
        params = load_params()
    e = params["dry_enclosure"]
    wall = e["sheet_wall_thickness"]
    z_center = (e["z_min"] + e["z_max"]) / 2
    body_depth = e["service_collar_y"][0] - e["bulkhead_y"][1]
    body_center_y = (e["service_collar_y"][0] + e["bulkhead_y"][1]) / 2

    bulkhead = _box(
        e["outer_length_x"],
        e["bulkhead_thickness_y"],
        e["outer_height_z"],
        (
            0.0,
            sum(e["bulkhead_y"]) / 2,
            z_center,
        ),
    )
    amplifier_opening = _box(
        e["amplifier_opening_width_x"],
        e["bulkhead_thickness_y"] + 2.0,
        e["amplifier_opening_height_z"],
        (
            0.0,
            sum(e["bulkhead_y"]) / 2,
            e["amplifier_opening_center_z"],
        ),
    )
    bulkhead = bulkhead.cut(amplifier_opening)

    side_parts = []
    for x_sign in (-1, 1):
        side_parts.append(
            _box(
                wall,
                body_depth,
                e["outer_height_z"],
                (
                    x_sign * (e["outer_length_x"] - wall) / 2,
                    body_center_y,
                    z_center,
                ),
            )
        )

    horizontal_span = e["outer_length_x"] - 2 * wall
    top_bottom_parts = []
    for z in (e["z_min"] + wall / 2, e["z_max"] - wall / 2):
        top_bottom_parts.append(
            _box(
                horizontal_span,
                body_depth,
                wall,
                (0.0, body_center_y, z),
            )
        )

    collar = _rect_ring_xz(
        e["service_collar_outer_width_x"],
        e["service_collar_outer_height_z"],
        e["service_collar_inner_width_x"],
        e["service_collar_inner_height_z"],
        e["service_collar_y"][0],
        e["service_collar_y"][1],
        z_center,
    )

    result = bulkhead
    for part in [*side_parts, *top_bottom_parts, collar]:
        result = result.union(part)
    return result


def create_part(params: dict | None = None) -> cq.Workplane:
    """Evaluation entry point: the welded pressure body is the source part."""
    return create_pressure_body(params)


def create_service_door(params: dict | None = None) -> cq.Workplane:
    """Create the removable service plate and integral passive fins."""
    if params is None:
        params = load_params()
    d = params["service_door"]
    e = params["dry_enclosure"]
    z_center = (e["z_min"] + e["z_max"]) / 2

    door = _box(
        d["outer_width_x"],
        d["plate_thickness_y"],
        d["outer_height_z"],
        (0.0, sum(d["plate_y"]) / 2, z_center),
    )

    usable_width = d["outer_width_x"] - 40.0
    if d["fin_count"] == 1:
        fin_x = [0.0]
    else:
        pitch = usable_width / (d["fin_count"] - 1)
        fin_x = [-usable_width / 2 + index * pitch for index in range(d["fin_count"])]
    for x in fin_x:
        fin = _box(
            d["fin_thickness_x"],
            d["fin_projection_y"],
            d["fin_height_z"],
            (
                x,
                sum(d["fin_y"]) / 2,
                z_center,
            ),
        )
        door = door.union(fin)
    return door


def create_service_gasket(params: dict | None = None) -> cq.Workplane:
    if params is None:
        params = load_params()
    d = params["service_door"]
    e = params["dry_enclosure"]
    inner_width = d["gasket_outer_width_x"] - 2 * d["gasket_ring_width"]
    inner_height = d["gasket_outer_height_z"] - 2 * d["gasket_ring_width"]
    return _rect_ring_xz(
        d["gasket_outer_width_x"],
        d["gasket_outer_height_z"],
        inner_width,
        inner_height,
        d["gasket_y"][0],
        d["gasket_y"][1],
        (e["z_min"] + e["z_max"]) / 2,
    )


def create_amplifier_reference(params: dict | None = None) -> cq.Workplane:
    """Import and place the exact user-supplied AM59 STEP."""
    if params is None:
        params = load_params()
    if not AMPLIFIER_STEP.is_file():
        raise FileNotFoundError(f"Missing amplifier STEP: {AMPLIFIER_STEP}")
    transform = params["amplifier"]["pose_transform"]
    return (
        cq.Workplane(obj=_import_step_shape(str(AMPLIFIER_STEP)))
        .rotate(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            transform["first_rotate_x_deg"],
        )
        .translate(tuple(transform["first_translate"]))
        .rotate(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            transform["second_rotate_x_deg"],
        )
        .translate(tuple(transform["second_translate"]))
    )


def create_amplifier_boundary_gasket(
    params: dict | None = None,
) -> cq.Workplane:
    """Create the conceptual one-piece L-section transition boot."""
    if params is None:
        params = load_params()
    b = params["amplifier_boundary"]
    e = params["dry_enclosure"]
    center_z = e["amplifier_opening_center_z"]

    flange = _rect_ring_xz(
        b["gasket_outer_flange_width_x"],
        b["gasket_outer_flange_height_z"],
        b["gasket_lip_outer_width_x"],
        b["gasket_lip_outer_height_z"],
        b["gasket_flange_y"][0],
        b["gasket_flange_y"][1],
        center_z,
    )
    lip = _rect_ring_xz(
        b["gasket_lip_outer_width_x"],
        b["gasket_lip_outer_height_z"],
        b["gasket_lip_inner_width_x"],
        b["gasket_lip_inner_height_z"],
        b["gasket_lip_y"][0],
        b["gasket_lip_y"][1],
        center_z,
    )
    return flange.union(lip)


def amplifier_clamp_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    if params is None:
        params = load_params()
    b = params["amplifier_boundary"]
    e = params["dry_enclosure"]
    center_z = e["amplifier_opening_center_z"]
    return {
        "dry_compression_frame": _rect_ring_xz(
            b["dry_clamp_outer_width_x"],
            b["dry_clamp_outer_height_z"],
            b["dry_clamp_inner_width_x"],
            b["dry_clamp_inner_height_z"],
            b["dry_clamp_y"][0],
            b["dry_clamp_y"][1],
            center_z,
        )
    }


def create_amplifier_clamp_frames(
    params: dict | None = None,
) -> cq.Workplane:
    return _compound(list(amplifier_clamp_components(params).values()))


def _din_rail(
    length_x: float,
    center_y: float,
    center_z: float,
    profile_height_z: float,
    profile_depth_y: float,
) -> cq.Workplane:
    """Lightweight geometric proxy for a 35 mm steel top-hat rail."""
    sheet = 1.0
    web = _box(
        length_x,
        sheet,
        profile_height_z,
        (0.0, center_y, center_z),
    )
    lip_offset_z = (profile_height_z - 1.2) / 2
    for z_sign in (-1, 1):
        lip = _box(
            length_x,
            profile_depth_y,
            1.2,
            (
                0.0,
                center_y + (profile_depth_y - sheet) / 2,
                center_z + z_sign * lip_offset_z,
            ),
        )
        web = web.union(lip)
    return web


def din_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    if params is None:
        params = load_params()
    d = params["din_service_space"]
    e = params["dry_enclosure"]
    center_z = (e["z_min"] + e["z_max"]) / 2
    carrier = _box(
        d["carrier_width_x"],
        d["carrier_thickness_y"],
        d["carrier_height_z"],
        (
            0.0,
            sum(d["carrier_y"]) / 2,
            center_z,
        ),
    )
    # Four large openings retain a stiff perimeter/crossbar proxy while
    # avoiding a needlessly heavy solid back panel.
    opening_width = (d["carrier_width_x"] - 45.0) / 2
    opening_height = (d["carrier_height_z"] - 55.0) / 2
    for x_sign in (-1, 1):
        for z_sign in (-1, 1):
            opening = _box(
                opening_width,
                d["carrier_thickness_y"] + 2.0,
                opening_height,
                (
                    x_sign * (opening_width / 2 + 7.5),
                    sum(d["carrier_y"]) / 2,
                    center_z + z_sign * (opening_height / 2 + 7.5),
                ),
            )
            carrier = carrier.cut(opening)

    parts = {"removable_din_carrier": carrier}
    rail_center_y = d["carrier_y"][1] + 0.5
    for index, z in enumerate(d["rail_center_z"], start=1):
        parts[f"din_rail_{index}"] = _din_rail(
            d["rail_length_x"],
            rail_center_y,
            z,
            d["rail_profile_height_z"],
            d["rail_depth_y"],
        )
    return parts


def create_din_carrier_and_rails(
    params: dict | None = None,
) -> cq.Workplane:
    return _compound(list(din_components(params).values()))


def create_din_reserve_envelopes(
    params: dict | None = None,
) -> cq.Workplane:
    if params is None:
        params = load_params()
    d = params["din_service_space"]
    depth = d["component_reserve_y"][1] - d["component_reserve_y"][0]
    center_y = sum(d["component_reserve_y"]) / 2
    reserve_parts = []
    for z in d["rail_center_z"]:
        reserve_parts.append(
            _box(
                d["component_reserve_width_x"],
                depth,
                d["component_reserve_height_z_each"],
                (0.0, center_y, z),
            )
        )
    return _compound(reserve_parts)


def rain_hood_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    if params is None:
        params = load_params()
    h = params["wet_weather_shroud"]
    t = h["sheet_thickness"]
    x_center = (h["x_min"] + h["x_max"]) / 2
    y_center = (h["y_min"] + h["y_max"]) / 2
    wet_depth = h["y_max"] - h["y_min"]
    height = h["z_roof"] - h["z_bottom"]
    z_center = (h["z_roof"] + h["z_bottom"]) / 2

    wet_wall = _box(
        h["outer_length_x"],
        t,
        height,
        (
            x_center,
            h["y_min"] + t / 2,
            z_center,
        ),
    )
    roof = _box(
        h["outer_length_x"],
        wet_depth,
        t,
        (
            x_center,
            y_center,
            h["z_roof"] - t / 2,
        ),
    )

    end_height = h["z_roof"] - h["end_wall_bottom_z"]
    end_center_z = (h["z_roof"] + h["end_wall_bottom_z"]) / 2
    inlet_end = _box(
        t,
        wet_depth,
        end_height,
        (
            h["x_min"] + t / 2,
            y_center,
            end_center_z,
        ),
    )
    exhaust_end = _box(
        t,
        wet_depth,
        end_height,
        (
            h["x_max"] - t / 2,
            y_center,
            end_center_z,
        ),
    )

    floor_length = h["central_floor_x"][1] - h["central_floor_x"][0]
    central_splash_floor = _box(
        floor_length,
        wet_depth,
        t,
        (
            sum(h["central_floor_x"]) / 2,
            y_center,
            h["z_bottom"] + t / 2,
        ),
    )

    return {
        "wet_back_wall": wet_wall,
        "wet_roof": roof,
        "inlet_turning_wall": inlet_end,
        "exhaust_turning_wall": exhaust_end,
        "central_splash_floor": central_splash_floor,
    }


def create_rain_hood(params: dict | None = None) -> cq.Workplane:
    return _compound(list(rain_hood_components(params).values()))


def create_sun_shield(params: dict | None = None) -> cq.Workplane:
    if params is None:
        params = load_params()
    s = params["sun_shield"]
    shield = _box(
        s["length_x"],
        s["depth_y"],
        s["thickness"],
        (
            0.0,
            s["center_y"],
            s["center_z"],
        ),
    )
    return shield.rotate(
        (0.0, s["center_y"], s["center_z"]),
        (1.0, s["center_y"], s["center_z"]),
        s["slope_deg_about_x"],
    )


def airflow_reference_components(
    params: dict | None = None,
) -> dict[str, cq.Workplane]:
    """Return non-physical keep-out volumes for the two large drain openings."""
    if params is None:
        params = load_params()
    h = params["wet_weather_shroud"]
    opening_height = h["end_wall_bottom_z"] - h["z_bottom"]
    center_z = h["z_bottom"] + opening_height / 2
    y_center = (h["y_min"] + h["y_max"]) / 2
    length = h["downward_opening_length_x_each"]
    inlet_center_x = h["x_min"] + length / 2
    exhaust_center_x = h["x_max"] - length / 2
    return {
        "ambient_inlet_keepout": _box(
            length,
            h["downward_opening_width_y_each"],
            opening_height,
            (inlet_center_x, y_center, center_z),
        ),
        "ambient_exhaust_keepout": _box(
            length,
            h["downward_opening_width_y_each"],
            opening_height,
            (exhaust_center_x, y_center, center_z),
        ),
    }


def create_airflow_references(
    params: dict | None = None,
) -> cq.Workplane:
    return _compound(list(airflow_reference_components(params).values()))


def vendor_cooling_reference_components() -> dict[str, cq.Workplane]:
    """Import every exact cooling STEP supplied in the two vendor folders."""
    paths = {
        "Seifert_3050303_REFERENCE": SEIFERT_STEP,
        "Hoffman_TE121024010_REFERENCE": HOFFMAN_TE12_STEP,
        "Hoffman_TE162024020_REFERENCE": HOFFMAN_TE16_STEP,
    }
    result = {}
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing vendor cooling STEP: {path}")
        result[name] = cq.Workplane(obj=_import_step_shape(str(path)))
    return result


def thermal_assessment(params: dict | None = None) -> dict:
    if params is None:
        params = load_params()
    thermal = params["thermal_budget"]
    heat_sum = sum(thermal["heat_sources_w"].values())
    ua = thermal["total_effective_area_m2"] * thermal["conservative_overall_u_w_m2_k"]
    design_rise = heat_sum / ua
    margin_heat = heat_sum * (1.0 + thermal["selection_margin_percent"] / 100.0)
    margin_rise = margin_heat / ua
    required_ua = margin_heat / (thermal["dry_air_design_target_c"] - thermal["maximum_ambient_c"])
    return {
        "dry_design_heat_w": heat_sum,
        "margin_adjusted_heat_w": margin_heat,
        "passive_ua_w_k": ua,
        "required_ua_w_k": required_ua,
        "ua_margin_percent": 100.0 * (ua / required_ua - 1.0),
        "design_dry_air_c": thermal["maximum_ambient_c"] + design_rise,
        "margin_dry_air_c": thermal["maximum_ambient_c"] + margin_rise,
        "passes_preliminary_passive_target": ua >= required_ua,
        "wet_side_rejection_w": thermal["wet_side_rejection_w_at_severe_basis"],
        "basis": "lumped steady-state zero-wind concept model; test controls",
    }


def _mass_item(
    name: str,
    geometry: cq.Workplane,
    density_kg_m3: float,
) -> dict:
    volume = _volume_mm3(geometry)
    return {
        "name": name,
        "mass_kg": volume * 1.0e-9 * density_kg_m3,
        "cg_mm": _volume_centroid(geometry),
        "volume_mm3": volume,
    }


def mass_assessment(
    params: dict | None = None,
    include_future_payload: bool = False,
) -> dict:
    if params is None:
        params = load_params()
    density = params["mass_model"]["density_kg_m3"]
    items = [
        _mass_item(
            "pressure_body",
            create_pressure_body(params),
            density["aluminum_5052"],
        ),
        _mass_item(
            "finned_service_door",
            create_service_door(params),
            density["aluminum_5052"],
        ),
        _mass_item(
            "rain_hood",
            create_rain_hood(params),
            density["aluminum_5052"],
        ),
        _mass_item(
            "sun_shield",
            create_sun_shield(params),
            density["aluminum_5052"],
        ),
        _mass_item(
            "amplifier_clamp_frames",
            create_amplifier_clamp_frames(params),
            density["aluminum_6061"],
        ),
        _mass_item(
            "amplifier_transition_boot",
            create_amplifier_boundary_gasket(params),
            density["epdm"],
        ),
        _mass_item(
            "service_door_gasket",
            create_service_gasket(params),
            density["epdm"],
        ),
    ]

    din = din_components(params)
    items.append(
        _mass_item(
            "din_carrier",
            din["removable_din_carrier"],
            density["aluminum_5052"],
        )
    )
    rails = _compound([part for name, part in din.items() if name.startswith("din_rail_")])
    items.append(_mass_item("din_rails", rails, density["steel_din"]))

    amp_cg = tuple(params["amplifier"]["planned_volume_centroid_mm_reference_only"])
    items.append(
        {
            "name": "AM59",
            "mass_kg": params["amplifier"]["nominal_mass_kg"],
            "cg_mm": amp_cg,
            "volume_mm3": None,
        }
    )

    allowance_locations = {
        "door_and_boundary_fasteners": (0.0, 60.0, 145.0),
        "bonding_isolation_and_labels": (0.0, 20.0, 130.0),
        "coating": (0.0, 20.0, 150.0),
        "wiring_and_sensors": (0.0, 75.0, 120.0),
    }
    for name, mass in params["mass_model"]["allowances_kg"].items():
        items.append(
            {
                "name": name,
                "mass_kg": mass,
                "cg_mm": allowance_locations[name],
                "volume_mm3": None,
            }
        )

    if include_future_payload:
        items.append(
            {
                "name": "future_din_payload_allowance",
                "mass_kg": params["mass_model"]["future_din_payload_allowance_kg"],
                "cg_mm": (0.0, 85.0, 80.0),
                "volume_mm3": None,
            }
        )

    total_mass = sum(item["mass_kg"] for item in items)
    cg = tuple(
        sum(item["mass_kg"] * item["cg_mm"][axis] for item in items) / total_mass
        for axis in range(3)
    )
    axis_reference = tuple(params["coordinate_system"]["rotator_axis_reference"])
    cg_from_axis = tuple(cg[index] - axis_reference[index] for index in range(3))
    hood = params["wet_weather_shroud"]
    shield = params["sun_shield"]
    shield_projected_height = shield["depth_y"] * math.sin(
        math.radians(shield["slope_deg_about_x"])
    ) + shield["thickness"] * math.cos(math.radians(shield["slope_deg_about_x"]))
    frontal_wind_area = (
        hood["outer_length_x"] * (hood["z_roof"] - hood["z_bottom"])
        + shield["length_x"] * shield_projected_height
    ) * 1.0e-6
    total_depth = max(
        params["service_door"]["fin_y"][1],
        shield["center_y"] + shield["depth_y"] / 2,
    ) - min(
        hood["y_min"],
        shield["center_y"] - shield["depth_y"] / 2,
    )
    side_wind_area = (
        total_depth
        * (create_sun_shield(params).val().BoundingBox().zmax - hood["z_bottom"])
        * 1.0e-6
    )
    return {
        "total_mass_kg": total_mass,
        "cg_mm": cg,
        "rotator_axis_reference_mm": axis_reference,
        "cg_from_rotator_axis_mm": cg_from_axis,
        "radial_cg_mm": math.hypot(cg_from_axis[0], cg_from_axis[1]),
        "vertical_cg_mm": cg_from_axis[2],
        "frontal_wind_area_m2": frontal_wind_area,
        "side_wind_area_m2": side_wind_area,
        "plan_wind_area_m2": (shield["length_x"] * shield["depth_y"] * 1.0e-6),
        "includes_future_payload": include_future_payload,
        "items": items,
        "status": "preliminary; vendor AM59 mass centroid and mounting hardware are not known",
    }


def architecture_trade_study(params: dict | None = None) -> list[dict]:
    if params is None:
        params = load_params()
    rows = []
    for architecture in params["architecture_trade"]:
        row = dict(architecture)
        # Lower is better. Weather/vendor-interface risk and mass are dominant;
        # thermal risk remains explicit because every option must first be viable.
        row["weighted_penalty"] = round(
            4.0 * architecture["weather_risk_1_low_5_high"]
            + 4.0 * architecture["vendor_interface_risk_1_low_5_high"]
            + 2.0 * architecture["thermal_risk_1_low_5_high"]
            + 1.5 * architecture["estimated_mass_kg"]
            + 0.025 * architecture["estimated_vertical_cg_mm"]
            + 12.0 * architecture["frontal_wind_area_m2"]
            + 0.0005 * architecture["prototype_cost_usd_mid"]
            - 1.0 * architecture["serviceability_1_poor_5_good"],
            2,
        )
        rows.append(row)
    return sorted(rows, key=lambda row: row["weighted_penalty"])


def create_assembly(
    service_open: bool = False,
    show_airflow: bool = False,
    show_din_reserves: bool = True,
    weather_exploded: bool = False,
) -> cq.Assembly:
    params = load_params()
    assembly = cq.Assembly(name="AM59_IP66_LOW_CG_PASSIVE_ENCLOSURE")

    assembly.add(
        create_pressure_body(params),
        name="WELDED_IP66_DRY_BODY",
        color=cq.Color(0.76, 0.79, 0.82),
    )
    assembly.add(
        create_amplifier_reference(params),
        name="AM59_3S_64_64_EXACT_REFERENCE",
        color=cq.Color(0.20, 0.22, 0.24),
    )
    assembly.add(
        create_amplifier_boundary_gasket(params),
        name="ONE_PIECE_AM59_TRANSITION_BOOT",
        color=cq.Color(0.05, 0.32, 0.26),
    )
    for name, frame in amplifier_clamp_components(params).items():
        assembly.add(
            frame,
            name=name.upper(),
            color=cq.Color(0.46, 0.50, 0.54),
        )

    door_shift = (0.0, 260.0, 0.0) if service_open else (0.0, 0.0, 0.0)
    assembly.add(
        create_service_gasket(params).translate(door_shift),
        name="SERVICE_DOOR_GASKET",
        color=cq.Color(0.10, 0.15, 0.12),
    )
    assembly.add(
        create_service_door(params).translate(door_shift),
        name="FINNED_SERVICE_DOOR",
        color=cq.Color(0.88, 0.89, 0.90),
    )

    din_shift = (0.0, 145.0, 0.0) if service_open else (0.0, 0.0, 0.0)
    for name, part in din_components(params).items():
        assembly.add(
            part.translate(din_shift),
            name=name.upper(),
            color=(
                cq.Color(0.25, 0.30, 0.34)
                if name.startswith("din_rail")
                else cq.Color(0.62, 0.66, 0.70)
            ),
        )
    if show_din_reserves:
        assembly.add(
            create_din_reserve_envelopes(params).translate(din_shift),
            name="FUTURE_DIN_COMPONENT_RESERVES",
            color=cq.Color(0.20, 0.55, 0.90, 0.28),
        )

    hood_explode = {
        "wet_back_wall": (0.0, -110.0, 0.0),
        "wet_roof": (0.0, 0.0, 90.0),
        "inlet_turning_wall": (-90.0, 0.0, 0.0),
        "exhaust_turning_wall": (90.0, 0.0, 0.0),
        "central_splash_floor": (0.0, 0.0, -70.0),
    }
    for name, part in rain_hood_components(params).items():
        if weather_exploded:
            part = part.translate(hood_explode[name])
        assembly.add(
            part,
            name=name.upper(),
            color=cq.Color(0.92, 0.92, 0.90),
        )
    shield = create_sun_shield(params)
    if weather_exploded:
        shield = shield.translate((0.0, 0.0, 140.0))
    assembly.add(
        shield,
        name="VENTILATED_SOLAR_SHIELD",
        color=cq.Color(0.98, 0.98, 0.96),
    )

    if show_airflow:
        colors = {
            "ambient_inlet_keepout": cq.Color(0.15, 0.55, 0.95, 0.35),
            "ambient_exhaust_keepout": cq.Color(0.95, 0.35, 0.12, 0.35),
        }
        for name, part in airflow_reference_components(params).items():
            assembly.add(
                part,
                name=name.upper(),
                color=colors[name],
            )
    return assembly


def _export_context(args: list[str]) -> Path:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    service_open = "--open" in args
    show_airflow = "--airflow" in args
    weather_exploded = "--exploded" in args
    suffix = ""
    if service_open:
        suffix += "_service_open"
    if show_airflow:
        suffix += "_airflow"
    if weather_exploded:
        suffix += "_exploded"
    output = EXPORTS_DIR / f"am59_ip66_passive_enclosure_v4_context{suffix}.step"
    create_assembly(
        service_open=service_open,
        show_airflow=show_airflow,
        weather_exploded=weather_exploded,
    ).save(str(output))
    return output


if __name__ == "__main__":
    output_path = _export_context(sys.argv[1:])
    print(output_path)
