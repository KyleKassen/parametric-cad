"""
The invariance contract: how the part is held must not change what it measures.

Why this file exists
--------------------
tests/design_corpus.py proves the score puts a set of solids in the right ORDER.
It says nothing about whether the same solid measures the same twice, and this
repo had nothing that did. That gap has already cost it five times, and every
one of those costs is an executable meta-test at the bottom of this file.

THE AXIAL LENGTH. `lib/analyze_step.py` derived a cylindrical feature's axial
`length` from the span of the face's WORLD axis-aligned bounding box projected
onto the axis. That is exact only while the axis lies on a world axis. A D6 hole
through a 10 mm plate measured 10.000 as modelled and 18.303 rotated 77 degrees;
`Topology.cylinder_wrap` divides by that length, so the inflated value pushed a
full through bore under BORE_WRAP_MIN, `_merge_fasteners` discarded every
fastener hole, and feature_composition and pattern_discipline both reported a
plate full of holes as a plate with none - `absent_defect`, 0.0 at full weight,
always FAIL. The square plate below went 64.0/C to 34.5/F for no change to the
part.

THE WORLD RULER. Every dimensional term used to be measured against
`shape.BoundingBox()` and the world mirror planes. Turn the part and the ruler
turned with the room instead of with the part: `symmetry` moved the full 100
points on every probe, `feature_composition` 100 on any part with a hole
pattern, and the overall score up to 27.6. `lib/frame.py` replaced it with a
frame measured from the part's own surfaces, and this file is where that is
asserted rather than asserted-about.

THE TANGENT EDGE. An edge whose two faces meet tangentially has a dihedral of
exactly 0.0 degrees, so the old "which side is the material on" test - a point
inside one face measured against the OTHER face's tangent plane AT THE EDGE -
was identically zero and its sign came out of round-off in the vertex
coordinates. The edge flipped between `smooth_convex` (banks 0.5 * length as
broken) and `smooth_concave` (banks nothing) with orientation AND with position,
and it classified the two runouts of a single press-brake bend differently from
each other at identity. It used to be "bounded" here at 2.0 points, on a probe
set containing no formed sheet part - which is not bounding a defect, it is
failing to test for it. `probe_formed_bracket` is that missing part class: with
the old test restored the score moves 6.80 points, `radius_vocabulary` 35.19 and
`edge_break_coverage` 14.09, and `edge_break_coverage`'s RUBRIC FLOOR flips
between met and unmet on a ONE degree rotation, a TWO degree rotation, a FIVE
degree rotation and a 500 mm translation. Forced each way, the exposure on that
shape is 12.30 points overall and 59.33 on a single metric. Convexity is now
decided a short way OFF the edge, where tangency still has an answer
(`Topology._convex`), and measures 0.0000 over every motion below.

THE AXIS FOLD. An axis line has two directions, and everything that compares one
against another folded them onto one hemisphere first - by the sign of the
component of largest magnitude, with the tie left to `max()`. There is no
largest component on an axis lying at 45 degrees in a plane, which is not an
edge case but the ordinary way a part gets held, so the winner was whichever of
two equal magnitudes the last bit of the arithmetic favoured: the same direction
folded one way from the 4-decimal `dir` `lib/analyze_step.py` stores and the
other way from the face's own full-precision axis. The two differed by a SIGN,
`_point_on_axis` answered False for a feature against its own faces,
`cylinder_wrap` summed no area, and the feature was deleted as an unwrapped
sliver. On this repo's reference enclosure at 45 degrees about Z the review
dropped 20 of 90 feature centres and 19 of 54 screws while the raw cylinder
census stayed BIT-IDENTICAL, and the part scored 90.2 as modelled and 92.6
turned. Every probe here drilled on ONE axis, so not one of them could reach it;
`probe_side_drilled` is that missing part class, and on it the defect is worth
16.90 points overall and 77.31 on feature_composition, all upward. The fold now
falls back to a fixed order inside `analyze_step.DOMINANT_TIE` and every
direction comparison takes the magnitude of the dot product, either of which is
sufficient alone - both are asserted by
test_the_contract_detects_a_round_off_decided_axis_fold.

THE PARTITION. Cutting a face into coplanar pieces does not change the part, and
it is what a boolean leaves behind and what a round trip through another kernel
produces. Every per-face measurement is taken against the face's own extent, so
halving a face halved its largest empty region relative to its own silhouette:
`face_composition` rose by up to 44.2 points and ONLY EVER UPWARD, and
`edge_break_coverage` moved 7.2. The partition is canonicalised before anything
measures it (`design_review._canonical_partition`), and cut-and-refuse now
measures 0.000000 on every probe, every metric and every cutting plane.

What is asserted
----------------
ROTATION, TRANSLATION and RE-PARTITION are all contracted hard, per metric, on
nine probes covering the part classes each defect actually lives in - prismatic,
plate, tapered, turned, FORMED SHEET, thin cover, MULTI-AXIS DRILLED, handed -
over 13 rotations including 1, 2, 5 and 10 degree ones and three oblique axes,
five translations out to (5000, -5000, 5000) mm, and EVERY ONE OF THE 65 PAIRS
of the two. That cross product replaced a single hand-picked rotation-plus-
translation case, which is one sample of an interaction rather than a test of
it; the fold defect above showed at 45 degrees paired with all five offsets and
at none of the other twelve rotations, so a contract that got to choose the pair
could have missed it exactly as this one did.

Measured worst case over that whole matrix - 9 probes x 87 cases, on the
in-memory solid:

    every metric except face_composition   0.000000 points   EXACT
    face_composition                       0.405028 points   tapered_arm at z45
    the overall score                      0.100000 points   turned_hub at z1
    re-partition, everything                0.000000 points   EXACT

`face_composition` is the only term that is not exact, and its cause is named:
its largest-empty-circle term is a numerical search over a grid sampled on each
face, and the grid does not land in the same places on a face that has been
turned. It is bounded at INEXACT_METRIC_TOL rather than excused.

UNIFORM SCALE is deliberately NOT contracted here; it is the corpus's business
and the several absolute-millimetre thresholds are a separate open question.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import lib.analyze_step as analyze_step  # noqa: E402
import lib.design_review as design_review  # noqa: E402
import lib.frame as frame_module  # noqa: E402
from lib.design_review import review_shape, review_step  # noqa: E402
from lib.frame import Frame, reference_frame  # noqa: E402

#: Points the overall score may move under any rigid motion or re-partition.
#: Measured worst case 0.1000, on tapered_arm under rotation.
RIGID_TOL = 0.5

#: Points a single metric's sub-score may move. Measured worst case 0.000000 for
#: every metric except the one named below, on every probe and every motion.
RIGID_METRIC_TOL = 0.5

#: The ONE metric that is not exact under rigid motion, with the reason and the
#: measured worst case. `face_composition`'s largest-empty-circle term is a
#: numerical search over a grid sampled on each face, and the grid does not land
#: in the same places on a face that has been turned. Measured worst case
#: 0.405028, on tapered_arm at z45; every other metric measures 0.000000 and is
#: held to that by test_rigid_motion_is_exact_on_every_metric_but_one.
INEXACT_METRICS = {"face_composition"}
INEXACT_METRIC_TOL = 0.5

#: Points a RE-PARTITION may move anything, on any probe, on any metric.
#: Measured worst case 0.000000 - it is exact, and asserted as an equality by
#: test_repartitioning_is_exact.
REPARTITION_TOL = 0.01

#: The frame bases that mean "the part's own surfaces fixed this frame".
#: `lib/frame.py` reports `axis` for a body of revolution, whose single surface
#: direction fixes the axis exactly while the two directions across it come from
#: the biggest off-axis feature the part marks out. Both are measured from the
#: part; `obb` and `world` are not, and a probe landing on one of those is a
#: finding rather than a tolerance - see test_every_probe_measures_in_its_own_frame.
DETERMINED_BASES = ("faces", "axis")


# --------------------------------------------------------------------------- #
# probes - one per part class a defect above actually lives in
# --------------------------------------------------------------------------- #
def probe_plain_box() -> cq.Shape:
    """The degenerate case: three equal-area axis pairs, frame fully ambiguous."""
    return cq.Workplane("XY").box(60, 40, 25).val()


def probe_worked_box() -> cq.Shape:
    """Plan radii, rim chamfers and a four-hole pattern - the ladder's top rung."""
    body = (
        cq.Workplane("XY")
        .rect(60, 40)
        .extrude(25)
        .edges("|Z")
        .fillet(6.0)
        .faces(">Z")
        .chamfer(1.5)
        .faces("<Z")
        .chamfer(1.0)
    )
    return (
        body.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .rect(40, 24, forConstruction=True)
        .vertices()
        .hole(5.0)
        .val()
    )


