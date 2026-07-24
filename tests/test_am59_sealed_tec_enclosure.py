"""Geometry, thermal, and environmental-boundary checks for V3 TEC enclosure."""

import importlib.util
import sys
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.housing import clearance, interference  # noqa: E402

MODEL_PATH = (
    PROJECT_ROOT
    / "parts"
    / "custom"
    / "am59_sealed_tec_enclosure"
    / "model.py"
)

REQUIRED_BUILDERS = (
    "create_pressure_body",
    "create_service_lid",
    "create_service_gasket",
    "create_internal_cartridge",
    "create_cartridge_support_structure",
    "create_cartridge_retainers",
    "create_cartridge_service_sweep_reference",
    "create_amplifier_reference",
    "create_cooler_doubler_frames",
    "create_seifert_cooler_bank",
    "create_cooler_interface_gaskets",
    "create_internal_air_management",
    "create_condensation_management",
    "create_immersion_caps",
    "create_immersion_cap_gaskets",
    "create_sun_shields",
    "thermal_assessment",
    "mass_assessment",
    "create_assembly",
)


def _load_model():
    spec = importlib.util.spec_from_file_location(
        "am59_sealed_tec_enclosure_model_test",
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
        "lid": model.create_service_lid(),
        "service_gasket": model.create_service_gasket(),
        "cartridge": model.create_internal_cartridge(),
        "supports": model.create_cartridge_support_structure(),
        "retainers": model.create_cartridge_retainers(),
        "service_sweep": model.create_cartridge_service_sweep_reference(),
        "amplifier": model.create_amplifier_reference(),
        "cooler_components": model.seifert_cooler_components(),
        "coolers": model.create_seifert_cooler_bank(),
        "cooler_gaskets": model.create_cooler_interface_gaskets(),
        "baffles": model.create_internal_air_management(),
        "trays": model.create_condensation_management(),
        "controller": model.create_controller_reference(),
        "cap_components": model.immersion_cap_components(),
        "caps": model.create_immersion_caps(),
        "cap_gaskets": model.create_immersion_cap_gaskets(),
        "shields": model.create_sun_shields(),
    }


def test_public_builder_contract_is_complete(model):
    for builder_name in REQUIRED_BUILDERS:
        assert callable(getattr(model, builder_name, None)), builder_name


def test_vendor_steps_are_exact_user_supplied_files(model):
    params = model.load_params()
    assert model.AMPLIFIER_STEP.is_file()
    assert model.SEIFERT_STEP.is_file()
    assert params["amplifier"]["vendor_part"] == "AM59-3S-64-64"
    assert params["seifert_3050303"]["count"] == 4
    assert params["seifert_3050303"]["step_file"].endswith(
        "Seifert - 3050303.STEP"
    )


def test_pressure_body_has_standalone_enclosure_envelope(geometry):
    body = geometry["body"]
    _assert_valid_nonempty(body)
    bb = body.val().BoundingBox()

    # The pressure shell itself is 410 x 320 mm in Y/Z. The localized
    # 430 x 340 mm welded service collar governs the accepted outer envelope.
    assert bb.xmin == pytest.approx(-390.0, abs=0.1)
    assert bb.xmax == pytest.approx(105.0, abs=0.1)
    assert bb.ymin == pytest.approx(-215.0, abs=0.1)
    assert bb.ymax == pytest.approx(215.0, abs=0.1)
    assert bb.zmin == pytest.approx(10.0, abs=0.1)
    assert bb.zmax == pytest.approx(350.0, abs=0.1)


