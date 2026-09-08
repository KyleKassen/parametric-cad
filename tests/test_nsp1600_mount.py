"""
Tests for the MEAN WELL NSP-1600 mount family.

The parametric invariants - what must stay true when somebody edits a number
in params.json. The heavy geometry (placing the vendor solid and booleaning it
against every variant) lives in the part's own fit_check.py, which lib.evaluate
runs as a gating validator; flat_patterns.py runs as a second one.

Run with: make test  (or: pytest tests/test_nsp1600_mount.py -v)
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PART_DIR = PROJECT_ROOT / "parts" / "custom" / "nsp1600-mount"
VENDOR_DIR = PROJECT_ROOT / "parts" / "vendor" / "meanwell-nsp-1600"

_CACHE: dict = {}


def _load(name: str):
    key = f"mod:{name}"
    if key not in _CACHE:
        if str(PART_DIR) not in sys.path:
            sys.path.insert(0, str(PART_DIR))
        spec = importlib.util.spec_from_file_location(
            f"nsp1600_mount_{name}", PART_DIR / f"{name}.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _CACHE[key] = m
    return _CACHE[key]


def _model():
    if "params" not in _CACHE:
        _CACHE["params"] = _load("model").load_params()
    return _load("model"), _CACHE["params"]


def _built(name: str):
    if name not in _CACHE:
        m, params = _model()
        _CACHE[name] = m.BUILDERS[name](params)
    return _CACHE[name]


@pytest.fixture(params=["side_tab", "bulkhead_strap", "terminal_box",
                        "bulkhead_shelf", "deck_tray", "busbar_hood", "spacer_ring"])
def variant(request):
    return request.param


@pytest.fixture(params=["side_tab", "bulkhead_strap", "bulkhead_shelf", "deck_tray"])
def folded(request):
    return request.param


BENDS = {"side_tab": 1, "bulkhead_strap": 1, "bulkhead_shelf": 2, "deck_tray": 2}


# ---------------------------------------------------------------------------
# Every variant
# ---------------------------------------------------------------------------
def test_builds_and_is_solid(variant):
    solid = _built(variant)
    assert solid.solids().vals(), f"{variant} produced no solids"
    assert solid.val().Volume() > 100.0


def test_single_solid(variant):
    """A bracket in two pieces is a modelling failure, not a two-part design."""
    assert len(_built(variant).val().Solids()) == 1


def test_valid_brep(variant):
    from OCP.BRepCheck import BRepCheck_Analyzer

    assert BRepCheck_Analyzer(_built(variant).val().wrapped).IsValid()


def test_material_and_process_are_stated(variant):
    """Every variant is real hardware - somebody has to make it."""
    _, params = _model()
    v = params["variants"][variant]
    assert v["material"].strip() and v["process"].strip()


def test_sheet_variants_are_one_gauge(variant):
    """No metal variant may quietly need a second thickness."""
    _, params = _model()
    if variant in ("terminal_box", "busbar_hood"):
        return
    bb = _built(variant).val().BoundingBox()
    assert min(bb.xlen, bb.ylen, bb.zlen) >= params["dimensions"]["sheet_t"] - 1e-6


# ---------------------------------------------------------------------------
# The attitude and the frame
# ---------------------------------------------------------------------------
def test_only_the_horizontal_attitude_is_built():
    """
    The datasheet's derating curve is labelled HORIZONTAL and nothing else is
    published. A variant that stood the unit up would be a thermal claim
    nobody can back.
    """
    iface = _load("interface")
    assert iface.QUALIFIED_ATTITUDES == ("horizontal",)
    m, params = _model()
    for name in m.METAL_VARIANTS:
        s = m.channel_stations(params)
        # the unit's bottom face sits on the pan top at Z = 0, bottom down
        assert m.walls_for(params, name)
        assert s["x_tan"] == pytest.approx(iface.HALF_W)
    # v2: the tab foot and the strap shelf both put the unit's bottom on Z = 0
    assert m.tab_stations(params)["leg_tan"] > 0
    assert _built("bulkhead_strap").val().BoundingBox().zmax == pytest.approx(0.0)


def test_vendor_transform_is_a_pure_translation_that_lands_the_body():
    """No rotation anywhere in the frame change, so no mirror is possible."""
    iface = _load("interface")
    analysis = json.loads(
        (VENDOR_DIR / "references" / "NSP-1600_0417_analysis.json").read_text(encoding="utf-8"))
    lo = [a + b for a, b in zip(analysis["bbox_min"], iface.VENDOR_TO_MOUNT)]
    hi = [a + b for a, b in zip(analysis["bbox_max"], iface.VENDOR_TO_MOUNT)]
    assert lo == pytest.approx([-iface.HALF_W, iface.BODY_Y[0], 0.0], abs=0.002)
    assert hi[0] == pytest.approx(iface.HALF_W, abs=0.002)
    assert hi[1] == pytest.approx(iface.BLADES["long"]["y"][1], abs=0.002)
    assert hi[2] == pytest.approx(iface.BODY_Z[1], abs=0.002)


def test_measured_holes_agree_with_the_datasheet_drawing():
    """Case No. 296A: 3-M3 on 70 x 264.7, 16.1 from the terminal end, 7.5 from the
    sides; 2-M4 per side 252 apart, 22.8 above the base, 5.8 from the terminal end."""
    iface = _load("interface")
    (xa, ya), (xb, yb), (xc, yc) = iface.BOTTOM_M3_XY
    assert xb - xa == pytest.approx(70.0, abs=0.05)
    assert ya - yc == pytest.approx(264.7, abs=0.05)
    assert -ya == pytest.approx(16.1, abs=0.05)
    assert iface.HALF_W - xb == pytest.approx(7.5, abs=0.05)
    (y1, z1), (y2, z2) = iface.SIDE_M4_YZ
    assert y1 - y2 == pytest.approx(252.0, abs=0.05)
    assert z1 == z2 == pytest.approx(22.8, abs=0.05)
    assert -y1 == pytest.approx(5.8, abs=0.05)


# ---------------------------------------------------------------------------
# Screw arithmetic
# ---------------------------------------------------------------------------
def test_side_screw_arithmetic_is_checked_not_assumed():
    iface = _load("interface")
    assert iface.check_side_screw(10.0, 6.8) == pytest.approx(3.2)
    with pytest.raises(ValueError):
        iface.check_side_screw(12.0, 6.8)     # 5.2 - past the datasheet's 5.0
    with pytest.raises(ValueError):
        iface.check_side_screw(8.0, 6.8)      # 1.2 - fewer than three threads


def test_bottom_screw_arithmetic_is_checked_not_assumed():
    iface = _load("interface")
    assert iface.check_bottom_screw(6.0, 3.0) == pytest.approx(3.0)
    with pytest.raises(ValueError):
        iface.check_bottom_screw(8.0, 3.0)    # 5.0 - into the PCB
    assert iface.BOTTOM_M3_MAX_PENETRATION < iface.BOTTOM_M3_MEASURED_FREE


def test_fastener_schedule_never_exceeds_a_penetration_limit():
    fp = _load("flat_patterns")
    for row in fp.fastener_schedule():
        if row["max_penetration_mm"] == "" or row["engagement_mm"] == "":
            continue
        assert row["engagement_mm"] <= row["max_penetration_mm"], row["id"]


def test_side_m4_grip_is_washer_plus_wall_plus_ring():
    """The grip in params must be what the geometry actually stacks up."""
    m, params = _model()
    f = params["fasteners"]["side_m4"]
    t = params["dimensions"]["sheet_t"]
    assert f["grip"] == pytest.approx(0.8 + t + t)
    assert f["engagement"] == pytest.approx(float(f["screw"].split("x")[1].split()[0]) - f["grip"])


# ---------------------------------------------------------------------------
# The 3 mm idea
# ---------------------------------------------------------------------------
def test_side_gap_equals_sheet_thickness_equals_bend_radius():
    """
    side_gap = t = Ri is what puts the pan tangent exactly at the unit's corner
    and lets the spacer be a ring from the same sheet. Change any one of the
    three and the unit either rides up the fillet or needs a second thickness.
    """
    m, params = _model()
    d = params["dimensions"]
    assert d["side_gap"] == d["sheet_t"] == d["bend_radius_inside"]
    assert m.channel_stations(params)["x_tan"] == pytest.approx(_load("interface").HALF_W)


def test_spacer_ring_is_one_sheet_thick_and_clears_the_screw():
    m, params = _model()
    v = params["variants"]["spacer_ring"]
    ring = _built("spacer_ring").val().BoundingBox()
    assert ring.zlen == pytest.approx(params["dimensions"]["sheet_t"])
    assert v["id"] >= params["fasteners"]["side_m4"]["clearance_d"]


# ---------------------------------------------------------------------------
# Air paths and live parts
# ---------------------------------------------------------------------------
@pytest.fixture(params=["bulkhead_shelf", "deck_tray"])
def channel(request):
    """The two v1 channels - the folded variants that have walls."""
    return request.param


def test_walls_stop_short_of_both_end_faces(channel):
    iface = _load("interface")
    m, params = _model()
    for w in m.walls_for(params, channel).values():
        if w["y"][0] > params["dimensions"]["pan_y"][0]:
            assert w["y"][1] <= iface.TERMINAL_FACE_Y - 1.0
            assert w["y"][1] < params["variants"]["busbar_hood"]["y"][0]


def test_hood_is_a_plenum_not_a_lid():
    """The hood covers the unit's only intake; it must have more louvre than the unit."""
    iface = _load("interface")
    _, params = _model()
    v = params["variants"]["busbar_hood"]
    tl, sl = v["top_louvres"], v["side_louvres"]
    top = len(tl["x"]) * (tl["y"][1] - tl["y"][0]) * tl["w"]
    side = 2 * len(sl["z"]) * (sl["y"][1] - sl["y"][0]) * sl["w"]
    assert top + side >= 3.0 * iface.LOUVRE_OPEN_AREA


