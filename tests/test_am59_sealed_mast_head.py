"""Geometry and environmental-boundary checks for the sealed AM59 mast head."""

import importlib.util
import sys
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.housing import clearance, interference  # noqa: E402

MODEL_PATH = PROJECT_ROOT / "parts" / "custom" / "am59_sealed_mast_head" / "model.py"

REQUIRED_BUILDERS = (
    "create_structural_frame",
    "create_dry_enclosure",
    "create_service_lid",
    "create_environmental_gasket",
    "create_internal_cartridge",
    "create_amplifier_reference",
    "create_internal_thermal_module",
    "create_wet_cooling_module",
    "create_sun_shield",
    "create_mast_reference",
    "create_rotator_reference",
    "create_assembly",
)


def _load_model():
    spec = importlib.util.spec_from_file_location(
        "am59_sealed_mast_head_model_test",
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


def test_public_builder_contract_is_complete(model):
    for builder_name in REQUIRED_BUILDERS:
        assert callable(getattr(model, builder_name, None)), builder_name


def test_structural_frame_has_revised_load_bypass_envelope(model):
    frame = model.create_structural_frame()
    _assert_valid_nonempty(frame)
    assert len(frame.solids().vals()) == 1

    bb = frame.val().BoundingBox()
    # The blank central interface plates are compact, while the welded
    # longitudinal cradle rails reach beneath the external wet bay.
    assert bb.xlen == pytest.approx(605.0, abs=0.1)
    assert bb.ylen == pytest.approx(380.0, abs=0.1)
    assert bb.zlen == pytest.approx(340.0, abs=0.1)
    assert bb.zmin == pytest.approx(0.0, abs=0.1)
    assert bb.zmax == pytest.approx(340.0, abs=0.1)


def test_dry_enclosure_has_revised_asymmetric_envelope(model):
    enclosure = model.create_dry_enclosure()
    _assert_valid_nonempty(enclosure)

    bb = enclosure.val().BoundingBox()
    assert bb.xmin == pytest.approx(-380.0, abs=0.1)
    assert bb.xmax == pytest.approx(220.0, abs=0.1)
    assert bb.ymin == pytest.approx(-135.0, abs=0.1)
    assert bb.ymax == pytest.approx(135.0, abs=0.1)
    assert bb.zmin == pytest.approx(20.0, abs=0.1)
    assert bb.zmax == pytest.approx(280.0, abs=0.1)


def test_amplifier_reference_uses_exact_v2_pose(model):
    amplifier = model.create_amplifier_reference()
    _assert_valid_nonempty(amplifier)

    bb = amplifier.val().BoundingBox()
    assert bb.xmin == pytest.approx(-345.4, abs=0.05)
    assert bb.xmax == pytest.approx(18.72, abs=0.05)
    assert bb.ymin == pytest.approx(-100.0, abs=0.05)
    assert bb.ymax == pytest.approx(100.0, abs=0.05)
    assert bb.zmin == pytest.approx(52.0, abs=0.05)
    assert bb.zmax == pytest.approx(154.0, abs=0.05)


def test_amplifier_is_clear_of_shell_and_structural_load_path(model):
    amplifier = model.create_amplifier_reference()
    enclosure = model.create_dry_enclosure()
    frame = model.create_structural_frame()

    assert interference(enclosure, amplifier) <= 0.5
    assert clearance(enclosure, amplifier) >= 20.0
    assert interference(frame, amplifier) <= 0.5
    assert clearance(frame, amplifier) >= 10.0


def test_internal_cartridge_contacts_without_overlapping_amplifier(model):
    cartridge = model.create_internal_cartridge()
    amplifier = model.create_amplifier_reference()
    _assert_valid_nonempty(cartridge)

    assert interference(cartridge, amplifier) <= 0.5
    assert clearance(cartridge, amplifier) <= 0.05


def test_service_lid_and_gasket_are_on_negative_x_service_end(model):
    enclosure = model.create_dry_enclosure()
    lid = model.create_service_lid()
    gasket = model.create_environmental_gasket()
    _assert_valid_nonempty(lid)
    _assert_valid_nonempty(gasket)

    enclosure_bb = enclosure.val().BoundingBox()
    lid_bb = lid.val().BoundingBox()
    gasket_bb = gasket.val().BoundingBox()

    assert lid_bb.xmax <= enclosure_bb.xmin + 0.1
    assert gasket_bb.xmax <= enclosure_bb.xmin + 1.0
    assert clearance(lid, enclosure) <= 0.05
    assert interference(lid, enclosure) <= 0.5
    assert clearance(gasket, lid) <= 0.5


def test_environmental_gasket_is_one_continuous_end_face_ring(model):
    gasket = model.create_environmental_gasket()
    bb = gasket.val().BoundingBox()

    assert len(gasket.solids().vals()) == 1
    assert bb.xlen <= 10.0
    assert bb.ylen >= 220.0
    assert bb.zlen >= 210.0

    # A solid plate would defeat the service opening; the ring must occupy
    # substantially less than its bounding-prism volume.
    bounding_prism_volume = bb.xlen * bb.ylen * bb.zlen
    gasket_volume = sum(abs(s.Volume()) for s in gasket.solids().vals())
    assert gasket_volume < 0.35 * bounding_prism_volume


def test_service_fasteners_are_outside_seal_and_meet_pitch_limit(model):
    params = model.load_params()
    lid = params["service_lid"]
    locations = model.service_fastener_locations(params)

    assert len(locations) == 24
    assert len(set(locations)) == 24

    seal_y = lid["seal_ring_outer_width_y"] / 2
    seal_z = lid["seal_ring_outer_height_z"] / 2
    seal_center_z = (params["sealed_enclosure"]["z_min"] + params["sealed_enclosure"]["z_max"]) / 2
    for y, z in locations:
        assert abs(y) > seal_y or abs(z - seal_center_z) > seal_z

    max_pitch = lid["maximum_fastener_pitch"]
    top_bottom_y = sorted(lid["fastener_y_top_bottom"])
    side_z = sorted(lid["fastener_z_sides"])
    assert max(b - a for a, b in zip(top_bottom_y, top_bottom_y[1:])) <= max_pitch
    assert max(b - a for a, b in zip(side_z, side_z[1:])) <= max_pitch

    corner_distance = (
        (lid["fastener_edge_y"] - max(top_bottom_y)) ** 2
        + (min(side_z) - lid["fastener_edge_z_bottom"]) ** 2
    ) ** 0.5
    assert corner_distance <= max_pitch


def test_pressure_body_contacts_cradle_without_crossing_load_path(model):
    frame = model.create_structural_frame()
    enclosure = model.create_dry_enclosure()

    assert interference(frame, enclosure) <= 0.5
    assert clearance(frame, enclosure) <= 0.05


def test_dry_and_wet_thermal_modules_stay_clear_of_amplifier(model):
    amplifier = model.create_amplifier_reference()
    internal = model.create_internal_thermal_module()
    wet = model.create_wet_cooling_module()
    _assert_valid_nonempty(internal)
    _assert_valid_nonempty(wet)

    assert interference(internal, amplifier) <= 0.5
    assert clearance(internal, amplifier) >= 10.0
    assert interference(wet, amplifier) <= 0.5
    assert clearance(wet, amplifier) >= 20.0


def test_wet_cooling_module_is_external_in_positive_x_thermal_bay(model):
    amplifier_bb = model.create_amplifier_reference().val().BoundingBox()
    enclosure_bb = model.create_dry_enclosure().val().BoundingBox()
    wet_bb = model.create_wet_cooling_module().val().BoundingBox()

    assert wet_bb.xmin >= amplifier_bb.xmax + 20.0
    assert wet_bb.xmin >= enclosure_bb.xmax - 0.1
    assert wet_bb.xmax > enclosure_bb.xmax + 100.0


def test_wet_module_does_not_cross_the_dry_shell(model):
    enclosure = model.create_dry_enclosure()
    wet = model.create_wet_cooling_module()

    # Contact with the continuous thermal wall is intended; volumetric
    # overlap would create an unqualified penetration into the dry chamber.
    assert interference(enclosure, wet) <= 0.5


def test_sun_shield_covers_enclosure_and_retains_an_air_gap(model):
    enclosure = model.create_dry_enclosure()
    shield = model.create_sun_shield()
    _assert_valid_nonempty(shield)

    enclosure_bb = enclosure.val().BoundingBox()
    shield_bb = shield.val().BoundingBox()
    assert shield_bb.xlen >= enclosure_bb.xlen
    assert shield_bb.ylen >= enclosure_bb.ylen
    assert shield_bb.zmin >= enclosure_bb.zmax + 8.0


def test_reference_equipment_is_axially_outside_electronics_bay(model):
    mast_bb = model.create_mast_reference().val().BoundingBox()
    rotator_bb = model.create_rotator_reference().val().BoundingBox()
    amplifier = model.create_amplifier_reference()

    assert mast_bb.zmax <= 0.1
    assert rotator_bb.zmin >= 339.9
    assert interference(model.create_mast_reference(), amplifier) <= 0.5
    assert interference(model.create_rotator_reference(), amplifier) <= 0.5


def test_context_assembly_builds(model):
    assembly = model.create_assembly()
    assert isinstance(assembly, cq.Assembly)
    assert len(assembly.objects) >= 10