def test_amplifier_uses_verified_pose_and_fits_pressure_body(model, geometry):
    amplifier = geometry["amplifier"]
    body = geometry["body"]
    _assert_valid_nonempty(amplifier)

    bb = amplifier.val().BoundingBox()
    assert bb.xmin == pytest.approx(-345.4, abs=0.05)
    assert bb.xmax == pytest.approx(18.72, abs=0.05)
    assert bb.ymin == pytest.approx(-100.0, abs=0.05)
    assert bb.ymax == pytest.approx(100.0, abs=0.05)
    assert bb.zmin == pytest.approx(52.0, abs=0.05)
    assert bb.zmax == pytest.approx(154.0, abs=0.05)

    assert interference(body, amplifier) <= 0.5
    # The nearest body geometry is now an intentional welded support rail.
    assert clearance(body, amplifier) >= 5.0
    params = model.load_params()
    enclosure = params["sealed_enclosure"]
    wall = enclosure["wall_thickness"]
    assert bb.zmin - (enclosure["z_min"] + wall) >= 20.0
    assert enclosure["outer_width_y"] / 2 - wall - bb.ymax >= 20.0


def test_four_exact_seifert_units_are_symmetric_and_recessed(model, geometry):
    parts = geometry["cooler_components"]
    assert len(parts) == 4
    for cooler in parts.values():
        _assert_valid_nonempty(cooler)
        bb = cooler.val().BoundingBox()
        assert bb.xlen == pytest.approx(153.5, abs=0.05)
        assert bb.ylen == pytest.approx(134.93, abs=0.05)
        assert bb.zlen == pytest.approx(206.0, abs=0.05)

    combined = geometry["coolers"].val().BoundingBox()
    assert combined.xmin == pytest.approx(-321.75, abs=0.05)
    assert combined.xmax == pytest.approx(36.75, abs=0.05)
    assert combined.ymin == pytest.approx(-268.0, abs=0.05)
    assert combined.ymax == pytest.approx(268.0, abs=0.05)
    assert combined.zmin == pytest.approx(77.0, abs=0.05)
    assert combined.zmax == pytest.approx(283.0, abs=0.05)

    locations = model.cooler_mount_locations()
    assert len(locations) == 4
    assert {side for side, _, _ in locations} == {-1, 1}


def test_opposed_cooler_projections_clear_amplifier(geometry):
    amplifier = geometry["amplifier"]
    coolers = geometry["coolers"]
    assert interference(amplifier, coolers) <= 0.5
    assert clearance(amplifier, coolers) >= 35.0


def test_cooler_cutouts_and_mounting_holes_match_supplied_drawing(model):
    params = model.load_params()
    cooler = params["seifert_3050303"]
    cutouts = model.cooler_mount_cutout_references()
    _assert_valid_nonempty(cutouts)

    assert cooler["cutout_width_x"] == pytest.approx(120.0)
    assert cooler["cutout_height_z"] == pytest.approx(170.0)
    assert cooler["mount_hole_spacing_x"] == pytest.approx(105.0)
    assert cooler["mount_hole_spacing_z"] == pytest.approx(185.0)
    assert cooler["mount_hole_diameter"] == pytest.approx(8.0)

    holes = model.cooler_mount_hole_locations()
    assert len(holes) == 16
    assert len(set(holes)) == 16