def probe_square_plate() -> cq.Shape:
    """
    A SQUARE plate with a rectangular hole pattern.

    The nastiest case for any frame that comes from an eigen-decomposition: the
    two in-plane directions carry identical area, so the eigenvectors are
    degenerate and a solver is free to return any pair in the plane. The hole
    pattern is deliberately not square, so an arbitrary in-plane frame would be
    caught by pattern_discipline rather than hidden by symmetry.

    It is also the axial-length repro - four D6 holes through 10 mm of plate -
    and the probe on which one coplanar split used to be worth 44.2 points of
    face_composition.
    """
    return (
        cq.Workplane("XY")
        .rect(80, 80)
        .extrude(10)
        .edges("|Z")
        .fillet(8.0)
        .faces(">Z")
        .chamfer(1.0)
        .faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .rect(56, 30, forConstruction=True)
        .vertices()
        .hole(6.0)
        .val()
    )


def probe_tapered_arm() -> cq.Shape:
    """
    A tapered arm, symmetric about its own centreline.

    Its two flanks each carry more area than either end face, so a frame taken
    from the heaviest surface direction lands 3.6 degrees off the centreline and
    reports a symmetric part as 48% asymmetric. The frame has to fit the whole
    surface population, not pick the biggest face.
    """
    plan = cq.Workplane("XY").polyline([(-80, -30), (80, -20), (80, 20), (-80, 30)]).close()
    return plan.extrude(18).edges("|Z").fillet(8.0).faces(">Z").chamfer(1.2).val()


def probe_turned_hub() -> cq.Shape:
    """
    A round flanged hub with a bore and a bolt circle.

    A body of revolution: every planar face and every cylinder is normal to or
    coaxial with one direction, so the part states its axis exactly and states
    nothing at all about the two directions across it. That is the case
    `lib/frame.py`'s `axis` basis and `_fix_inplane` exist for, and this is the
    probe that keeps them honest.
    """
    body = (
        cq.Workplane("XY")
        .circle(40)
        .extrude(8)
        .faces(">Z")
        .workplane()
        .circle(18)
        .extrude(22)
        .edges("%CIRCLE and >Z")
        .chamfer(1.0)
    )
    return (
        body.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .circle(10)
        .cutThruAll()
        .faces("<Z")
        .workplane(centerOption="CenterOfBoundBox")
        .polarArray(30, 0, 360, 6)
        .hole(6.0)
        .val()
    )


def probe_formed_bracket() -> cq.Shape:
    """
    A 2 mm press-braked angle with ONE R3 inside bend - the tangent-convexity case.

    Four EXACTLY tangent joins: the R3 inner cylinder and the concentric R5 outer
    one each meet their flat leg at a dihedral of 0.0 degrees. The two outer
    runouts carry most of this part's broken-edge budget, so how a tangent edge
    is classified is not a detail here, it IS the metric. With the old convexity
    test restored the score moves 6.80 points and edge_break_coverage's rubric
    floor flips between met and unmet on a one degree rotation - which is why the
    probe set had to contain a formed sheet part before any bound on that defect
    could mean anything. See
    test_the_contract_detects_a_degenerate_tangent_convexity_test.
    """
    thickness, inner_radius = 2.0, 3.0
    leg_a, leg_b, width = 22.0, 18.0, 150.0
    outer_radius = inner_radius + thickness
    cx = cz = inner_radius  # both arcs concentric: a real bend, not two radii
    profile = (
        cq.Workplane("XZ")
        .moveTo(leg_a, 0.0)
        .lineTo(cx, 0.0)
        .radiusArc((0.0, cz), inner_radius)
        .lineTo(0.0, leg_b)
        .lineTo(-thickness, leg_b)
        .lineTo(-thickness, cz)
        .radiusArc((cx, -thickness), -outer_radius)
        .lineTo(leg_a, -thickness)
        .close()
    )
    return profile.extrude(width).faces(">Y").chamfer(0.3).faces("<Y").chamfer(0.3).val()