def test_hood_openings_are_finger_safe():
    _, params = _model()
    v = params["variants"]["busbar_hood"]
    assert v["top_louvres"]["w"] <= 12.0 and v["side_louvres"]["w"] <= 12.0
    assert v["led_window"]["x"][1] - v["led_window"]["x"][0] <= 12.0


def test_hood_walls_clear_the_ac_block_and_the_channel():
    iface = _load("interface")
    m, params = _model()
    v = params["variants"]["busbar_hood"]
    s = m.channel_stations(params)
    assert v["x"][0] + v["wall_t"] <= iface.AC_BLOCK["x"][0] - 2.0
    assert v["x"][0] >= -s["x_in"] + 2.0
    assert v["x"][1] <= s["x_out"]
    assert v["z_top"] - v["top_t"] >= iface.BODY_Z[1] + 2.0


def test_hood_cable_slots_do_not_merge_with_the_led_window():
    _, params = _model()
    v = params["variants"]["busbar_hood"]
    lw = v["led_window"]["x"]
    for cs in v["cable_slots"].values():
        assert cs["x"][1] <= lw[0] - 2.0 or cs["x"][0] >= lw[1] + 2.0


# ---------------------------------------------------------------------------
# Host fixings stay reachable
# ---------------------------------------------------------------------------
def test_bulkhead_bolt_heads_clear_the_unit():
    """Heads sit on the flange's inner face, 3 mm from the unit: every bolt must be
    above the unit's top or beyond its ends."""
    iface = _load("interface")
    _, params = _model()
    v = params["variants"]["bulkhead_shelf"]
    head_r = 8.5 / 2
    for y, z in v["bulkhead_holes"] + v["bulkhead_keyholes"]:
        beyond = y - head_r > iface.TERMINAL_FACE_Y or y + head_r < iface.FAN_FACE_Y
        above = z - head_r > iface.BODY_Z[1]
        assert beyond or above, f"bolt at ({y}, {z}) would land on the unit's side"