def test_service_lid_gasket_and_fastener_pitch(model, geometry):
    body = geometry["body"]
    lid = geometry["lid"]
    gasket = geometry["service_gasket"]
    _assert_valid_nonempty(lid)
    _assert_valid_nonempty(gasket)

    body_bb = body.val().BoundingBox()
    lid_bb = lid.val().BoundingBox()
    assert lid_bb.xmax <= body_bb.xmin + 0.1
    assert clearance(lid, body) <= 0.05
    assert interference(lid, body) <= 0.5
    assert clearance(gasket, lid) <= 0.5

    params = model.load_params()
    lid_params = params["service_lid"]
    locations = model.service_fastener_locations()
    assert len(locations) == 32
    assert len(set(locations)) == 32
    assert max(
        b - a
        for a, b in zip(
            lid_params["fastener_y_top_bottom"],
            lid_params["fastener_y_top_bottom"][1:],
        )
    ) <= lid_params["maximum_fastener_pitch"]

    enclosure = params["sealed_enclosure"]
    gasket_inner_y = (
        lid_params["seal_ring_outer_width_y"]
        - 2 * lid_params["seal_ring_width"]
    )
    gasket_inner_z = (
        lid_params["seal_ring_outer_height_z"]
        - 2 * lid_params["seal_ring_width"]
    )
    assert (
        gasket_inner_y - enclosure["flange_opening_width_y"]
    ) / 2 >= 5.0
    opening_z_min = (
        enclosure["flange_opening_center_z"]
        - enclosure["flange_opening_height_z"] / 2
    )
    opening_z_max = (
        enclosure["flange_opening_center_z"]
        + enclosure["flange_opening_height_z"] / 2
    )
    gasket_z_min = (
        lid_params["seal_ring_center_z"] - gasket_inner_z / 2
    )
    gasket_z_max = (
        lid_params["seal_ring_center_z"] + gasket_inner_z / 2
    )
    assert opening_z_min - gasket_z_min >= 5.0
    assert gasket_z_max - opening_z_max >= 5.0

    fastener_radius = lid_params["fastener_diameter"] / 2
    side_outer_web = (
        lid_params["outer_width_y"] / 2
        - lid_params["fastener_edge_y"]
        - fastener_radius
    )
    side_gasket_web = (
        lid_params["fastener_edge_y"]
        - fastener_radius
        - lid_params["seal_ring_outer_width_y"] / 2
    )
    bottom_outer_web = (
        lid_params["fastener_edge_z_bottom"]
        - (lid_params["seal_ring_center_z"] - lid_params["outer_height_z"] / 2)
        - fastener_radius
    )
    bottom_gasket_web = (
        lid_params["seal_ring_center_z"]
        - lid_params["seal_ring_outer_height_z"] / 2
        - lid_params["fastener_edge_z_bottom"]
        - fastener_radius
    )
    assert min(
        side_outer_web,
        side_gasket_web,
        bottom_outer_web,
        bottom_gasket_web,
    ) >= 5.0
    assert max(
        b - a
        for a, b in zip(
            lid_params["fastener_z_sides"],
            lid_params["fastener_z_sides"][1:],
        )
    ) <= lid_params["maximum_fastener_pitch"]


def test_cartridge_contacts_without_intersecting_amplifier(geometry):
    cartridge = geometry["cartridge"]
    amplifier = geometry["amplifier"]
    _assert_valid_nonempty(cartridge)
    assert interference(cartridge, amplifier) <= 0.5
    assert clearance(cartridge, amplifier) <= 0.05


def test_cartridge_has_supported_retained_serviceable_load_path(
    model,
    geometry,
):
    cartridge = geometry["cartridge"]
    supports = geometry["supports"]
    retainers = geometry["retainers"]
    amplifier = geometry["amplifier"]
    _assert_valid_nonempty(supports)
    _assert_valid_nonempty(retainers)
    _assert_valid_nonempty(geometry["service_sweep"])

    assert interference(cartridge, supports) <= 0.5
    assert clearance(cartridge, supports) <= 0.05
    assert interference(cartridge, retainers) <= 0.5
    assert clearance(cartridge, retainers) <= 0.05
    assert interference(amplifier, supports) <= 0.5
    assert clearance(amplifier, supports) >= 5.0

    params = model.load_params()
    cartridge_params = params["cartridge"]
    enclosure = params["sealed_enclosure"]
    assert cartridge_params["support_rail_bottom_z"] == pytest.approx(
        enclosure["z_min"] + enclosure["wall_thickness"]
    )
    assert cartridge_params["support_rail_top_z"] == pytest.approx(
        cartridge_params["bottom_z"]
    )

    # The cold-drop module is removed with the lid. All remaining fixed
    # baffles clear representative extraction positions.
    baffle_parts = model.air_management_components()
    removable = baffle_parts.pop("cold_inlet_drop_baffle")
    assert interference(removable, geometry["service_sweep"]) > 0.5
    fixed_baffles = model._compound(list(baffle_parts.values()))
    for dx in (0.0, -100.0, -200.0, -300.0, -430.0):
        moving = model._compound(
            [
                cartridge.translate((dx, 0, 0)),
                amplifier.translate((dx, 0, 0)),
            ]
        )
        assert interference(moving, fixed_baffles) <= 0.5