def probe_thin_cover() -> cq.Shape:
    """
    A 4 mm lid: large plan area, almost no thickness, one recessed panel.

    The thin-wall class. Its whole silhouette is two big faces and a narrow band,
    so `proportion`, `face_composition` and the band exclusions bite here and
    nowhere else, and a face split along the panel edge would be free score if
    the partition were not canonicalised first.
    """
    body = (
        cq.Workplane("XY")
        .rect(120, 80)
        .extrude(4.0)
        .edges("|Z")
        .fillet(10.0)
        .faces(">Z")
        .chamfer(0.8)
    )
    return (
        body.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .rect(96, 56)
        .cutBlind(-1.6)
        .faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .rect(100, 60, forConstruction=True)
        .vertices()
        .hole(4.2)
        .val()
    )


def probe_side_drilled() -> cq.Shape:
    """
    A box drilled on TWO axes: a regular pattern on +Z, an irregular row on +Y.

    The multi-axis class, and the one every probe above was missing. A feature's
    axis is folded onto one hemisphere before anything is compared against it,
    and the fold used to pick the component of largest magnitude - a choice with
    no answer at all when two components are equal, which is exactly what a 45
    degree rotation makes of an axis in that plane. The two foldings of one
    direction then differed by a sign, every coaxial face failed to match its
    own feature, `cylinder_wrap` summed no area, and the whole +Y family was
    dropped as an unwrapped sliver.

    The row on +Y is deliberately IRREGULAR - unequal pitch, unequal heights -
    because a family that is dropped only pays if it was the family costing
    points: with a tidy row here the same defect fires and both metrics stay
    saturated at 100, which is how it would have gone on measuring nothing. As
    built the defect is worth 16.9 points, feature_composition 77.3 and
    pattern_discipline 38.2, all UPWARD - see
    test_the_contract_detects_a_round_off_decided_axis_fold.
    """
    body = (
        cq.Workplane("XY")
        .rect(120, 80)
        .extrude(40)
        .edges("|Z")
        .fillet(6.0)
        .faces(">Z")
        .chamfer(1.2)
        .faces("<Z")
        .chamfer(0.8)
    )
    body = (
        body.faces(">Y")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(-37, -8), (-11, 3), (9, -9), (31, 7), (41, -2)])
        .hole(5.0)
    )
    return (
        body.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .rect(90, 50, forConstruction=True)
        .vertices()
        .hole(4.2)
        .val()
    )


def probe_handed_bracket() -> cq.Shape:
    """
    A HANDED bracket: no mirror plane, and a hole pattern that is not symmetric.

    Every other probe here is mirror-symmetric about at least one frame plane, so
    `symmetry` reads 100 on all of them and a defect in how the mirror planes are
    chosen would be invisible. This one is deliberately left-handed, which is
    also the case where a frame that flipped an axis sign would show up as a
    score change rather than as nothing.
    """
    plan = (
        cq.Workplane("XY")
        .polyline([(-45, -25), (45, -25), (45, 10), (10, 10), (10, 25), (-45, 25)])
        .close()
    )
    body = plan.extrude(12).edges("|Z").fillet(4.0).faces(">Z").chamfer(1.0)
    return (
        body.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(-30, -12), (-30, 12), (0, -12), (30, -12)])
        .hole(5.0)
        .val()
    )


PROBES = {
    "plain_box": probe_plain_box,
    "worked_box": probe_worked_box,
    "square_plate": probe_square_plate,
    "tapered_arm": probe_tapered_arm,
    "turned_hub": probe_turned_hub,
    "formed_bracket": probe_formed_bracket,
    "thin_cover": probe_thin_cover,
    "side_drilled": probe_side_drilled,
    "handed_bracket": probe_handed_bracket,
}

#: The probe whose features are drilled on more than one axis, so a defect in
#: how an axis DIRECTION is folded onto one hemisphere has somewhere to show.
#: Named for the same reason TANGENT_PROBE is: a bound is worth nothing measured
#: on a probe that cannot reach the failure.
MULTI_AXIS_PROBE = "side_drilled"

#: The probe that carries exactly-tangent edges as a load-bearing share of its
#: edge budget. Named so the tangent meta-test cannot be pointed at a part that
#: cannot exercise the defect - which is exactly how the old 2.0-point bound came
#: to be written on a probe set with no formed sheet part in it.
TANGENT_PROBE = "formed_bracket"

#: (label, axis, degrees). Rotation about the world origin, with the part left
#: where it is - kept SEPARATE from translation so a failure names which one. The
#: small angles are here because a decision made by round-off does not need a big
#: rotation to flip, and 1 and 2 degrees are where the tangent defect flipped a
#: rubric floor.
ROTATIONS = [
    ("z1", (0, 0, 1), 1.0),
    ("z2", (0, 0, 1), 2.0),
    ("z5", (0, 0, 1), 5.0),
    ("z10", (0, 0, 1), 10.0),
    ("z15", (0, 0, 1), 15.0),
    ("z45", (0, 0, 1), 45.0),
    ("x30", (1, 0, 0), 30.0),
    ("y37", (0, 1, 0), 37.0),
    ("oblique1", (1, 1, 1), 1.0),
    ("oblique5", (1, 1, 1), 5.0),
    ("oblique30", (1, 1, 1), 30.0),
    ("oblique77", (0.3, -0.7, 0.5), 77.0),
    ("oblique131", (-0.6, 0.2, 0.77), 131.0),
]

#: (label, offset mm). An arbitrary offset with no round numbers, then the ones
#: the contract is really about. The far cases move all three coordinates at
#: once, because the defects that live here are functions of coordinate
#: MAGNITUDE rather than of any one axis.
TRANSLATIONS = [
    ("t_awkward", (13.7, -4.2, 91.3)),
    ("t500", (500.0, 0.0, 0.0)),
    ("t_far", (500.0, -500.0, 500.0)),
    ("t_2000", (2000.0, -2000.0, 2000.0)),
    ("t_5000", (5000.0, -5000.0, 5000.0)),
]

#: EVERY rotation with EVERY translation - 13 x 5 = 65 cases, not one.
#:
#: This used to be a single hand-picked pair, and a single pair is not a test of
#: an interaction, it is one sample of one. Two of the defects this file exists
#: for are interactions by construction: `_point_on_axis`'s old reconstructed
#: foot needed a rotation for the oblique direction AND a translation for the
#: magnitude, and neither alone could reach it. The cross product is the only
#: form that cannot be passed by choosing the pair.
COMBINED = [
    (f"{rotation}+{shift}", axis, angle, offset)
    for rotation, axis, angle in ROTATIONS
    for shift, offset in TRANSLATIONS
]