def test_keyhole_slots_stay_inside_the_flange():
    _, params = _model()
    v = params["variants"]["bulkhead_shelf"]
    f = params["fasteners"]["host_bulkhead"]
    for _, z in v["bulkhead_keyholes"]:
        assert z + 4.0 <= v["flange_h"]                       # material above the slot
        ri = params["dimensions"]["bend_radius_inside"]
        assert z - f["keyhole_slot_len"] - f["keyhole_d"] / 2 > ri


def test_deck_bolts_are_beyond_the_unit_and_clear_of_the_hood():
    iface = _load("interface")
    _, params = _model()
    v = params["variants"]["deck_tray"]
    hood = params["variants"]["busbar_hood"]
    for x, y in v["host_holes"]:
        assert y > iface.TERMINAL_FACE_Y or y < iface.FAN_FACE_Y
        if y > 0:
            assert y - 5.2 > hood["y"][1]


# ---------------------------------------------------------------------------
# Sheet-metal invariants
# ---------------------------------------------------------------------------
def test_bend_allowance_matches_the_standard_formula():
    fp = _load("flat_patterns")
    _, params = _model()
    d = params["dimensions"]
    ba = fp.bend_allowance(90.0, d["bend_radius_inside"], d["sheet_t"], d["k_factor"])
    assert ba == pytest.approx(6.692, abs=0.002)
    assert fp.bend_deduction(90.0, d["bend_radius_inside"], d["sheet_t"], d["k_factor"]) == \
        pytest.approx(5.308, abs=0.002)


