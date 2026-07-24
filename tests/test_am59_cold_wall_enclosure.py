"""Geometry, thermal, and boundary checks for the AM59 cold-wall enclosure."""

import importlib.util
import sys
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.housing import clearance, interference  # noqa: E402

MODEL_PATH = PROJECT_ROOT / "parts" / "custom" / "am59_cold_wall_enclosure" / "model.py"

REQUIRED_BUILDERS = (
    "create_enclosure_tub",
    "create_lid",
    "create_lid_gasket_reference",
    "create_amplifier_chassis_reference",
    "create_relocated_heatsink_reference",
    "create_flange_clamp_bars",
    "create_heatsink_cradle",
    "create_heatsink_duct_sheet",
    "create_air_tunnel_hood",
    "create_mesh_screens_reference",
    "create_din_provision",
    "create_din_keepout_reference",
    "create_tim_references",
    "create_solar_shield",
    "thermal_assessment",
    "mass_cg_assessment",
    "create_assembly",
)


def _load_model():
    spec = importlib.util.spec_from_file_location(
        "am59_cold_wall_enclosure_model_test",
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
        "tub": model.create_enclosure_tub(),
        "lid": model.create_lid(),
        "gasket": model.create_lid_gasket_reference(),
        "chassis": model.create_amplifier_chassis_reference(),
        "heatsink": model.create_relocated_heatsink_reference(),
        "clamps": model.create_flange_clamp_bars(),
        "cradle": model.create_heatsink_cradle(),
        "duct": model.create_heatsink_duct_sheet(),
        "hood": model.create_air_tunnel_hood(),
        "mesh": model.create_mesh_screens_reference(),
        "din": model.create_din_provision(),
        "keepout": model.create_din_keepout_reference(),
        "tim": model.create_tim_references(),
        "shield": model.create_solar_shield(),
    }


def test_public_builder_contract_is_complete(model):
    for builder_name in REQUIRED_BUILDERS:
        assert callable(getattr(model, builder_name, None)), builder_name


def test_vendor_step_is_exact_supplied_file_and_split_is_lossless(model):
    assert model.AMPLIFIER_STEP.is_file()
    counts = model.amp_solid_counts()
    assert counts["total"] == 80
    assert counts["chassis"] == 29
    assert counts["heatsink"] == 51


def test_all_builders_produce_valid_geometry(geometry):
    for workplane in geometry.values():
        _assert_valid_nonempty(workplane)


def test_tub_envelope(geometry):
    bb = geometry["tub"].val().BoundingBox()
    assert bb.xmin == pytest.approx(-214.5, abs=0.1)
    assert bb.xmax == pytest.approx(234.5, abs=0.1)
    assert bb.ymin == pytest.approx(-124.5, abs=0.1)
    assert bb.ymax == pytest.approx(234.5, abs=0.1)
    assert bb.zmin == pytest.approx(73.0, abs=0.1)
    assert bb.zmax == pytest.approx(205.0, abs=0.1)
    assert len(geometry["tub"].solids().vals()) == 1


def test_chassis_is_inside_the_dry_volume(model, geometry):
    params = model.load_params()
    inner_x = params["enclosure"]["inner_x"]
    inner_y = params["enclosure"]["inner_y"]
    bb = geometry["chassis"].val().BoundingBox()
    assert bb.xmin > inner_x[0] and bb.xmax < inner_x[1]
    assert bb.ymin > inner_y[0] and bb.ymax < inner_y[1]
    assert bb.zmin >= params["cold_floor"]["floor_top_z"] + 0.9
    assert bb.zmax < params["enclosure"]["rim_top_z"]


def test_heatsink_is_entirely_outside_the_dry_volume(model, geometry):
    params = model.load_params()
    bb = geometry["heatsink"].val().BoundingBox()
    # Everything below the floor bottom is outside the sealed boundary.
    assert bb.zmax <= params["cold_floor"]["floor_bottom_z"]
    # And the conduction face registers on the pad TIM plane.
    assert bb.zmax == pytest.approx(params["amplifier"]["placed_heatsink_contact_z"], abs=0.05)


def test_dry_boundary_pairs_do_not_interfere(geometry):
    for name_a, name_b in (
        ("chassis", "tub"),
        ("heatsink", "tub"),
        ("chassis", "clamps"),
        ("heatsink", "cradle"),
        ("heatsink", "hood"),
        ("hood", "tub"),
        ("lid", "tub"),
        ("gasket", "tub"),
        ("din", "chassis"),
        ("shield", "lid"),
    ):
        overlap = interference(geometry[name_a], geometry[name_b])
        assert overlap <= 0.5, f"{name_a} vs {name_b}: {overlap:.2f} mm3"


def test_load_path_contacts(geometry):
    for name_a, name_b, limit in (
        ("chassis", "tim", 0.05),
        ("heatsink", "tim", 0.05),
        ("tim", "tub", 0.05),
        ("lid", "tub", 0.05),
        ("clamps", "chassis", 0.1),
        ("cradle", "heatsink", 0.1),
        ("cradle", "tub", 0.05),
    ):
        gap = clearance(geometry[name_a], geometry[name_b])
        assert gap <= limit, f"{name_a} vs {name_b}: gap {gap:.3f} mm"


def test_din_keepout_is_reserved_and_clear(model, geometry):
    params = model.load_params()
    d = params["din_provision"]
    assert d["rail_x"][1] - d["rail_x"][0] >= 300.0
    assert clearance(geometry["chassis"], geometry["keepout"]) >= 15.0
    assert interference(geometry["chassis"], geometry["keepout"]) <= 0.5
    keepout_volume_l = (
        (d["keepout_x"][1] - d["keepout_x"][0])
        * (d["keepout_y"][1] - d["keepout_y"][0])
        * (d["keepout_z"][1] - d["keepout_z"][0])
        / 1e6
    )
    assert keepout_volume_l >= 2.4


def test_thermal_assessment_passes_all_modes(model):
    thermal = model.thermal_assessment()
    for mode, result in thermal["modes"].items():
        assert result["passes"], mode
    assert thermal["case_temperatures_c"]["matched_45c"] <= 64.0
    assert thermal["cabin_air_max_gate_45c"] <= 65.0
    # The amplifier heat never loads the cabin budget.
    params = model.load_params()
    budget = params["internal_heat_budget_w"]
    assert budget["max_gate_total"] < 100.0


def test_mass_and_cg_meet_rotator_targets(model):
    mass = model.mass_cg_assessment()
    assert mass["total_mass_kg"] <= 18.0
    assert mass["cg_height_above_skirt_base_mm"] <= 135.0
    assert mass["cg_moment_about_base_kg_m"] <= 2.5


def test_assembly_builds(model):
    assembly = model.create_assembly()
    assert len(assembly.children) >= 12