#: Cut the solid on a plane through the origin and fuse the pieces straight back:
#: the same solid with more faces. That is what a boolean leaves behind, what a
#: round trip through another kernel produces, and what an author can do
#: deliberately - and it used to pay.
REPARTITIONS = [("cut_x", "YZ"), ("cut_y", "XZ"), ("cut_z", "XY")]


def _repartition(shape: cq.Shape, plane: str) -> cq.Shape:
    """The same solid, with faces split into coplanar pieces along `plane`."""
    pieces = (
        cq.Workplane(plane).newObject([shape]).split(keepTop=True, keepBottom=True).solids().vals()
    )
    if len(pieces) < 2:
        raise AssertionError(f"the {plane} plane did not split this probe")
    fused = pieces[0]
    for piece in pieces[1:]:
        fused = fused.fuse(piece)
    return fused


def _scores(shape: cq.Shape) -> tuple[float | None, dict[str, float | None], dict[str, str]]:
    report = review_shape(shape)
    scores = {k: v.get("score") for k, v in report["metrics"].items()}
    statuses = {k: v["status"] for k, v in report["metrics"].items()}
    return report["score"], scores, statuses


@pytest.fixture(scope="module")
def measured() -> dict:
    """
    Score every probe under every motion and every re-partition, once.

    Returns {probe: {"basis", "rotation", "translation", "combined",
    "repartition"}}, each a {label: (overall, metrics, statuses)} keyed against
    "identity", which is the probe exactly as built - at the origin, unrotated,
    as the modeller wrote it.
    """
    out: dict[str, dict] = {}
    for name, build in PROBES.items():
        base = build()
        identity = _scores(base)
        rotation = {"identity": identity}
        for label, axis, angle in ROTATIONS:
            rotation[label] = _scores(base.rotate((0, 0, 0), axis, angle))
        translation = {"identity": identity}
        for label, offset in TRANSLATIONS:
            translation[label] = _scores(base.translate(offset))
        combined = {"identity": identity}
        for label, axis, angle, offset in COMBINED:
            combined[label] = _scores(base.rotate((0, 0, 0), axis, angle).translate(offset))
        repartition = {"identity": identity}
        for label, plane in REPARTITIONS:
            repartition[label] = _scores(_repartition(base, plane))
        out[name] = {
            "basis": reference_frame(base).basis,
            "rotation": rotation,
            "translation": translation,
            "combined": combined,
            "repartition": repartition,
        }
    return out


def _metric_tol(metric: str) -> float:
    """How far a sub-score may move, given the metric."""
    return INEXACT_METRIC_TOL if metric in INEXACT_METRICS else RIGID_METRIC_TOL


def _deviations(cases: dict, reference: str = "identity") -> list[tuple[str, str, float]]:
    """(case, metric-or-'overall', absolute deviation) against the reference case."""
    ref_score, ref_metrics, _ = cases[reference]
    out = []
    for label, (score, mets, _) in cases.items():
        if label == reference:
            continue
        if ref_score is not None and score is not None:
            out.append((label, "overall", abs(score - ref_score)))
        for metric, value in mets.items():
            other = ref_metrics.get(metric)
            if value is not None and other is not None:
                out.append((label, metric, abs(value - other)))
    return out


def _assert_invariant(measured: dict, probe: str, motion: str) -> None:
    """The whole contract for one probe under one family of motions."""
    basis = measured[probe]["basis"]
    deviations = _deviations(measured[probe][motion])
    limit = REPARTITION_TOL if motion == "repartition" else RIGID_TOL

    worst_overall = max(
        (d for d in deviations if d[1] == "overall"),
        key=lambda d: d[2],
        default=("none", "overall", 0.0),
    )
    assert worst_overall[2] <= limit, (
        f"{probe} (frame basis {basis!r}): {motion} moved the score by "
        f"{worst_overall[2]:.6f} points ({worst_overall[0]}). The part did not "
        f"change; the ruler did."
    )

    metric_limit = (lambda m: REPARTITION_TOL) if motion == "repartition" else _metric_tol
    bad = [d for d in deviations if d[1] != "overall" and d[2] > metric_limit(d[1])]
    assert not bad, f"{probe} (frame basis {basis!r}): metrics moved under {motion}: " + ", ".join(
        f"{m} by {v:.6f} at {c}" for c, m, v in sorted(bad, key=lambda d: -d[2])[:6]
    )


# --------------------------------------------------------------------------- #
# rotation, translation, and the two together
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("probe", list(PROBES))
def test_rotation_does_not_move_the_measurement(measured, probe):
    _assert_invariant(measured, probe, "rotation")


@pytest.mark.parametrize("probe", list(PROBES))
def test_translation_does_not_move_the_measurement(measured, probe):
    _assert_invariant(measured, probe, "translation")


@pytest.mark.parametrize("probe", list(PROBES))
def test_rotation_and_translation_together_do_not_move_the_measurement(measured, probe):
    _assert_invariant(measured, probe, "combined")


def test_rigid_motion_is_exact_on_every_metric_but_one(measured):
    """
    Seven of the eight metrics measure IDENTICALLY under every rigid motion on
    every probe - not "within tolerance", 0.0 points.

    Stated separately, and as an equality rather than a bound, so RIGID_METRIC_TOL
    can never quietly become the claim. `face_composition` is excepted for one
    written reason (INEXACT_METRICS) and held to its own number by the tests
    above.
    """
    worst = 0.0
    culprit = ""
    for probe, data in measured.items():
        for motion in ("rotation", "translation", "combined"):
            for case, metric, deviation in _deviations(data[motion]):
                if metric in INEXACT_METRICS or metric == "overall":
                    continue
                if deviation > worst:
                    worst, culprit = deviation, f"{probe} {metric} at {motion}/{case}"
    assert worst < 1e-9, f"a rigid motion moved a metric by {worst:.3e} points ({culprit})"


def test_translation_is_exact_on_every_metric(measured):
    """
    A part 500 mm - or 5000 mm - from the origin is the same part, and unlike
    rotation there is not even a re-sampled grid to excuse: EVERY metric,
    including face_composition, measures identically at every offset.
    """
    worst = 0.0
    culprit = ""
    for probe, data in measured.items():
        for case, metric, deviation in _deviations(data["translation"]):
            if deviation > worst:
                worst, culprit = deviation, f"{probe} {metric} at {case}"
    assert worst < 1e-9, f"translation moved a measurement by {worst:.3e} points ({culprit})"