def test_folded_variants_develop_into_one_connected_blank(folded):
    fp = _load("flat_patterns")
    _, params = _model()
    blank, legs = fp.develop(folded, params)
    assert len(blank.val().Solids()) == 1
    assert len(legs) == BENDS[folded] + 1
    bb = blank.val().BoundingBox()
    if folded in ("bulkhead_shelf", "deck_tray"):
        y0, y1 = params["dimensions"]["pan_y"]
        assert bb.ylen == pytest.approx(y1 - y0)
    else:
        assert bb.ylen == pytest.approx(params["variants"][folded]["width"])


def test_every_bend_is_in_the_bend_table(folded):
    fp = _load("flat_patterns")
    rows = fp.bend_table(folded)
    assert len(rows) == BENDS[folded]
    for r in rows:
        assert r["angle_deg"] == 90 and r["inside_radius_mm"] > 0


# ---------------------------------------------------------------------------
# v2 - the tab kits
# ---------------------------------------------------------------------------
def test_v2_is_the_default_and_the_tab_is_the_part():
    _, params = _model()
    assert params["version"] == "v2"
    assert params["default_variant"] == "side_tab"
    assert set(params["kits"]) == {"deck_tab_kit", "bulkhead_strap_kit",
                                   "deck_tray_kit", "bulkhead_shelf_kit"}


def test_tab_lies_flush_and_its_bend_clears_the_unit_corner():
    """
    The foot bends OUTWARD, so the fillet is outside the unit's corner: the
    leg's inner face is flush at X = 42.5 and the unit's corner point sits
    outside the bend's outer radius.
    """
    m, params = _model()
    iface = _load("interface")
    s = m.tab_stations(params)
    assert s["leg_in"] == pytest.approx(iface.HALF_W)
    assert s["foot_tan"] > s["leg_out"] > s["leg_in"]
    cx, cz = s["foot_tan"], s["leg_tan"]                 # bend centre
    corner = ((iface.HALF_W - cx) ** 2 + (0.0 - cz) ** 2) ** 0.5
    assert corner >= s["orr"] + 2.0                       # 8.49 vs 6.0
    bb = _built("side_tab").val().BoundingBox()
    assert bb.xmin == pytest.approx(iface.HALF_W)         # nothing inboard of the wall
    assert bb.zmin == pytest.approx(0.0)                  # foot on the deck


def test_tab_is_the_same_part_on_both_sides_and_both_stations():
    m, params = _model()
    tab = _built("side_tab")
    bb = tab.val().BoundingBox()
    assert bb.ymin == pytest.approx(-bb.ymax)             # symmetric about its station
    placed = m.tabs_deck(params)
    assert len(placed.val().Solids()) == 4
    vols = [s.Volume() for s in placed.val().Solids()]
    assert max(vols) - min(vols) < 1e-3


def test_tab_screw_is_flush_arithmetic():
    """grip = washer + tab, nothing else; penetration inside [3.0, 5.0]."""
    _, params = _model()
    iface = _load("interface")
    f = params["fasteners"]["side_m4_tab"]
    assert f["grip"] == pytest.approx(0.8 + params["dimensions"]["sheet_t"])
    length = float(f["screw"].split("x")[1].split()[0])
    assert iface.check_side_screw(length, f["grip"]) == pytest.approx(f["engagement"])


def test_tab_slot_absorbs_the_unit_width_tolerance():
    _, params = _model()
    f = params["fasteners"]["tab_to_host"]
    assert (f["slot_len"] - f["clearance_d"]) / 2 >= 2.0   # +/-0.5 unit, +/-0.5 bend, drilling


def test_strap_bolt_heads_are_below_the_shelf():
    _, params = _model()
    v = params["variants"]["bulkhead_strap"]
    t = params["dimensions"]["sheet_t"]
    for z in v["bolt_z"]:
        assert z + 8.5 / 2 < -t                            # head fully below the shelf
        assert z - 8.5 / 2 > -v["flange_depth"]


