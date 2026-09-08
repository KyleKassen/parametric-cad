"""
Tests for the SolidRun Bedrock V3000 mount family.

The parametric invariants — the things that must stay true when somebody edits a
number in params.json. Most of them exist because the Bedrock's fixing set is so
thin that an innocuous-looking parameter change turns into a bracket that jacks
itself off the unit or covers a fin bank.

The heavy geometry (placing the 44 MB vendor solid and booleaning it against
every variant) lives in the part's own fit_check.py, which lib.evaluate runs as
a gating validator; flat_patterns.py runs as a second one.

Run with: make test  (or: pytest tests/test_bedrock_v3000_mount.py -v)
"""

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PART_DIR = PROJECT_ROOT / "parts" / "custom" / "bedrock-v3000-mount"

_CACHE: dict = {}


def _load(name: str):
    """
    Load one of the part's modules by path, under the same namespaced key the
    part itself uses. Putting PART_DIR on sys.path would hand this part's
    `model.py` to every other part's tests in the same pytest process — which is
    exactly what happened the first time, and it showed up as 37 failures in a
    part this one never touches.
    """
    key = f"bedrock_v3000_mount.{name}"
    mod = sys.modules.get(key)
    if mod is None:
        spec = importlib.util.spec_from_file_location(key, PART_DIR / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return mod


def _model():
    if "params" not in _CACHE:
        m = _load("model")
        _CACHE["params"] = m.load_params()
    return _load("model"), _CACHE["params"]


def _built(name: str):
    if name not in _CACHE:
        m, params = _model()
        _CACHE[name] = m.BUILDERS[name](params)
    return _CACHE[name]


@pytest.fixture(params=["upright_deck", "upright_bulkhead", "low_profile_side",
                        "tile_side_plate", "hybrid_cold_plate"])
def variant(request):
    return request.param


@pytest.fixture(params=["upright_deck", "upright_bulkhead", "low_profile_side"])
def folded(request):
    """The three folded-sheet variants (the Tile plate has no bends)."""
    return request.param


# ---------------------------------------------------------------------------
# Every variant
# ---------------------------------------------------------------------------
def test_builds_and_is_solid(variant):
    solid = _built(variant)
    assert solid.solids().vals(), f"{variant} produced no solids"
    assert solid.val().Volume() > 1000.0


def test_single_solid(variant):
    """A bracket in two pieces is a modelling failure, not a two-part design."""
    assert len(_built(variant).val().Solids()) == 1


def test_valid_brep(variant):
    from OCP.BRepCheck import BRepCheck_Analyzer

    assert BRepCheck_Analyzer(_built(variant).val().wrapped).IsValid()


def test_sheet_thickness_is_uniform(variant):
    """
    Every variant is one gauge of sheet or plate — no variant may quietly need
    two thicknesses, which is two purchase lines and two setups.
    """
    m, params = _model()
    t = params["dimensions"]["sheet_t"]
    if variant in m.FLAT_VARIANTS:
        t = params["variants"][variant]["plate_t"]
    bb = _built(variant).val().BoundingBox()
    assert min(bb.xlen, bb.ylen, bb.zlen) >= t - 1e-6


# ---------------------------------------------------------------------------
# The interface: the two faces every general variant works
# ---------------------------------------------------------------------------
def test_backwall_screw_arithmetic_is_checked_not_assumed():
    """
    The +Y tapping is 3.000 mm deep. A screw that reaches the bottom jacks the
    bracket off the bearing land, and the joint still feels tight — so the
    arithmetic has to raise, not warn.
    """
    iface = _load("interface")
    assert iface.check_backwall_screw(5.0, 2.5) == pytest.approx(2.5)
    with pytest.raises(ValueError):
        iface.check_backwall_screw(6.0, 2.5)      # 3.5 mm — bottoms out
    with pytest.raises(ValueError):
        iface.check_backwall_screw(4.0, 3.0)      # 1.0 mm — barely two threads


def test_bottom_screw_arithmetic_is_checked_not_assumed():
    iface = _load("interface")
    assert iface.check_bottom_screw(8.0, 3.0) == pytest.approx(5.0)
    with pytest.raises(ValueError):
        iface.check_bottom_screw(12.0, 3.0)       # 9.0 mm — past the thread


def test_fastener_schedule_never_exceeds_a_penetration_limit():
    """Whatever params.json says, no screw in the schedule may bottom out."""
    iface = _load("interface")
    fp = _load("flat_patterns")
    for row in fp.fastener_schedule():
        limit = row["max_penetration_mm"]
        if limit == "" or row["engagement_mm"] == "":
            continue
        assert row["engagement_mm"] <= limit, (
            f"{row['id']} engages {row['engagement_mm']} mm into a "
            f"{limit} mm limit")
    assert iface.BACKWALL_M3_MAX_PENETRATION == 3.0
    assert iface.TILE_M4_MAX_PENETRATION == 3.5


def test_bearing_tongue_stays_inside_the_back_wall_land():
    """
    The continuous flat on the back wall is only X -10..+10. Anything wider
    rides on two blend ridges instead of bearing, so the tongue is cut back and
    the relief slots start inboard of the land edge.
    """
    m, params = _model()
    iface = _load("interface")
    inner = params["clearances"]["relief_slot_x_inner"]
    assert inner < iface.BACKWALL_LAND_X
    assert iface.BACKWALL_LAND_X - inner >= 0.4
    assert params["clearances"]["relief_slot_outer_x"] > iface.BACKWALL_LAND_X


def test_bottom_bearing_leaves_the_fin_inlets_open():
    """
    The -Z cap looks like a plate but the fin channels are open through it
    outboard of |X| ~ 14.5. A pan that bears past that blanks the chimney inlet.
    """
    m, params = _model()
    iface = _load("interface")
    for name in ("upright_deck", "upright_bulkhead"):
        window_inner = params["variants"][name]["window_x"][0]
        assert window_inner >= iface.BOTTOM_CORE_X, (
            f"{name} bears out to |X| = {window_inner}, past the fin inlet at "
            f"{iface.BOTTOM_CORE_X}")


def test_shock_walls_clear_the_fin_tips():
    """The walls are a stop, not a clamp: they must not touch a fin in service."""
    m, params = _model()
    iface = _load("interface")
    # the wall's INNER face is the pan's own edge; the material lies outboard of it
    wall_inner = params["variants"]["upright_deck"]["pan_x"]
    gap = wall_inner - iface.FIN["60w"]["tip_x"]
    assert gap == pytest.approx(params["clearances"]["fin_tip_gap"])
    assert gap >= 1.0


def test_low_profile_base_never_touches_the_lower_fin_bank():
    """
    On its side the unit has no fin-free surface underneath it, so the base is a
    guard at a stated standoff — not a seat. If that standoff goes to zero the
    variant silently becomes a fin crusher.
    """
    m, params = _model()
    iface = _load("interface")
    v = params["variants"]["low_profile_side"]
    standoff = -v["base_x"] - iface.FIN["60w"]["tip_x"]
    assert standoff == pytest.approx(params["clearances"]["side_plenum"])
    assert standoff >= 5.0


# ---------------------------------------------------------------------------
# Sheet-metal invariants
# ---------------------------------------------------------------------------
def test_bend_centre_is_derived_from_both_outer_faces():
    """
    A 90 degree bend's arc centre sits r_outer inboard of BOTH outer faces. Get
    the side wrong and the profile self-intersects into a face the kernel will
    not fuse — which shows up as a flange silently missing, not as an error.
    """
    m, _ = _model()
    assert m.bend_centre(68.0, -1, -3.0, +1, 6.0) == (62.0, 3.0)
    assert m.bend_centre(42.0, +1, 98.0, -1, 6.0) == (48.0, 92.0)


def test_fuse_refuses_to_lose_a_flange():
    import cadquery as cq

    m, _ = _model()
    base = cq.Workplane("XY").box(20, 20, 3)
    good = cq.Workplane("XY").box(20, 20, 3).translate((15, 0, 0))
    assert m.fuse(base, good, "overlapping block").val().Volume() > base.val().Volume()


def test_folded_variants_develop_into_one_connected_blank(folded):
    """
    A blank in two pieces means a leg is not reaching its bend strip. The
    developer raises on that, and on any feature that runs into a bend tangent.
    """
    fp = _load("flat_patterns")
    m, params = _model()
    blank, legs = fp.develop(folded, params)
    assert len(blank.val().Solids()) == 1
    assert len(legs) >= 3
    bb = blank.val().BoundingBox()
    assert bb.xlen > 50 and bb.ylen > 50


def test_bend_allowance_matches_the_standard_formula():
    fp = _load("flat_patterns")
    m, params = _model()
    d = params["dimensions"]
    ba = fp.bend_allowance(90.0, d["bend_radius_inside"], d["sheet_t"], d["k_factor"])
    assert ba == pytest.approx(6.692, abs=0.002)
    # bend deduction = 2 * outside setback - allowance
    bd = 2 * (d["bend_radius_inside"] + d["sheet_t"]) - ba
    assert bd == pytest.approx(5.308, abs=0.002)


def test_every_bend_is_in_the_bend_table(folded):
    """A bend a shop is not told about is a bend that comes back wrong."""
    fp = _load("flat_patterns")
    rows = fp.bend_table(folded)
    assert rows, f"{folded} has no bend table"
    for r in rows:
        assert r["angle_deg"] == 90
        assert r["inside_radius_mm"] > 0
        assert "line" in r and r["line"]
        assert "direction" in r and r["direction"]


def test_deck_rear_ear_clears_the_shock_wall_bend_line():
    """
    Flat material outboard of a bend line cannot be folded. The ear must start
    past where the walls end, and the model raises if it does not.
    """
    m, params = _model()
    v = params["variants"]["upright_deck"]
    assert v["ear_y_start"] > v["wall_y"][1]

    bad = dict(params)
    bad["variants"] = dict(params["variants"])
    bad["variants"]["upright_deck"] = dict(v, ear_y_start=v["wall_y"][1] - 5.0)
    with pytest.raises(ValueError, match="ear"):
        m.create_upright_deck(bad)


# ---------------------------------------------------------------------------
# The Tile plate is a different animal
# ---------------------------------------------------------------------------
def test_tile_plate_uses_all_six_side_bores():
    m, params = _model()
    iface = _load("interface")
    assert len(iface.TILE_M4_YZ) == 6
    solid = _built("tile_side_plate")
    from lib.analyze_step import _cylinder_features

    holes = [f for f in _cylinder_features(solid.val())
             if f["axis_label"] == "X" and abs(f["diameter"] - 4.5) < 0.1]
    assert len(holes) >= 6


# ---------------------------------------------------------------------------
# The hybrid: Tile core + ONE fin bank
# ---------------------------------------------------------------------------
def test_hybrid_is_the_tile_core_plus_one_measured_fin_bank():
    """
    The hybrid is derived from the vendor file, not invented: the 60 W separates
    into a Tile core and two identical banks at |X| = 14.5. If a future vendor
    file breaks that, the split must fail loudly rather than silently redefine
    what the cold plate is bolted to.
    """
    iface = _load("interface")
    tile = iface.VARIANTS["tile"]["shell_mm3"]
    hybrid = iface.VARIANTS["hybrid_posx"]["shell_mm3"]
    assert hybrid == pytest.approx(tile + iface.FIN_BANK_VOLUME, rel=0.001)
    assert iface.FIN_SPLIT_X == iface.TILE_FACE_X          # same plane, measured twice


def test_hybrid_is_asymmetric_in_x_and_the_handedness_is_explicit():
    iface = _load("interface")
    pos, neg = iface.VARIANTS["hybrid_posx"], iface.VARIANTS["hybrid_negx"]
    assert (pos["x_min"], pos["x_max"]) == (-14.5, 36.5)
    assert (neg["x_min"], neg["x_max"]) == (-36.5, 14.5)
    assert pos["fin_sides"] == ("+X",) and neg["fin_sides"] == ("-X",)
    assert iface.flat_side_x("hybrid_posx") == -iface.flat_side_x("hybrid_negx")


def test_a_hybrid_keeps_only_the_fin_bank_it_has():
    """
    A keep-out list that names both banks on a one-bank chassis would forbid the
    flat side — which is the whole reason the hybrid is worth mounting.
    """
    iface = _load("interface")
    assert set(iface.keepouts("hybrid_posx")) & {"fin_bank_neg_x"} == set()
    assert "fin_bank_pos_x" in iface.keepouts("hybrid_posx")
    assert "fin_bank_neg_x" in iface.keepouts("hybrid_negx")
    assert "fin_bank_pos_x" not in iface.keepouts("hybrid_negx")
    assert "fin_bank_pos_x" not in iface.keepouts("tile")


def test_finned_chassis_have_no_flat_side_to_bolt_to():
    """Asking for one should raise, not return a fin bank's tips."""
    iface = _load("interface")
    for v in ("60w", "30w"):
        with pytest.raises(ValueError, match="no flat side"):
            iface.flat_side_x(v)


def test_cold_plate_is_solid_where_the_tile_plate_is_skeletal():
    """
    The hybrid gave up a whole fin bank. The plate that replaces it has to be a
    heat path, so it may not be lightened — if someone adds windows to save
    240 g they have quietly deleted the reason the variant exists.
    """
    m, params = _model()
    cold = params["variants"]["hybrid_cold_plate"]
    assert "windows" not in cold
    assert params["variants"]["tile_side_plate"]["windows"]
    assert cold["plate_t"] > params["variants"]["tile_side_plate"]["plate_t"]
    # solid stock minus only the holes: a windowed plate would be far lighter
    t, (y0, y1), (z0, z1) = cold["plate_t"], cold["plate_y"], cold["plate_z"]
    stock = (y1 - y0) * (z1 - z0) * t
    assert _built("hybrid_cold_plate").val().Volume() > 0.94 * stock
    # and the border is extra conducting area, not a bracket tab
    assert (y1 - y0) * (z1 - z0) > 1.4 * 20410.1


def test_cold_plate_border_bolts_are_reachable_with_the_unit_fitted():
    """
    The point of the border. v2's plate stopped 1.5 mm outboard of the chassis
    flat, so its only host interface was blind tapped holes — fine for a VESA arm,
    useless for bolting it flat to a plate you cannot reach behind. Every border
    bolt head must land clear of the chassis flat.
    """
    m, params = _model()
    iface = _load("interface")
    v = params["variants"]["hybrid_cold_plate"]
    head_r = params["fasteners"]["hybrid_border"]["head_d"] / 2
    assert v["border_holes"], "the cold plate has no through bolts at all"
    for hy, hz in v["border_holes"]:
        assert abs(hy) - head_r > iface.TILE_SIDE_FLAT_Y, (
            f"border bolt at (Y {hy}, Z {hz}) puts its head over the chassis flat")
    # and the plate has to be wide enough to carry them
    y0, y1 = v["plate_y"]
    assert min(-y0, y1) - iface.TILE_SIDE_FLAT_Y >= 12.0


def test_cold_plate_refuses_a_border_it_cannot_reach():
    """Shrink the plate back to v2's outline and the build must stop."""
    m, params = _model()
    v = params["variants"]["hybrid_cold_plate"]
    bad = dict(params)
    bad["variants"] = dict(params["variants"])
    bad["variants"]["hybrid_cold_plate"] = dict(
        v, plate_y=[-66.0, 66.0], border_holes=[[-60.0, 80.0], [60.0, 80.0]])
    with pytest.raises(ValueError, match="nowhere to put a through bolt"):
        m.create_hybrid_cold_plate(bad)


def test_border_bolts_go_all_the_way_through():
    """
    A blind hole here would defeat the point: these are the ones a bolt passes
    through from the unit side into the host.
    """
    from lib.analyze_step import _cylinder_features

    m, params = _model()
    bolt = params["fasteners"]["hybrid_border"]
    t = params["variants"]["hybrid_cold_plate"]["plate_t"]
    holes = [f for f in _cylinder_features(_built("hybrid_cold_plate").val())
             if f["axis_label"] == "X"
             and abs(f["diameter"] - bolt["clearance_d"]) < 0.1]
    assert len(holes) == len(params["variants"]["hybrid_cold_plate"]["border_holes"])
    for h in holes:
        assert h["length"] >= t - 1e-6, "border bolt hole does not go through"


def test_host_drilling_table_matches_the_plate():
    fp = _load("flat_patterns")
    m, params = _model()
    rows = fp.host_drilling(params)
    holes = {(hy, hz) for hy, hz in params["variants"]["hybrid_cold_plate"]["border_holes"]}
    assert {(r["y_mm"], r["z_mm"]) for r in rows} == holes
    assert all(r["clearance_d_mm"] == params["fasteners"]["hybrid_border"]["clearance_d"]
               for r in rows)


def test_cold_plate_host_taps_never_break_through_the_bearing_face():
    """
    A through-tapped host hole lets an over-length host screw stand proud on the
    face that beds against the chassis — the plate then pivots on a screw tip.
    """
    m, params = _model()
    host = params["fasteners"]["hybrid_host"]
    assert host["tap_drill_depth"] < params["variants"]["hybrid_cold_plate"]["plate_t"]
    bad = dict(params)
    bad["fasteners"] = dict(params["fasteners"],
                            hybrid_host=dict(host, tap_drill_depth=6.0))
    with pytest.raises(ValueError, match="breaks through"):
        m.create_hybrid_cold_plate(bad)


def test_cold_plate_features_do_not_run_into_one_another():
    """The guard that caught two M5 taps sitting inside an 8.4 mm countersink."""
    m, params = _model()
    v = params["variants"]["hybrid_cold_plate"]
    bad = dict(params)
    bad["variants"] = dict(params["variants"])
    # a border bolt dragged inboard onto one of the chassis countersinks
    bad["variants"]["hybrid_cold_plate"] = dict(
        v, border_holes=[[-74.0, -10.0], [74.0, -10.0], [-74.0, 80.0],
                         [74.0, 80.0], [-74.0, 170.0], [-60.0, 12.0]])
    with pytest.raises(ValueError, match="apart but need|over the chassis flat"):
        m.create_hybrid_cold_plate(bad)


def test_cold_plate_screw_stays_inside_the_side_bore_limit():
    m, params = _model()
    iface = _load("interface")
    f = params["fasteners"]["hybrid_m4"]
    length = float(f["screw"].split("x")[1].split()[0])
    assert length - f["grip"] == pytest.approx(f["engagement"])
    assert f["engagement"] <= iface.TILE_M4_MAX_PENETRATION
    bad = dict(params)
    bad["fasteners"] = dict(params["fasteners"],
                            hybrid_m4=dict(f, screw="M4x12 countersunk 90deg A4-70"))
    with pytest.raises(ValueError, match="per side"):
        m.create_hybrid_cold_plate(bad)


def test_tile_pattern_is_not_carried_onto_the_finned_chassis():
    """
    The 6x M4 side pattern exists ONLY on the Tile. A bracket that assumed it
    generalised would find bare fin tips on a 30 W or 60 W unit.
    """
    m, params = _model()
    assert "tile" in params["variants"]["tile_side_plate"]["description"].lower()
    for other in ("upright_deck", "upright_bulkhead", "low_profile_side"):
        text = params["variants"][other]["description"].lower()
        assert "6x m4" not in text
    # ...but the hybrid's flat side IS a Tile core face, so it does have them
    assert "tile core" in params["variants"]["hybrid_cold_plate"]["description"].lower()


# ---------------------------------------------------------------------------
# The vendor file's trap
# ---------------------------------------------------------------------------
def test_three_chassis_variants_are_distinguished_by_measured_half_width():
    """
    The vendor STEP superimposes three chassis at one origin. Selecting them by
    solid order would be a coin flip; selecting by half-width is a fact.
    """
    iface = _load("interface")
    halves = {k: v["half_x"] for k, v in iface.VARIANTS.items()
              if not k.startswith("hybrid")}
    assert halves == {"60w": 36.5, "30w": 22.5, "tile": 14.5}
    assert len(set(halves.values())) == 3


def test_fin_banks_are_recorded_as_present_on_both_sides():
    """
    Both +X and -X are live fin banks on the 30 W and 60 W, mirror-identical.
    A design that shadows "the back one" has misread the part.
    """
    iface = _load("interface")
    ko = iface.keepouts("60w")
    assert "fin_bank_pos_x" in ko and "fin_bank_neg_x" in ko
    pos, neg = ko["fin_bank_pos_x"], ko["fin_bank_neg_x"]
    assert pos[1] == pytest.approx(-neg[0])
    assert pos[0] == pytest.approx(-neg[1])
    assert "tile" not in iface.FIN            # the Tile has no fins at all
