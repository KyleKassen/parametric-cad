"""
The role guards, attacked.

A role is a claim about what a part IS FOR, and every relaxation a rubric makes
has to be paid for by that claim holding on the measured B-rep. These tests are
the executable half of that bargain: one per way a claim was accepted on
geometry that contradicts it, plus the structural rule that a role which relaxes
something a part can be wrong about must declare a guard at all.

The escapes reproduced here, each measured on this repo before it was closed:

1. **A SOLID MACHINED SLAB claimed `sheet`.** `sheet` is the one shipped rubric
   that excludes ``sharp_edge_length``, and a role exclusion is the only thing
   that removes a rubric floor - so a 200 x 120 x 12 milled slab declaring
   `sheet` took that floor from UNMET to never emitted. The guard read stock
   thickness only as a FRACTION of the part (10.18 mm on a 200 mm part is 5%,
   comfortably inside). Measured: knife-edged, 44.5/D honest against 68.4/D as
   sheet; with its top face broken, 70.3/B honest against 89.2/A as sheet.

2. **A FLAT KNIFE-EDGED BLANK claimed `sheet`.** The guard's "and it has to be
   formed" test counted any small blend radius, so four plan-radiused corners
   milled into an unformed 220 x 140 x 4 blank read as bends: accepted, 68.7
   with the floor gone against 47.4 honestly. A bend is a coaxial PAIR of
   cylinders separated by the material thickness, and the blank has none.

3. **A SLAB claimed `structural`.** ``max(bbox) / min(bbox)`` is satisfied by any
   thin slab, so a 200 x 150 x 42 slab measured 4.76 against a bar of 4.0 and
   collected the relaxed proportion and emptiness knots: 14.4 honest, 21.3 as a
   long member.

4. **A MILLED TRAY claimed `sheet`.** "Coaxial, one stock apart" is arithmetic,
   and the derived stock is an average, so any constant-wall tray can be walked
   onto the coincidence by choosing its wall. Measured on a 200 x 120 x 5 tray
   with a 1 mm pocket inset 4 mm, outer plan R8 against pocket R4: four "bends",
   46.2/D honest with the ``edge_break_coverage`` floor UNMET, 75.3/B as `sheet`
   with every floor met and ``sharp_edge_length`` never emitted - a hard gate
   failure converted into a clean pass.

5. **A BAR claimed `cover`.** ``min(bbox) / max(bbox)`` is satisfied by anything
   slender, and `cover` and `plate` DROP ``proportion``, which is a max/min
   ratio - so a bar is exactly the shape that profits. Measured: a 300 x 40 x 30
   bar 80.0/B to 90.5/A, a 400 x 60 x 40 bar 79.8 to 91.0/A, and the repo's own
   153 x 90 x 34 scaffold 86.0/B to 91.1/A.

6. **A THIN COVER claimed `bracket`.** `bracket` dropped ``proportion`` on a
   claim about its INTERIOR, which says nothing about proportion. Measured on a
   160 x 100 x 6 lid: +14.7 to band A. Fixed on the rubric rather than the
   guard - `bracket` no longer drops it.

All six are the same defect, and the last three were found only after the rule
was stated: A GUARD MUST MEASURE EVERYTHING ITS ROLE RELAXES. Section 4 is that
rule made executable over relaxations ENUMERATED FROM THE RUBRIC, so a seventh
instance cannot be added silently.

Units: mm throughout.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import lib.design_review as dr  # noqa: E402
from lib.design_review import (  # noqa: E402
    DEFAULT_ROLE,
    ROLE_GUARDS,
    ROLE_RUBRICS,
    ROLES,
    RUBRIC_FLOORS,
    Rubric,
    Topology,
    check_role_claim,
    review_shape,
    rubric_relaxations,
)

# --------------------------------------------------------------------------- #
# geometry: the adversaries, and one genuinely formed control
# --------------------------------------------------------------------------- #


def milled_slab(length=200.0, width=120.0, thick=12.0, corner=8.0) -> cq.Shape:
    """A solid milled slab: plan-radiused outline, knife edges, drilled."""
    body = cq.Workplane("XY").rect(length, width).extrude(thick).edges("|Z").fillet(corner)
    pts = [(x, y) for x in (-30.0, 30.0) for y in (-20.0, 20.0)]
    return body.faces(">Z").workplane().pushPoints(pts).hole(6.6).val()


def knife_blank(length=220.0, width=140.0, thick=4.0, corner=8.0) -> cq.Shape:
    """Thin enough to be sheet stock, but flat: no bend anywhere on it."""
    body = cq.Workplane("XY").rect(length, width).extrude(thick).edges("|Z").fillet(corner)
    pts = [(x, y) for x in (-75.0, -25.0, 25.0, 75.0) for y in (-45.0, 0.0, 45.0)]
    return body.faces(">Z").workplane().pushPoints(pts).hole(6.6).val()


def formed_angle(depth=110.0, base=110.0, up=40.0, t=2.0, ri=3.0) -> cq.Shape:
    """
    A real formed part: one 90 degree bend in 2 mm stock, inner ri, outer ri + t.

    Built as an extruded section rather than by filleting a solid, because that
    is how the bend gets its two coaxial faces - which is the thing the guard
    reads. A late fillet on 2 mm walls is also what the kernel refuses.
    """
    ro = ri + t
    k = 0.7071
    sec = (
        cq.Workplane("XZ")
        .moveTo(-base, 0.0)
        .lineTo(-ro, 0.0)
        .threePointArc((-ro + ro * k, ro - ro * k), (0.0, ro))
        .lineTo(0.0, up)
        .lineTo(-t, up)
        .lineTo(-t, ro)
        .threePointArc((-ro + ri * k, ro - ri * k), (-ro, t))
        .lineTo(-base, t)
        .close()
        .extrude(depth)
    )
    return sec.val().translate((0, depth / 2, 0))


def milled_tray(length=200.0, width=120.0, thick=5.0, corner=8.0, wall=4.0, depth=1.0) -> cq.Shape:
    """
    THE D1 ADVERSARY, and an entirely unremarkable part.

    A solid milled tray whose pocket is inset by roughly its own derived stock,
    so the pocket's corner fillets are concentric with the outline's plan radii
    and one thickness smaller. Every arithmetic test for a bend passes on it.
    """
    body = cq.Workplane("XY").box(length, width, thick).edges("|Z").fillet(corner)
    pocket = (
        cq.Workplane("XY")
        .workplane(offset=thick / 2 - depth)
        .rect(length - 2 * wall, width - 2 * wall)
        .extrude(depth + 1)
        .edges("|Z")
        .fillet(corner - wall)
    )
    body = body.cut(pocket).faces(">Z").chamfer(0.4)
    pts = [(x, y) for x in (-70.0, -25.0, 25.0, 70.0) for y in (-45.0, 45.0)]
    return body.faces("<Z").workplane().pushPoints(pts).hole(6.0).val()


def corner_window_plate(length=200.0, width=120.0, thick=5.0, corner=10.0, inset=4.56) -> cq.Shape:
    """
    The tray's failure mode was unequal axial extents. This is the fake built to
    have EQUAL ones: a nearly solid plate with a small THROUGH window whose
    fillet is concentric with a plan corner and one derived stock smaller, so
    both cylinders span the full 5 mm and coincide over all of it.

    `inset` is the fixed point of "inset = the derived stock this produces",
    reached by iterating on the exported solid: 4.70 -> 4.56 -> 4.56.
    """
    body = cq.Workplane("XY").box(length, width, thick).edges("|Z").fillet(corner)
    ri = corner - inset
    cx, cy = length / 2 - corner, width / 2 - corner
    win = (
        cq.Workplane("XY")
        .moveTo(cx + ri - 60.0, cy + ri - 45.0)
        .rect(60.0, 45.0, centered=False)
        .extrude(thick + 4, both=True)
        .edges("|Z")
        .fillet(ri)
    )
    return body.cut(win).val()


def chunky_box(length=120.0, width=100.0, thick=90.0) -> cq.Shape:
    """A plain solid body: vast empty faces, not thin, not long, not a shell."""
    return cq.Workplane("XY").box(length, width, thick).val()


def long_bar(length=300.0, width=40.0, thick=30.0, corner=4.0) -> cq.Shape:
    """The D2 adversary: slender against its thinnest side, a bar in every other."""
    body = cq.Workplane("XY").box(length, width, thick).edges("|Z").fillet(corner)
    body = body.faces(">Z").chamfer(0.6).faces("<Z").chamfer(0.6)
    return body.faces(">Z").workplane().rarray(75.0, 1, 4, 1).hole(6.0).val()


def wide_slab(length=300.0, width=250.0, thick=20.0) -> cq.Shape:
    """Long against its thinnest side (15.0) and a slab against its section (1.2)."""
    return cq.Workplane("XY").box(length, width, thick).val()


def shell_box(length=120.0, width=90.0, thick=60.0, wall=3.0) -> cq.Shape:
    """A housing: mostly inside, which is what `bracket` claims not to be."""
    body = cq.Workplane("XY").box(length, width, thick).edges("|Z").fillet(6.0)
    return body.faces(">Z").shell(-wall).val().Solids()[0]


def _round_trip(shape: cq.Shape, tmp_path: Path, name: str) -> cq.Shape:
    """Export and re-import: the review reads the artifact, never the builder."""
    out = tmp_path / f"{name}.step"
    cq.exporters.export(cq.Workplane(obj=shape), str(out))
    return cq.importers.importStep(str(out)).val()


@pytest.fixture(scope="module")
def slab_topo(tmp_path_factory) -> Topology:
    tmp = tmp_path_factory.mktemp("guards")
    return Topology(_round_trip(milled_slab(), tmp, "slab"))


@pytest.fixture(scope="module")
def blank_topo(tmp_path_factory) -> Topology:
    tmp = tmp_path_factory.mktemp("guards")
    return Topology(_round_trip(knife_blank(), tmp, "blank"))


@pytest.fixture(scope="module")
def formed_topo(tmp_path_factory) -> Topology:
    tmp = tmp_path_factory.mktemp("guards")
    return Topology(_round_trip(formed_angle(), tmp, "formed"))


# --------------------------------------------------------------------------- #
# 1. a solid slab is not sheet metal
# --------------------------------------------------------------------------- #
def test_a_solid_machined_slab_cannot_claim_sheet(slab_topo):
    """12 mm of plate is 5% of a 200 mm part, and it is still not sheet metal."""
    why = dr._guard_sheet(slab_topo)
    assert why is not None, "a solid 12 mm milled slab was accepted as sheet metal"
    assert "plate rather than sheet" in why


def test_the_slabs_stock_thickness_is_what_gives_it_away(slab_topo):
    """The fraction test passes it; the absolute one is what refuses it."""
    size = max(slab_topo.bbox_size())
    t = slab_topo.sheet_thickness
    assert t < dr.SHEET_THICKNESS_MAX_FRACTION * size
    assert t > dr.SHEET_STOCK_MAX_MM


def test_a_refused_sheet_claim_does_not_remove_the_sharp_edge_floor(slab_topo, tmp_path):
    """
    The consequence that makes this a blocker rather than a scoring quibble.

    `sheet` is the only rubric that drops `sharp_edge_length`, so an accepted
    claim takes that floor out of the report entirely. On geometry that
    contradicts the claim the floor has to come back, unmet.
    """
    shape = _round_trip(milled_slab(), tmp_path, "slab")
    rep = review_shape(shape, source="test", config={"role": "sheet", "min_score": 70})
    assert rep.get("role_error"), "the sheet claim was honoured on a solid machined slab"
    # Re-judged under the fallback rubric, which is the only one that asserts
    # nothing about the geometry and so is the only one that cannot be wrong.
    assert rep["role"] == dr.DEFAULT_ROLE
    floors = {f["metric"]: f["met"] for f in rep["floors"]}
    assert floors["sharp_edge_length"] is False
    assert "sharp_edge_length" in rep["floor_failures"]


# --------------------------------------------------------------------------- #
# 2. a flat blank is not a formed part
# --------------------------------------------------------------------------- #
def test_plan_radii_on_a_flat_blank_are_not_bends(blank_topo):
    """`formed_radii` counts them; `bend_pairs` is the one that knows better."""
    assert blank_topo.formed_radii() >= 1
    assert blank_topo.bend_pairs() == 0
    why = dr._guard_sheet(blank_topo)
    assert why is not None and "no bend at all" in why


def test_a_milled_slabs_plan_corners_are_not_bends_either(slab_topo):
    assert slab_topo.formed_radii() >= 1
    assert slab_topo.bend_pairs() == 0


def test_a_genuinely_formed_part_still_passes(formed_topo):
    """The guard has to refuse the fakes without refusing sheet metal."""
    assert formed_topo.sheet_thickness < dr.SHEET_STOCK_MAX_MM
    assert formed_topo.bend_pairs() >= 1
    assert dr._guard_sheet(formed_topo) is None


def test_a_bend_is_read_as_a_coaxial_pair_one_material_apart(formed_topo):
    """The measurement itself, not just its verdict: inner ri, outer ri + t."""
    t = formed_topo.sheet_thickness
    assert t == pytest.approx(2.0, abs=0.25)
    radii = sorted(
        rec["radius"]
        for i, rec in enumerate(formed_topo.faces)
        if rec["kind"] == "cylinder" and formed_topo.is_blend_face(i)
    )
    assert any(abs(b - a - t) < dr.BEND_THICKNESS_TOL * t for a in radii for b in radii if b > a)


def test_the_exclusion_cannot_launder_a_badly_designed_formed_part(tmp_path):
    """
    The other half of the bargain. An HONESTLY formed part passes the guard, so
    the `sheet` rubric is applied - and it must still measure the design. Same
    blank, same single bend, only the layout differs: one hole size on one pitch
    at one inset against seven scattered holes in three sizes.
    """

    def _fuse(tools):
        out = tools[0]
        for s in tools[1:]:
            out = out.fuse(s)
        return out

    t, base, depth, up = 2.0, 110.0, 110.0, 40.0
    good = cq.Workplane(obj=formed_angle())
    tools = [
        cq.Workplane("XY").center(x, y).circle(2.75).extrude(6 * t).val().translate((0, 0, -2 * t))
        for x in (-92.0, -62.0, -32.0)
        for y in (-30.0, 30.0)
    ]
    tools += [
        cq.Workplane("YZ")
        .center(y, 22.0)
        .circle(2.75)
        .extrude(6 * t)
        .val()
        .translate((-3 * t, 0, 0))
        for y in (-30.0, 30.0)
    ]
    trim = (
        cq.Workplane("XY")
        .center(-base / 2, 0.0)
        .rect(base + 2 * t, depth)
        .extrude(up + 4 * t)
        .edges("|Z")
        .fillet(6.0)
        .val()
        .translate((0, 0, -2 * t))
    )
    good_shape = good.val().cut(_fuse(tools)).intersect(trim)

    scatter = [
        (-95.0, -41.0, 2.6),
        (-77.0, 13.0, 4.1),
        (-52.0, -8.0, 3.3),
        (-38.0, 44.0, 2.6),
        (-23.0, -31.0, 5.2),
        (-64.0, 37.0, 3.3),
        (-88.0, 6.0, 4.1),
    ]
    bad_shape = (
        cq.Workplane(obj=formed_angle())
        .val()
        .cut(
            _fuse(
                [
                    cq.Workplane("XY")
                    .center(x, y)
                    .circle(r)
                    .extrude(6 * t)
                    .val()
                    .translate((0, 0, -2 * t))
                    for x, y, r in scatter
                ]
            )
        )
    )

    reps = {}
    for name, shape in (("good", good_shape), ("bad", bad_shape)):
        rt = _round_trip(shape, tmp_path, name)
        assert dr._guard_sheet(Topology(rt)) is None, f"the {name} control is honestly formed"
        reps[name] = review_shape(rt, source=name, config={"role": "sheet"})
        assert not reps[name].get("role_error")
    assert reps["good"]["score"] - reps["bad"]["score"] > 10.0, (
        f"the sheet exclusion laundered a badly designed formed part: "
        f"good={reps['good']['score']} bad={reps['bad']['score']}"
    )


# --------------------------------------------------------------------------- #
# 2b. a milled pocket is not a bend either
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def tray_topo(tmp_path_factory) -> Topology:
    tmp = tmp_path_factory.mktemp("guards")
    return Topology(_round_trip(milled_tray(), tmp, "tray"))


@pytest.fixture(scope="module")
def corner_window_topo(tmp_path_factory) -> Topology:
    tmp = tmp_path_factory.mktemp("guards")
    return Topology(_round_trip(corner_window_plate(), tmp, "cornerwin"))


def test_a_milled_pocket_concentric_with_the_outline_is_not_a_bend(tray_topo):
    """
    The pocket wall was chosen to equal the derived stock, so the pocket corners
    and the plan corners are coaxial and one thickness apart. Every arithmetic
    test passes; the part has still never been near a press brake.
    """
    assert tray_topo.sheet_thickness < dr.SHEET_STOCK_MAX_MM
    assert tray_topo.formed_radii() >= 4
    assert tray_topo.bend_pairs() == 0
    why = dr._guard_sheet(tray_topo)
    assert why is not None and "no bend at all" in why


def _coaxial_pairs_one_stock_apart(topo: Topology) -> list[tuple[int, int]]:
    """Every pair that satisfies the ARITHMETIC of a bend, before the two tests
    that ask whether it is one."""
    t = topo.sheet_thickness
    cyls = [
        (i, rec)
        for i, rec in enumerate(topo.faces)
        if rec["kind"] == "cylinder" and rec["axis"] is not None and rec["radius"]
    ]
    out = []
    for a, (i, ri) in enumerate(cyls):
        for j, rj in cyls[a + 1 :]:
            if not dr._same_axis(ri["axis"], rj["axis"]):
                continue
            if abs(abs(ri["radius"] - rj["radius"]) - t) > dr.BEND_THICKNESS_TOL * t:
                continue
            out.append((i, j))
    return out


def test_the_trays_two_corners_do_not_span_the_same_bend(tray_topo):
    """
    The measurement, not the verdict. A fold runs the full width of what it
    joins; the tray's plan corner runs the plate's full thickness and its pocket
    corner only the pocket's depth, so they merely overlap.
    """
    pairs = _coaxial_pairs_one_stock_apart(tray_topo)
    assert pairs, "the tray no longer even satisfies the arithmetic - test is moot"
    unequal = 0
    for i, j in pairs:
        span_i = tray_topo.axial_span(i, tray_topo.faces[i]["axis"])
        span_j = tray_topo.axial_span(j, tray_topo.faces[j]["axis"])
        length_i, length_j = span_i[1] - span_i[0], span_j[1] - span_j[0]
        short, long_ = min(length_i, length_j), max(length_i, length_j)
        no_flange = tray_topo.bend_flange(i) is None or tray_topo.bend_flange(j) is None
        assert short < dr.BEND_EXTENT_MIN_RATIO * long_ or no_flange, (
            f"faces {i}/{j} span {length_i:.1f} and {length_j:.1f} mm and both reach a flange"
        )
        unequal += short < dr.BEND_EXTENT_MIN_RATIO * long_
    assert unequal, "the extent test caught none of them, so it is not what refuses the tray"


def test_a_through_window_with_equal_extents_is_still_not_a_bend(corner_window_topo):
    """
    The next fake along, and the reason the extent test is not enough on its own:
    cut the window THROUGH and both cylinders span the whole blank, so extent and
    overlap are perfect. What it does not have is a flange - both cylinders run
    out into the 5 mm thickness band of the plate, which is the geometric way of
    saying the axis is normal to the sheet rather than in its plane.
    """
    topo = corner_window_topo
    t = topo.sheet_thickness
    paired = []
    for i, ri in enumerate(topo.faces):
        for j, rj in enumerate(topo.faces):
            if j <= i or ri["kind"] != "cylinder" or rj["kind"] != "cylinder":
                continue
            if ri["axis"] is None or rj["axis"] is None or not ri["radius"] or not rj["radius"]:
                continue
            if not dr._same_axis(ri["axis"], rj["axis"]):
                continue
            if abs(abs(ri["radius"] - rj["radius"]) - t) > dr.BEND_THICKNESS_TOL * t:
                continue
            paired.append((i, j))
    assert paired, "the fake did not even produce a coaxial pair one stock apart"
    for i, j in paired:
        span_i = topo.axial_span(i, topo.faces[i]["axis"])
        span_j = topo.axial_span(j, topo.faces[j]["axis"])
        length_i, length_j = span_i[1] - span_i[0], span_j[1] - span_j[0]
        assert min(length_i, length_j) >= dr.BEND_EXTENT_MIN_RATIO * max(length_i, length_j)
        assert topo.bend_flange(i) is None and topo.bend_flange(j) is None
    assert topo.bend_pairs() == 0
    assert dr._guard_sheet(topo) is not None


def test_a_real_bend_runs_out_into_a_flange(formed_topo):
    """The other side of it: on a fold, both faces of the pair reach flat stock."""
    t = formed_topo.sheet_thickness
    found = False
    for i, rec in enumerate(formed_topo.faces):
        if rec["kind"] != "cylinder" or rec["axis"] is None or not rec["radius"]:
            continue
        flange = formed_topo.bend_flange(i)
        if flange is None:
            continue
        found = True
        assert formed_topo.faces[flange]["width"] >= dr.BEND_FLANGE_MIN_STOCK * t
    assert found, "no face of a genuinely formed part reaches a flange"
    assert formed_topo.bend_pairs() >= 1


def test_the_tray_cannot_launder_its_own_floor_failure(tmp_path):
    """
    Why this was a blocker. Honestly the tray fails the `edge_break_coverage`
    floor, which is hard at every severity; as `sheet` its whole blanked
    perimeter left the population and the floor was met.
    """
    shape = _round_trip(milled_tray(), tmp_path, "tray")
    claimed = review_shape(shape, source="t", config={"role": "sheet", "min_score": 70})
    assert claimed.get("role_error"), "the sheet claim was honoured on a milled tray"
    assert claimed["role"] == DEFAULT_ROLE
    assert "edge_break_coverage" in claimed["floor_failures"]
    assert claimed["metrics"]["sharp_edge_length"]["status"] == dr.SCORED


# --------------------------------------------------------------------------- #
# 3. a slab is not a long member
# --------------------------------------------------------------------------- #
def _bbox_shape(x: float, y: float, z: float) -> cq.Shape:
    return cq.Workplane("XY").box(x, y, z).val()


@pytest.mark.parametrize(
    "dims,ok",
    [
        ((200.0, 150.0, 42.0), False),  # a slab: long only against its thinnest side
        ((200.0, 45.0, 25.0), True),  # a member: long against its whole section
    ],
)
def test_guard_long_wants_a_member_not_a_slab(dims, ok, tmp_path):
    topo = Topology(_round_trip(_bbox_shape(*dims), tmp_path, "member"))
    why = dr._guard_long(topo)
    assert (why is None) is ok, why or "a 200 x 150 x 42 slab was accepted as a long member"
    if not ok:
        assert "slab rather than a long member" in why


def test_a_refused_structural_claim_is_re_judged_as_an_enclosure(tmp_path):
    shape = _round_trip(_bbox_shape(200.0, 150.0, 42.0), tmp_path, "slab_structural")
    claimed = review_shape(shape, source="t", config={"role": "structural"})
    honest = review_shape(shape, source="t", config={"role": "enclosure"})
    assert claimed.get("role_error")
    assert claimed["role"] == dr.DEFAULT_ROLE
    assert claimed["score"] == honest["score"]


# --------------------------------------------------------------------------- #
# 3b. a bar is not a lid, and a lid is not a bracket
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "dims,ok,note",
    [
        ((300.0, 40.0, 30.0), False, "a 300 x 40 x 30 bar"),
        ((400.0, 60.0, 40.0), False, "a 400 x 60 x 40 bar"),
        # parts/_template's own bounding box. The guard reads nothing else, so a
        # box of the scaffold's size is an exact stand-in for the scaffold here;
        # measured on the scaffold itself, 86.0/B honest against 91.1/A as cover.
        ((153.0, 90.0, 34.0), False, "the repo's scaffold"),
        ((160.0, 58.5, 27.0), False, "the corpus's structural arm"),
        ((150.0, 110.0, 12.5), True, "the corpus's cover reference"),
        ((180.0, 130.0, 12.0), True, "the corpus's plate reference"),
    ],
)
def test_guard_thin_wants_a_lid_not_a_bar(dims, ok, note, tmp_path):
    topo = Topology(_round_trip(_bbox_shape(*dims), tmp_path, "thin"))
    why = dr._guard_thin(topo)
    assert (why is None) is ok, why or f"{note} was accepted as thin by function"
    if not ok:
        assert "SECOND longest" in why


def test_bracket_no_longer_drops_proportion():
    """
    D3, fixed on the rubric rather than the guard: "solid material, not a shell"
    is a claim about the interior area fraction and bounds no bbox ratio, so the
    only honest fix was to stop excusing a metric nothing was measuring.
    """
    assert "proportion" in ROLE_RUBRICS["bracket"].weights
    assert "drop:proportion" not in rubric_relaxations(ROLE_RUBRICS["bracket"])
    assert sum(ROLE_RUBRICS["bracket"].weights.values()) == pytest.approx(1.0)


def test_a_thin_lid_gains_far_less_from_claiming_bracket(tmp_path):
    """The measured consequence: 160 x 100 x 6, which scored 0 on proportion and
    used simply not to be asked."""
    lid = cq.Workplane("XY").box(160.0, 100.0, 6.0).edges("|Z").fillet(8.0)
    lid = lid.faces(">Z").chamfer(0.8).faces("<Z").chamfer(0.8)
    pts = [(x, y) for x in (-65.0, 0.0, 65.0) for y in (-38.0, 38.0)]
    drilled = lid.faces(">Z").workplane().pushPoints(pts).hole(5.5).val()
    shape = _round_trip(drilled, tmp_path, "lid")
    honest = review_shape(shape, source="t", config={"role": DEFAULT_ROLE})
    claimed = review_shape(shape, source="t", config={"role": "bracket"})
    assert not claimed.get("role_error"), "a solid lid genuinely is not a shell"
    assert claimed["metrics"]["proportion"]["status"] == dr.SCORED
    assert claimed["score"] - honest["score"] < 8.0, (
        f"claiming bracket is still worth {claimed['score'] - honest['score']:+.1f}"
    )


# --------------------------------------------------------------------------- #
# 4. the structural rule: a guard must measure everything its role relaxes
# --------------------------------------------------------------------------- #
#
# The rule that took three audits to state and a fourth to enforce. Sections 1-3
# are six instances of one defect: a rubric took something off the table and the
# guard that was supposed to pay for it measured something else, or nothing.
#
# The enumeration side of this is MECHANICAL - `rubric_relaxations` derives it
# from the rubric - because every previous version of this check read the guards
# and asked whether they looked sufficient, which is how `bracket` kept dropping
# `proportion` through two passes that both concluded the roles were sound.
#
# Each (role, relaxation) needs a PROBE: a part the relaxation would help and the
# claim does not fit. The test asserts both halves, so a probe cannot pass by
# being irrelevant. Adding a role, or adding an exclusion to one, changes the
# enumeration and fails here until a probe exists.
# The parenthesised number is what that one relaxation was measured to be worth
# on that probe, priced by `_single_relaxation_rubric` on 2026-07-27. They are
# recorded because their SIZE is the finding: `bracket` has almost nothing left
# to steal, `cover` has a lot.
RELAXATION_PROBES: dict[tuple[str, str], tuple[str, object]] = {
    # `proportion` is max/min of the bbox. Only a role whose guard PINS that
    # ratio may drop it: `_guard_thin` forces max/min >= 4 and `_guard_sheet`
    # forces >= 10 through its absolute stock bar. A bar is slender without
    # being thin, which is exactly the part that profits.
    ("cover", "drop:proportion"): ("long_bar", long_bar),  # +2.6
    ("plate", "drop:proportion"): ("long_bar", long_bar),  # +2.6
    ("sheet", "drop:proportion"): ("milled_slab", milled_slab),  # +3.3
    # The emptiness knots are paid for by the claim that the part's big faces
    # are not free product surfaces: thin stock for `cover`/`plate`/`sheet`, a
    # long section for `structural`, solid material for `bracket`. A bar and a
    # chunky body contradict the first four; a SHELL - which is what `bracket`
    # says it is not - contradicts the last.
    ("cover", "relax:void_knots"): ("long_bar", long_bar),  # +6.5
    ("plate", "relax:void_knots"): ("long_bar", long_bar),  # +1.6
    ("sheet", "relax:void_knots"): ("milled_slab", milled_slab),  # +7.6
    ("structural", "relax:void_knots"): ("chunky_box", chunky_box),  # +2.4
    # +0.7, and that is the whole of it: a shell's faces are so far past both
    # knot sets that they score near zero under either, so what `bracket` still
    # relaxes is worth well under a point to the one shape its claim excludes.
    ("bracket", "relax:void_knots"): ("shell_box", shell_box),  # +0.7
    # A wider proportion knot is paid for by being long. A 300 x 250 x 20 slab
    # is long only against its thinnest side (15.0), and 1.2 against its section.
    ("structural", "relax:proportion_knots"): ("wide_slab", wide_slab),  # +4.5
    # Dropping a FLOORED metric, and deleting a whole edge population, are both
    # paid for by "2 mm stock cannot carry a chamfer on its blanked outline".
    # 12 mm plate carries one perfectly well.
    ("sheet", "drop:sharp_edge_length"): ("milled_slab", milled_slab),  # +1.6
    ("sheet", "exclude:blank_perimeter"): ("milled_slab", milled_slab),  # +3.1
}


def _single_relaxation_rubric(role: str, relaxation: str) -> Rubric:
    """
    The default rubric with EXACTLY ONE of `role`'s relaxations applied.

    Scoring a probe under this and under the default prices that one relaxation
    on its own, which is what makes the probe demonstrably relevant rather than
    merely refused. Dropping a metric renormalises the rest, which is what the
    real rubrics do - a role may excuse a metric, never lighten the total bar.
    """
    default = ROLE_RUBRICS[DEFAULT_ROLE]
    role_rubric = ROLE_RUBRICS[role]
    weights = dict(default.weights)
    void = default.void_knots
    proportion = default.proportion_knots
    blank = default.exclude_blank_perimeter
    if relaxation.startswith("drop:"):
        dropped = weights.pop(relaxation.split(":", 1)[1])
        scale = 1.0 / (1.0 - dropped)
        weights = {k: v * scale for k, v in weights.items()}
    elif relaxation == "relax:void_knots":
        void = role_rubric.void_knots
    elif relaxation == "relax:proportion_knots":
        proportion = role_rubric.proportion_knots
    elif relaxation == "exclude:blank_perimeter":
        blank = role_rubric.exclude_blank_perimeter
    else:  # pragma: no cover - the enumeration grew a case this cannot build
        raise AssertionError(f"no way to build a rubric for relaxation {relaxation!r}")
    return Rubric(
        role=role,
        weights=weights,
        void_knots=void,
        proportion_knots=proportion,
        exclude_blank_perimeter=blank,
        claim=role_rubric.claim,
    )


@pytest.fixture(scope="module")
def probe_shapes(tmp_path_factory) -> dict:
    tmp = tmp_path_factory.mktemp("probes")
    out = {}
    for name, builder in {n: b for n, b in RELAXATION_PROBES.values()}.items():
        out[name] = _round_trip(builder(), tmp, name)
    return out


@pytest.mark.parametrize("role", sorted(r for r in ROLES if r != DEFAULT_ROLE))
def test_a_guard_measures_everything_its_role_relaxes(role, probe_shapes, monkeypatch):
    relaxations = rubric_relaxations(ROLE_RUBRICS[role])
    assert relaxations, f"role {role!r} exists and relaxes nothing - why is it a role?"
    for relaxation in relaxations:
        key = (role, relaxation)
        assert key in RELAXATION_PROBES, (
            f"role {role!r} relaxes {relaxation!r} and no probe proves the guard "
            f"measures it. Add one to RELAXATION_PROBES, or stop relaxing it."
        )
        name, _builder = RELAXATION_PROBES[key]
        shape = probe_shapes[name]

        # 1. the relaxation is worth something to this probe, so refusing it is
        #    not a formality. Priced with the guard lifted and with the role's
        #    OTHER relaxations left out, so this is that one relaxation's value.
        base = review_shape(shape, source=name, config={"role": DEFAULT_ROLE})["score"]
        with monkeypatch.context() as m:
            m.setitem(dr.ROLE_RUBRICS, role, _single_relaxation_rubric(role, relaxation))
            m.setitem(dr.ROLE_DELTA_ALLOWANCE, role, 100.0)
            m.delitem(dr.ROLE_GUARDS, role, raising=False)
            relaxed = review_shape(shape, source=name, config={"role": role})
        assert not relaxed.get("role_error")
        assert relaxed["score"] - base > 0.5, (
            f"probe {name!r} gains only {relaxed['score'] - base:+.2f} from "
            f"{role}/{relaxation}, so it proves nothing about the guard"
        )

        # 2. ... and the guard refuses it.
        topo = Topology(shape)
        why = check_role_claim(role, topo)
        assert why is not None, (
            f"role {role!r} relaxes {relaxation!r}, probe {name!r} takes "
            f"{relaxed['score'] - base:+.1f} points from it, and the guard accepted it"
        )


def test_the_default_role_relaxes_nothing():
    """The fallback rubric is the bar, so it can never be the thing being shopped for."""
    assert rubric_relaxations(ROLE_RUBRICS[DEFAULT_ROLE]) == ()


def test_every_relaxation_probe_is_reachable():
    """No stale entries: a probe for a relaxation no role makes is a dead letter."""
    live = {(role, r) for role in ROLES for r in rubric_relaxations(ROLE_RUBRICS[role])}
    stale = sorted(set(RELAXATION_PROBES) - live)
    missing = sorted(live - set(RELAXATION_PROBES))
    assert set(RELAXATION_PROBES) == live, f"stale: {stale}; missing: {missing}"


def test_every_role_that_drops_a_floored_metric_declares_a_guard():
    """
    A dropped floor is the largest thing a role can be wrong about, so it is the
    one relaxation that may never be taken on a rubric's own say-so.
    """
    droppers: dict[str, set[str]] = {mid: set() for mid in RUBRIC_FLOORS}
    for name, rubric in sorted(ROLE_RUBRICS.items()):
        for mid in RUBRIC_FLOORS:
            if rubric.applies(mid):
                continue
            droppers[mid].add(name)
            assert ROLE_GUARDS.get(name), f"role {name!r} drops {mid} and declares no guard"
            assert rubric.claim, f"role {name!r} drops {mid} and states no claim"
    # and the one that is dropped is dropped by exactly one role, so this stays
    # a fact about the rubric set rather than about whichever role is read first
    assert droppers["edge_break_coverage"] == set()
    assert droppers["sharp_edge_length"] == {"sheet"}


def test_every_role_that_excludes_the_blank_perimeter_declares_a_guard():
    for name, rubric in sorted(ROLE_RUBRICS.items()):
        if rubric.exclude_blank_perimeter:
            assert ROLE_GUARDS.get(name), f"role {name!r} excludes the blanked perimeter unguarded"
            assert rubric.claim


def test_every_role_but_the_default_is_guarded_and_states_its_claim():
    for name, rubric in sorted(ROLE_RUBRICS.items()):
        if name == dr.DEFAULT_ROLE:
            continue
        assert callable(ROLE_GUARDS.get(name)), f"role {name!r} relaxes something unguarded"
        assert rubric.claim, f"role {name!r} states no geometric claim"


# --------------------------------------------------------------------------- #
# 5. the corpus's own role references must survive the tightening
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "case_id,role",
    [
        ("good_sheet_bracket", "sheet"),
        ("good_structural_arm", "structural"),
        ("good_sealed_cover", "cover"),
        ("good_interface_plate", "plate"),
        ("good_machined_bracket", "bracket"),
    ],
)
def test_each_roles_own_reference_still_claims_it(case_id, role):
    """A guard that refuses the case it was calibrated on is not a tightening."""
    from tests.design_corpus import CASES, step_for

    case = next(c for c in CASES if c.id == case_id)
    topo = Topology(cq.importers.importStep(str(step_for(case))).val())
    assert ROLE_GUARDS[role](topo) is None