def test_air_baffles_and_controller_clear_vendor_hardware(geometry):
    amplifier = geometry["amplifier"]
    coolers = geometry["coolers"]
    baffles = geometry["baffles"]
    controller = geometry["controller"]
    _assert_valid_nonempty(baffles)
    _assert_valid_nonempty(controller)

    assert interference(amplifier, baffles) <= 0.5
    assert clearance(amplifier, baffles) >= 10.0
    assert interference(coolers, baffles) <= 0.5
    assert clearance(coolers, baffles) >= 5.0
    assert interference(amplifier, controller) <= 0.5
    assert interference(coolers, controller) <= 0.5
    assert interference(controller, baffles) <= 0.5
    assert clearance(controller, baffles) >= 3.0


def test_condensate_trays_are_internal_and_clear_of_amplifier(model, geometry):
    trays = geometry["trays"]
    amplifier = geometry["amplifier"]
    _assert_valid_nonempty(trays)
    assert len(model.condensate_tray_components()) == 4
    assert interference(trays, amplifier) <= 0.5
    assert clearance(trays, amplifier) >= 5.0
    bb = trays.val().BoundingBox()
    assert bb.zmin >= 20.0
    assert bb.zmin > 52.0
    assert bb.zmax < 77.0


def test_immersion_caps_clear_and_enclose_external_cooler_banks(
    model,
    geometry,
):
    caps = geometry["cap_components"]
    coolers = geometry["cooler_components"]
    assert len(caps) == 2
    for cap in caps.values():
        _assert_valid_nonempty(cap)

    pos_cap = caps["immersion_cap_posY"]
    neg_cap = caps["immersion_cap_negY"]
    pos_cap_bb = pos_cap.val().BoundingBox()
    neg_cap_bb = neg_cap.val().BoundingBox()
    assert pos_cap_bb.xmin == pytest.approx(-371.5, abs=0.1)
    assert pos_cap_bb.xmax == pytest.approx(86.5, abs=0.1)
    assert pos_cap_bb.ymax == pytest.approx(295.8, abs=0.1)
    assert neg_cap_bb.ymin == pytest.approx(-295.8, abs=0.1)

    for name, cooler in coolers.items():
        cap = pos_cap if "posY" in name else neg_cap
        cap_bb = cap.val().BoundingBox()
        cooler_bb = cooler.val().BoundingBox()
        assert cap_bb.xmin < cooler_bb.xmin
        assert cap_bb.xmax > cooler_bb.xmax
        assert cap_bb.zmin < cooler_bb.zmin
        assert cap_bb.zmax > cooler_bb.zmax
        assert interference(cap, cooler) <= 0.5

    _assert_valid_nonempty(geometry["cap_gaskets"])

    body = geometry["body"]
    gaskets = geometry["cap_gaskets"]
    assert interference(geometry["caps"], body) <= 0.5
    assert clearance(geometry["caps"], body) == pytest.approx(0.8, abs=0.05)
    assert clearance(gaskets, body) <= 0.05
    assert clearance(gaskets, geometry["caps"]) <= 0.05

    params = model.load_params()
    cap_params = params["immersion_caps"]
    assert (
        cap_params["cap_outer_width_x"]
        - cap_params["cap_flange_inner_width_x"]
    ) == pytest.approx(2 * cap_params["cap_wall_thickness"])
    assert (
        cap_params["cap_outer_height_z"]
        - cap_params["cap_flange_inner_height_z"]
    ) == pytest.approx(2 * cap_params["cap_wall_thickness"])
    for cap in caps.values():
        material_volume = sum(
            abs(solid.Volume()) for solid in cap.solids().vals()
        )
        assert material_volume < 1.1e6

    fasteners = model.immersion_cap_fastener_locations()
    assert len(fasteners) == 64
    assert len(set(fasteners)) == 64
    radius = cap_params["fastener_hole_diameter"] / 2
    edge_web = min(
        cap_params["coaming_outer_width_x"] / 2
        - cap_params["fastener_edge_abs_x"]
        - radius,
        cap_params["coaming_outer_height_z"] / 2
        - cap_params["fastener_edge_abs_z"]
        - radius,
    )
    gasket_web = min(
        cap_params["fastener_edge_abs_x"]
        - radius
        - cap_params["gasket_outer_width_x"] / 2,
        cap_params["fastener_edge_abs_z"]
        - radius
        - cap_params["gasket_outer_height_z"] / 2,
    )
    assert min(edge_web, gasket_web) >= 5.0


