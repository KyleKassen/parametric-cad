"""Tests for the AM59 IP66 low-CG passive enclosure concept."""

import importlib.util
from pathlib import Path

import cadquery as cq
import pytest

from lib.housing import clearance, interference

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "parts" / "custom" / "am59_ip66_passive_enclosure" / "model.py"

REQUIRED_BUILDERS = (
    "create_pressure_body",
    "create_part",
    "create_service_door",
    "create_service_gasket",
    "create_amplifier_reference",
    "create_amplifier_boundary_gasket",
    "create_amplifier_clamp_frames",
    "create_din_carrier_and_rails",
    "create_din_reserve_envelopes",
    "create_rain_hood",
    "create_sun_shield",
    "create_airflow_references",
    "thermal_assessment",
    "mass_assessment",
    "architecture_trade_study",
    "create_assembly",
)


def _load_model():
    spec = importlib.util.spec_from_file_location(
        "am59_ip66_passive_enclosure_model_test",
        MODEL_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assert_valid_nonempty(workplane):
    assert isinstance(workplane, cq.Workplane)
    assert workplane.val().isValid()
    assert len(workplane.solids().vals()) >= 1
    assert sum(abs(s.Volume()) for s in workplane.solids().vals()) > 1.0


@pytest.fixture(scope="module")
def model():
    return _load_model()


@pytest.fixture(scope="module")
def geometry(model):
    return {
        "body": model.create_pressure_body(),
        "door": model.create_service_door(),
        "service_gasket": model.create_service_gasket(),
        "amplifier": model.create_amplifier_reference(),
        "boot": model.create_amplifier_boundary_gasket(),
        "frames": model.create_amplifier_clamp_frames(),
        "din": model.create_din_carrier_and_rails(),
        "din_reserves": model.create_din_reserve_envelopes(),
        "hood": model.create_rain_hood(),
        "shield": model.create_sun_shield(),
        "airflow": model.create_airflow_references(),
    }


def test_public_builder_contract_is_complete(model):
    for builder_name in REQUIRED_BUILDERS:
        assert callable(getattr(model, builder_name, None)), builder_name


def test_exact_vendor_sources_are_present(model):
    assert model.AMPLIFIER_STEP.is_file()
    assert model.SEIFERT_STEP.is_file()
    assert model.HOFFMAN_TE12_STEP.is_file()
    assert model.HOFFMAN_TE16_STEP.is_file()
    params = model.load_params()
    assert params["amplifier"]["vendor_part"] == "AM59-3S-64-64"


def test_all_selected_geometry_is_valid(geometry):
    for workplane in geometry.values():
        _assert_valid_nonempty(workplane)


def test_pressure_body_is_compact_single_solid(geometry):
    body = geometry["body"]
    bb = body.val().BoundingBox()
    assert len(body.solids().vals()) == 1
    assert bb.xlen == pytest.approx(416.0, abs=0.1)
    assert bb.ylen == pytest.approx(128.0, abs=0.1)
    assert bb.zlen == pytest.approx(286.0, abs=0.1)
    assert bb.ymin == pytest.approx(8.0, abs=0.1)


def test_exact_am59_straddles_boundary_with_heatsink_wet(model, geometry):
    amplifier = geometry["amplifier"]
    bb = amplifier.val().BoundingBox()
    assert bb.xmin == pytest.approx(-182.06, abs=0.06)
    assert bb.xmax == pytest.approx(182.06, abs=0.06)
    assert bb.ymin == pytest.approx(-53.0, abs=0.06)
    assert bb.ymax == pytest.approx(49.0, abs=0.06)
    assert bb.zmin == pytest.approx(30.0, abs=0.06)
    assert bb.zmax == pytest.approx(230.0, abs=0.06)
    assert bb.ymin < 0 < bb.ymax
    assert model.load_params()["amplifier"]["heatsink_transition_plane_y"] == 0


def test_exact_am59_passes_bulkhead_and_rigid_clamp(model, geometry):
    amplifier = geometry["amplifier"]
    body = geometry["body"]
    frames = geometry["frames"]
    assert interference(amplifier, body) <= 0.5
    assert clearance(amplifier, body) == pytest.approx(0.5, abs=0.02)
    assert interference(amplifier, frames) <= 0.5

    boot_interference = interference(geometry["boot"], amplifier)
    assert 7000.0 <= boot_interference <= 14000.0
    assert model.load_params()["amplifier_boundary"]["nominal_radial_interference_per_side"] == 1.0


def test_future_din_space_is_accessible_and_clear(geometry):
    amplifier = geometry["amplifier"]
    assert interference(amplifier, geometry["din"]) <= 0.5
    assert clearance(amplifier, geometry["din"]) >= 4.99
    assert interference(amplifier, geometry["din_reserves"]) <= 0.5
    assert clearance(amplifier, geometry["din_reserves"]) >= 10.0
    assert clearance(geometry["door"], geometry["din_reserves"]) >= 15.0


def test_service_door_and_gasket_seat_on_blind_collar(geometry):
    assert interference(geometry["body"], geometry["door"]) <= 0.5
    assert clearance(geometry["body"], geometry["door"]) <= 0.05
    assert clearance(geometry["service_gasket"], geometry["body"]) <= 0.05
    assert clearance(geometry["service_gasket"], geometry["door"]) <= 0.05


def test_wet_hood_is_large_low_restriction_and_drained(model, geometry):
    params = model.load_params()
    wet = params["wet_weather_shroud"]
    amp_air = params["amplifier"]["airflow"]
    assert interference(geometry["amplifier"], geometry["hood"]) <= 0.5
    assert clearance(geometry["amplifier"], geometry["hood"]) >= 20.0
    assert wet["net_open_area_each_end_mm2"] >= (amp_air["minimum_net_open_area_each_end_mm2"])
    assert (
        wet["estimated_labyrinth_pressure_drop_pa"] <= (amp_air["hood_pressure_drop_target_pa_max"])
    )
    assert len(model.airflow_reference_components()) == 2


def test_sun_shield_preserves_passive_convection_gap(geometry):
    assert clearance(geometry["shield"], geometry["door"]) >= 12.0
    assert clearance(geometry["shield"], geometry["hood"]) >= 12.0


def test_passive_thermal_budget_uses_only_dry_heat(model):
    params = model.load_params()
    assessment = model.thermal_assessment()
    assert sum(params["thermal_budget"]["heat_sources_w"].values()) == 45.0
    assert assessment["margin_adjusted_heat_w"] == pytest.approx(51.75)
    assert assessment["passive_ua_w_k"] == pytest.approx(2.75)
    assert assessment["required_ua_w_k"] == pytest.approx(2.5875)
    assert assessment["passes_preliminary_passive_target"]
    assert assessment["margin_dry_air_c"] < 65.0
    assert assessment["wet_side_rejection_w"] == pytest.approx(181.8)


def test_mass_cg_and_wind_area_prioritize_rotator_load(model):
    empty = model.mass_assessment()
    future = model.mass_assessment(include_future_payload=True)
    assert empty["total_mass_kg"] < 8.0
    assert empty["radial_cg_mm"] < 2.0
    assert empty["vertical_cg_mm"] < 160.0
    assert empty["frontal_wind_area_m2"] < 0.15
    assert future["total_mass_kg"] < 9.5
    assert future["radial_cg_mm"] < 12.0
    assert future["vertical_cg_mm"] < empty["vertical_cg_mm"]


def test_architecture_a_is_selected_by_quantified_trade(model):
    trade = model.architecture_trade_study()
    assert len(trade) >= 3
    assert trade[0]["id"] == "A"
    assert trade[0]["selected"]
    assert {row["id"] for row in trade} >= {"A", "B", "C", "D"}


def test_active_cooling_options_are_rejected_for_specific_reasons(model):
    options = model.load_params()["cooling_options"]
    assert options["selected_passive"]["added_input_power_w"] == 0.0
    assert options["seifert_3050303"]["mass_kg"] > 3.0
    assert "IP65" in options["hoffman_te121024010"]["rating"]
    assert options["hoffman_te162024020"]["mass_kg"] > 6.0
    assert options["hoffman_tx23_air_to_air"]["mass_kg"] > 13.0
    assert options["internal_or_external_fans_only"]["dry_heat_removed_w"] == 0.0


def test_am59_boundary_has_annular_and_internal_bypass_gates(model):
    params = model.load_params()
    boundary = params["amplifier_boundary"]
    release_text = " ".join(params["release_gates"])
    assert "narrow OEM mounting flange" in boundary["seal_strategy"]
    assert "internal bypass" in boundary["seal_strategy"]
    assert "thermal wall" in release_text
    assert "fan-lead route" in release_text
    assert "vendor-sealed modular/cold-wall variant" in release_text


def test_no_deferred_interfaces_are_designed(model):
    params = model.load_params()
    text = json_text = str(params)
    assert "No pressure vent is designed" in text
    assert "intentionally absent" in text
    assert "connector/feedthrough hardware" in json_text


def test_operating_and_service_assemblies_build(model):
    closed = model.create_assembly()
    open_assembly = model.create_assembly(
        service_open=True,
        show_airflow=True,
    )
    assert isinstance(closed, cq.Assembly)
    assert isinstance(open_assembly, cq.Assembly)
    assert len(closed.objects) >= 15
    assert len(open_assembly.objects) >= len(closed.objects) + 2