def test_the_tangent_probe_carries_tangent_edges():
    """
    The tangent bound is worth nothing unless the probe it is measured on has
    exactly-tangent edges in the first place.

    This asserts the GEOMETRY rather than a score: probe_formed_bracket must
    present tangent joins on both sides of its bend, and the two runouts of one
    cylinder must agree with each other - which is precisely what the old test
    could not do even at identity, let alone under rotation.
    """
    topo = design_review.Topology(PROBES[TANGENT_PROBE]())
    tangent = [
        e
        for e in topo.edges
        if e.get("angle_deg") is not None and e["angle_deg"] < design_review.SMOOTH_DEG
    ]
    assert len(tangent) >= 4, f"{TANGENT_PROBE} has only {len(tangent)} tangent edges"
    kinds = {e["kind"] for e in tangent}
    assert "smooth_convex" in kinds and "smooth_concave" in kinds, (
        "a formed bend has an outer runout over material and an inner one into a "
        f"corner; this probe classified {sorted(kinds)}"
    )
    by_face: dict[int, list[str]] = {}
    for e in tangent:
        for f in e["faces"]:
            if topo.faces[f]["kind"] == "cylinder":
                by_face.setdefault(f, []).append(e["kind"])
    assert by_face, "no cylindrical face took part in a tangent join"
    for face, found in by_face.items():
        assert len(set(found)) == 1, (
            f"the two runouts of cylindrical face {face} were classified {found} - "
            f"one bend cannot be convex at one end and concave at the other"
        )


# --------------------------------------------------------------------------- #
# re-partition - the same solid cut into more faces
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("probe", list(PROBES))
def test_repartitioning_a_face_does_not_move_the_measurement(measured, probe):
    """
    Splitting a face into coplanar pieces changes nothing about the part.

    It used to be a free score in ONE direction: every per-face measurement is
    taken against the face's own extent, so a halved face has a smaller largest
    empty region relative to its own silhouette and `face_composition` rose - by
    up to 44.2 points. It is also what a round trip through another kernel does,
    so it was an exposure and not only a lever.
    """
    _assert_invariant(measured, probe, "repartition")


def test_repartitioning_is_exact(measured):
    """
    Every probe measures IDENTICALLY re-partitioned - 0.0 points on every metric,
    at every cutting plane. Stated as an equality so REPARTITION_TOL cannot
    become the claim.
    """
    worst = 0.0
    culprit = ""
    for probe, data in measured.items():
        for case, metric, deviation in _deviations(data["repartition"]):
            if deviation > worst:
                worst, culprit = deviation, f"{probe} {metric} at {case}"
    assert worst < 1e-9, f"a re-partition moved a measurement by {worst:.3e} points ({culprit})"


# --------------------------------------------------------------------------- #
# status, frame, and the report of the margin
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("probe", list(PROBES))
@pytest.mark.parametrize("motion", ["rotation", "translation", "combined", "repartition"])
def test_no_motion_changes_a_metric_status(measured, probe, motion):
    cases = measured[probe][motion]
    _, _, reference = cases["identity"]
    for label, (_, _, statuses) in cases.items():
        differing = {k: (reference[k], v) for k, v in statuses.items() if reference[k] != v}
        assert not differing, (
            f"{probe} at {label}: a metric changed status under {motion} "
            f"{differing} - a measurement that becomes unmeasurable when the part "
            f"is moved was never measuring the part."
        )


def test_every_probe_measures_in_its_own_frame(measured):
    """
    The tolerances above are a single ladder with no exemptions in it, and that
    is only defensible while every probe's frame comes from the part.

    If a probe falls back to the oriented bounding box or to the world axes, its
    in-plane direction is no longer a property of the part and the numbers above
    stop meaning what they say - so that is a failing assertion here rather than
    a widened tolerance somewhere else.
    """
    fell_back = {p: d["basis"] for p, d in measured.items() if d["basis"] not in DETERMINED_BASES}
    assert not fell_back, (
        f"these probes no longer measure in a frame their own surfaces fix: {fell_back}. "
        f"The bounds in this file are written for {DETERMINED_BASES}."
    )


def test_every_report_names_the_frame_it_measured_in():
    """
    A score that cannot name its own reference frame is not evidence, so every
    report carries one - and a frame that did not come from the surfaces carries
    its reason.
    """
    for name, build in PROBES.items():
        report = review_shape(build())
        frame = report["shape"]["frame"]
        assert frame["basis"] in ("faces", "axis", "obb", "world"), name
        assert len(frame["size_mm"]) == 3 and len(frame["axes"]) == 3, name
        assert "world_aligned" in frame, name
        if frame["basis"] == "faces":
            assert frame["explained"] >= 0.55, f"{name}: {frame}"
        elif frame["basis"] != "axis":
            assert frame.get("fallback_reason"), (
                f"{name} fell back to the {frame['basis']} basis without saying why"
            )


def test_motion_worst_case_is_reported(measured, capsys):
    """
    Print the measured worst case per metric, so the contract carries numbers and
    not only a pass. A contract nobody can read the margin of gets loosened by
    accident, and this table is the one any claim about this repo's invariance
    has to be copied from.
    """
    rows = []
    for probe, data in measured.items():
        for motion in ("rotation", "translation", "combined", "repartition"):
            for case, metric, deviation in _deviations(data[motion]):
                rows.append((deviation, probe, data["basis"], f"{motion}/{case}", metric))
    rows.sort(reverse=True)
    metric_names = sorted({r[4] for r in rows if r[4] != "overall"})
    with capsys.disabled():
        print("\n  worst deviation per metric, over every probe and every motion (points):")
        for metric in ["overall", *metric_names]:
            hits = [r for r in rows if r[4] == metric]
            worst = max(hits) if hits else (0.0, "-", "-", "-", metric)
            print(f"    {metric:<24}{worst[0]:11.6f}   {worst[1]} {worst[3]}")
        print("  worst 6 over all probes:")
        for deviation, probe, basis, case, metric in rows[:6]:
            print(f"    {deviation:11.6f}  {probe:<15} {basis:<6} {case:<26} {metric}")
    assert rows, "nothing was measured"
    assert rows[0][0] <= max(RIGID_METRIC_TOL, INEXACT_METRIC_TOL), (
        f"a measurement moved {rows[0][0]:.6f} points: {rows[0]}"
    )


