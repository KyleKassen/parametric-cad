"""Part-local acceptance checks for the AM59 IP66 passive enclosure."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
MODEL_PATH = PART_DIR / "model.py"
PARAMS_PATH = PART_DIR / "params.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.housing import clearance, interference  # noqa: E402


def _load_model():
    spec = importlib.util.spec_from_file_location(
        "am59_ip66_passive_enclosure_fit_model",
        MODEL_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _valid_nonempty(workplane: cq.Workplane, name: str) -> None:
    _assert(isinstance(workplane, cq.Workplane), f"{name} is not a Workplane")
    _assert(workplane.val().isValid(), f"{name} is not a valid BREP")
    _assert(len(workplane.solids().vals()) >= 1, f"{name} has no solids")
    _assert(
        sum(abs(s.Volume()) for s in workplane.solids().vals()) > 1.0,
        f"{name} is empty",
    )


def run_checks() -> dict:
    model = _load_model()
    params = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))

    body = model.create_pressure_body()
    door = model.create_service_door()
    service_gasket = model.create_service_gasket()
    amplifier = model.create_amplifier_reference()
    boot = model.create_amplifier_boundary_gasket()
    frames = model.create_amplifier_clamp_frames()
    din = model.create_din_carrier_and_rails()
    din_reserves = model.create_din_reserve_envelopes()
    hood = model.create_rain_hood()
    shield = model.create_sun_shield()
    airflow = model.create_airflow_references()

    geometry = {
        "pressure body": body,
        "service door": door,
        "service gasket": service_gasket,
        "exact AM59": amplifier,
        "transition boot": boot,
        "clamp frame": frames,
        "DIN carrier": din,
        "DIN reserves": din_reserves,
        "rain hood": hood,
        "sun shield": shield,
        "airflow references": airflow,
    }
    for name, workplane in geometry.items():
        _valid_nonempty(workplane, name)

    body_bb = body.val().BoundingBox()
    _assert(abs(body_bb.xlen - 416.0) <= 0.1, "pressure body X envelope")
    _assert(abs(body_bb.ylen - 128.0) <= 0.1, "pressure body Y envelope")
    _assert(abs(body_bb.zlen - 286.0) <= 0.1, "pressure body Z envelope")
    _assert(len(body.solids().vals()) == 1, "pressure body must be one solid")

    amp_bb = amplifier.val().BoundingBox()
    expected_amp = params["amplifier"]["planned_bbox_mm"]
    for measured, expected, label in (
        (amp_bb.xmin, expected_amp["x"][0], "AM59 xmin"),
        (amp_bb.xmax, expected_amp["x"][1], "AM59 xmax"),
        (amp_bb.ymin, expected_amp["y"][0], "AM59 ymin"),
        (amp_bb.ymax, expected_amp["y"][1], "AM59 ymax"),
        (amp_bb.zmin, expected_amp["z"][0], "AM59 zmin"),
        (amp_bb.zmax, expected_amp["z"][1], "AM59 zmax"),
    ):
        _assert(abs(measured - expected) <= 0.06, label)
    _assert(
        amp_bb.ymin < 0.0 < amp_bb.ymax,
        "AM59 must straddle the wet/dry reference plane",
    )

    _assert(
        interference(body, amplifier) <= 0.5,
        "AM59 interferes with welded pressure body",
    )
    _assert(
        0.4 <= clearance(body, amplifier) <= 0.7,
        "AM59/bulkhead opening clearance is not controlled",
    )
    _assert(
        interference(frames, amplifier) <= 0.5,
        "rigid amplifier frame interferes with exact AM59",
    )

    boot_interference = interference(boot, amplifier)
    _assert(
        7000.0 <= boot_interference <= 14000.0,
        "transition-boot proxy does not represent intended radial squeeze",
    )
    _assert(
        params["amplifier_boundary"]["nominal_radial_interference_per_side"] == 1.0,
        "transition boot radial squeeze changed without review",
    )

    _assert(
        interference(amplifier, din) <= 0.5,
        "AM59 interferes with DIN carrier",
    )
    _assert(
        clearance(amplifier, din) >= 4.99,
        "DIN carrier is too close to AM59",
    )
    _assert(
        interference(amplifier, din_reserves) <= 0.5,
        "future DIN reserve intersects AM59",
    )
    _assert(
        clearance(amplifier, din_reserves) >= 10.0,
        "future DIN reserve lacks service clearance",
    )
    _assert(
        clearance(door, din_reserves) >= 15.0,
        "future DIN reserve is too close to service door",
    )

    _assert(
        interference(body, door) <= 0.5,
        "service door materially overlaps welded collar",
    )
    _assert(
        clearance(body, door) <= 0.05,
        "service door does not seat on welded collar",
    )
    _assert(
        clearance(service_gasket, body) <= 0.05,
        "service gasket does not contact collar",
    )
    _assert(
        clearance(service_gasket, door) <= 0.05,
        "service gasket does not contact door",
    )

    _assert(
        interference(amplifier, hood) <= 0.5,
        "rain hood intersects exact AM59",
    )
    _assert(
        clearance(amplifier, hood) >= 20.0,
        "rain hood lacks amplifier clearance",
    )
    _assert(
        clearance(shield, door) >= 12.0,
        "sun shield lacks door-fin convection gap",
    )
    _assert(
        clearance(shield, hood) >= 12.0,
        "sun shield lacks rain-hood convection gap",
    )

    wet = params["wet_weather_shroud"]
    _assert(
        wet["net_open_area_each_end_mm2"]
        >= params["amplifier"]["airflow"]["minimum_net_open_area_each_end_mm2"],
        "rain-hood free area is below the AM59 minimum",
    )
    _assert(
        wet["estimated_labyrinth_pressure_drop_pa"]
        <= params["amplifier"]["airflow"]["hood_pressure_drop_target_pa_max"],
        "rain-hood estimated pressure drop exceeds target",
    )

    thermal = model.thermal_assessment()
    _assert(
        thermal["dry_design_heat_w"] == 45.0,
        "dry heat sources no longer sum to 45 W",
    )
    _assert(
        thermal["passes_preliminary_passive_target"],
        "passive conductance does not meet margin-adjusted target",
    )
    _assert(
        thermal["margin_dry_air_c"] < 65.0,
        "margin-adjusted predicted dry air exceeds 65 C",
    )

    empty_mass = model.mass_assessment()
    future_mass = model.mass_assessment(include_future_payload=True)
    _assert(empty_mass["total_mass_kg"] < 8.0, "empty concept exceeds 8 kg")
    _assert(
        empty_mass["radial_cg_mm"] < 2.0,
        "empty concept is not balanced about provisional rotator axis",
    )
    _assert(
        empty_mass["vertical_cg_mm"] < 160.0,
        "empty concept vertical CG exceeds 160 mm",
    )
    _assert(
        future_mass["total_mass_kg"] < 9.5,
        "concept plus future payload allowance exceeds 9.5 kg",
    )
    _assert(
        future_mass["radial_cg_mm"] < 12.0,
        "future payload moves CG too far from provisional axis",
    )
    _assert(
        empty_mass["frontal_wind_area_m2"] < 0.15,
        "frontal projected area exceeds 0.15 m2",
    )

    cooling_refs = model.vendor_cooling_reference_components()
    expected_cooling = {
        "Seifert_3050303_REFERENCE": (153.5, 134.93, 206.0),
        "Hoffman_TE121024010_REFERENCE": (159.45, 182.32, 304.68),
        "Hoffman_TE162024020_REFERENCE": (180.01, 177.76, 400.0),
    }
    for name, expected in expected_cooling.items():
        reference = cooling_refs[name]
        _valid_nonempty(reference, name)
        bb = reference.val().BoundingBox()
        for measured, target in zip((bb.xlen, bb.ylen, bb.zlen), expected):
            _assert(
                abs(measured - target) <= 0.08,
                f"{name} exact STEP envelope changed",
            )

    trade = model.architecture_trade_study()
    _assert(trade[0]["id"] == "A", "selected architecture no longer ranks first")
    _assert(trade[0]["selected"], "top-ranked architecture is not selected")

    if step_path := os.environ.get("EVAL_STEP_PATH"):
        exported = cq.importers.importStep(step_path)
        _valid_nonempty(exported, "evaluated exported body")
        exported_bb = exported.val().BoundingBox()
        _assert(
            abs(exported_bb.xlen - body_bb.xlen) <= 0.05
            and abs(exported_bb.ylen - body_bb.ylen) <= 0.05
            and abs(exported_bb.zlen - body_bb.zlen) <= 0.05,
            "evaluated STEP envelope differs from source body",
        )

    return {
        "status": "PASS",
        "thermal": thermal,
        "empty_mass": empty_mass,
        "future_mass": future_mass,
        "boot_interference_mm3": boot_interference,
        "selected_architecture": trade[0],
    }


if __name__ == "__main__":
    try:
        result = run_checks()
    except Exception as exc:
        print(f"FAIL: {exc}")
        raise
    print(json.dumps(result, indent=2, default=list))