def test_strap_carries_the_tab_and_the_box():
    m, params = _model()
    v = params["variants"]["bulkhead_strap"]
    hf = params["fasteners"]["tab_to_host"]
    tab = params["variants"]["side_tab"]
    # the tab's slot, at its station, lands inside the strap's shelf
    assert v["shelf_x_tip"] >= tab["slot_x"] + hf["slot_len"] / 2 + 3.0
    assert -v["station_offset_y"] - tab["width"] / 2 > -v["width"] / 2
    # the box's near screws land on the terminal strap
    box = params["variants"]["terminal_box"]
    near = [xy for xy in box["floor_screws_xy"] if xy[1] < 20]
    assert sorted(near) == sorted(v["box_tap_xy"])
    for x, y in near:
        assert -v["width"] / 2 < y < v["width"] / 2
        assert -m.channel_stations(params)["x_tan"] < x < v["shelf_x_tip"]


def test_strap_shelf_starts_at_the_unit_corner():
    m, params = _model()
    iface = _load("interface")
    bb = _built("bulkhead_strap").val().BoundingBox()
    assert bb.zmax == pytest.approx(0.0)
    assert bb.xmin == pytest.approx(-m.channel_stations(params)["x_out"])
    assert m.channel_stations(params)["x_tan"] == pytest.approx(iface.HALF_W)


def test_box_gap_at_the_unit_is_finger_safe_and_clears_the_tab():
    _, params = _model()
    iface = _load("interface")
    box = params["variants"]["terminal_box"]
    tab = params["variants"]["side_tab"]
    gap = box["y"][0] - iface.TERMINAL_FACE_Y
    assert gap <= 12.0
    assert gap >= iface.SIDE_M4_YZ[0][0] + tab["width"] / 2 + 1.0


def test_box_exits_do_not_run_into_each_other():
    _, params = _model()
    v = params["variants"]["terminal_box"]
    circles = [(e["xz"][0], e["xz"][1], e["d"] / 2) for e in v["exits"].values() if "d" in e]
    rects = [(e["x"], e["z"]) for e in v["exits"].values() if "x" in e]
    rects.append((v["led_window"]["x"], v["led_window"]["z"]))
    for i, (x1, z1, r1) in enumerate(circles):
        for x2, z2, r2 in circles[i + 1:]:
            assert ((x1 - x2) ** 2 + (z1 - z2) ** 2) ** 0.5 >= r1 + r2 + 1.5
        for (rx, rz) in rects:
            dx = max(rx[0] - x1, 0, x1 - rx[1])
            dz = max(rz[0] - z1, 0, z1 - rz[1])
            assert (dx ** 2 + dz ** 2) ** 0.5 >= r1 + 1.0
    (ax, az), (bx, bz) = rects
    apart_x = ax[1] <= bx[0] - 1.0 or bx[1] <= ax[0] - 1.0
    apart_z = az[1] <= bz[0] - 1.0 or bz[1] <= az[0] - 1.0
    assert apart_x or apart_z


def test_box_fixed_openings_are_finger_safe():
    _, params = _model()
    v = params["variants"]["terminal_box"]
    assert v["top_louvres"]["w"] <= 12.0 and v["side_louvres"]["w"] <= 12.0
    assert v["led_window"]["x"][1] - v["led_window"]["x"][0] <= 12.0
    assert v["floor_t"] > 0


def test_box_ears_reach_the_bulkhead_plane_past_the_far_wall():
    m, params = _model()
    v = params["variants"]["terminal_box"]
    bb = _built("terminal_box").val().BoundingBox()
    assert bb.xmin == pytest.approx(-m.channel_stations(params)["x_out"])
    assert v["ears"]["y"][1] > v["y"][1]
    for hy, _ in v["ears"]["hole_yz"]:
        assert hy > v["y"][1]                              # head reachable past the wall


def test_v2_kits_carry_a_fraction_of_the_v1_metal():
    """The whole reason v2 exists."""
    _, params = _model()
    tab = _built("side_tab").val().Volume()
    strap = _built("bulkhead_strap").val().Volume()
    assert 4 * tab < 0.15 * _built("deck_tray").val().Volume()
    assert 2 * strap + 2 * tab < 0.35 * _built("bulkhead_shelf").val().Volume()


def test_fuse_refuses_to_lose_a_piece():
    import cadquery as cq

    m, _ = _model()
    base = cq.Workplane("XY").box(20, 20, 3)
    apart = cq.Workplane("XY").box(20, 20, 3).translate((50, 0, 0))
    with pytest.raises(RuntimeError):
        m.fuse(base, apart, "disconnected block")
