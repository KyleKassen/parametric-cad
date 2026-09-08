"""
Tests for lib/features.py - the design language as parametric builders.

Every public builder is actually executed and the resulting B-rep interrogated:
valid, one solid where one solid is meant, the bbox the caller asked for, and
the measured effect the docstring claims. The guards get the most attention,
because a guard that silently lets a wall through is worse than no guard: a
recess deeper than the wall must RAISE, an unmeasurable wall must RAISE rather
than be assumed thick, and a bolt pattern must come out symmetric and evenly
divided or it is scatter with a nice API.
Run with: make test  (or: pytest tests/)
"""

import math
import sys
import warnings
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import lib.features as F  # noqa: E402
from lib.features import (  # noqa: E402
    FASTENERS,
    STYLE,
    Build,
    BuildOrderError,
    FeatureError,
    Style,
    WallGuardError,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def shape(obj) -> cq.Shape:
    """The single Shape behind a Workplane or result record (never .val())."""
    return F._shape(getattr(obj, "solid", obj))


def bbox(obj):
    return shape(obj).BoundingBox()


def volume(obj) -> float:
    return sum(abs(s.Volume()) for s in shape(obj).Solids())


def assert_solid(obj, label: str, solids: int = 1):
    """Every builder owes us a valid, non-empty solid."""
    s = shape(obj)
    assert s.isValid(), f"{label}: kernel produced an invalid shape"
    assert len(s.Solids()) == solids, f"{label}: expected {solids} solid(s), got {len(s.Solids())}"
    assert volume(obj) > 0.0, f"{label}: zero volume"
    return s


def close(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


def spacings(values):
    """Gaps between consecutive sorted values."""
    v = sorted(values)
    return [b - a for a, b in zip(v, v[1:])]


def assert_even(gaps, label: str, tol: float = 1e-4):
    """A run of holes is rhythm only if every gap is the same."""
    assert gaps, f"{label}: no gaps to measure"
    assert max(gaps) - min(gaps) < tol, f"{label}: ragged spacing {gaps}"
    return gaps[0]


def top_plane(obj, height: float) -> cq.Plane:
    return F._offset_plane(F._as_plane("XY"), dn=height)


# ---------------------------------------------------------------------------
# Style - the ladder selectors
# ---------------------------------------------------------------------------
def test_plan_radius_quantises_to_the_ladder():
    """Similar sizes must land on the SAME rung: that is what makes a family."""
    for size in (20, 40, 60, 100, 140, 200, 400):
        assert STYLE.plan_radius(size) in STYLE.radius_ladder
    assert STYLE.plan_radius(140) == STYLE.plan_radius(155), (
        "a 10% size change must not produce a 10% radius change"
    )
    # monotonic non-decreasing with size
    rungs = [STYLE.plan_radius(s) for s in (20, 40, 60, 100, 140, 200, 400)]
    assert rungs == sorted(rungs)
    assert rungs[0] < rungs[-1]


def test_plan_radius_is_governed_by_the_smaller_dimension_and_capped():
    """A long thin part must not get a radius that eats its width."""
    assert STYLE.plan_radius(100, 10) == STYLE.plan_radius(10), "the smaller plan dimension governs"
    # below the smallest rung the result is capped, not taken off the ladder
    capped = STYLE.plan_radius(6)
    assert capped <= 0.45 * 6 + 1e-9
    assert capped < min(STYLE.radius_ladder)
    for size in (4, 6, 8, 12, 30, 90):
        assert STYLE.plan_radius(size) <= 0.45 * size + 1e-9, (
            f"radius for {size} would degenerate the rounded rectangle"
        )
    with pytest.raises(FeatureError, match="positive size"):
        STYLE.plan_radius(0)


def test_edge_break_ladder_and_wall_clamp():
    assert STYLE.edge_break(200) in STYLE.break_ladder
    assert STYLE.edge_break(20) < STYLE.edge_break(400)
    # a break bigger than 40% of the wall is a knife edge from the other side
    clamped = STYLE.edge_break(200, wall=1.6)
    assert clamped <= 0.4 * 1.6 + 1e-9
    assert clamped < STYLE.edge_break(200)
    with pytest.raises(FeatureError, match="positive size"):
        STYLE.edge_break(-1)


def test_wall_selector_uses_the_process_table():
    assert STYLE.wall("machined-aluminium") == 2.5
    assert STYLE.wall("cast-aluminium") > STYLE.wall("machined-aluminium")
    assert STYLE.wall("machined-aluminium", span=200) == 4.0, "0.02 x 200 span"
    assert STYLE.wall("machined-aluminium", span=10) == 2.5, "nominal is the floor"
    assert STYLE.wall_spec("sheet-metal").minimum == 1.0
    with pytest.raises(FeatureError, match="unknown process"):
        STYLE.wall_spec("unobtainium")


def test_fastener_selectors():
    m4 = STYLE.fastener("M4")
    assert m4 is FASTENERS["M4"]
    assert STYLE.fastener("m4") is m4, "lookup is case-insensitive"
    assert STYLE.fastener(m4) is m4, "a Fastener passes straight through"
    assert m4.min_tap_depth == 8.0
    assert STYLE.pitch("M4") == round(sum(m4.pitch_band) / 2, 1)
    # insets rise with screw size and are rounded to 0.5
    insets = [STYLE.edge_inset(n) for n in ("M3", "M4", "M5", "M6", "M8")]
    assert insets == sorted(insets)
    assert all(close(i * 2, round(i * 2)) for i in insets), "not on a 0.5 grid"
    assert all(
        i >= STYLE.fastener(n).min_edge for i, n in zip(insets, ("M3", "M4", "M5", "M6", "M8"))
    )
    with pytest.raises(FeatureError, match="unknown fastener"):
        STYLE.fastener("M9")


def test_recess_and_frame_selectors():
    assert STYLE.recess(2.5) == round(2.5 * STYLE.recess_depth_fraction, 2)
    assert STYLE.recess(100) == STYLE.recess_depth, "clamped for a thick wall"
    assert STYLE.frame(100) == STYLE.frame_width, "the floor governs a small face"
    assert STYLE.frame(200) == round(200 * STYLE.frame_fraction, 1)
    assert STYLE.frame(200, 60) == STYLE.frame(60), "the smaller dimension governs"


def test_style_is_frozen_hashable_and_copyable():
    assert hash(STYLE) == hash(Style()), "Style must be usable as a cache key"
    tuned = STYLE.tuned(min_wall=0.8, rib_thickness=3.0)
    assert tuned.min_wall == 0.8 and tuned.rib_thickness == 3.0
    assert STYLE.min_wall == 1.6, "tuned() must not mutate the shared STYLE"
    with pytest.raises(Exception):
        STYLE.min_wall = 0.1


# ---------------------------------------------------------------------------
# base solids
# ---------------------------------------------------------------------------
def test_rounded_box_is_never_a_raw_extrusion():
    box = F.rounded_box(120, 80, 40)
    s = assert_solid(box, "rounded_box")
    bb = box.val().BoundingBox()
    assert close(bb.xlen, 120, 1e-6) and close(bb.ylen, 80, 1e-6) and close(bb.zlen, 40, 1e-6)
    assert close(bb.zmin, 0.0, 1e-6), "default is base-at-origin"
    assert volume(box) < 120 * 80 * 40, "plan radii and rim chamfers remove material"
    # the plan radius is IN THE PROFILE: four vertical cylindrical corner faces
    cyls = [f for f in s.Faces() if f.geomType() == "CYLINDER"]
    assert len(cyls) == 4, f"expected 4 corner fillet faces, got {len(cyls)}"


def test_rounded_box_radius_and_break_suppression():
    raw = F.rounded_box(30, 20, 10, radius=0.0, top_break=0.0, bottom_break=0.0)
    assert close(volume(raw), 30 * 20 * 10, 1e-6), "r=0 and no breaks is exactly a box"
    assert len(raw.val().Faces()) == 6
    with_breaks = F.rounded_box(30, 20, 10, radius=0.0)
    assert volume(with_breaks) < volume(raw), "default rim chamfers must cut material"
    centred = F.rounded_box(30, 20, 10, centered=(True, True, True))
    bb = centred.val().BoundingBox()
    assert close(bb.zmin, -5.0, 1e-6) and close(bb.zmax, 5.0, 1e-6)
    with pytest.raises(FeatureError, match="positive height"):
        F.rounded_box(10, 10, 0)


def test_rounded_prism_rounds_an_arbitrary_outline():
    profile = [(0, 0), (60, 0), (60, 20), (20, 20), (20, 50), (0, 50)]
    prism = F.rounded_prism(profile, 10)
    assert_solid(prism, "rounded_prism")
    bb = prism.val().BoundingBox()
    assert close(bb.xlen, 60, 1e-6) and close(bb.ylen, 50, 1e-6) and close(bb.zlen, 10, 1e-6)
    # an L of 60x20 + 20x30 = 1800 mm2 before the corners are taken off
    assert 0.9 * 1800 * 10 < volume(prism) < 1800 * 10
    with pytest.raises(FeatureError, match=">= 3 profile points"):
        F.rounded_prism([(0, 0), (1, 1)], 5)
    with pytest.raises(FeatureError, match="does not fit this outline"):
        F.rounded_prism([(0, 0), (10, 0), (10, 10), (0, 10)], 5, radius=9)


def test_base_flange_corner_holes_are_a_symmetric_frame():
    plate = F.base_flange(140, 100, 10, fastener="M6")
    assert_solid(plate, "base_flange")
    bb = bbox(plate)
    assert close(bb.xlen, 140, 1e-6) and close(bb.ylen, 100, 1e-6) and close(bb.zlen, 10, 1e-6)
    inset = STYLE.edge_inset("M6")
    assert set(plate.points) == {
        (x, y) for x in (-(70 - inset), 70 - inset) for y in (-(50 - inset), 50 - inset)
    }
    assert plate.plane.origin.z == pytest.approx(10.0), "the returned plane sits on the top face"


def test_base_flange_variants_change_geometry_not_validity():
    chamfered = F.base_flange(140, 100, 10, holes="none")
    stepped = F.base_flange(140, 100, 10, edge="step", holes="none")
    assert_solid(chamfered, "flange chamfer")
    assert_solid(stepped, "flange step")
    assert volume(stepped) < volume(chamfered), "a step removes more than a rim chamfer"
    assert close(bbox(stepped).zlen, 10, 1e-6)
    perim = F.base_flange(140, 100, 10, holes="perimeter", fastener="M6")
    assert_solid(perim, "flange perimeter")
    assert len(perim.points) > 4, "a perimeter pattern is more than the four corners"
    assert volume(perim) < volume(chamfered)
    assert F.base_flange(140, 100, 10, holes="none").points == ()
    with pytest.raises(FeatureError, match="positive thickness"):
        F.base_flange(140, 100, 0)
    with pytest.raises(FeatureError, match="edge must be"):
        F.base_flange(140, 100, 10, edge="bevel")
    with pytest.raises(FeatureError, match="holes must be"):
        F.base_flange(140, 100, 10, holes="everywhere")


# ---------------------------------------------------------------------------
# pockets - and the guards, which are the point
# ---------------------------------------------------------------------------
def test_recessed_panel_sizes_itself_from_the_face_and_the_measured_wall():
    slab = F.rounded_box(120, 80, 20)
    pocket = F.recessed_panel(slab, "+Z")
    assert_solid(pocket, "recessed_panel")
    # sized from the face's OWN extents, which the rim chamfer has already
    # narrowed - not from the nominal 120 x 80 of the box
    fu, fv = F._face_extents(slab, F.face_plane(slab, "+Z"), "+Z")
    assert fu < 120.0 and fv < 80.0, "the rim chamfer must shrink the flat top face"
    frame = STYLE.frame(fu, fv)
    assert close(pocket.length, fu - 2 * frame, 1e-6)
    assert close(pocket.width, fv - 2 * frame, 1e-6)
    assert pocket.depth == STYLE.recess(20.0)
    assert close(pocket.wall_before, 20.0, 1e-3), "the wall is MEASURED, not assumed"
    assert close(pocket.wall_after, pocket.wall_before - pocket.depth, 1e-9)
    assert volume(pocket) < volume(slab), "a recess must remove material"
    assert close(bbox(pocket).zlen, 20.0, 1e-6), "a recess must not change the envelope"
    # the returned plane is the pocket FLOOR, +Z out of the part
    assert pocket.plane.origin.z == pytest.approx(20.0 - pocket.depth)
    assert pocket.plane.zDir.z == pytest.approx(1.0)


def test_recessed_panel_refuses_to_breach_the_minimum_wall():
    """The guard is the whole safety story: it must RAISE, not thin the wall."""
    thin = F.rounded_box(60, 40, 3.0)
    with pytest.raises(WallGuardError) as exc:
        F.recessed_panel(thin, "+Z", depth=2.5)
    msg = str(exc.value)
    assert "2.50" in msg and "3.00" in msg and "1.60" in msg, (
        f"the guard must state the numbers, got: {msg}"
    )
    # and the part is untouched: the guard raises before any cut
    assert close(volume(thin), volume(F.rounded_box(60, 40, 3.0)), 1e-6)
    # exactly at the limit it is allowed through
    ok = F.recessed_panel(thin, "+Z", depth=3.0 - STYLE.min_wall)
    assert ok.wall_after == pytest.approx(STYLE.min_wall, abs=1e-6)


def test_lightening_pocket_guard_and_effect():
    member = F.rounded_box(120, 80, 20)
    pocket = F.lightening_pocket(member, "+Z", size=(60, 40), depth=10.0)
    assert_solid(pocket, "lightening_pocket")
    assert close(pocket.wall_after, 10.0, 1e-6)
    assert volume(member) - volume(pocket) > 0.8 * (60 * 40 * 10), (
        "a 60x40x10 pocket should remove most of that volume"
    )
    with pytest.raises(WallGuardError, match="below the"):
        F.lightening_pocket(member, "+Z", size=(60, 40), depth=19.0)


def test_wall_guard_refuses_an_unmeasurable_wall_instead_of_assuming():
    """`None` from wall_at means UNKNOWN. It must never read as 'thick enough'."""
    part = F.rounded_box(40, 30, 10)
    plane = F.face_plane(part, "+Z")
    assert F.wall_at(part, plane) == pytest.approx(10.0, abs=1e-3)
    assert F.wall_at(part, F._offset_plane(plane, du=200.0)) is None
    with pytest.raises(WallGuardError, match="cannot measure the wall"):
        F.recessed_panel(part, plane, size=(10, 10), depth=2.0, center=(200.0, 0.0))


def test_wall_and_min_wall_overrides_are_explicit_escape_hatches():
    part = F.rounded_box(40, 30, 10)
    ok = F.recessed_panel(part, "+Z", size=(20, 15), depth=2.0, wall=10.0)
    assert ok.wall_before == 10.0 and close(ok.wall_after, 8.0, 1e-9)
    deep = F.recessed_panel(part, "+Z", size=(20, 15), depth=8.6, wall=10.0, min_wall=1.0)
    assert deep.wall_after == pytest.approx(1.4, abs=1e-6)
    with pytest.raises(WallGuardError):
        F.recessed_panel(part, "+Z", size=(20, 15), depth=8.6, wall=10.0)


def test_recessed_panel_rejects_a_frame_that_leaves_no_panel():
    slab = F.rounded_box(60, 40, 10)
    with pytest.raises(FeatureError, match="leaves no panel"):
        F.recessed_panel(slab, "+Z", frame=25.0)


# ---------------------------------------------------------------------------
# ribs and fins
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("pattern", ["chevron", "x", "triangulated", "parallel", "diagonal-grid"])
def test_rib_field_fills_its_pocket_and_stays_below_the_face(pattern):
    slab = F.rounded_box(120, 80, 20)
    pocket = F.recessed_panel(slab, "+Z", depth=3.0)
    ribs = F.rib_field(pocket, pattern)
    s = shape(ribs)
    assert s.isValid() and ribs.volume_mm3 > 0.0
    assert close(ribs.height, 3.0 - STYLE.rib_relief, 1e-9)
    bb = s.BoundingBox()
    floor = 20.0 - 3.0
    assert bb.zmin == pytest.approx(floor, abs=1e-6), "ribs must start on the pocket floor"
    assert bb.zmax <= 20.0 - STYLE.rib_relief + 1e-6, "rib crests must stay below the outer face"
    # clipped to the pocket, so it can never spill onto the proud frame
    assert bb.xlen <= pocket.length + 1e-6 and bb.ylen <= pocket.width + 1e-6
    merged = pocket.solid.union(ribs.solid)
    assert F._shape(merged).isValid()
    assert volume(merged) > volume(pocket), "ribs must add material back"


def test_rib_field_error_paths():
    slab = F.rounded_box(120, 80, 20)
    pocket = F.recessed_panel(slab, "+Z", depth=3.0)
    with pytest.raises(FeatureError, match="unknown rib pattern"):
        F.rib_field(pocket, "swirl")
    with pytest.raises(FeatureError, match="rib height"):
        F.rib_field(pocket, "x", relief=5.0)
    with pytest.raises(FeatureError, match="leaves no room"):
        F.rib_field(pocket, "x", margin=200.0)


def test_fin_bank_flat_holds_its_pitch_and_reports_net_area():
    bank = F.fin_bank(height=12, base="flat", length=40, count=8, pitch=6.0)
    assert_solid(bank, "fin_bank flat", solids=8)
    assert bank.count == 8 and bank.pitch == 6.0
    assert close(bank.span, 7 * 6.0, 1e-9)
    assert close(bank.root_area_mm2, 8 * STYLE.fin_thickness * 40, 1e-6)
    assert bank.added_area_mm2 > 0.0, "fins must be a NET gain in wetted area"
    assert bank.added_area_mm2 < shape(bank).Area(), "net gain must be less than raw surface area"
    bb = bbox(bank)
    assert close(bb.xlen, bank.span + STYLE.fin_thickness, 1e-6)
    assert bb.zmin == pytest.approx(-F.EMBED, abs=1e-6), "roots sink below the mounting plane"
    assert bb.zmax == pytest.approx(12.0, abs=1e-6)


def test_fin_bank_solves_count_from_span_and_supports_annular():
    flat = F.fin_bank(height=10, base="flat", length=30, span=60, pitch=6.0)
    assert flat.count == 11 and close(flat.span, 60.0, 1e-9)
    assert close(flat.pitch, 6.0, 1e-9)
    rings = F.fin_bank(height=10, base="cylinder", radius=15, span=60, pitch=6.0)
    assert_solid(rings, "fin_bank cylinder", solids=rings.count)
    assert close(bbox(rings).xlen, 2 * (15 + 10), 1e-3), "fins reach radius + height"
    assert rings.added_area_mm2 > 0.0


def test_fin_bank_error_paths():
    with pytest.raises(FeatureError, match="needs count or span"):
        F.fin_bank(height=10, base="flat", length=20)
    with pytest.raises(FeatureError, match="fins would merge"):
        F.fin_bank(height=10, base="flat", length=20, count=4, pitch=1.0, thickness=2.0)
    with pytest.raises(FeatureError, match="fin base must be"):
        F.fin_bank(height=10, base="hex", length=20, count=4)
    with pytest.raises(FeatureError, match="positive length"):
        F.fin_bank(height=10, base="flat", count=4)


# ---------------------------------------------------------------------------
# louvers - the measurement is the deliverable
# ---------------------------------------------------------------------------
def test_louver_bank_cuts_real_slots_and_measures_its_own_free_area():
    wall = F.rounded_box(80, 60, 4, top_break=0.0, bottom_break=0.0)
    bank = F.louver_bank(wall, "+Z", width=40, height=30, count=4, blade_angle_deg=35.0)
    assert bank.count == 4 and close(bank.pitch, 30 / 4, 1e-9)
    assert 0 < bank.gap < bank.pitch

    cut = wall.cut(bank.cut)
    assert F._shape(cut).isValid()
    assert volume(cut) < volume(wall), "the louver bank must actually open the wall"

    # free area is measured in the plane of the wall, so a slot tilted by `ang`
    # presents gap / cos(ang); the throat is the perpendicular section.
    nominal = 4 * 40 * bank.gap
    assert bank.free_area_mm2 == pytest.approx(nominal / math.cos(math.radians(35.0)), rel=0.02)
    assert bank.throat_area_mm2 == pytest.approx(nominal, rel=0.02)
    assert bank.throat_area_mm2 < bank.free_area_mm2, "the throat is what limits flow"


def test_louver_scallop_and_drip_lip():
    wall = F.rounded_box(80, 60, 4, top_break=0.0, bottom_break=0.0)
    blade = F.louver_bank(wall, "+Z", width=40, height=30, count=4, shape="blade")
    scallop = F.louver_bank(wall, "+Z", width=40, height=30, count=4, shape="scallop", lip=6.0)
    assert blade.add is None
    assert scallop.add is not None and scallop.add.isValid()
    assert scallop.free_area_mm2 < blade.free_area_mm2, (
        "rounder slot ends remove more area than a light corner radius"
    )
    assert F._shape(wall.cut(scallop.cut).union(scallop.add)).isValid()


def test_louver_bank_error_paths():
    wall = F.rounded_box(60, 40, 4)
    with pytest.raises(FeatureError, match="blade_angle_deg"):
        F.louver_bank(wall, "+Z", width=20, height=20, blade_angle_deg=95)
    with pytest.raises(FeatureError, match="shape must be"):
        F.louver_bank(wall, "+Z", width=20, height=20, shape="flap")
    with pytest.raises(FeatureError, match="positive width/height"):
        F.louver_bank(wall, "+Z", width=0, height=20)


# ---------------------------------------------------------------------------
# fastener rhythm - the property the eye reads as "designed"
# ---------------------------------------------------------------------------
def test_perimeter_pattern_is_symmetric_and_evenly_divided():
    bp = F.bolt_pattern("perimeter", length=200, width=140, fastener="M5")
    pts = set(bp.points)
    assert bp.count == len(pts) > 4
    for x, y in pts:
        for mirrored in ((-x, y), (x, -y), (-x, -y)):
            assert any(
                close(mx, mirrored[0], 1e-5) and close(my, mirrored[1], 1e-5) for mx, my in pts
            ), f"({x}, {y}) has no mirror in the pattern"
    inset = STYLE.edge_inset("M5")
    xs = sorted({x for x, _ in pts})
    ys = sorted({y for _, y in pts})
    assert close(xs[0], -(100 - inset), 1e-6) and close(xs[-1], 100 - inset, 1e-6)
    assert close(ys[0], -(70 - inset), 1e-6) and close(ys[-1], 70 - inset, 1e-6)
    # evenly divided: one pitch along each run, and it is what the record claims
    assert assert_even(spacings(xs), "perimeter u") == pytest.approx(bp.pitch, abs=1e-3)
    assert assert_even(spacings(ys), "perimeter v") == pytest.approx(bp.pitch_v, abs=1e-3)
    assert bp.in_band, "the solved pitch should sit in M5's structural band"


def test_grid_and_line_patterns_are_symmetric_and_even():
    grid = F.bolt_pattern("grid", length=200, width=140, fastener="M5")
    xs = sorted({x for x, _ in grid.points})
    ys = sorted({y for _, y in grid.points})
    assert grid.count == len(xs) * len(ys), "a grid must be a full array"
    assert_even(spacings(xs), "grid u")
    assert_even(spacings(ys), "grid v")
    assert close(sum(xs), 0.0, 1e-6) and close(sum(ys), 0.0, 1e-6), "not centred"

    line = F.bolt_pattern("line", length=200, fastener="M5")
    ln = sorted(x for x, _ in line.points)
    assert all(close(y, 0.0) for _, y in line.points)
    assert close(sum(ln), 0.0, 1e-6)
    assert assert_even(spacings(ln), "line") == pytest.approx(line.pitch, abs=1e-3)


def test_circle_pattern_count_is_a_multiple_of_four_and_equally_spaced():
    bp = F.bolt_pattern("circle", diameter=80, fastener="M5")
    assert bp.count % 4 == 0, "an odd bolt circle cannot be symmetric about both axes"
    radii = [math.hypot(x, y) for x, y in bp.points]
    assert all(close(r, 40.0, 1e-6) for r in radii)
    angles = sorted(math.degrees(math.atan2(y, x)) % 360 for x, y in bp.points)
    assert_even(spacings(angles), "bolt circle", tol=1e-3)
    assert bp.pitch == pytest.approx(math.pi * 80 / bp.count, abs=1e-3)
    with pytest.raises(FeatureError, match="positive diameter"):
        F.bolt_pattern("circle")


def test_exact_pitch_holds_the_published_number():
    solved = F.bolt_pattern("line", length=200, target_pitch=40.0, fastener="M6")
    exact = F.bolt_pattern("line", length=200, target_pitch=40.0, fastener="M6", exact_pitch=True)
    assert exact.pitch == 40.0, "an interface pitch is a contract, not a suggestion"
    assert solved.pitch != 40.0, "the default solves for an even division instead"
    assert assert_even(spacings(sorted(x for x, _ in exact.points)), "exact") == 40.0


def test_in_band_reports_rhythm_honestly():
    lo, hi = FASTENERS["M4"].pitch_band
    tight = F.bolt_pattern("line", length=200, target_pitch=lo / 3, fastener="M4", exact_pitch=True)
    assert not tight.in_band, "a zipper of screws must not claim to be in band"
    good = F.bolt_pattern(
        "line", length=200, target_pitch=(lo + hi) / 2, fastener="M4", exact_pitch=True
    )
    assert good.in_band


def test_bolt_pattern_error_paths():
    with pytest.raises(FeatureError, match="unknown bolt pattern kind"):
        F.bolt_pattern("spiral", length=100, width=80)
    with pytest.raises(FeatureError, match="leaves no perimeter"):
        F.bolt_pattern("perimeter", length=10, width=10, fastener="M8")
    with pytest.raises(FeatureError, match="leaves no grid"):
        F.bolt_pattern("grid", length=10, width=10, fastener="M8")
    with pytest.raises(FeatureError, match="leaves no run"):
        F.bolt_pattern("line", length=10, fastener="M8")


# ---------------------------------------------------------------------------
# hardware
# ---------------------------------------------------------------------------
def test_fastener_holes_drill_the_right_hole_for_each_kind():
    # square plan on purpose: corner fillets read as cylinders too, and would
    # blur the check that only the intended drill diameters are present
    land = F.rounded_box(60, 60, 10, radius=0.0, top_break=0.0, bottom_break=0.0)
    pts = ((-20, -20), (20, -20), (-20, 20), (20, 20))
    top = top_plane(land, 10)
    clear = F.fastener_holes(land, pts, plane=top, fastener="M4", kind="clearance")
    cbore = F.fastener_holes(land, pts, plane=top, fastener="M4", kind="cbore")
    tapped = F.fastener_holes(land, pts, plane=top, fastener="M4", kind="tap")
    for label, part in (("clearance", clear), ("cbore", cbore), ("tap", tapped)):
        assert_solid(part, f"fastener_holes {label}")
        assert volume(part) < volume(land)
    assert volume(cbore) < volume(clear), "a counterbore removes more than a through hole"
    assert volume(tapped) > volume(clear), "a blind tap drill removes less than a through hole"

    from lib.analyze_step import _cylinder_features

    m4 = FASTENERS["M4"]
    dias = {round(f["diameter"], 2) for f in _cylinder_features(shape(cbore))}
    assert m4.clearance in dias and m4.cbore_dia in dias, f"got {sorted(dias)}"
    assert {round(f["diameter"], 2) for f in _cylinder_features(shape(tapped))} == {m4.tap_drill}

    assert F.counterbore_at(land, pts, plane=top, fastener="M4").val().isValid()
    assert volume(F.fastener_holes(land, (), plane=top)) == pytest.approx(volume(land))
    with pytest.raises(FeatureError, match="hole kind must be"):
        F.fastener_holes(land, pts, plane=top, kind="drill")


def test_tapped_hole_grid_holds_the_published_pitch_exactly():
    plate = F.rounded_box(200, 150, 12, top_break=0.0, bottom_break=0.0)
    grid = F.tapped_hole_grid(plate, "+Z", pitch=25.0, fastener="M6")
    assert grid.pitch == 25.0 and grid.pitch_v == 25.0, (
        "a grid that quietly came out at 24 mm is a grid nothing bolts to"
    )
    xs = sorted({x for x, _ in grid.points})
    ys = sorted({y for _, y in grid.points})
    assert set(spacings(xs)) == {25.0} and set(spacings(ys)) == {25.0}
    assert close(sum(xs), 0.0, 1e-6) and close(sum(ys), 0.0, 1e-6)
    assert not grid.in_band, "25 mm is deliberately tighter than M6's structural band - and says so"
    assert_solid(grid.solid, "tapped_hole_grid")
    assert volume(grid.solid) < volume(plate)


def test_bosses_build_with_a_revolved_root_fillet_and_a_real_bore():
    m4 = FASTENERS["M4"]
    boss = F.tapped_boss(12, fastener="M4")
    assert_solid(boss, "tapped_boss")
    bb = bbox(boss)
    assert close(bb.zmax, 12.0, 1e-6)
    assert bb.zmin == pytest.approx(-F.EMBED, abs=1e-6), "the boss overlaps its parent"
    assert bb.xlen > m4.boss_dia, "the root fillet flares wider than the boss OD"
    assert volume(boss) < math.pi * (bb.xlen / 2) ** 2 * 12.2, "the bore must be cut"

    stand = F.standoff_boss(10, fastener="M3")
    cbored = F.standoff_boss(10, fastener="M3", counterbore=True)
    assert_solid(stand, "standoff_boss")
    assert volume(cbored) < volume(stand), "the counterbore must remove more"

    with pytest.raises(FeatureError, match="does not fit"):
        F.tapped_boss(5, fastener="M6")


def test_connector_land_gives_a_flat_land_with_its_own_screws():
    body = F.rounded_box(120, 80, 30)
    raised = F.connector_land(body, "+Z", length=40, width=30, raised=2.0, aperture=16.0)
    assert_solid(raised, "connector_land raised")
    assert close(bbox(raised).zlen, 32.0, 1e-6), "a proud land raises the envelope"
    assert raised.plane.origin.z == pytest.approx(32.0)
    assert raised.aperture_area_mm2 == pytest.approx(math.pi * 64, rel=1e-6)
    inset = STYLE.edge_inset("M3")
    assert set(raised.screw_points) == {
        (x, y) for x in (-(20 - inset), 20 - inset) for y in (-(15 - inset), 15 - inset)
    }

    recessed = F.connector_land(body, "+Z", length=40, width=30, raised=-2.0, aperture=(20, 12))
    assert_solid(recessed, "connector_land recessed")
    assert close(bbox(recessed).zlen, 30.0, 1e-6), "a recessed land stays in the envelope"
    assert volume(recessed) < volume(body)
    assert 0 < recessed.aperture_area_mm2 < 20 * 12

    with pytest.raises(FeatureError, match="leaves no room"):
        F.connector_land(body, "+Z", length=8, width=8)
    with pytest.raises(WallGuardError):
        F.connector_land(F.rounded_box(60, 40, 3), "+Z", length=20, width=15, raised=-2.5)


# ---------------------------------------------------------------------------
# transitions
# ---------------------------------------------------------------------------
def test_step_shoulder_is_a_turned_stack_not_a_butt_joint():
    up = F.step_shoulder(30, 60, 20, steps=3)
    assert_solid(up, "step_shoulder widening")
    bb = bbox(up)
    assert close(bb.zlen, 20.0, 1e-6)
    assert bb.xlen < 60.0, "a widening stack only reaches full diameter at the top"
    down = F.step_shoulder(60, 30, 20, steps=3)
    assert_solid(down, "step_shoulder narrowing")
    assert close(bbox(down).xlen, 60.0, 1e-3)
    assert volume(down) > volume(up)
    # more steps means a finer stack, not a different envelope
    assert close(bbox(F.step_shoulder(30, 60, 20, steps=5)).zlen, 20.0, 1e-6)
    with pytest.raises(FeatureError, match="at least one step"):
        F.step_shoulder(30, 60, 20, steps=0)
    with pytest.raises(FeatureError, match="positive height"):
        F.step_shoulder(30, 60, 0)
    with pytest.raises(FeatureError, match="two different diameters"):
        F.step_shoulder(30, 30, 10)


@pytest.mark.parametrize("kind", ["fillet", "cone", "facet"])
def test_blend_transition_kinds_all_build(kind):
    solid = F.blend_transition(60, 40, 20, kind=kind)
    assert_solid(solid, f"blend_transition {kind}")
    bb = bbox(solid)
    assert close(bb.zlen, 20.0, 1e-6)
    assert bb.xlen == pytest.approx(60.0, abs=0.05)
    # a transition must be usable as the joint between a prism and a cylinder
    stack = F.rounded_box(80, 80, 10).union(
        F._wp(F._place(shape(solid), F._offset_plane(F._as_plane("XY"), dn=10)))
    )
    assert F._shape(stack).isValid()
    assert len(F._shape(stack).Solids()) == 1


def test_blend_transition_error_paths():
    with pytest.raises(FeatureError, match="blend kind must be"):
        F.blend_transition(30, 60, 20, kind="swoosh")
    with pytest.raises(FeatureError, match=">= 3 facets"):
        F.blend_transition(30, 60, 20, kind="facet", facets=2)
    with pytest.raises(FeatureError, match="does not fit"):
        F.blend_transition(30, 60, 2)
    with pytest.raises(FeatureError, match="positive height"):
        F.blend_transition(30, 60, 0)


# ---------------------------------------------------------------------------
# sealing and weather
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cord", sorted(F.CORD_TABLE))
def test_every_standard_cord_lands_in_the_sealing_band(cord):
    """ "Sealed" is a claim; squeeze and fill are the proof."""
    groove = F.oring_groove(cord=cord, shape="circle", diameter=60)
    assert 20.0 <= groove.squeeze_pct <= 30.0, f"cord {cord} squeeze {groove.squeeze_pct}%"
    assert 75.0 <= groove.fill_pct <= 85.0, f"cord {cord} fill {groove.fill_pct}%"
    assert groove.cut.isValid() and abs(groove.cut.Volume()) > 0
    assert groove.path_length == pytest.approx(math.pi * 60, rel=1e-6)


def test_oring_groove_rect_cuts_a_closed_loop_in_a_lid():
    lid = F.rounded_box(120, 90, 8, top_break=0.0, bottom_break=0.0)
    groove = F.oring_groove(cord=2.62, shape="rect", length=100, width=70, plane=top_plane(lid, 8))
    sealed = lid.cut(groove.cut)
    assert F._shape(sealed).isValid()
    removed = volume(lid) - volume(sealed)
    assert removed == pytest.approx(
        groove.path_length * groove.groove_width * groove.groove_depth, rel=0.05
    )
    assert groove.groove_width == F.CORD_TABLE[2.62][0]


def test_oring_groove_error_paths():
    with pytest.raises(FeatureError, match="not in the table"):
        F.oring_groove(cord=9.9, shape="circle", diameter=50)
    with pytest.raises(FeatureError, match="groove shape must be"):
        F.oring_groove(shape="oval", length=50, width=40)
    with pytest.raises(FeatureError, match="must exceed width"):
        F.oring_groove(shape="circle", diameter=1.0)
    # a non-standard cord is allowed once the caller supplies the numbers
    custom = F.oring_groove(cord=9.9, shape="circle", diameter=50, groove_width=13.0, depth=7.5)
    assert custom.groove_width == 13.0 and custom.cut.isValid()


def test_drip_edge_sheds_and_has_a_kerf():
    lip = F.drip_edge(length=60, projection=8, thickness=4, shed_deg=8.0)
    assert_solid(lip, "drip_edge")
    bb = bbox(lip)
    assert close(bb.xlen, 60.0, 1e-6)
    assert bb.zlen == pytest.approx(8.0, abs=1e-6), "projection is along the plane normal"
    # isolate the kerf from the edge break (radius=0.0 suppresses the chamfer):
    # the groove that breaks surface tension is 60 x kerf x kerf_depth of material
    kerfed = F.drip_edge(length=60, projection=8, thickness=4, radius=0.0, kerf=1.2, kerf_depth=0.8)
    plain = F.drip_edge(length=60, projection=8, thickness=4, radius=0.0, kerf=0.0, kerf_depth=0.0)
    assert volume(plain) - volume(kerfed) == pytest.approx(60 * 1.2 * 0.8, rel=1e-6)
    assert len(shape(kerfed).Faces()) > len(shape(plain).Faces())
    with pytest.raises(FeatureError, match="positive length/projection/thickness"):
        F.drip_edge(length=0, projection=5)


@pytest.mark.xfail(
    strict=True,
    reason="DEFECT: with a kerf, drip_edge's edges('|X') selector also picks up the four "
    "kerf edges, so the 1.0 mm chamfer is impossible and OCCT raises "
    "'BRep_API: command not done'. The bare `except Exception: pass` swallows it, "
    "so the DEFAULT drip edge (kerf=1.2) ships with entirely unbroken edges - "
    "exactly the knife rim the design language forbids. Fix: chamfer before "
    "cutting the kerf, or select only the four outer edges.",
)
def test_drip_edge_breaks_its_own_edges_by_default():
    default = F.drip_edge(length=60, projection=8, thickness=4)
    unbroken = F.drip_edge(length=60, projection=8, thickness=4, radius=0.0)
    assert volume(default) < volume(unbroken), (
        "the default drip edge must carry the chamfer it asks for"
    )


# ---------------------------------------------------------------------------
# identity marks
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("motif", ["rings", "crosshair", "target"])
def test_emblem_embosses_and_engraves_within_the_relief_limit(motif):
    face = F.rounded_box(80, 60, 10)
    embossed = F.emblem(face, "+Z", motif=motif, diameter=30, relief=0.6)
    assert_solid(embossed, f"emblem {motif}")
    assert bbox(embossed).zmax == pytest.approx(10.6, abs=1e-6)
    assert volume(embossed) > volume(face)

    engraved = F.emblem(face, "+Z", motif=motif, diameter=30, relief=-0.6)
    assert_solid(engraved, f"emblem {motif} engraved")
    assert close(bbox(engraved).zmax, 10.0, 1e-6), "engraving must not grow the envelope"
    assert volume(engraved) < volume(face)


def test_emblem_relief_limit_and_bad_motif():
    face = F.rounded_box(80, 60, 10)
    with pytest.raises(FeatureError, match="exceeds the"):
        F.emblem(face, "+Z", diameter=30, relief=2.0)
    with pytest.raises(FeatureError, match="motif must be"):
        F.emblem(face, "+Z", motif="star")
    with pytest.raises(FeatureError, match="positive diameter"):
        F.emblem(face, "+Z", diameter=0)


def test_text_mark_degrades_instead_of_taking_the_part_with_it(monkeypatch):
    """A font missing on one machine must not fail a whole enclosure."""
    face = F.rounded_box(80, 60, 10)

    def boom(*args, **kwargs):
        raise RuntimeError("no font on this machine")

    monkeypatch.setattr(cq.Workplane, "text", boom)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = F.text_mark(face, "+Z", text="ATAERO")
    assert len(caught) == 1 and issubclass(caught[0].category, RuntimeWarning)
    assert volume(out) == pytest.approx(volume(face), abs=1e-9), (
        "a degraded text mark must leave the part EXACTLY unchanged"
    )
    with pytest.raises(FeatureError, match="failed"):
        F.text_mark(face, "+Z", text="ATAERO", strict=True)


def test_text_mark_embosses_when_the_font_is_available():
    face = F.rounded_box(80, 60, 10)
    marked = F.text_mark(face, "+Z", text="ATAERO", size=8, relief=0.6)
    assert_solid(marked, "text_mark")
    if volume(marked) == pytest.approx(volume(face), abs=1e-9):
        pytest.skip("no usable font on this machine - text_mark degraded, as designed")
    assert bbox(marked).zmax == pytest.approx(10.6, abs=1e-6)
    assert volume(marked) > volume(face)
    assert F.text_mark(face, "+Z", text="").val().isValid()


# ---------------------------------------------------------------------------
# face resolution - the ">Z means HIGHEST" gotcha
# ---------------------------------------------------------------------------
def test_face_plane_selectors_and_the_boss_crown_trap():
    base = F.rounded_box(80, 60, 10, top_break=0.0, bottom_break=0.0)
    assert F.face_plane(base, "+Z").origin.z == pytest.approx(10.0)
    assert F.face_plane(base, "+Z").zDir.z == pytest.approx(1.0)
    assert F.face_plane(base, "-Z").zDir.z == pytest.approx(-1.0)

    with_boss = base.union(F._shape(F.tapped_boss(15, plane=top_plane(base, 10))))
    assert F.face_plane(with_boss, ">Z").origin.z == pytest.approx(25.0), (
        "'>Z' finds the HIGHEST face - once a boss exists that is its crown"
    )
    assert F.face_plane(with_boss, "+Z").origin.z == pytest.approx(10.0), (
        "'+Z' must stay on the widest +Z-facing face as the part grows features"
    )

    plane = F.face_plane(base, "+Z")
    assert F.face_plane(base, plane) is plane, "a Plane passes straight through"
    with pytest.raises(FeatureError, match="must be a selector"):
        F.face_plane(base, 42)


def test_wall_at_measures_the_real_brep():
    solid = F.rounded_box(100, 60, 20, top_break=0.0, bottom_break=0.0)
    assert F.wall_at(solid, F.face_plane(solid, "+Z")) == pytest.approx(20.0, abs=1e-6)
    shell = cq.Workplane("XY").box(100, 60, 20).faces(">Z").shell(-3)
    assert F.wall_at(shell, F.face_plane(shell, "+Z")) == pytest.approx(3.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Build - the order of operations, mechanically enforced
# ---------------------------------------------------------------------------
def test_build_refuses_to_go_backwards_through_the_phases():
    b = Build(F.rounded_box(60, 40, 20), "stock")
    b.hole(
        lambda s: F.fastener_holes(
            s, ((-15, -10), (15, 10)), plane=top_plane(s, 20), kind="clearance"
        ),
        "screws",
    )
    assert b.phase == "hole"
    with pytest.raises(BuildOrderError, match="cannot run a 'boolean' step after 'hole'"):
        b.boolean(lambda s: s, "too late")
    with pytest.raises(BuildOrderError, match="cannot run a 'pocket' step after 'hole'"):
        b.pocket(lambda s: s, "too late")
    with pytest.raises(BuildOrderError, match="unknown phase"):
        b.step("polish", lambda s: s)
    # break is still ahead of hole, so it is allowed
    b.edge_break(lambda s: s, "no-op")
    assert b.phase == "break"


def test_build_lets_pocket_and_rib_interleave():
    b = Build(F.rounded_box(120, 80, 40), "stock")
    top = b.pocket(lambda s: F.recessed_panel(s, "+Z", frame=12), "top panel")
    b.rib(lambda s: s.union(F.rib_field(top, "x").solid), "top ribs")
    front = b.pocket(lambda s: F.recessed_panel(s, "+Y", frame=10), "front panel")
    b.rib(lambda s: s.union(F.rib_field(front, "parallel").solid), "front ribs")
    assert [name for name, _ in b.stages()] == [
        "stock",
        "top panel",
        "top ribs",
        "front panel",
        "front ribs",
    ]
    assert_solid(b.result, "interleaved build")


def test_build_report_and_stages_protocol():
    b = Build(F.rounded_box(120, 80, 40), "stock")
    pocket = b.pocket(lambda s: F.recessed_panel(s, "+Z", frame=12), "panel")
    b.rib(lambda s: s.union(F.rib_field(pocket, "chevron").solid), "ribs")
    b.hole(
        lambda s: F.counterbore_at(
            s,
            ((-45, -30), (45, -30), (-45, 30), (45, 30)),
            plane=F.face_plane(s, "+Z"),
            fastener="M4",
        ),
        "screws",
    )
    report = b.report()
    assert report["phase"] == "hole"
    assert [st["stage"] for st in report["stages"]] == ["stock", "panel", "ribs", "screws"]
    vols = [st["volume_mm3"] for st in report["stages"]]
    assert vols[1] < vols[0], "the pocket must remove material"
    assert vols[2] > vols[1], "the ribs must add it back"
    assert vols[3] < vols[2], "the counterbores must remove material"
    assert all(st["solids"] == 1 for st in report["stages"]), (
        "no stage may leave the part in disjoint bodies"
    )
    assert report["stages"][-1]["faces"] > report["stages"][0]["faces"]

    # stages() is exactly lib/debug_build.py's protocol
    stages = list(b.stages())
    assert len(stages) == 4
    assert all(isinstance(wp, cq.Workplane) for _, wp in stages)
    assert F._shape(stages[-1][1]).isValid()


def test_build_warns_when_a_stage_leaves_a_loose_body():
    """A shape that only touches the part re-imports as a separate solid."""
    b = Build(F.rounded_box(40, 30, 10, top_break=0.0, bottom_break=0.0), "stock")
    adrift = cq.Workplane("XY").box(6, 6, 6).translate((0, 0, 40))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        b.boolean(lambda s: s.union(adrift), "adrift")
    assert any("disjoint solids" in str(w.message) for w in caught), (
        f"expected a disjoint-solid warning, got {[str(w.message) for w in caught]}"
    )
    assert len(F._shape(b.result).Solids()) == 2


def test_build_accepts_records_with_a_solid_attribute():
    b = Build(F.rounded_box(120, 80, 30), "stock")
    land = b.hole(
        lambda s: F.connector_land(s, "+Z", length=40, width=30, raised=0.0, aperture=12.0),
        "connector",
    )
    assert isinstance(land, F.ConnectorLand), "the record itself comes back"
    assert_solid(b.result, "build from a record")
    assert volume(b.result) < volume(F.rounded_box(120, 80, 30))


# ---------------------------------------------------------------------------
# the whole vocabulary, through the artifact
# ---------------------------------------------------------------------------
def test_composed_part_survives_a_step_round_trip(tmp_path):
    """
    What lib/evaluate.py actually gates on: the EXPORTED artifact. A part built
    from these builders must come back from STEP as one valid solid with the
    same volume - a coplanar tangency that fused into two bodies would show up
    here and nowhere else.
    """
    b = Build(F.rounded_box(120, 80, 40), "stock")
    b.boolean(lambda s: s.union(F.tapped_boss(12, plane=top_plane(s, 40))), "boss")
    pocket = b.pocket(lambda s: F.recessed_panel(s, "+Y", frame=10), "front panel")
    b.rib(lambda s: s.union(F.rib_field(pocket, "chevron").solid), "front ribs")
    b.hole(
        lambda s: F.counterbore_at(
            s,
            ((-45, -30), (45, -30), (-45, 30), (45, 30)),
            plane=F.face_plane(s, "+Z"),
            fastener="M4",
        ),
        "screws",
    )
    built = b.result
    assert_solid(built, "composed part")

    step = tmp_path / "composed.step"
    cq.exporters.export(built, str(step))
    reimported = cq.importers.importStep(str(step)).val()
    assert reimported.isValid()
    assert len(reimported.Solids()) == 1, "the artifact must not contain loose bodies"
    assert abs(reimported.Volume()) == pytest.approx(volume(built), rel=1e-6)