def test_high_power_feedthrough_axis_preserves_short_straight_run(model):
    params = model.load_params()
    amp_axis = params["amplifier"]["rf_output_axis_reference_mm"]
    feedthrough = params["feedthroughs"]["high_power_rf_axis_mm"]
    assert feedthrough["y"] == pytest.approx(amp_axis["y"])
    assert feedthrough["z"] == pytest.approx(amp_axis["z"])
    assert params["feedthroughs"][
        "internal_straight_length_from_step_nose_mm_approx"
    ] == pytest.approx(87.0)


def test_thermal_modes_enforce_required_degradation(model):
    assessment = model.thermal_assessment()
    modes = assessment["modes"]
    assert assessment["per_unit_capacity_w"] == pytest.approx(91.0)
    assert modes["four_healthy_300w"]["capacity_w"] == pytest.approx(364.0)
    assert modes["four_healthy_300w"]["passes"]
    assert modes["three_healthy_200w"]["passes"]
    assert modes["two_healthy_125w"]["passes"]
    assert not modes["one_healthy_125w"]["passes"]
    assert assessment["design_hot_side_rejection_w"] == pytest.approx(564.0)

    params = model.load_params()
    thermal = params["amplifier"]["electrical_and_thermal"]
    breakdown = thermal["enclosure_design_heat_breakdown_w"]
    assert sum(breakdown.values()) == pytest.approx(
        thermal["enclosure_design_heat_w"]
    )
    assert thermal["case_hardware_inhibit_c"] < thermal["case_target_c"]
    assert thermal["amplifier_power_remove_c"] < thermal["case_target_c"]
    airflow = params["internal_air_management"]
    assert "TBD" in airflow["production_flow_acceptance_limit"]
    assert "free-air" in airflow["production_flow_acceptance_limit"]


def test_preliminary_mass_report_flags_unknown_system_cg(model):
    mass = model.mass_assessment()
    assert mass["single_immersion_cap_mass_kg_approx"] < 3.0
    assert (
        mass["immersion_known_mass_excluding_am59_gaskets_fasteners_wiring_kg"]
        > mass[
            "operating_known_mass_excluding_am59_gaskets_fasteners_wiring_kg"
        ]
    )
    assert "Not releasable" in mass["system_cg_status"]


def test_environmental_claim_is_configuration_specific(model):
    params = model.load_params()
    modes = params["environmental_modes"]
    cooler = params["seifert_3050303"]
    caps = params["immersion_caps"]
    assert "IP66" in cooler["rating"]
    assert "IPX7" in modes["temporary_immersion"]
    assert "both cooler-bank immersion caps installed" in modes[
        "temporary_immersion"
    ]
    assert "never installed while the enclosure is energized" in caps[
        "use_limit"
    ]


def test_operating_and_immersion_assemblies_build(model):
    operating = model.create_assembly()
    immersion = model.create_assembly(immersion_ready=True)
    assert isinstance(operating, cq.Assembly)
    assert isinstance(immersion, cq.Assembly)
    assert len(operating.objects) >= 20
    assert len(immersion.objects) >= len(operating.objects) + 4