# --------------------------------------------------------------------------- #
# the artifact, not the in-memory solid
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("probe", ["square_plate", "formed_bracket"])
def test_invariance_survives_the_step_round_trip(tmp_path, probe):
    """
    The contract above transforms solids in memory, to isolate the scorer from
    export noise. The gate scores exported artifacts, so prove it there too - on
    the probe that carries the axial-length repro and on the one that carries the
    tangent joins.
    """
    base = PROBES[probe]()
    scores = []
    for label, shape in (
        ("as-is", base),
        ("rotated 77 deg", base.rotate((0, 0, 0), (0.3, -0.7, 0.5), 77.0)),
        ("rotated 5 deg", base.rotate((0, 0, 0), (0, 0, 1), 5.0)),
        ("translated", base.translate((500.0, -500.0, 500.0))),
        ("both", base.rotate((0, 0, 0), (0, 1, 0), 37.0).translate((0.0, 0.0, 500.0))),
    ):
        path = tmp_path / f"{label.replace(' ', '-')}.step"
        cq.exporters.export(cq.Workplane("XY").newObject([shape]), str(path))
        scores.append((label, review_step(path)["score"]))
    reference = scores[0][1]
    for label, score in scores[1:]:
        assert abs(score - reference) <= RIGID_TOL, (
            f"{probe}: exported and re-imported, the same part scored "
            f"{reference:.2f} as-is and {score:.2f} {label}"
        )


# --------------------------------------------------------------------------- #
# the meta-tests - each puts one defect back and requires this file to catch it
# --------------------------------------------------------------------------- #
def _legacy_tangent_convexity():
    """
    The pre-2026-07-26 convexity test, as a drop-in for ``Topology._convex``.

    It asks which side the material is on AT the edge, where a tangent join has
    no signal by construction: the probe point lies in the other face's tangent
    plane and the dot product is identically zero, so the sign is whatever
    round-off in the vertex coordinates makes it.
    """

    def _one(self, mid, tangent, fi, other_normal):
        rec = self.faces[fi]
        normal = rec["normal"] if rec["kind"] == "plane" else None
        if normal is None:
            try:
                normal = rec["face"].normalAt(mid)
            except Exception:
                return None
        try:
            step = normal.cross(tangent).normalized()
        except Exception:
            return None
        delta = design_review._clamp(1e-3 * math.sqrt(max(rec["area"], 1e-9)), 1e-4, 0.05)
        for sign in (1.0, -1.0):
            probe = mid + step * (sign * delta)
            if self._on_face(rec["face"], probe):
                return (probe - mid).dot(other_normal) < 0
        return None

    def _legacy(self, mid, tangent, i0, i1):
        n0 = self.faces[i0]["face"].normalAt(mid)
        n1 = self.faces[i1]["face"].normalAt(mid)
        conv = _one(self, mid, tangent, i0, n1)
        if conv is None:
            conv = _one(self, mid, tangent, i1, n0)
        return conv

    return _legacy


def test_the_contract_detects_a_degenerate_tangent_convexity_test(monkeypatch, capsys):
    """
    Put the tangent defect back and require this file to catch it, ON THE PART
    CLASS WHERE IT BITES.

    This is the meta-test the previous version of this file could not have
    written: its probe set had no formed sheet part, so the defect measured 1.87
    points there and was "bounded" at 2.0 - a bound that says nothing, because
    the probes could not reach the failure. On probe_formed_bracket the same
    defect moves the score several points and flips a rubric floor on a one
    degree rotation, and all three of those are asserted here.
    """
    monkeypatch.setattr(design_review.Topology, "_convex", _legacy_tangent_convexity())
    base = PROBES[TANGENT_PROBE]()
    reference = _scores(base)
    identity = review_shape(base)
    floors = {f["met"] for f in identity["floors"] if f["metric"] == "edge_break_coverage"}

    worst_score = 0.0
    worst_metric = (0.0, "", "")
    cases = [(label, base.rotate((0, 0, 0), axis, angle)) for label, axis, angle in ROTATIONS]
    cases.append(("t500", base.translate((500.0, 0.0, 0.0))))
    for label, moved in cases:
        report = review_shape(moved)
        worst_score = max(worst_score, abs(report["score"] - reference[0]))
        floors.update(f["met"] for f in report["floors"] if f["metric"] == "edge_break_coverage")
        for metric, block in report["metrics"].items():
            value, base_value = block.get("score"), reference[1][metric]
            if value is None or base_value is None:
                continue
            if abs(value - base_value) > worst_metric[0]:
                worst_metric = (abs(value - base_value), metric, label)

    with capsys.disabled():
        print(
            f"\n  degenerate tangent test restored on {TANGENT_PROBE}: the score moves "
            f"{worst_score:.2f} points, {worst_metric[1]} moves {worst_metric[0]:.2f} at "
            f"{worst_metric[2]}, and the edge_break_coverage floor reads {sorted(floors)}"
        )
    assert worst_score > RIGID_TOL, (
        "the degenerate tangent test was restored and the score did NOT move "
        f"(worst {worst_score:.3f}) - this contract cannot see the defect it exists for"
    )
    assert worst_metric[0] > RIGID_METRIC_TOL, (
        f"no metric moved past {RIGID_METRIC_TOL} with the defect restored"
    )
    assert len(floors) > 1, (
        "with the defect restored the edge_break_coverage rubric floor should flip "
        "between met and unmet under rotation, and it did not - the probe is no "
        "longer sitting where the defect decides the floor, so the meta-test has "
        "stopped proving what it says it proves"
    )


def _legacy_dominant_fold():
    """
    The pre-2026-07-27 `_canonical_dir`: fold on the component of largest
    magnitude, with the tie left to `max()`.

    There is no largest component on an axis lying at 45 degrees in a plane, so
    the winner was whichever of two equal magnitudes the last bit of the
    arithmetic favoured - and the same direction folded one way from the
    4-decimal `dir` lib/analyze_step.py stores and the other way from the face's
    own full-precision axis.
    """

    def _legacy(d: tuple) -> tuple:
        i = max(range(3), key=lambda k: abs(d[k]))
        return tuple(-c for c in d) if d[i] < 0 else tuple(d)

    return _legacy


