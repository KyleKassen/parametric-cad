"""Geometry and fit checks for the preliminary AM59 centered bridge mast head."""

import importlib.util
import sys
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.housing import clearance, interference  # noqa: E402

MODEL_PATH = PROJECT_ROOT / "parts" / "custom" / "am59_mast_head" / "model.py"


def _load_model():
    spec = importlib.util.spec_from_file_location("am59_mast_head_model_test", MODEL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def model():
    return _load_model()


def test_structural_frame_is_valid_single_load_path(model):
    frame = model.create_structural_frame()
    assert frame.val().isValid()
    assert len(frame.solids().vals()) == 1
    bb = frame.val().BoundingBox()
    assert bb.xlen == pytest.approx(260.0, abs=0.1)
    assert bb.ylen == pytest.approx(320.0, abs=0.1)
    assert bb.zlen == pytest.approx(168.0, abs=0.1)


def test_amplifier_reference_uses_exact_expected_pose(model):
    amplifier = model.create_amplifier_reference()
    bb = amplifier.val().BoundingBox()
    assert bb.xmin == pytest.approx(-185.4, abs=0.05)
    assert bb.xmax == pytest.approx(178.72, abs=0.05)
    assert bb.ymin == pytest.approx(-100.0, abs=0.05)
    assert bb.ymax == pytest.approx(100.0, abs=0.05)
    assert bb.zmin == pytest.approx(20.0, abs=0.05)
    assert bb.zmax == pytest.approx(122.0, abs=0.05)


def test_cartridge_matches_all_twelve_am59_mounting_points(model):
    cartridge = model.create_cartridge()
    params = model.load_params()
    assert cartridge.val().isValid()
    assert len(params["amplifier"]["mount_hole_x"]) == 6
    assert len(params["amplifier"]["mount_hole_y"]) == 2

    # Twelve 4.5-mm hole cylinders plus four larger retention holes.
    cylinders = [
        face
        for face in cartridge.val().Faces()
        if face.geomType() == "CYLINDER"
    ]
    radii = sorted(
        round(face._geomAdaptor().Cylinder().Radius(), 3)
        for face in cylinders
    )
    assert radii.count(2.25) >= 12
    assert radii.count(3.25) >= 4
    conical_faces = [
        face
        for face in cartridge.val().Faces()
        if face.geomType() == "CONE"
    ]
    assert len(conical_faces) >= 12


def test_cartridge_locks_align_with_tapped_support_bars(model):
    params = model.load_params()
    frame_params = params["frame"]
    cartridge_params = params["cartridge"]
    frame = model.create_structural_frame()

    assert cartridge_params["end_lock_hole_x"] == pytest.approx(
        frame_params["support_bar_center_x"]
    )
    assert (
        cartridge_params["end_lock_hole_y"]
        < frame_params["support_bar_length_y"] / 2
    )

    cylinders = [
        face
        for face in frame.val().Faces()
        if face.geomType() == "CYLINDER"
    ]
    radii = [
        round(face._geomAdaptor().Cylinder().Radius(), 3)
        for face in cylinders
    ]
    assert radii.count(
        frame_params["cartridge_lock_tap_diameter"] / 2
    ) >= 4


def test_cartridge_lock_hardware_clears_amplifier(model):
    params = model.load_params()
    cartridge = params["cartridge"]
    amplifier = model.create_amplifier_reference()
    head_radius = 5.5
    head_height = 4.0
    heads = []

    for x_sign in (-1, 1):
        for y_sign in (-1, 1):
            heads.append(
                cq.Workplane(
                    obj=cq.Solid.makeCylinder(
                        head_radius,
                        head_height,
                        cq.Vector(
                            x_sign * cartridge["end_lock_hole_x"],
                            y_sign * cartridge["end_lock_hole_y"],
                            cartridge["bottom_z"] + cartridge["thickness"],
                        ),
                        cq.Vector(0, 0, 1),
                    )
                )
            )

    assert interference(model._compound(heads), amplifier) <= 0.5


def test_am59_mounting_screws_are_flush_and_clear_support_bars(model):
    params = model.load_params()
    frame = params["frame"]
    amplifier = params["amplifier"]
    preliminary_m4_head_radius = (
        params["cartridge"]["mount_countersink_diameter"] / 2
    )
    support_half_width = frame["support_bar_width_x"] / 2

    for mount_x in amplifier["mount_hole_x"]:
        distance_to_support_center = min(
            abs(mount_x - frame["support_bar_center_x"]),
            abs(mount_x + frame["support_bar_center_x"]),
        )
        assert (
            distance_to_support_center
            > support_half_width + preliminary_m4_head_radius
        )


def test_vendor_amplifier_clears_structural_frame(model):
    frame = model.create_structural_frame()
    amplifier = model.create_amplifier_reference()
    assert interference(frame, amplifier) <= 0.5
    assert clearance(frame, amplifier) >= 5.0


def test_vendor_amplifier_contacts_but_does_not_overlap_cartridge(model):
    cartridge = model.create_cartridge()
    amplifier = model.create_amplifier_reference()
    assert interference(cartridge, amplifier) <= 0.5
    assert clearance(cartridge, amplifier) <= 0.05


def test_weather_shell_preserves_amplifier_keepout(model):
    shell = model.create_weather_shell()
    amplifier = model.create_amplifier_reference()
    assert shell.val().isValid()
    assert interference(shell, amplifier) <= 0.5
    assert clearance(shell, amplifier) >= 25.0


def test_weather_openings_provision_minimum_gross_area(model):
    params = model.load_params()
    shell = params["weather_shell"]

    inlet_area = (
        shell["outer_width_y"] * shell["inlet_baffle_bottom_z"]
        + len(shell["inlet_window_centers_y"])
        * shell["inlet_window_width_y"]
        * shell["inlet_window_height_z"]
    )
    end_exhaust_area = (
        2
        * shell["exhaust_window_width_y"]
        * shell["exhaust_window_height_z"]
    )
    side_exhaust_area = (
        2
        * (
            shell["side_exhaust_window_x_max"]
            - shell["side_exhaust_window_x_min"]
        )
        * shell["side_exhaust_window_height_z"]
    )
    minimum_gross_area = (
        params["amplifier"]["airflow"]["preferred_net_area"]
    )

    assert inlet_area >= minimum_gross_area
    assert end_exhaust_area + side_exhaust_area >= minimum_gross_area


def test_connector_doghouse_encloses_without_collision(model):
    doghouse = model.create_connector_doghouse()
    amplifier = model.create_amplifier_reference()
    assert doghouse.val().isValid()
    assert interference(doghouse, amplifier) <= 0.5
    # The open doghouse edge intentionally lands on the amplifier output
    # panel plane for a closed-cell environmental gasket.
    assert clearance(doghouse, amplifier) <= 0.05


def test_connector_doghouse_clears_cartridge(model):
    doghouse = model.create_connector_doghouse()
    cartridge = model.create_cartridge()
    assert interference(doghouse, cartridge) <= 0.5


def test_service_opening_allows_positive_x_cartridge_extraction(model):
    frame = model.create_structural_frame()
    remaining_weather = [
        component
        for name, component in model.weather_components().items()
        if (
            name not in {"service_side", "fixed_side"}
            and name != "exhaust_baffle"
            and not name.startswith("exhaust_louver_")
        )
    ]
    obstacles = model._compound([frame, *remaining_weather])
    removable_module = model._compound(
        [
            model.create_cartridge(),
            model.create_amplifier_reference(),
        ]
    )

    for travel_x in range(0, 451, 25):
        moved = removable_module.translate((travel_x, 0, 0))
        assert interference(moved, obstacles) <= 0.5


def test_end_louvers_drain_outward(model):
    params = model.load_params()["weather_shell"]
    assert params["louver_blade_angle_deg"] > 0
