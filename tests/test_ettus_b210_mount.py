"""
Tests for the Ettus USRP B210 mount family.

These are the parametric invariants — the things that must stay true when
somebody changes a number in params.json. The heavy geometric work (placing
the 11 MB vendor solid and booleaning it against every variant) lives in the
part's own fit_check.py, which lib.evaluate runs as a gating validator.

Run with: make test  (or: pytest tests/test_ettus_b210_mount.py -v)
"""

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PART_DIR = PROJECT_ROOT / "parts" / "custom" / "ettus-b210-mount"

_CACHE: dict = {}


def _model():
    if "m" not in _CACHE:
        spec = importlib.util.spec_from_file_location(
            "ettus_b210_mount", PART_DIR / "model.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _CACHE["m"] = m
        _CACHE["params"] = m.load_params()
    return _CACHE["m"], _CACHE["params"]


def _built(name: str):
    if name not in _CACHE:
        m, params = _model()
        _CACHE[name] = m.BUILDERS[name](params)
    return _CACHE[name]


@pytest.fixture(params=["flat_plate", "edge_bracket", "clamp_cradle"])
def variant(request):
    return request.param


# ---------------------------------------------------------------------------
# Every variant
# ---------------------------------------------------------------------------
def test_builds_and_is_solid(variant):
    solid = _built(variant)
    assert solid.solids().vals(), f"{variant} produced no solids"
    assert solid.val().Volume() > 1000.0


def test_valid_brep(variant):
    from OCP.BRepCheck import BRepCheck_Analyzer

    solid = _built(variant)
    assert BRepCheck_Analyzer(solid.val().wrapped).IsValid()


def test_material_and_process_are_stated(variant):
    """Every variant is real hardware — somebody has to make it."""
    _, params = _model()
    v = params["variants"][variant]
    assert v["material"].strip(), f"{variant} has no material"
    assert v["process"].strip(), f"{variant} has no process"


def test_reversible_in_y(variant):
    """
    Y is the axis that carries the radio's 6.1 mm asymmetry, so every variant
    is symmetric in Y and long enough for the LONGER overhang. Rotating the
    radio 180 degrees about Z maps the four bores onto themselves, so it can
    be fitted either way round and there is no wrong orientation to get wrong.
    """
    m, params = _model()
    bb = _built(variant).val().BoundingBox()
    assert bb.ymin == pytest.approx(-bb.ymax, abs=0.01)
    front = params["b210_interface"]["front_overhang_y"]
    assert bb.ymax >= front - 0.01, (
        "shorter than the front overhang — the radio would hang off one end")


def test_x_symmetry_where_it_is_claimed(variant):
    """
    The flat plate and the cradle tray are symmetric in X. The edge bracket
    deliberately is NOT: its flange side needs 10.8 mm of standoff to clear a
    vent slot, its free side needs 1.8 mm, and making it symmetric would cost
    9 mm of enclosure depth for nothing.
    """
    bb = _built(variant).val().BoundingBox()
    if variant == "edge_bracket":
        assert bb.xmin < -bb.xmax, "the flange-side offset has been lost"
    else:
        assert bb.xmin == pytest.approx(-bb.xmax, abs=0.01)


def test_height_above_the_seating_plane(variant):
    """
    z = 0 is the plane the radio's pan seats on, so mount material normally
    lives below it. Two variants reach above, and both heights are load-bearing
    design decisions rather than accidents.
    """
    m, params = _model()
    bb = _built(variant).val().BoundingBox()
    top_cover = params["b210_interface"]["top_cover_z"]
    if variant == "flat_plate":
        assert bb.zmax <= 0.001
    elif variant == "edge_bracket":
        # the flange must stay under the radio's own height, or it widens the
        # panel strip this variant exists to keep narrow
        assert bb.zmax <= top_cover
    else:
        # the bridges clear the top cover by exactly the pad thickness
        pad = params["variants"]["clamp_cradle"]["pad_thickness"]
        t = params["variants"]["clamp_cradle"]["bridge_thickness"]
        assert bb.zmax == pytest.approx(top_cover + pad + t, abs=0.01)


# ---------------------------------------------------------------------------
# The interface the radio actually offers
# ---------------------------------------------------------------------------
def test_hole_pattern_matches_the_measured_bores():
    _, params = _model()
    mh = params["b210_interface"]["mount_holes"]
    xs = sorted({abs(x) for x, _ in mh["positions_xy"]})
    ys = sorted({abs(y) for _, y in mh["positions_xy"]})
    assert len(xs) == 1 and len(ys) == 1, "pattern is not symmetric"
    assert 2 * xs[0] == pytest.approx(mh["pattern_x"], abs=0.001)
    assert 2 * ys[0] == pytest.approx(mh["pattern_y"], abs=0.001)


def test_body_is_offset_from_the_pattern_centre():
    """
    The trap this part exists to survive: the pattern is centred in X but sits
    3.05 mm off centre in Y. A bracket drawn symmetric about the BODY misses
    all four holes by 2.86 mm.
    """
    _, params = _model()
    iface = params["b210_interface"]
    front, rear = iface["front_overhang_y"], iface["rear_overhang_y"]
    assert front - rear == pytest.approx(6.106, abs=0.001)
    assert (front - rear) / 2 == pytest.approx(3.053, abs=0.001)


def test_screw_never_reaches_the_pcb_screw():
    """
    The safety-critical dimension. A screw longer than this jacks the PCB off
    its standoffs, and it does so silently.
    """
    _, params = _model()
    iface = params["b210_interface"]
    eng = iface["screw_grip"]["engagement"]
    assert eng <= iface["mount_holes"]["max_screw_penetration"]
    assert iface["mount_holes"]["max_screw_penetration"] < \
        iface["mount_holes"]["measured_free_depth"]


def test_bolted_variants_all_use_an_m3x6():
    """
    Plate thickness must stay independent of thread engagement: anything
    thicker than the grip gets counterbored from the underside.
    """
    _, params = _model()
    grip = params["b210_interface"]["screw_grip"]["value"]
    eng = params["b210_interface"]["screw_grip"]["engagement"]
    for name in ("flat_plate", "edge_bracket"):
        t = params["variants"][name]["thickness"]
        assert min(t, grip) + eng == pytest.approx(6.0, abs=0.001)
        if t > grip:
            assert params["variants"][name]["m3_counterbore_diameter"] > \
                params["variants"][name]["m3_clearance"]


def test_cradle_uses_no_bores_and_swallows_the_feet():
    """The insurance variant: if the standoffs are blind, this is what is left."""
    _, params = _model()
    iface = params["b210_interface"]
    cc = params["variants"]["clamp_cradle"]
    assert cc["foot_pocket_diameter"] > iface["feet"]["diameter"]
    assert cc["tray_thickness"] > iface["feet"]["height"], \
        "the tray must be deeper than the feet are proud, or the pan cannot seat"
    # 0.4 mm radial clearance — well above any process noise
    radial = (cc["foot_pocket_diameter"] - iface["feet"]["diameter"]) / 2
    assert radial >= 0.3


def test_cradle_bridge_legs_clear_the_vent_slots():
    """
    One bridge passes directly over a vent slot. The 10 mm keep-out survives
    only because the legs stand outboard of the side walls.
    """
    _, params = _model()
    iface = params["b210_interface"]
    cc = params["variants"]["clamp_cradle"]
    assert cc["bridge_leg_x"] - iface["body"]["x"][1] >= 10.0


def test_side_slots_are_diagonally_opposite_not_mirrored():
    """
    The reason nothing in this family clamps the side walls: a side clamp
    symmetric in Y fouls one of the two slots.
    """
    _, params = _model()
    ko = params["b210_interface"]["connector_keepouts"]
    front_y = sum(ko["front_end_slot"]["y"]) / 2
    rear_y = sum(ko["rear_end_slot"]["y"]) / 2
    assert front_y > 0 > rear_y
    assert ko["front_end_slot"]["x"][0] > 0 > ko["rear_end_slot"]["x"][1]


# ---------------------------------------------------------------------------
# Bent parts
# ---------------------------------------------------------------------------
def test_bent_parts_are_not_6061():
    """
    6061-T6 needs a 2.5-3t inside bend radius; these form at 1t. Every bent
    part in this family is 5052-H32 and the unbent plate is 6061-T6.
    """
    _, params = _model()
    for name in ("edge_bracket", "clamp_cradle"):
        assert "5052" in params["variants"][name]["material"]
    assert "6061" in params["variants"]["flat_plate"]["material"]


def test_bend_radius_is_at_least_one_thickness():
    _, params = _model()
    eb = params["variants"]["edge_bracket"]
    cc = params["variants"]["clamp_cradle"]
    assert eb["bend_inside_radius"] >= eb["thickness"]
    assert cc["bend_inside_radius"] >= cc["bridge_thickness"]


def test_flat_pattern_closes_against_the_solid(variant):
    """
    The blank and the formed part come from one set of bend numbers, so the
    developed length must equal the sum of the outside legs minus one bend
    deduction per bend. If these ever disagree, the shop cuts the wrong blank.
    """
    m, params = _model()
    _, info = m.flat_pattern(params, variant)
    assert info["blank_mm"][0] > 0 and info["blank_mm"][1] > 0
    for b in info["bends"]:
        expected_ba = m.bend_allowance(b["inside_radius"],
                                       info["thickness"], b["k_factor"])
        expected_bd = m.bend_deduction(b["inside_radius"],
                                       info["thickness"], b["k_factor"])
        assert b["bend_allowance"] == pytest.approx(expected_ba, abs=0.001)
        assert b["bend_deduction"] == pytest.approx(expected_bd, abs=0.001)


def test_edge_bracket_blank_arithmetic():
    """Sum of outside legs, minus one bend deduction, is the blank length."""
    m, params = _model()
    eb = params["variants"]["edge_bracket"]
    _, info = m.flat_pattern(params, "edge_bracket")
    t = eb["thickness"]
    x_bend, x_free = eb["web_x"]
    outside_web = x_free - (x_bend - t)
    outside_flange = eb["flange_width"]
    bd = m.bend_deduction(eb["bend_inside_radius"], t)
    assert info["blank_mm"][0] == pytest.approx(
        outside_web + outside_flange - bd, abs=0.01)


def test_cradle_bridge_has_four_bends():
    m, params = _model()
    _, info = m.flat_pattern(params, "clamp_cradle")
    assert len(info["bends"]) == 4


# ---------------------------------------------------------------------------
# The vendor file this all derives from
# ---------------------------------------------------------------------------
def test_vendor_step_is_present():
    _, params = _model()
    p = PROJECT_ROOT / params["b210_interface"]["source_step"]
    assert p.is_file(), f"vendor STEP missing: {p}"


def test_transform_is_a_rotation_not_a_reflection():
    """
    The obvious map (x, z, y) has determinant -1 and would silently mirror the
    vendor solid. This one is +90 about X then 180 about Z.
    """
    import numpy as np

    m, _ = _model()
    steps = m.b210_transform()
    mat = np.eye(3)
    for s in steps:
        if "rotate" not in s:
            continue
        a, deg = s["rotate"]["axis"], np.radians(s["rotate"]["angle"])
        c, sn = np.cos(deg), np.sin(deg)
        r = {"X": np.array([[1, 0, 0], [0, c, -sn], [0, sn, c]]),
             "Y": np.array([[c, 0, sn], [0, 1, 0], [-sn, 0, c]]),
             "Z": np.array([[c, -sn, 0], [sn, c, 0], [0, 0, 1]])}[a]
        mat = r @ mat
    assert np.linalg.det(mat) == pytest.approx(1.0, abs=1e-9)
    # and it must send the pan normal (part +Y) to mount +Z
    assert np.allclose(mat @ np.array([0, 1, 0]), np.array([0, 0, 1]), atol=1e-9)