def _legacy_sign_locked_point_on_axis():
    """
    The pre-2026-07-27 `_point_on_axis`: fold both directions and require the
    two folds to AGREE IN SIGN, which asks a question about the arithmetic
    rather than about the line.
    """

    def _legacy(point, direction, axis: tuple, tol: float = 0.05) -> bool:
        d_axis, foot = axis
        folded = design_review._canonical_dir(tuple(direction))
        if sum(x * y for x, y in zip(folded, d_axis)) < 0.999:
            return False
        w = tuple(p - f for p, f in zip(point, foot))
        along = sum(x * y for x, y in zip(w, d_axis))
        return max(sum(x * x for x in w) - along * along, 0.0) < tol * tol

    return _legacy


def test_the_contract_detects_a_round_off_decided_axis_fold(monkeypatch, capsys):
    """
    Put the axis-fold defect back and require this file to catch it, and require
    EACH HALF OF THE FIX to be sufficient on its own.

    The defect had two halves: a fold with no answer on a tie, and a comparison
    that demanded two independent folds of one direction agree in sign. It was
    live on this repo's reference enclosure - 90.2 as modelled, 92.6 at 45
    degrees about Z, with 20 of 90 feature centres and 19 of 54 screws deleted
    while the raw cylinder census stayed bit-identical - and no probe in this
    file could reach it, because every probe drilled on one axis only.

    Both halves are closed, so restoring either alone must measure EXACTLY
    nothing: the tie-tolerant fold makes the sign-locked comparison correct
    again, and the sign-blind comparison makes the fold's sign irrelevant. Only
    with both restored does the part move, and that is asserted here so neither
    half can be dropped later as redundant.
    """
    fold = _legacy_dominant_fold()
    compare = _legacy_sign_locked_point_on_axis()
    base = PROBES[MULTI_AXIS_PROBE]()
    reference = _scores(base)
    turned = base.rotate((0, 0, 0), (0, 0, 1), 45.0)

    def worst(case) -> tuple[float, float, str]:
        overall = abs(case[0] - reference[0])
        metric = max(
            ((abs(v - reference[1][k]), k) for k, v in case[1].items() if v is not None),
            default=(0.0, ""),
        )
        return overall, metric[0], metric[1]

    with monkeypatch.context() as m:
        m.setattr(analyze_step, "_canonical_dir", fold)
        m.setattr(design_review, "_canonical_dir", fold)
        fold_only = worst(_scores(turned))
    with monkeypatch.context() as m:
        m.setattr(design_review, "_point_on_axis", compare)
        compare_only = worst(_scores(turned))
    with monkeypatch.context() as m:
        m.setattr(analyze_step, "_canonical_dir", fold)
        m.setattr(design_review, "_canonical_dir", fold)
        m.setattr(design_review, "_point_on_axis", compare)
        both = worst(_scores(turned))

    with capsys.disabled():
        print(
            f"\n  round-off decided fold restored on {MULTI_AXIS_PROBE} at z45: the score "
            f"moves {both[0]:.2f} points and {both[2]} {both[1]:.2f}; the legacy fold alone "
            f"moves {fold_only[0]:.6f} and the legacy sign-locked comparison alone "
            f"{compare_only[0]:.6f}"
        )
    assert both[0] > RIGID_TOL, (
        "the round-off decided axis fold was restored and the score did NOT move "
        f"(worst {both[0]:.3f}) - this contract cannot see the defect it exists for"
    )
    assert both[1] > RIGID_METRIC_TOL, (
        f"no metric moved past {RIGID_METRIC_TOL} with the defect restored"
    )
    assert fold_only[0] < 1e-9 and fold_only[1] < 1e-9, (
        f"the legacy fold alone moved {fold_only[0]:.6f} points - the sign-blind "
        f"comparisons are no longer absorbing it, so half the fix has been lost"
    )
    assert compare_only[0] < 1e-9 and compare_only[1] < 1e-9, (
        f"the legacy sign-locked comparison alone moved {compare_only[0]:.6f} points - "
        f"the fold is no longer stable on a tie, so half the fix has been lost"
    )


def test_the_axis_fold_is_decided_by_the_direction_and_not_by_round_off():
    """
    The fix at the unit it lives at: two representations of ONE direction fold
    the same way.

    A cylinder's axis reaches `_point_on_axis` twice over - once as the
    4-decimal `dir` on the merged feature, once as the full-precision direction
    on the face's own axis key - and at 45 degrees in a plane those two
    representations tie. The fold has to give both the same answer, and the dot
    product of the two folds has to be +1 and not -1.
    """
    exact = math.sqrt(0.5)
    for direction in (
        (-exact, exact, 0.0),
        (exact, -exact, 0.0),
        (0.0, -exact, exact),
        (exact, 0.0, exact),
        (-0.5773502691896258, 0.5773502691896258, 0.5773502691896258),
    ):
        rounded = tuple(round(c, 4) for c in direction)
        a = design_review._canonical_dir(direction)
        b = design_review._canonical_dir(rounded)
        assert sum(x * y for x, y in zip(a, b)) > 0.999, (
            f"{direction} folded to {a} at full precision and {b} rounded to 4 "
            f"decimals - the same axis, folded into opposite directions"
        )


def test_the_contract_detects_an_uncanonical_partition(monkeypatch, capsys):
    """
    Put the re-partition defect back - measure the FILE'S partition instead of
    the part's - and require this file to catch it.
    """
    monkeypatch.setattr(design_review, "_canonical_partition", lambda shape: shape)
    base = probe_square_plate()
    flat = _scores(base)
    split = _scores(_repartition(base, "YZ"))
    delta = abs(flat[0] - split[0])
    face_delta = (split[1]["face_composition"] or 0.0) - (flat[1]["face_composition"] or 0.0)
    with capsys.disabled():
        print(
            f"\n  uncanonical partition restored: one coplanar split moves the score "
            f"{flat[0]:.1f} -> {split[0]:.1f} ({delta:.2f} points), face_composition "
            f"by {face_delta:+.2f}"
        )
    assert delta > REPARTITION_TOL, (
        "the uncanonical partition was restored and the score did NOT move "
        f"(delta {delta:.4f}) - this contract cannot see the defect it exists for"
    )
    assert face_delta > 0.0, (
        "the defect only ever paid UPWARD; if the split now costs face_composition "
        "points, this meta-test is measuring something else"
    )


def test_the_contract_detects_a_world_aligned_measurement_basis(monkeypatch, capsys):
    """
    `_world_frame` is the pre-frame-port behaviour: measure everything against
    the world axis-aligned bounding box. If the assertions above can pass with
    this in place, they are decoration.
    """

    def _world_frame(shape) -> Frame:
        if hasattr(shape, "val"):
            shape = shape.val()
        bb = shape.BoundingBox()
        axes = (cq.Vector(1, 0, 0), cq.Vector(0, 1, 0), cq.Vector(0, 0, 1))
        size = (bb.xlen, bb.ylen, bb.zlen)
        order = sorted(range(3), key=lambda i: -size[i])
        return Frame(
            axes=tuple(axes[i] for i in order),
            size=tuple(size[i] for i in order),
            centre=cq.Vector(
                (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, (bb.zmin + bb.zmax) / 2
            ),
            basis="world",
            explained=0.0,
        )

    monkeypatch.setattr(design_review, "reference_frame", _world_frame)
    base = probe_worked_box()
    flat = _scores(base)
    turned = _scores(base.rotate((0, 0, 0), (0, 0, 1), 15.0))
    delta = abs(flat[0] - turned[0])
    with capsys.disabled():
        print(
            f"\n  world-aligned basis restored: 15 deg about Z moves the score "
            f"{flat[0]:.1f} -> {turned[0]:.1f} ({delta:.2f} points)"
        )
    assert delta > RIGID_TOL, (
        "the world axis-aligned basis was restored and the score did NOT move "
        f"(delta {delta:.3f}) - this contract cannot see the defect it exists for"
    )


def test_the_contract_detects_a_translation_dependent_ruler(monkeypatch, capsys):
    """
    The translation contract is the one this file asserts as an equality, so it
    needs its own proof of teeth. `_from_origin` measures the part's size from
    the WORLD ORIGIN to its far corner instead of across the part - a size
    derived from a coordinate rather than from the geometry, which is the exact
    shape of every defect this module hunts, and which reads the square plate as
    80 x 80 x 10 mm at the origin and 540 x 540 x 505 mm at (500, -500, 500).
    Every threshold scaled by the part's size is downstream of it.
    """

    def _from_origin(self) -> tuple[float, float, float]:
        return (
            max(abs(self.bb.xmin), abs(self.bb.xmax)),
            max(abs(self.bb.ymin), abs(self.bb.ymax)),
            max(abs(self.bb.zmin), abs(self.bb.zmax)),
        )

    monkeypatch.setattr(design_review.Topology, "bbox_size", _from_origin)
    base = probe_square_plate()
    here = _scores(base)
    there = _scores(base.translate((500.0, -500.0, 500.0)))
    moved = max(
        abs(v - here[1][k])
        for k, v in there[1].items()
        if v is not None and here[1].get(k) is not None
    )
    with capsys.disabled():
        print(f"\n  position-dependent align_tol restored: worst metric moves {moved:.2f} points")
    assert moved > RIGID_METRIC_TOL, (
        "a ruler that depends on where the part sits was restored and no metric "
        f"moved by more than {moved:.4f} - the translation contract has no teeth"
    )


def test_the_contract_detects_a_world_bounding_box_axial_length(monkeypatch, capsys):
    """
    Put the axial-length defect back and require this file to catch it.

    `_bbox_axial_extent` is the derivation `_cylinder_features` used before the
    fix: project the face's WORLD axis-aligned bounding box corners onto the
    axis. It is exact for an axis-aligned cylinder and inflates for every other,
    and the whole fastener population is downstream of it.
    """

    def _bbox_axial_extent(face, surf, surf_dir, canon_dir, base):
        bb = face.BoundingBox()
        corners = [
            (x, y, z)
            for x in (bb.xmin, bb.xmax)
            for y in (bb.ymin, bb.ymax)
            for z in (bb.zmin, bb.zmax)
        ]
        ts = [sum(c * dc for c, dc in zip(corner, canon_dir)) for corner in corners]
        return min(ts), max(ts)

    monkeypatch.setattr(analyze_step, "_axial_extent", _bbox_axial_extent)
    base = probe_square_plate()
    flat = _scores(base)
    turned = _scores(base.rotate((0, 0, 0), (0.3, -0.7, 0.5), 77.0))
    delta = abs(flat[0] - turned[0])
    with capsys.disabled():
        print(
            f"\n  world-bbox axial length restored: 77 deg moves the score "
            f"{flat[0]:.1f} -> {turned[0]:.1f} ({delta:.2f} points)"
        )
    assert delta > RIGID_TOL, (
        "the world bounding-box axial length was restored and the score did NOT "
        f"move (delta {delta:.3f}) - this contract cannot see the defect it caught"
    )
    for metric in ("feature_composition", "pattern_discipline"):
        assert turned[1][metric] == 0.0, (
            f"with the defect restored {metric} should collapse to 0.0, got "
            f"{turned[1][metric]} - this contract cannot see the defect it exists for"
        )


def test_the_axial_length_is_the_faces_own_parametric_range():
    """
    The fix itself, at the unit it lives at: a D6 hole through a 10 mm plate is
    10.0 mm long however the file is held. This is the measurement the whole
    fastener population is built on, so it is asserted directly rather than only
    through a score.
    """
    plate = (
        cq.Workplane("XY")
        .box(40, 40, 10)
        .faces(">Z")
        .workplane()
        .rect(24, 24, forConstruction=True)
        .vertices()
        .hole(6.0)
        .val()
    )
    for label, shape in (
        ("as modelled", plate),
        ("rotated 77 deg", plate.rotate((0, 0, 0), (0.3, -0.7, 0.5), 77.0)),
        ("translated 500 mm", plate.translate((500.0, -500.0, 500.0))),
    ):
        holes = [
            f for f in analyze_step._cylinder_features(shape) if abs(f["diameter"] - 6.0) < 1e-6
        ]
        assert len(holes) == 4, f"{label}: found {len(holes)} D6 holes, expected 4"
        for hole in holes:
            assert abs(hole["length"] - 10.0) < 1e-6, (
                f"{label}: a D6 hole through 10 mm of plate measured {hole['length']} mm"
            )


def test_the_frame_module_is_the_one_this_file_contracts():
    """
    Every bound above is written for `lib/frame.py`'s frame. If the scorer stops
    using it, the numbers here are about something that is no longer running.
    """
    assert design_review.reference_frame is frame_module.reference_frame
