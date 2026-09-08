"""
Tests for lib/design_review.py - the refinement gate.

The load-bearing test is the CALIBRATION ORDERING: five solids of known,
increasing refinement must score in that order, and a sharp box must land far
below a solid that carries radii, breaks, panels and a disciplined bolt
pattern. If that ordering ever inverts the module is measuring something other
than refinement, and every number it prints is decoration.

Everything else exists so the score can be trusted: each metric must move in
the direction it claims when the geometry is perturbed in exactly the way it
is supposed to detect, and a kernel failure must surface as ERROR rather than
as a flattering partial score. Run with: make test  (or: pytest tests/)
"""

import json
import subprocess
import sys
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import lib.design_review as dr  # noqa: E402
from lib.design_review import (  # noqa: E402
    BANDS,
    DEFAULT_WEIGHTS,
    SCHEMA,
    config_from_spec,
    design_review_checks,
    format_report,
    review_shape,
    review_step,
)

# Small on purpose: the metrics are size-normalised, and every second here is
# paid by every future run of the suite.
L, W, H = 60.0, 40.0, 25.0
R_PLAN, BREAK = 5.0, 1.0  # both on the ladder lib/features.py exposes


def _formed_sheet_bracket(t: float = 2.0, a: float = 50.0, b: float = 40.0, width: float = 60.0):
    """
    A real FORMED sheet part: 2 mm stock with one 90 degree bend, inner radius
    2.0 and outer radius 4.0 - a bend, not a mitre.

    The `sheet` role deletes the whole blanked perimeter from the edge
    population and pays for it with the formed radii it is judged on instead, so
    a part claiming the role has to have some. A flat blank does not, which is
    the root of G2a; everything asserted about `sheet` therefore needs a part
    that is actually bent.
    """
    import math  # noqa: PLC0415

    r_o, r_i, s = 4.0, 2.0, math.sqrt(0.5)
    return (
        cq.Workplane("XZ")
        .moveTo(a, 0)
        .lineTo(a, t)
        .lineTo(r_o, t)
        .threePointArc((r_o - r_i * s, r_o - r_i * s), (t, r_o))
        .lineTo(t, b)
        .lineTo(0, b)
        .lineTo(0, r_o)
        .threePointArc((r_o - r_o * s, r_o - r_o * s), (r_o, 0))
        .close()
        .extrude(width)
    )


def _turned(od: float = 30.0, bore: float = 12.0, length: float = 40.0, breaks: bool = True):
    """
    A turned spacer: a body of revolution with a through bore.

    `breaks=False` leaves every corner of the silhouette raw and deburrs only
    the two bore mouths - the exact shape of G1 and G2b, on a part whose OD used
    to be filed under "bore rim" so that the whole body population vanished.
    """
    body = cq.Workplane("XY").circle(od / 2.0).extrude(length)
    body = body.faces(">Z").workplane().hole(bore)
    if breaks:
        return body.edges().chamfer(1.0).val()
    solid = body.val()
    for z, d in ((0.0, (0, 0, 1)), (length, (0, 0, -1))):
        solid = solid.cut(
            cq.Solid.makeCone(bore / 2.0 + 1.0, bore / 2.0, 1.0, cq.Vector(0, 0, z), cq.Vector(*d))
        )
    return solid


def _zband(z: float, tol: float = 0.4):
    """Every edge lying in a thin slab at height `z` - a whole profile ring."""
    return cq.selectors.BoxSelector((-1e4, -1e4, z - tol), (1e4, 1e4, z + tol))


def _stepped_cylinder():
    """The audit's six-line arbitrary stepped cylinder: measured 100.0 / A."""
    b = cq.Workplane("XY").circle(20).extrude(12)
    b = b.faces(">Z").workplane().circle(14).extrude(16)
    b = b.faces(">Z").workplane().circle(9).extrude(22)
    return b.edges("%CIRCLE").chamfer(1.0)


def _ring(z: float, radius: float, tol: float = 0.4):
    """One profile ring, picked out by BOTH its height and its radius."""
    r = radius + 0.1
    return cq.selectors.BoxSelector((-r, -r, z - tol), (r, r, z + tol))


def _shaft_blank():
    """Three diameters, 12 / 9 / 6, stepping down along +Z. Nothing broken."""
    b = cq.Workplane("XY").circle(12).extrude(30)
    b = b.faces(">Z").workplane().circle(9).extrude(25)
    return b.faces(">Z").workplane().circle(6).extrude(20)


def _stepped_shaft():
    """The trivial-end case: a stepped shaft with every edge chamfered."""
    return _shaft_blank().edges("%CIRCLE").chamfer(1.0)


def _shaft_roots(mode: str | None):
    """
    The same shaft with the two SHOULDER ROOTS treated three different ways and
    everything else identical: both ends chamfered, both convex shoulder rings
    left as they are. The three variants therefore have exactly the same convex
    edge population, which is what makes them indistinguishable to every
    convex-only metric in the module.
    """
    b = _shaft_blank()
    if mode == "chamfer":
        b = b.edges(_ring(30.0, 9.0)).chamfer(1.0).edges(_ring(55.0, 6.0)).chamfer(1.0)
    elif mode == "fillet":
        b = b.edges(_ring(30.0, 9.0)).fillet(1.0).edges(_ring(55.0, 6.0)).fillet(1.0)
    return b.edges(_ring(0.0, 12.0)).chamfer(1.0).edges(_ring(75.0, 6.0)).chamfer(1.0)


def _turned_gland():
    """The corpus's turned reference, rebuilt here so this file stands alone."""
    body = cq.Workplane("XY").circle(17.0).extrude(18.0)
    body = body.faces(">Z").workplane().circle(13.0).extrude(14.0)
    body = body.faces(">Z").workplane().circle(10.0).extrude(10.0)
    body = body.faces(">Z").workplane().hole(12.0)
    body = body.faces("<Z").workplane().cboreHole(12.0, 20.0, 6.0)
    return body.edges("%CIRCLE").chamfer(1.0)


def _turned_spool():
    """A finished spool: two flanges, RADIUSED web roots, bored and chamfered."""
    body = cq.Workplane("XY").newObject(
        [
            cq.Solid.makeCylinder(24.0, 5.0, cq.Vector(0, 0, 0))
            .fuse(cq.Solid.makeCylinder(13.0, 22.0, cq.Vector(0, 0, 5.0)))
            .fuse(cq.Solid.makeCylinder(24.0, 5.0, cq.Vector(0, 0, 27.0)))
            .clean()
        ]
    )
    body = body.edges(_zband(5.0)).fillet(2.5).edges(_zband(27.0)).fillet(2.5)
    body = cq.Workplane("XY").newObject(
        [body.val().cut(cq.Solid.makeCylinder(6.0, 60.0, cq.Vector(0, 0, -10.0)))]
    )
    return body.edges(_zband(0.0)).chamfer(1.0).edges(_zband(32.0)).chamfer(1.0)


def _turned_knob():
    """A knob: an R8 crown blend over a skirt, bored, with a broken skirt rim."""
    b = cq.Workplane("XY").circle(15).extrude(24).edges(">Z").fillet(8.0)
    b = b.faces("<Z").workplane().hole(8.0)
    return b.edges("<Z").chamfer(1.0)


def _turned_crowned_knob():
    """
    A COMPOSED crowned knob: two diameters, an R8 crown, an R1.5 relieved
    shoulder root, a counterbored socket and a broken skirt rim.

    _turned_knob above is the same idea with one move made instead of four: one
    diameter, one crown, one bore. The pair is the calibration for what reading
    a curved surface does to the turned class - the composed knob measures 81.5
    and the plain drum 68.4, where before the skin could be read they measured
    90.6 and 77.3 and nothing distinguished a shaped knob from a drum.
    """
    b = cq.Workplane("XY").circle(20.0).extrude(22.0)
    b = b.faces(">Z").workplane().circle(14.0).extrude(12.0)
    b = b.edges(_zband(22.0)).fillet(1.5)
    b = b.edges(_zband(34.0)).fillet(8.0)
    b = b.faces("<Z").workplane().cboreHole(8.0, 14.0, 6.0)
    return b.edges(_zband(0.0)).chamfer(1.0)


# ---------------------------------------------------------------------------
# the calibration ladder
# ---------------------------------------------------------------------------
def _recess_tool(w, h, depth, radius, mouth):
    """
    A recessed-panel cutter whose MOUTH is broken, so the recess is a properly
    executed feature and not a knife-rimmed hole. Both prisms get their plan
    radii before the union - never a late fillet on the result.
    """
    over = 20.0
    pocket = (
        cq.Workplane("XY")
        .box(w, h, depth + over)
        .edges("|Z")
        .fillet(radius)
        .translate((0, 0, (depth + over) / 2 - depth))
    )
    flare = (
        cq.Workplane("XY")
        .box(w + 2 * mouth, h + 2 * mouth, over)
        .edges("|Z")
        .fillet(radius + mouth)
        .faces("<Z")
        .chamfer(mouth)
        .translate((0, 0, over / 2 - mouth))
    )
    return pocket.union(flare)


def rung1_sharp():
    """A raw extrusion: every edge a knife edge, every face blank."""
    return cq.Workplane("XY").box(L, W, H)


def rung2_plan_radii():
    """Plan corners only - the usual 'I filleted it' first pass."""
    return rung1_sharp().edges("|Z").fillet(R_PLAN)


def rung3_edge_breaks():
    """Plus a chamfer on both rims: no knife edge left on the body."""
    return rung2_plan_radii().faces(">Z").chamfer(BREAK).faces("<Z").chamfer(BREAK)


def rung4_panels():
    """Plus recessed panels with broken mouths on the crown and both flanks."""
    body = rung3_edge_breaks()
    body = body.cut(_recess_tool(44, 26, 2.0, 5.0, 1.0).translate((0, 0, H / 2)))
    for sign in (1, -1):
        body = body.cut(
            _recess_tool(44, 14, 2.0, 4.0, 1.0)
            .rotate((0, 0, 0), (1, 0, 0), -90 * sign)
            .translate((0, sign * W / 2, 0))
        )
    return body


def rung5_fasteners():
    """Plus counterbored screws: constant pitch, constant inset, symmetric."""
    return (
        rung4_panels()
        .faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(x, y) for x in (-24, 0, 24) for y in (-15, 15)])
        .cboreHole(4.5, 8.0, 2.5)
    )


RUNGS = ("sharp", "plan_radii", "edge_breaks", "panels", "fasteners")


@pytest.fixture(scope="module")
def ladder():
    """Every rung built and reviewed once - the rest of the file reads it."""
    builders = (rung1_sharp, rung2_plan_radii, rung3_edge_breaks, rung4_panels, rung5_fasteners)
    return {name: review_shape(fn(), source=name) for name, fn in zip(RUNGS, builders)}


def metric(report, mid):
    m = report["metrics"][mid]
    assert m["status"] != dr.METRIC_ERROR, f"{mid} errored: {m['message']}"
    return m


def test_refinement_ladder_scores_monotonically(ladder):
    """The one ordering the whole module stands on."""
    scores = [ladder[name]["score"] for name in RUNGS]
    assert all(s is not None for s in scores), f"a rung failed to score: {scores}"
    assert scores == sorted(scores), f"ladder is not monotonic: {scores}"
    assert all(b > a for a, b in zip(scores, scores[1:])), (
        f"each rung must score strictly higher than the last: {scores}"
    )


def test_sharp_box_scores_materially_below_a_refined_solid(ladder):
    sharp, refined = ladder["sharp"], ladder["fasteners"]
    assert refined["score"] - sharp["score"] >= 40.0, (
        f"only {refined['score'] - sharp['score']:.1f} points separate a raw box "
        f"from a fully refined one - the gate cannot discriminate"
    )
    assert sharp["band"] == "F", f"a raw extrusion must band F, got {sharp['band']}"
    assert refined["band"] in ("A", "B"), f"a refined solid must band A or B, got {refined['band']}"
    assert all(r["status"] == "ok" for r in ladder.values()), (
        "every rung must produce a real verdict, not 'insufficient'"
    )


def test_report_shape_is_the_documented_schema(ladder):
    rep = ladder["fasteners"]
    assert rep["schema"] == SCHEMA
    assert set(rep["metrics"]) == set(DEFAULT_WEIGHTS)
    assert rep["coverage"] == pytest.approx(1.0), "every metric should be measurable here"
    assert rep["errored"] == []
    assert rep["shape"]["solids"] == 1 and rep["shape"]["faces"] > 6
    assert rep["shape"]["bbox_size"] == [L, W, H]
    assert rep["band_label"] == next(lbl for cut, _, lbl in BANDS if rep["score"] >= cut)
    assert isinstance(rep["findings"], list)
    assert json.loads(json.dumps(rep, default=str))["schema"] == SCHEMA
    assert "Design review" in format_report(rep)


# ---------------------------------------------------------------------------
# per-metric direction: perturb the geometry the metric claims to detect
# ---------------------------------------------------------------------------
def test_edge_break_coverage_sees_broken_edges(ladder):
    sharp = metric(ladder["sharp"], "edge_break_coverage")
    broken = metric(ladder["edge_breaks"], "edge_break_coverage")
    assert sharp["value"] == 0.0 and sharp["score"] == 0.0
    # not one edge broken anywhere: a state of the DESIGN, reported as a defect
    # rather than renormalised away as "nothing to measure"
    assert sharp["status"] == dr.ABSENT
    # a 60 x 40 x 25 box has 4(60) + 4(40) + 4(25) = 500 mm of convex edge
    assert sharp["body_sharp_mm"] == pytest.approx(500.0, abs=0.5)
    assert sharp["body_broken_mm"] == 0.0
    assert sharp["worst"], "an unbroken box must name where its knife edges are"
    assert broken["value"] > 0.95 and broken["score"] > 95.0
    assert broken["body_sharp_mm"] < 1.0, "every rim is chamfered - nothing should be left"


def _l_section(fillet=None):
    """A 60 x 60 L, 15 thick, 40 deep - the audit's hand-verified test case."""
    solid = (
        cq.Workplane("XY")
        .moveTo(0, 0)
        .lineTo(60, 0)
        .lineTo(60, 15)
        .lineTo(15, 15)
        .lineTo(15, 60)
        .lineTo(0, 60)
        .close()
        .extrude(40)
    )
    if fillet:
        solid = (
            solid.edges("|Z")
            .edges(cq.selectors.NearestToPointSelector((15.0, 15.0, 20.0)))
            .fillet(fillet)
        )
    return solid


def test_a_concave_blend_earns_no_edge_break_credit():
    """
    Audit defect 1, as a regression, with the audit's own numbers. Convexity
    used to be computed lazily, AFTER the tangent short-circuit, so a smooth
    edge never had one - and _classify_breaks credited every tangent edge that
    touched a break face, at half length, twice. Filleting ONLY the internal
    corner of an L-section, a feature no eye can see from outside, moved it from
    broken 0.0 / sharp 680.0 to broken 40.0 / sharp 674.8.
    """
    plain = review_shape(_l_section())["metrics"]["edge_break_coverage"]
    inside = review_shape(_l_section(fillet=6.0))["metrics"]["edge_break_coverage"]
    assert plain["body_broken_mm"] == pytest.approx(0.0, abs=1e-6)
    assert inside["body_broken_mm"] == pytest.approx(0.0, abs=1e-6), (
        f"a buried concave blend must earn nothing, got {inside['body_broken_mm']} mm"
    )
    assert inside["value"] == 0.0 and inside["score"] == 0.0


def test_drilling_holes_cannot_raise_the_body_coverage():
    """
    Audit defect 3, as a regression. A countersink's cone passed the width test,
    so it was credited at BOTH of its boundary circles while adding nothing to
    the denominator, and every plane-to-cylinder edge that was NOT credited went
    to an unscored "rim" bucket. Both branches of the fork were free or better
    than free: on a knife-edged 120x80x40 box, three D5.5/D10 countersinks moved
    broken from 0.0 to 73.0 mm.
    """
    box = cq.Workplane("XY").box(120, 80, 40)
    points = [(-30, -18), (5, 20), (34, -8)]
    csk = (
        box.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints(points)
        .cskHole(5.5, 10.0, 90.0)
    )
    plain = review_shape(box)["metrics"]["edge_break_coverage"]
    drilled = review_shape(csk)["metrics"]["edge_break_coverage"]
    assert plain["body_broken_mm"] == 0.0 and plain["body_sharp_mm"] == pytest.approx(960.0, abs=1)
    assert drilled["body_broken_mm"] == pytest.approx(0.0, abs=1e-6), (
        f"a countersink breaks a RIM, not the body silhouette: {drilled['body_broken_mm']} mm"
    )
    assert drilled["body_sharp_mm"] == pytest.approx(960.0, abs=1)
    assert drilled["rim_bare_mm"] > 0.0, "the bores' far mouths are still bare rim"
    # and the rim term is SCORED, not a free bucket
    assert drilled["rim_coverage"] is not None and 0.0 < drilled["rim_coverage"] < 1.0
    assert drilled["score"] < 20.0, "a raw drilled box is still a raw box"


def test_sharp_edge_length_falls_as_edges_are_broken(ladder):
    sharp = metric(ladder["sharp"], "sharp_edge_length")
    broken = metric(ladder["edge_breaks"], "sharp_edge_length")
    assert sharp["value"] == pytest.approx(500.0, abs=0.5)
    assert broken["value"] < sharp["value"]
    assert broken["score"] > sharp["score"]


def _pocket_every_face(plain):
    pocketed = plain
    for sel, dims in (
        (">Z", (40, 24)),
        ("<Z", (40, 24)),
        (">Y", (40, 15)),
        ("<Y", (40, 15)),
        (">X", (24, 15)),
        ("<X", (24, 15)),
    ):
        pocketed = (
            pocketed.faces(sel)
            .workplane(centerOption="CenterOfBoundBox")
            .rect(*dims)
            .cutBlind(-1.5)
        )
    return pocketed


def test_face_composition_falls_when_faces_get_features():
    """
    Replaces the old blank_face_ratio, which was a two-valued step function:
    ANY inner wire covering 1% of a face flipped it from 0 to a perfect 100, so
    three through holes made a raw knife-edged box read as "every face carries a
    feature". The replacement is graded - it measures the largest EMPTY region
    left on the face, so a feature only helps as much as it actually fills.
    """
    plain = cq.Workplane("XY").box(L, W, H)
    bare = review_shape(plain)["metrics"]["face_composition"]
    dressed = review_shape(_pocket_every_face(plain))["metrics"]["face_composition"]
    assert bare["void_worst"] > 0.7, "a bare box leaves an empty circle across its face"
    assert dressed["void_worst"] < bare["void_worst"] - 0.15
    assert dressed["void_mean"] < bare["void_mean"] - 0.15
    assert dressed["score"] > bare["score"] + 20.0


def test_face_composition_is_a_gradient_not_a_step():
    """Three scattered holes must buy a few percent, not a perfect score."""
    plain = cq.Workplane("XY").box(L, W, H)
    drilled = (
        plain.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(-19, -11), (4, 13), (21, -3)])
        .hole(5.5)
    )
    bare = review_shape(plain)["metrics"]["face_composition"]
    holes = review_shape(drilled)["metrics"]["face_composition"]
    assert holes["void_worst"] < bare["void_worst"], "three holes do move the measure"
    assert holes["void_worst"] > 0.6, "but they leave a large empty region behind"
    assert holes["score"] - bare["score"] < 15.0, (
        "scattered holes must not buy a composition score; the old metric paid "
        "0 -> 100 for exactly this geometry"
    )


def test_face_composition_ignores_decoration_without_relief():
    """
    A shallow scribed outline is not a feature. Only relief past RELIEF_MIN_MM
    subtracts from the empty region, so wrapping a slab in grooves buys nothing.
    """
    plain = cq.Workplane("XY").box(L, W, H)
    scribed = (
        plain.faces(">Z").workplane(centerOption="CenterOfBoundBox").rect(44, 28).cutBlind(-0.6)
    )
    real = plain.faces(">Z").workplane(centerOption="CenterOfBoundBox").rect(44, 28).cutBlind(-3.0)

    def top_void(shape):
        m = review_shape(shape)["metrics"]["face_composition"]
        return next(f["void"] for f in m["faces"] if f["normal"] == "+Z")

    bare, fake, deep = top_void(plain), top_void(scribed), top_void(real)
    assert fake == pytest.approx(bare, abs=0.01), "0.6 mm of relief is decoration"
    assert deep < bare - 0.1, "3.0 mm of relief is a feature"


def test_face_composition_ignores_interior_cavity_walls():
    """
    A sealed cavity is not a product surface. The audit's gaming case buried its
    geometry inside one; anything only visible from inside is not scored.
    """
    lid = cq.Workplane("XY").box(L, W, H)
    hollow = lid.faces(">Z").shell(-3.0)
    sealed = hollow.union(cq.Workplane("XY").box(L, W, 3.0).translate((0, 0, H / 2 - 1.5)))
    m = review_shape(sealed)["metrics"]["face_composition"]
    assert m["status"] == dr.SCORED
    for face in m["faces"]:
        assert (
            abs(face["at"][2]) >= H / 2 - 1e-6
            or abs(face["at"][0]) >= L / 2 - 1e-6
            or (abs(face["at"][1]) >= W / 2 - 1e-6)
        ), f"an interior cavity wall was scored as a product surface: {face}"


def test_radius_vocabulary_rejects_off_ladder_sizes():
    # Every edge is broken at the one radius under test, so the APPLIED term is
    # saturated and this test isolates ladder conformance, which is what it is
    # about. A box with only its plan corners filleted breaks 5% of its
    # silhouette and is now discounted for it - see the applied-coverage test.
    def radv(radius):
        box = cq.Workplane("XY").box(L, W, H)
        shape = box.edges("|Z").fillet(radius).edges(">Z or <Z").fillet(radius)
        return review_shape(shape)["metrics"]["radius_vocabulary"]

    on = radv(5.0)
    off = radv(6.5)
    assert on["value"] == pytest.approx(1.0) and on["score"] == pytest.approx(100.0)
    assert [d["on_ladder"] for d in on["distinct"]] == [True]
    assert off["value"] == pytest.approx(0.0) and off["score"] == pytest.approx(0.0)
    assert off["off_ladder"], "an off-ladder radius must be named, not just scored"
    # no fillet or chamfer at all is the worst case, and says so
    none = review_shape(cq.Workplane("XY").box(L, W, H))["metrics"]["radius_vocabulary"]
    assert none["score"] == 0.0 and "knife edge" in none["message"]


def test_radius_vocabulary_does_not_charge_a_part_for_needing_several_radii():
    """
    Six sizes, all from the ladder, must cost exactly what two do: nothing.

    This test used to assert the OPPOSITE - `b["score"] < a["score"]`, "more
    distinct break sizes must score worse" - and that assertion was the defect.
    It is a statement about RICHNESS, not about vocabulary. A fin root, a seal
    land, a counterbore and an outer plan corner are four different jobs and the
    radius that suits one is wrong for the others, so the part that needs four
    was charged for doing the right thing. Measured before the change: the
    repo's exemplar enclosure, 10 sizes and 97% of its break area on this
    repo's own ladder, scored 48.5, while the scaffold - a soap-bar case whose
    features are decorative grooves - scored 91.7 for using 5.

    Conformance and application are untouched and still do their jobs; what
    replaced the count is a SPLIT RUNG charge, asserted directly below.
    """
    tidy = (
        cq.Workplane("XY")
        .box(L, W, H)
        .edges("|Z")
        .fillet(5.0)
        .faces(">Z")
        .chamfer(1.0)
        .faces("<Z")
        .chamfer(1.0)
    )
    sprawl = (
        cq.Workplane("XY")
        .box(L, W, H)
        .edges("|Z and >X and >Y")
        .fillet(3.0)
        .edges("|Z and >X and <Y")
        .fillet(5.0)
        .edges("|Z and <X and >Y")
        .fillet(8.0)
        .edges("|Z and <X and <Y")
        .fillet(12.0)
        .faces(">Z")
        .chamfer(1.0)
        .faces("<Z")
        .chamfer(2.5)
    )
    a = review_shape(tidy)["metrics"]["radius_vocabulary"]
    b = review_shape(sprawl)["metrics"]["radius_vocabulary"]
    assert len(a["distinct"]) == 2, f"one radius and one chamfer is TWO sizes: {a['distinct']}"
    assert len(b["distinct"]) == 6, f"four radii and two chamfers is SIX: {b['distinct']}"
    assert all(d["on_ladder"] for d in b["distinct"]), "isolate the count, not conformance"
    assert b["split_rungs"] == [], "every size is a full rung apart from every other"
    assert b["score"] == pytest.approx(a["score"]), (
        f"a rich but conforming vocabulary must cost nothing: 6 sizes scored {b['score']} "
        f"against 2 sizes at {a['score']}"
    )
    assert not [f for f in review_shape(sprawl)["findings"] if f["metric"] == "radius_vocabulary"]


def test_radius_vocabulary_charges_a_split_rung():
    """
    Same corner count, same job, two sizes one tenth apart: that is the defect.

    R5.5 beside R5.0 is not a fifth design decision, it is the fourth one drifting
    - nothing in the shared ladder distinguishes sizes that close (its own
    tightest step is 2.5 -> 3.0, a factor of 1.20), so no eye can either. The
    part below is the `tidy` reference with one of its four plan corners moved
    off its rung and nothing else changed, so the count, the coverage and the
    application are all held constant and only coherence moves.
    """
    tidy = (
        cq.Workplane("XY")
        .box(L, W, H)
        .edges("|Z")
        .fillet(5.0)
        .faces(">Z")
        .chamfer(1.0)
        .faces("<Z")
        .chamfer(1.0)
    )
    split = (
        cq.Workplane("XY")
        .box(L, W, H)
        .edges("|Z and (<X or <Y)")  # three of the four plan corners
        .fillet(5.0)
        .edges("|Z and >X and >Y")  # and the fourth, off its rung by 0.5 mm
        .fillet(5.5)
        .faces(">Z")
        .chamfer(1.0)
        .faces("<Z")
        .chamfer(1.0)
    )
    a = review_shape(tidy)["metrics"]["radius_vocabulary"]
    rep = review_shape(split)
    b = rep["metrics"]["radius_vocabulary"]
    assert sorted(d["size"] for d in b["distinct"]) == [1.0, 5.0, 5.5], b["distinct"]
    assert [s["size"] for s in b["split_rungs"]] == [5.5], b["split_rungs"]
    assert b["split_rungs"][0]["near"] == 5.0, "the heavier size is the language"
    assert b["score"] < a["score"], (
        f"a rung split in two must cost more than the same rung used once: "
        f"{b['score']} against {a['score']}"
    )
    finding = next(f for f in rep["findings"] if f["id"] == "split_radius_rung")
    assert "R5.5" in finding["message"] and "R5" in finding["message"]


def test_no_two_ladder_rungs_can_ever_read_as_a_split():
    """
    The property that makes richness free: the charge is derived FROM the
    ladder, so nothing drawn from the ladder can trip it.

    Asserted over the real Style ladder rather than a fixture, because the
    guarantee has to survive somebody editing lib.features.Style - which is now
    the only sanctioned way to change the radii this repo uses.
    """
    ladder, _provenance = dr._load_ladder()
    assert len(ladder) >= 5, ladder
    buckets = [
        {"size": r, "faces": 1, "area_mm2": 100.0 * (i + 1), "kind": "fillet", "on_ladder": True}
        for i, r in enumerate(ladder)
    ]
    splits, area = dr._split_rungs(buckets, ladder)
    assert splits == [] and area == 0.0, f"a ladder rung read as a split of another: {splits}"


def test_radius_vocabulary_measures_a_uniform_chamfer_as_one_size():
    """
    Audit defect 6, as a regression. _chamfer_leg used to average EVERY convex
    boundary edge of a chamfer land, which on a square plan corner sweeps in the
    ~60 deg mitre edges between adjacent lands. A textbook 2.0 mm x 45 deg
    chamfer on a box measured as three sizes - 0.667, 1.95, 2.059 - so the one
    behaviour the metric exists to reward was scored as incoherence.
    """
    # 2.5 mm and the shared ladder, not 2.0 mm and a one-rung override: a
    # single-rung `style.radius_ladder` is now a rejected config (it was a part
    # declaring that its own radius is the standard), and the metric this test
    # is about is better exercised against the real design language anyway.
    box = cq.Workplane("XY").box(60, 60, 30).edges().chamfer(2.5)
    m = review_shape(box)["metrics"]["radius_vocabulary"]
    sizes = [d["size"] for d in m["distinct"]]
    assert len(sizes) == 1, f"a uniform 2.5 mm chamfer must read as ONE size, got {sizes}"
    assert sizes[0] == pytest.approx(2.5, abs=0.05)
    assert m["score"] == pytest.approx(100.0), (
        "one design size, on the ladder, is what a coherent part looks like"
    )


def test_break_recognition_is_relative_to_the_part_not_an_absolute_cap():
    """
    Audit defects 7 and 8, as a regression. CHAMFER_W_MAX = 5.0 mm meant a 4 mm
    chamfer on a 300 mm part stopped registering as a chamfer and its two
    boundary edges were then scored as KNIFE EDGES: coverage went 100.0 -> 0.0
    between a 3 mm and a 4 mm break. BLEND_R_MAX = 40.0 was the mirror cliff at
    R45. Both caps are now a fraction of the part.
    """

    def coverage(shape):
        return review_shape(shape)["metrics"]["edge_break_coverage"]["score"]

    big = cq.Workplane("XY").box(300, 200, 120)
    assert coverage(big.edges().chamfer(3.0)) > 90.0
    assert coverage(big.edges().chamfer(4.0)) > 90.0, "a 4 mm break on a 300 mm part is a break"
    assert coverage(big.edges().chamfer(6.0)) > 90.0

    # The vocabulary half of the cliff, asserted on RECOGNITION rather than on
    # ladder conformance. It used to declare a seven-rung `style.radius_ladder`
    # covering every radius under test and demand a score of 100; that key is
    # retired (a part may not publish the standard it is measured against), and
    # 39 and 45 are genuinely off the shared ladder, which tops out at 24.
    # What BLEND_R_MAX = 40 actually broke was recognition: past the cap the
    # blend stopped being a blend at all and vanished from the population, so
    # the honest assertion is that every one of these radii is still SEEN.
    def vocabulary(radius):
        shape = cq.Workplane("XY").box(300, 200, 120).edges("|Z").fillet(radius)
        return review_shape(shape)["metrics"]["radius_vocabulary"]

    for radius in (8.0, 20.0, 39.0, 45.0):
        m = vocabulary(radius)
        sizes = [d["size"] for d in m["distinct"]]
        assert sizes == [pytest.approx(radius, abs=0.05)], (
            f"R{radius} is a blend on a 300 mm part; it must not leave the vocabulary: {m}"
        )
        assert m["status"] == dr.SCORED and m["population"] > 0.0, m

    # ... and the two that ARE on the shared ladder still read as coherent.
    # CONFORMANCE is the assertion, not the score: these boxes carry a plan
    # radius and nothing else, so 5% of the silhouette is broken and the APPLIED
    # term discounts them for it. The score is exactly conformance x applied, so
    # asserting both pins the whole calculation without asserting the defect
    # G3 removed (one break anywhere scoring a flat 100).
    for radius in (8.0, 16.0):
        m = vocabulary(radius)
        assert m["value"] == pytest.approx(1.0), m
        assert m["score"] == pytest.approx(100.0 * m["applied_factor"], abs=0.5), m


def _broken_body():
    return (
        cq.Workplane("XY")
        .box(L, W, H)
        .edges("|Z")
        .fillet(R_PLAN)
        .faces(">Z")
        .chamfer(BREAK)
        .faces("<Z")
        .chamfer(BREAK)
    )


def test_pattern_discipline_separates_rhythm_from_scatter():
    body = _broken_body()

    def holes(points, diameter=4.5):
        return review_shape(
            body.faces(">Z")
            .workplane(centerOption="CenterOfBoundBox")
            .pushPoints(points)
            .hole(diameter)
        )["metrics"]["pattern_discipline"]

    rhythm = holes([(x, y) for x in (-22, 0, 22) for y in (-14, 14)])
    scatter = holes([(-21, -13), (3, 15), (19, -6), (-7, 9), (24, 12), (-13, 2)])
    assert rhythm["score"] == pytest.approx(100.0)
    assert rhythm["groups"][0]["pitch_cv"] == pytest.approx(0.0, abs=1e-6)
    assert rhythm["groups"][0]["symmetric_fraction"] == pytest.approx(1.0)
    assert scatter["score"] < 50.0, "six scattered holes must not read as a pattern"
    assert scatter["groups"][0]["pitch_cv"] > 0.1
    assert scatter["groups"][0]["symmetric_fraction"] < 1.0


def test_enlarging_bad_holes_can_no_longer_erase_their_penalty():
    """
    Audit defect 5, as a regression, with the audit's own numbers: four
    deliberately scattered D8 holes scored fastener_rhythm 18.1 and the part
    17.7; the SAME four holes at D24 exceeded FASTENER_D_MAX, reported
    not_applicable, were renormalised out of the weighted mean, and the part
    scored 17.9. The gate paid 0.2 points for making the geometry worse.
    """
    body = _broken_body()
    points = [(-20, -12), (5, 14), (18, -5), (-8, 8)]

    def report(diameter):
        return review_shape(
            body.faces(">Z")
            .workplane(centerOption="CenterOfBoundBox")
            .pushPoints(points)
            .hole(diameter)
        )

    # D13, not the audit's D20: the closest pair of these points is 14.3 mm
    # apart, so at D20 two of the four holes FUSE and the large body is a
    # genuinely different, genuinely tidier part - three holes instead of four,
    # pitch CV 0.24 -> 0.11. That is not the metric paying for a bigger hole, it
    # is the fixture changing the geometry underneath the comparison, and it
    # would mask the defect this test exists to catch.
    small, large = report(8.0), report(13.0)
    counts, rhythm = [], []
    for rep in (small, large):
        m = rep["metrics"]["pattern_discipline"]
        assert m["status"] in (dr.SCORED, dr.ABSENT), (
            f"a hole is a hole at any diameter, got {m['status']}: {m['message']}"
        )
        assert m["score"] is not None, "an inapplicable metric must never be free"
        counts.append(m.get("screws"))
        rhythm.append(m["score"])
    assert counts[0] == counts[1], (
        f"the two bodies must carry the SAME four holes to be comparable, got {counts}"
    )
    # THE metric the diameter cap used to switch off. Scatter is scatter at any
    # size, so this one must not move at all.
    assert rhythm[1] <= rhythm[0] + 1e-9, f"fastener rhythm paid for a bigger hole: {rhythm}"
    # The overall bar is 0.5, not 0.05: face_composition is continuous in hole
    # size on purpose - a D13 hole genuinely removes more blank face than a D8
    # one, and it is worth +0.53 on that metric here. The defect being guarded
    # is a CLIFF (a metric flipping to a free state and taking whole points with
    # it), which is two orders of magnitude larger than this drift.
    assert large["score"] <= small["score"] + 0.5, (
        f"making the holes bigger must not pay: D8 {small['score']} -> D13 {large['score']}"
    )


def test_holes_with_no_pattern_are_a_defect_not_an_exemption():
    """
    Rule 5 of the three-state model: the geometry says the metric applies and it
    does not, so the metric scores 0 at FULL weight and emits a FAIL check. It
    is never renormalised out.
    """
    body = _broken_body()
    two_holes = (
        body.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(-20, -12), (7, 9)])
        .hole(5.0)
    )
    rep = review_shape(two_holes)
    m = rep["metrics"]["pattern_discipline"]
    assert m["status"] == dr.ABSENT and m["score"] == 0.0
    assert rep["coverage"] == pytest.approx(1.0), (
        "absent_defect is MEASURED weight - it was measured, and the answer was zero"
    )
    checks = design_review_checks(rep)
    check = next(c for c in checks if c["id"] == "design_review.pattern_discipline")
    assert check["status"] == "FAIL"
    assert "absent where the geometry requires it" in check["message"]


def test_an_enclosure_with_no_holes_at_all_is_a_defect():
    """A housing that cannot be fastened to anything is not 'not applicable'."""
    m = review_shape(_broken_body())["metrics"]["pattern_discipline"]
    assert m["status"] == dr.ABSENT and m["score"] == 0.0
    # ... but a structural member genuinely fastens through its ends. It has to
    # BE one, though: the 60 x 40 x 25 body above is 2.4:1 and claiming
    # `structural` on it is now a role ERROR, so the arm here is a real member.
    arm = (
        cq.Workplane("XY")
        .box(300.0, 40.0, 30.0)
        .edges("|Z")
        .fillet(R_PLAN)
        .faces(">Z")
        .chamfer(BREAK)
    )
    rep = review_shape(arm, config={"role": "structural"})
    assert rep.get("role_error") is None, rep.get("role_error")
    m2 = rep["metrics"]["pattern_discipline"]
    assert m2["status"] == dr.NOT_REQUIRED and m2["score"] is None


def test_symmetry_falls_when_no_mirror_plane_holds():
    box = cq.Workplane("XY").box(L, W, H)
    lopsided = (
        box.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .center(18, 12)
        .rect(18, 12)
        .cutBlind(-12)
    )
    clean = review_shape(box)["metrics"]["symmetry"]
    skew = review_shape(lopsided)["metrics"]["symmetry"]
    assert clean["value"] == pytest.approx(0.0, abs=1e-6) and clean["score"] == 100.0
    assert set(clean["per_axis"]) == {"X", "Y", "Z"}
    assert skew["value"] > clean["value"], "an off-centre blind pocket breaks every plane"
    assert skew["score"] < clean["score"]


def _lopsided(feature):
    """The same box, made asymmetric by one cut on the top face at (+18, +12)."""
    return feature(
        cq.Workplane("XY").box(L, W, H).faces(">Z").workplane(centerOption="CenterOfBoundBox")
    )


def test_symmetry_charges_a_sliver_and_excuses_a_compact_interface():
    """
    Identical difference VOLUME, identical location, opposite verdicts - and the
    only thing that differs is the SHAPE of the lump.

    The extent term exists to catch a difference that is thin but wide, such as
    a chamfer or a groove run down one side and not its mirror. It only ever
    measured the wide half, so it also charged the one asymmetry every real
    enclosure has to have: an interface. Measured on
    parts/custom/reference_mast_node_enclosure before this change - 0.87%
    asymmetric by volume about its best plane, symmetric to the eye and to the
    number, and scored 75.5 because its port-side connector bay is a 52 x 48 x
    33 mm lump spanning 30% of the bbox diagonal. Aspect ratio 1.6. That is not
    a sliver, it is a connector.

    Both parts below remove ~750 mm3 from the same side of the same box, and
    both cuts stay clear of all three mirror planes, so no axis sees a lump
    partly cancelled by its own image. The pocket is a chunk and is priced by
    the volume term alone;
    the groove is a sliver and pays the extent term in full. If this ever
    inverts, the term has gone back to measuring width and calling it thinness.
    """
    pocket = _lopsided(lambda wp: wp.center(18, 12).rect(10, 10).cutBlind(-7.5))
    groove = _lopsided(lambda wp: wp.center(15, 12).rect(26, 2.4).cutBlind(-12.0))
    a = review_shape(pocket)["metrics"]["symmetry"]
    b = review_shape(groove)["metrics"]["symmetry"]

    assert a["value"] == pytest.approx(b["value"], rel=0.05), (
        f"the fixtures must remove the same volume: {a['value']} vs {b['value']}"
    )
    assert a["extent"] == pytest.approx(0.0, abs=1e-6), (
        f"a 10 x 10 x 7.5 mm lump is a chunk, not a sliver: charged extent {a['extent']}"
    )
    assert a["raw_extent"] > 0.15, "and the review must still SAY the difference is there"
    assert b["extent"] > 0.35, f"a 26 x 2.4 x 12 mm lump is a sliver: {b['extent']}"
    assert a["score"] > 90.0 > b["score"], (
        f"compact {a['score']} must clear, slender {b['score']} must not"
    )


def test_sliver_weight_ramps_between_a_chunk_and_a_blade():
    """
    The ramp read directly, so the two constants are pinned to a meaning rather
    than to whatever the corpus happened to need.
    """
    assert dr._sliver_weight([10.0, 10.0, 10.0]) == 0.0, "a cube is not a sliver"
    assert dr._sliver_weight([52.0, 48.0, 33.0]) == 0.0, "the exemplar's connector bay"
    assert dr._sliver_weight([100.0, 5.0, 1.0]) == 1.0, "an unmirrored chamfer run"
    mid = dr._sliver_weight([55.0, 20.0, 10.0])  # aspect 5.5, between the knots
    assert 0.0 < mid < 1.0, mid
    assert dr._sliver_weight([1.0, 1.0, 0.0]) == 1.0, "a degenerate lump is never excused"


def test_symmetry_discloses_the_plane_it_did_not_score():
    """
    A 100.0 that reads "0.0% asymmetric volume" is the metric's most misleading
    output, and a box with a 20 x 20 x 16 boss welded to one end produces it:
    15.9% asymmetric about X, exactly symmetric about the other two, so the max
    over planes prints the plane that saw nothing.

    The score is defensible and is deliberately unchanged - this repo's own
    scaffold measures [X 18.6%, Y 0.0%, Z 32.7%] and its exemplar
    [X 0.9%, Y 10.2%, Z 35.9%], one connector end and one mounting face, which
    is the same measurement the welded boss makes. What must not survive is a
    message that lets a reader take it for "this part is symmetric".
    """
    box = cq.Workplane("XY").box(100, 60, 30)
    lumped = box.union(cq.Workplane("XY").box(20, 20, 16).translate((60, 0, 0)))

    m = dr._metric_symmetry(lumped.val())
    assert m["status"] == dr.SCORED and m["score"] == pytest.approx(100.0), m
    assert m["best_axis"] != "X" and m["value"] == pytest.approx(0.0), m
    # the plane the part actually fails on is named, with its own number
    assert m["worst_axis"] == "X", m
    assert m["worst_axis_score"] == pytest.approx(0.0), m
    assert m["per_axis"]["X"][0] > 0.15, m
    assert "least symmetric plane" in m["message"] and "15.9%" in m["message"], m["message"]
    assert "disclosed, not charged" in m["message"], m["message"]

    # a part with no asymmetry anywhere has nothing to disclose and says nothing
    plain = dr._metric_symmetry(box.val())
    assert plain["score"] == pytest.approx(100.0)
    assert "least symmetric plane" not in plain["message"], plain["message"]


def test_symmetry_max_faces_is_a_cost_guard_and_never_an_exemption():
    """
    It used to return NOT_REQUIRED: an integer knob in spec.json that deleted a
    metric from the rubric with no reason, no record and no cost, walking
    straight past the validator that demands a written justification for every
    waiver. Skipping a measurement to save time is a MEASUREMENT THAT DID NOT
    HAPPEN, so it is METRIC_ERROR - which under the error invariant costs the
    full weight at zero and cuts coverage.
    """
    box = _broken_body()
    assert len(box.val().Faces()) > dr.SYMMETRY_MAX_FACES_MIN, "the fixture must trip the guard"
    rep = review_shape(box, config={"symmetry_max_faces": dr.SYMMETRY_MAX_FACES_MIN})
    m = rep["metrics"]["symmetry"]
    assert m["status"] == dr.METRIC_ERROR and m["score"] is None
    assert "exceeds symmetry_max_faces" in m["message"]
    assert rep["coverage"] < 1.0, "an unmeasured metric must not count as covered"
    check = next(c for c in design_review_checks(rep) if c["id"] == "design_review.symmetry")
    assert check["status"] == "ERROR"

    # and the score can only go DOWN by skipping, never up
    honest = review_shape(box)
    assert rep["score"] <= honest["score"] + 1e-9, (
        f"skipping symmetry paid {rep['score']} against an honest {honest['score']}"
    )

    # below the floor it is a typo, not a decision
    bad = review_shape(box, config={"symmetry_max_faces": 3})
    assert [e["key"] for e in bad["config_errors"]] == ["symmetry_max_faces"]
    assert bad["metrics"]["symmetry"]["status"] == dr.SCORED, "the typo must not take effect"


def test_symmetry_mirrors_about_the_bbox_centre_not_the_centroid():
    """
    A part with holes has its centroid off the symmetry plane, so a centroid
    mirror differs from the part by a thin slab spanning the whole part. That
    made the difference EXTENT read 1.00 for anything with any asymmetry at all
    and scored two real, eye-symmetric parts a flat 0. Mirror symmetry forces
    the BBOX to be symmetric about the same plane, so the bbox centre is on it.
    """
    plate = (
        cq.Workplane("XY")
        .box(L, W, H)
        .faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(-20, 0), (20, 0)])
        .hole(6.0)
    )
    m = review_shape(plate)["metrics"]["symmetry"]
    assert m["score"] == pytest.approx(100.0), (
        f"this solid is exactly symmetric about YZ and XZ: {m['per_axis']}"
    )


def test_feature_composition_rewards_organisation_not_count(ladder):
    bare = metric(ladder["sharp"], "feature_composition")
    busy = metric(ladder["fasteners"], "feature_composition")
    assert bare["status"] == dr.ABSENT and bare["score"] == 0.0
    assert busy["status"] == dr.SCORED and busy["score"] > 80.0

    # adding MORE, unrelated features must LOWER it - the direct antidote to
    # the old feature_density, which counted faces and so rewarded flooding
    body = _broken_body()
    grid = (
        body.faces(">Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(x, y) for x in (-22, 0, 22) for y in (-14, 14)])
        .hole(4.5)
    )
    import random

    rng = random.Random(7)
    flooded = grid.faces(">Z").workplane(centerOption="CenterOfBoundBox")
    flooded = flooded.pushPoints(
        [(rng.uniform(-26, 26), rng.uniform(-17, 17)) for _ in range(12)]
    ).hole(3.0)
    tidy_score = review_shape(grid)["metrics"]["feature_composition"]["score"]
    flood_score = review_shape(flooded)["metrics"]["feature_composition"]["score"]
    assert flood_score < tidy_score, (
        f"flooding must be self-defeating: tidy {tidy_score}, flooded {flood_score}"
    )


def test_proportion_flags_slabs_and_sticks():
    def prop(shape):
        return review_shape(shape)["metrics"]["proportion"]

    balanced = prop(cq.Workplane("XY").box(50, 45, 40))
    stick = prop(cq.Workplane("XY").box(200, 6, 6))
    slab = prop(cq.Workplane("XY").box(200, 200, 2))
    assert balanced["score"] == 100.0 and not balanced["slab"] and not balanced["stick"]
    assert stick["stick"] and stick["score"] < balanced["score"]
    assert slab["slab"] and slab["score"] < balanced["score"]


# ---------------------------------------------------------------------------
# roles: a rubric may excuse a metric the part's function contradicts,
# and may never lighten the total bar
# ---------------------------------------------------------------------------
def test_every_role_rubric_sums_to_one_and_is_a_subset_of_the_metric_ids():
    for role, rubric in dr.ROLE_RUBRICS.items():
        assert set(rubric.weights) <= set(dr.METRIC_IDS), role
        assert sum(rubric.weights.values()) == pytest.approx(1.0), (
            f"role {role} must redistribute the weight it excuses, not drop it"
        )
    assert dr.ROLE_RUBRICS[dr.DEFAULT_ROLE].role == "enclosure"


def test_proportion_does_not_apply_to_the_roles_that_are_thin_by_function():
    """
    The audit's headline false negatives - a sealed cover at 50.2/D and a 2 mm
    sheet bracket at 43.1/D - were both scored near 0 on an aspect ratio that
    their function requires. There is no good answer for a thin part, so the
    metric is not applied to it.

    `bracket` IS NOT one of them, and used to be. `proportion` is max/min of the
    bounding box, and the only honest reason to drop it is a guard that pins
    that ratio: `_guard_thin` forces max/min >= 4 and `_guard_sheet` >= 10, so on
    those roles the exclusion is the geometry's own doing. `_guard_solid` reads
    the interior area fraction and bounds no bbox ratio at all, which made the
    exclusion free - measured, a 160 x 100 x 6 lid claiming `bracket` scored 0
    on proportion as an enclosure, was not asked as a bracket, and gained +14.7
    to band A for it.
    """
    slab = cq.Workplane("XY").box(200, 160, 8)
    for role in ("cover", "plate"):
        m = review_shape(slab, config={"role": role})["metrics"]["proportion"]
        assert m["status"] == dr.NOT_REQUIRED and m["score"] is None, role
    # `sheet` needs a FORMED part, not a flat slab: a blank with no bend radius
    # claims the blanked-perimeter exclusion and offers nothing in return, which
    # is a role error now (see _guard_sheet and the G2 tests below). So the
    # sheet half of this assertion is made on a part that is actually bent.
    bent = _formed_sheet_bracket()
    rep = review_shape(bent, config={"role": "sheet"})
    assert rep.get("role_error") is None, rep.get("role_error")
    assert rep["metrics"]["proportion"]["status"] == dr.NOT_REQUIRED
    for role in ("enclosure", "structural", "bracket"):
        m = review_shape(slab, config={"role": role})["metrics"]["proportion"]
        assert m["status"] == dr.SCORED, role


def test_an_unknown_role_is_an_error_and_falls_back_to_the_strictest_rubric():
    rep = review_shape(cq.Workplane("XY").box(L, W, H), config={"role": "widget"})
    assert rep["role"] == "enclosure"
    assert "unknown design role" in rep["role_error"]
    check = next(c for c in design_review_checks(rep) if c["id"] == "design_review.role")
    assert check["status"] == "ERROR"


def test_a_role_reports_the_rubric_it_was_judged_under():
    # a lid, so the cover CLAIM holds - a 60 x 40 x 25 box is not thin, and
    # calling it a cover is now a role error (see the role-guard tests below)
    rep = review_shape(cq.Workplane("XY").box(200, 160, 8), config={"role": "cover"})
    assert rep.get("role_error") is None, rep.get("role_error")
    assert rep["role"] == "cover"
    assert rep["rubric"]["weights"] == dr.ROLE_RUBRICS["cover"].weights
    assert "proportion" not in rep["weights"] or rep["metrics"]["proportion"]["status"] == (
        dr.NOT_REQUIRED
    )
    assert "role: cover" in format_report(rep)


# ---------------------------------------------------------------------------
# role GUARDS: a role is a claim about the geometry, and the geometry is asked
# ---------------------------------------------------------------------------
def test_a_role_the_geometry_contradicts_is_an_error_and_falls_back_to_enclosure():
    """
    Role selection used to rest entirely on author honesty: only `sheet` had any
    geometric guard, and it guarded only ONE of the three things that role
    changed. Measured on one identical 90 x 60 x 30 body, the six rubrics gave
    six different numbers with nothing to stop an author picking the best.
    """
    # A blended box with a pocketed underside: 3.0:1 so not long, 0.33 thin so
    # not thin, hollow enough not to be solid bracket stock, and it encloses a
    # void so it is not a formed blank. Every role but the default is a lie
    # about it, and the default claims nothing.
    body = cq.Workplane("XY").box(90, 60, 30).edges().fillet(10.0)
    body = body.cut(cq.Workplane("XY").box(70, 44, 22).val())
    scores = {}
    for role in dr.ROLES:
        rep = review_shape(body, config={"role": role})
        scores[role] = rep["score"]
        if role == dr.DEFAULT_ROLE:
            assert rep.get("role_error") is None
        else:
            assert rep["role"] == dr.DEFAULT_ROLE, f"{role} was honoured on geometry that denies it"
            assert rep["role_declared"] == role
            assert "claims to be" in rep["role_error"], role
            check = next(c for c in design_review_checks(rep) if c["id"] == "design_review.role")
            assert check["status"] == "ERROR", role
    assert len(set(scores.values())) == 1, f"role shopping still pays: {scores}"


def test_a_role_the_geometry_supports_is_honoured():
    """The guards refuse a false claim; they must not refuse a true one."""
    honoured = {
        "cover": cq.Workplane("XY").box(200, 160, 8).edges("|Z").fillet(R_PLAN),
        "plate": cq.Workplane("XY").box(200, 160, 8).edges("|Z").fillet(R_PLAN),
        "bracket": cq.Workplane("XY").box(80, 60, 40).edges("|Z").fillet(R_PLAN),
        "structural": cq.Workplane("XY").box(300, 50, 40).edges("|Z").fillet(R_PLAN),
    }
    for role, shape in honoured.items():
        rep = review_shape(shape, config={"role": role})
        assert rep.get("role_error") is None, f"{role}: {rep.get('role_error')}"
        assert rep["role"] == role


def test_a_thin_walled_hollow_enclosure_is_not_sheet_metal():
    """
    is_sheet_like derived the stock thickness as 2 * volume / area, which
    recovers the WALL thickness of a hollow box exactly as happily as the stock
    thickness of a formed blank: measured, a 3 mm walled 90 x 60 x 30 enclosure
    derived 2.99 mm and passed as sheet metal. A formed blank has no inside.
    """
    outer = cq.Workplane("XY").box(90, 60, 30)
    hollow = outer.cut(cq.Workplane("XY").box(84, 54, 24).val())
    topo = dr.Topology(hollow.val())
    assert topo.sheet_thickness < 0.10 * 90, "the thickness test alone still passes it"
    assert topo.interior_area_fraction() > dr.SHEET_INTERIOR_MAX_FRACTION
    assert topo.is_sheet_like() is False
    rep = review_shape(hollow, config={"role": "sheet"})
    assert rep["role"] == dr.DEFAULT_ROLE
    assert "enclosed void" in rep["role_error"]


def test_every_role_that_relaxes_anything_carries_a_guard():
    """The default rubric asserts nothing, so it is the only one without one."""
    for role, rubric in dr.ROLE_RUBRICS.items():
        if role == dr.DEFAULT_ROLE:
            assert role not in dr.ROLE_GUARDS and not rubric.claim
        else:
            assert role in dr.ROLE_GUARDS, f"{role} relaxes the rubric with nothing to pay for it"
            assert rubric.claim, f"{role} has a guard but does not say what it claims"


# ---------------------------------------------------------------------------
# the artifact, not the in-memory object
# ---------------------------------------------------------------------------
def test_review_step_reads_the_exported_artifact(tmp_path):
    step = tmp_path / "rung3.step"
    cq.exporters.export(rung3_edge_breaks(), str(step))
    rep = review_step(step)
    in_memory = review_shape(rung3_edge_breaks())
    assert rep["schema"] == SCHEMA
    assert rep["source"] == str(step)
    # The round trip re-splits faces, so the two are close but not identical -
    # which is exactly why the gate scores the artifact and not the model.
    assert rep["score"] == pytest.approx(in_memory["score"], abs=3.0)
    assert rep["band"] == in_memory["band"]
    with pytest.raises(FileNotFoundError, match="STEP file not found"):
        review_step(tmp_path / "nope.step")


# ---------------------------------------------------------------------------
# failures must never read as a pass
# ---------------------------------------------------------------------------
def test_a_shape_with_no_solids_is_an_error_not_a_score():
    rep = review_shape(cq.Workplane("XY").rect(5, 5))
    assert rep["status"] == "error" and rep["score"] is None and rep["band"] is None
    checks = design_review_checks(rep, {"min_score": 50})
    assert [c["status"] for c in checks] == ["ERROR"]
    assert checks[0]["measured"] is None


def test_topology_failure_surfaces_as_an_error(monkeypatch):
    def boom(_shape):
        raise RuntimeError("kernel traversal exploded")

    monkeypatch.setattr(dr, "Topology", boom)
    rep = review_shape(cq.Workplane("XY").box(10, 10, 10))
    assert rep["status"] == "error"
    assert rep["score"] is None, "a kernel failure must never produce a score"
    assert "kernel traversal exploded" in rep["message"]
    assert [c["status"] for c in design_review_checks(rep)] == ["ERROR"]


def test_one_failing_metric_errors_out_of_the_score_and_is_reported(monkeypatch):
    solid = rung3_edge_breaks()
    baseline = review_shape(solid)

    def boom(*args, **kwargs):
        raise RuntimeError("face-composition measurement exploded")

    monkeypatch.setattr(dr, "_metric_face_composition", boom)
    rep = review_shape(solid)
    m = rep["metrics"]["face_composition"]
    assert m["status"] == dr.METRIC_ERROR and m["score"] is None
    assert "face-composition measurement exploded" in m["message"]
    assert rep["errored"] == ["face_composition"]
    # dropped from the weighted score, and the loss of confidence is published
    assert rep["coverage"] == pytest.approx(
        baseline["coverage"] - DEFAULT_WEIGHTS["face_composition"], abs=1e-6
    )
    assert rep["score"] is not None, "one lost metric should still leave a verdict"
    checks = design_review_checks(rep)
    check = next(c for c in checks if c["id"] == "design_review.face_composition")
    assert check["status"] == "ERROR" and check["measured"] is None


def test_silent_degradation_is_an_error_and_never_a_perfect_score(monkeypatch):
    """
    THE audit finding this module exists to never repeat. When every convexity
    probe failed, unresolved edges were removed from the DENOMINATOR instead of
    from the METRIC: on a 120x80x40 box with R10 plan fillets, coverage went
    from 0.173 (score 2.9) to 1.00 (score 100.0) with no ERROR and no finding.
    26% of the total weight flipped from 2.9 to a perfect 100 because the kernel
    stopped answering.

    There are now TWO convexity probes, and "every probe failed" means both.
    `Topology._convex` is the off-edge test that replaced the degenerate
    first-order one; `Topology._convex_at_edge` is that first-order test, kept
    as a fallback a CREASE may use when the neighbour face will not yield an
    interior point. Disabling only the first leaves the fallback resolving 70.5%
    of this box's edge length - the metric still ERRORs and still refuses a
    score, which is the property under test, but `unmeasured_fraction` reads
    0.2948 rather than 1.0. Patch both, or this test silently stops testing the
    total failure it is named for.
    """
    solid = cq.Workplane("XY").box(120, 80, 40).edges("|Z").fillet(10.0)
    healthy = review_shape(solid)["metrics"]["edge_break_coverage"]
    assert healthy["status"] == dr.SCORED and healthy["score"] < 20.0

    monkeypatch.setattr(dr.Topology, "_convex", lambda *a, **k: None)
    monkeypatch.setattr(dr.Topology, "_convex_at_edge", lambda *a, **k: None)
    rep = review_shape(solid)
    m = rep["metrics"]["edge_break_coverage"]
    assert m["status"] == dr.METRIC_ERROR, (
        f"a total failure of the convexity test must be an ERROR, got {m['status']} "
        f"score {m['score']}"
    )
    assert m["score"] is None
    assert m["unmeasured_fraction"] > 0.9
    assert "edge_break_coverage" in rep["errored"]
    check = next(
        c for c in design_review_checks(rep) if c["id"] == "design_review.edge_break_coverage"
    )
    assert check["status"] == "ERROR"


def test_losing_only_the_primary_convexity_probe_still_refuses_a_score(monkeypatch):
    """
    The half-failure, which is the one a real kernel produces.

    Disabling `Topology._convex` alone leaves the crease fallback answering for
    most of the edge length, so this is NOT the total failure above - and it is
    exactly the shape of degradation that used to be absorbed into the
    denominator. The metric must still report ERROR and no score.
    """
    solid = cq.Workplane("XY").box(120, 80, 40).edges("|Z").fillet(10.0)
    monkeypatch.setattr(dr.Topology, "_convex", lambda *a, **k: None)
    m = review_shape(solid)["metrics"]["edge_break_coverage"]
    assert m["status"] == dr.METRIC_ERROR and m["score"] is None
    assert 0.0 < m["unmeasured_fraction"] < 1.0


def test_a_partly_degraded_metric_reports_the_loss_outside_any_score_gate():
    """
    The unresolved-edge warning used to sit inside `if score < 90`, so it could
    never fire in the one case that mattered - unresolved edges pushing coverage
    to a false 100. Degradation is a condition of the MEASUREMENT.
    """
    rep = review_shape(rung3_edge_breaks())
    metrics = rep["metrics"]
    for mid, m in metrics.items():
        if m["status"] in (dr.SCORED, dr.ABSENT):
            assert m.get("unmeasured_fraction", 0.0) == pytest.approx(0.0, abs=1e-9), (
                f"{mid} should be fully measurable on a clean box: {m}"
            )
    # and the finding is not gated behind a score
    findings = dr._build_findings(
        dr.Topology(rung3_edge_breaks().val()),
        {"edge_break_coverage": dict(metrics["edge_break_coverage"], unmeasured_fraction=0.4)},
        dr.DEFAULT_RADIUS_LADDER,
    )
    assert any(f["id"] == "degraded_measurement" for f in findings)


def test_a_failure_of_the_feature_extractor_errors_the_metrics_that_need_it(monkeypatch):
    """
    Audit defect 12: `except Exception: features = []` made a failed extraction
    indistinguishable from a part with no holes, so two metrics reported a shape
    of the FAILURE as though it were a shape of the part.
    """

    def boom(_shape):
        raise RuntimeError("cylinder feature extraction exploded")

    monkeypatch.setattr(dr, "_cylinder_features", boom)
    rep = review_shape(rung3_edge_breaks())
    assert "exploded" in rep["shape"]["features_error"]
    for mid in ("feature_composition", "pattern_discipline"):
        m = rep["metrics"][mid]
        assert m["status"] == dr.METRIC_ERROR and m["score"] is None, mid
    ids = {c["id"]: c["status"] for c in design_review_checks(rep)}
    assert ids["design_review.pattern_discipline"] == "ERROR"


def test_too_much_unmeasurable_weight_refuses_to_give_a_verdict(monkeypatch):
    """Below MIN_COVERAGE the module must say so rather than flatter the part."""

    def boom(*args, **kwargs):
        raise RuntimeError("kernel exploded")

    monkeypatch.setattr(dr, "_metric_edge_break", boom)  # weight .21
    monkeypatch.setattr(dr, "_metric_face_composition", boom)  # weight .19
    monkeypatch.setattr(dr, "_metric_feature_composition", boom)  # weight .16
    rep = review_shape(rung3_edge_breaks())
    assert set(rep["errored"]) >= {
        "edge_break_coverage",
        "face_composition",
        "feature_composition",
    }
    assert rep["coverage"] < dr.MIN_COVERAGE
    assert rep["status"] == "insufficient"
    assert "treat the score as indicative" in rep["message"]
    score_check = next(
        c for c in design_review_checks(rep, {"min_score": 10}) if c["id"] == "design_review.score"
    )
    assert score_check["status"] == "ERROR", (
        "an unreliable score must not be allowed to PASS a threshold"
    )


# ---------------------------------------------------------------------------
# the evaluate.py bridge and the spec.json config contract
# ---------------------------------------------------------------------------
def test_checks_gate_on_the_overall_score(ladder):
    below = design_review_checks(ladder["sharp"], {"min_score": 70, "severity": "hard"})
    above = design_review_checks(ladder["fasteners"], {"min_score": 70})
    score_below = next(c for c in below if c["id"] == "design_review.score")
    score_above = next(c for c in above if c["id"] == "design_review.score")
    assert score_below["status"] == "FAIL" and score_below["severity"] == "hard"
    assert score_above["status"] == "PASS" and score_above["severity"] == "soft", (
        "soft by default, so turning the review on cannot break an existing part"
    )
    assert score_below["measured"] == ladder["sharp"]["score"]


def test_per_metric_gates_use_score_and_raw_value(ladder):
    cfg = {
        "metrics": {
            "edge_break_coverage": {"min_score": 80, "severity": "hard"},
            "face_composition": {"max_value": 0.55},
            "proportion": {"max_value": 10.0},
        }
    }
    by_id = {c["id"]: c for c in design_review_checks(ladder["sharp"], cfg)}
    assert by_id["design_review.edge_break_coverage"]["status"] == "FAIL"
    assert by_id["design_review.edge_break_coverage"]["severity"] == "hard"
    assert by_id["design_review.face_composition"]["status"] == "FAIL"
    assert by_id["design_review.face_composition"]["measured"] > 0.55
    assert by_id["design_review.proportion"]["status"] == "PASS", (
        "60 x 40 x 25 is 2.4:1 - well inside a 10:1 gate"
    )
    # ungated metrics stay out of the report so it does not become noise
    assert "design_review.symmetry" not in by_id


def test_waived_and_disabled_metrics_emit_no_check_and_no_score():
    cfg = {
        "waivers": {"symmetry": "handed part - mirrored variant by design"},
        "metrics": {"pattern_discipline": {"enabled": False, "reason": "welded, not bolted"}},
    }
    rep = review_shape(rung3_edge_breaks(), config=cfg)
    assert rep["metrics"]["symmetry"]["status"] == dr.NOT_REQUIRED
    assert rep["metrics"]["symmetry"]["waived"] is True
    assert rep["metrics"]["pattern_discipline"]["status"] == dr.NOT_REQUIRED
    ids = {c["id"] for c in design_review_checks(rep, cfg)}
    assert "design_review.symmetry" not in ids
    assert "design_review.pattern_discipline" not in ids
    assert rep["coverage"] == pytest.approx(
        1.0 - DEFAULT_WEIGHTS["symmetry"] - DEFAULT_WEIGHTS["pattern_discipline"], abs=1e-6
    )
    # every excusal is RECORDED, with its reason and its share of the rubric
    assert set(rep["excused"]) == {"symmetry", "pattern_discipline"}
    assert "welded, not bolted" in rep["excused"]["pattern_discipline"]
    assert rep["excused_weight"] == pytest.approx(1.0 - rep["coverage"], abs=1e-6)
    # ... and so is what it bought, because a waiver is renormalised OUT and
    # waiving a metric the part fails always raises the score
    assert rep["score_unexcused"] <= rep["score"]
    assert "the waivers are worth" in format_report(rep)


def test_disabling_a_metric_without_a_reason_is_a_config_error():
    """
    `metrics.<id>.enabled: false` is a waiver by another name and reached
    NOT_REQUIRED with no reason at all, while design.waivers next door demanded
    a written justification for exactly the same effect.
    """
    rep = review_shape(
        rung3_edge_breaks(), config={"metrics": {"pattern_discipline": {"enabled": False}}}
    )
    assert [e["key"] for e in rep["config_errors"]] == ["metrics.pattern_discipline.enabled"]
    assert rep["metrics"]["pattern_discipline"]["status"] != dr.NOT_REQUIRED
    check = next(c for c in design_review_checks(rep) if c["id"].startswith("design_review.config"))
    assert check["status"] == "ERROR"


def test_excusal_by_assertion_is_capped_below_min_coverage():
    """
    MIN_COVERAGE alone let 40% of the rubric be waived on the author's say-so.
    A written reason makes an excusal deliberate; it does not make it measured.
    """
    # sharp_edge_length used to be the fourth waiver here. It carries a rubric
    # floor now and cannot be waived at all, so the fourth is a metric that has
    # no floor - the cap and the floors are separate mechanisms and this test is
    # about the cap.
    cfg = {
        "waivers": {
            "symmetry": "handed part",
            "proportion": "stock length is fixed by the mast",
            "pattern_discipline": "welded assembly, not bolted",
            "radius_vocabulary": "as-cast finish",
        }
    }
    rep = review_shape(rung3_edge_breaks(), config=cfg)
    assert rep["config_errors"] == [], rep["config_errors"]
    assert rep["excused_weight"] > dr.MAX_EXCUSED_WEIGHT
    assert rep["coverage"] > dr.MIN_COVERAGE, "this is the cap biting, not MIN_COVERAGE"
    assert rep["status"] == "insufficient"
    assert "excused by assertion" in rep["message"]
    check = next(c for c in design_review_checks(rep, cfg) if c["id"] == "design_review.score")
    assert check["status"] == "ERROR"


def test_breaking_a_metric_never_pays_more_than_scoring_it(monkeypatch):
    """
    THE ERROR INVARIANT, second half. METRIC_ERROR used to be renormalised out
    of the weighted mean exactly like a role exclusion, so BREAKING a metric was
    worth as much as being EXCUSED it - and the cheapest way to delete the one
    metric that would catch a sculpted blob was to sculpt it hard enough that
    the metric could not read it. An errored metric now sits in the denominator
    contributing zero.
    """
    shape = rung5_fasteners()
    honest = review_shape(shape)

    def boom(*args, **kwargs):
        raise RuntimeError("kernel exploded")

    for mid, fn in (
        ("face_composition", "_metric_face_composition"),
        ("pattern_discipline", "_metric_pattern_discipline"),
        ("radius_vocabulary", "_metric_radius_vocabulary"),
    ):
        monkeypatch.setattr(dr, fn, boom)
        rep = review_shape(shape)
        monkeypatch.undo()
        assert rep["metrics"][mid]["status"] == dr.METRIC_ERROR
        scored = honest["metrics"][mid]["score"]
        assert rep["score"] <= honest["score"] + 1e-9, (
            f"breaking {mid} scored {rep['score']} against an honest {honest['score']} "
            f"(the metric would have measured {scored})"
        )
        # ... and it is still reported as an ERROR, not silently absorbed
        assert mid in rep["errored"]
        assert rep["coverage"] < 1.0
        check = next(c for c in design_review_checks(rep) if c["id"] == f"design_review.{mid}")
        assert check["status"] == "ERROR"


def test_mirroring_a_random_scatter_does_not_manufacture_organisation():
    """
    _organised_fraction implemented "the fraction of feature centres sharing a
    small number of common lines" WITHOUT the "small number" part, and measured
    each axis independently, so mirroring ANY random scatter about both
    centrelines made every u a shared u and every v a shared v. Measured: a
    crude box went 31.2 -> 50.1 purely by 4-fold-mirroring a random number
    generator, feature_composition 4 -> 100.
    """
    import random

    def drilled(points):
        body = cq.Workplane("XY").box(200.0, 140.0, H)
        for x, y in points:
            body = body.cut(
                cq.Solid.makeCylinder(2.5, H + 8, cq.Vector(x, y, -H), cq.Vector(0, 0, 1))
            )
        return review_shape(body)["metrics"]["feature_composition"]

    rng = random.Random(41)
    seeds = [(rng.uniform(15.0, 90.0), rng.uniform(12.0, 60.0)) for _ in range(4)]
    mirrored = [(sx * x, sy * y) for x, y in seeds for sx in (1, -1) for sy in (1, -1)]
    scattered = [(rng.uniform(-88, 88), rng.uniform(-58, 58)) for _ in range(16)]

    m_mirror, m_scatter = drilled(mirrored), drilled(scattered)
    assert m_mirror["score"] <= m_scatter["score"] + 5.0, (
        f"4-fold mirroring a random scatter bought {m_mirror['score']} against "
        f"{m_scatter['score']} for the same 16 holes placed at random"
    )
    assert m_mirror["score"] < 20.0, f"mirrored noise is not a composition: {m_mirror['message']}"
    # the lattice economy is what says so: 16 holes over 8 x 8 centrelines
    fam = max(m_mirror["families"], key=lambda f: f["count"])
    assert fam["per_axis"] == [1.0, 1.0], "both axes still read as fully aligned, as they should"
    assert fam["lattice_economy"] <= 0.3, "...but the lattice they define is three quarters empty"


def test_a_real_bolt_lattice_keeps_its_organisation():
    """The economy factor must not punish the patterns it exists to reward."""

    def drilled(points):
        body = cq.Workplane("XY").box(200.0, 140.0, H)
        for x, y in points:
            body = body.cut(
                cq.Solid.makeCylinder(2.5, H + 8, cq.Vector(x, y, -H), cq.Vector(0, 0, 1))
            )
        return review_shape(body)["metrics"]["feature_composition"]

    corners = [(x, y) for x in (-80, 80) for y in (-55, 55)]
    grid = [(x, y) for x in (-75, -25, 25, 75) for y in (-45, 0, 45)]
    for label, pts in (("2 x 2 corners", corners), ("4 x 3 grid", grid)):
        m = drilled(pts)
        assert m["score"] > 90.0, f"{label} is a pattern, got {m['score']}: {m['message']}"


def test_waiving_edge_break_does_not_fake_a_kernel_error_next_door():
    """
    The `breaks` dict was filled as a SIDE EFFECT of the edge_break metric, and
    run() short-circuits on a waiver BEFORE calling it, so sharp_edge_length saw
    an empty dict and reported a kernel error - "edge classification did not
    run" - on a part where nothing was wrong. At the documented
    metric_severity=hard that failed the build.

    The waiver that triggered it is now REFUSED outright - edge_break_coverage
    carries a rubric floor - so the old path is unreachable twice over. Both
    halves are asserted here: the waiver is rejected AND the shared-input
    arrangement that fixed the original defect still holds, because the second
    guarantee is the one that would rot silently if the first were relaxed.
    """
    cfg = {"waivers": {"edge_break_coverage": "prototype - breaks come with the tooling"}}
    rep = review_shape(rung3_edge_breaks(), config=cfg)
    assert [e["key"] for e in rep["config_errors"]] == ["waivers.edge_break_coverage"]
    assert rep["metrics"]["edge_break_coverage"]["status"] == dr.SCORED
    assert rep["excused"] == {}, "a refused waiver must not excuse anything"
    m = rep["metrics"]["sharp_edge_length"]
    assert m["status"] == dr.SCORED, f"a waiver next door errored this metric: {m['message']}"
    assert m["score"] == review_shape(rung3_edge_breaks())["metrics"]["sharp_edge_length"]["score"]
    assert rep["errored"] == []


def test_the_weights_override_is_gone():
    """
    THE HEADLINE BYPASS. Measured on a crude knife-edged box with four random
    holes: 27.7/F honestly, 100.0/A with six design.weights entries set to zero,
    425.5/A with two of them negative - every hard check green, no geometry
    required, and coverage stayed 1.00 because it was computed FROM the
    overridden weights. Unlike a waiver it needed no reason, and unlike
    metrics.enabled=false it did not even cut coverage.
    """
    shape = cq.Workplane("XY").box(L, W, H)
    honest = review_shape(shape)
    for weights in (
        dict.fromkeys(dr.METRIC_IDS, 0.0),
        {"edge_break_coverage": 0.0, "sharp_edge_length": 0.0, "face_composition": 0.0},
        {"edge_break_coverage": -0.5, "sharp_edge_length": -0.2},
    ):
        cfg = {"weights": weights}
        rep = review_shape(shape, config=cfg)
        assert rep["score"] == honest["score"], f"design.weights still moves the score: {weights}"
        assert rep["weights"] == dr.ROLE_RUBRICS[dr.DEFAULT_ROLE].weights
        assert [e["key"] for e in rep["config_errors"]] == ["weights"]
        check = next(
            c
            for c in design_review_checks(rep, {**cfg, "min_score": 70, "severity": "hard"})
            if c["id"].startswith("design_review.config")
        )
        assert check["status"] == "ERROR" and check["severity"] == "hard"


def test_the_radius_ladder_override_is_gone():
    """
    THE SURVIVING HALF OF THE WEIGHTS BYPASS.

    `style.radius_ladder` was validated for SHAPE - at least five distinct
    rungs, a 4:1 span, a written reason - and never for the only thing that
    mattered, which is whether the rungs were a transcription of the part's own
    measured radii. A ladder that passes every one of those checks and happens
    to contain exactly this part's radii took radius_vocabulary from 0.0 to
    100.0 on unchanged geometry, which is the `weights` defect wearing a
    plausible costume.

    It is retired by the same route `weights` was, so a ladder that would have
    been ACCEPTED under the old validator is now an ERROR and changes nothing.
    """
    shape = cq.Workplane("XY").box(L, W, H).edges("|Z").fillet(6.5)
    default = review_shape(shape)
    assert default["metrics"]["radius_vocabulary"]["score"] == 0.0

    # the shape the old validator demanded: 5+ rungs, >4:1 span, a reason, and
    # 6.5 quietly among them
    cfg = {
        "style": {
            "radius_ladder": [1.0, 2.0, 4.0, 6.5, 10.0, 16.0],
            "reason": "cast tooling family, not machined",
        }
    }
    rep = review_shape(shape, config=cfg)
    assert [e["key"] for e in rep["config_errors"]] == ["style.radius_ladder"]
    assert "has been removed" in rep["config_errors"][0]["message"]
    assert rep["style"]["radius_ladder"] == list(dr._load_ladder()[0])
    assert "lib.features" in rep["style"]["ladder_source"]
    assert rep["metrics"]["radius_vocabulary"]["score"] == 0.0, (
        "the override must buy exactly nothing, not merely be complained about"
    )
    assert rep["score"] == default["score"]

    # and it is an ERROR check at the OVERALL severity, like every retired key
    checks = design_review_checks(rep, {**cfg, "severity": "hard"})
    check = next(c for c in checks if c["id"].startswith("design_review.config"))
    assert check["status"] == "ERROR" and check["severity"] == "hard"

    # config_errors() is the front door lib/evaluate.py uses, and it must agree
    assert any("style.radius_ladder" in m for m in dr.config_errors(cfg))


# ---------------------------------------------------------------------------
# rubric floors: the bar no weighted average may launder
# ---------------------------------------------------------------------------
def _knife_slab():
    """
    The measured worst part that could still pass a hard gate: a flat
    220 x 150 x 9 slab, three sunken pockets at three depths, ten border holes
    at a constant pitch and inset, and NOT ONE EDGE BROKEN anywhere.

    Under the default rubric it scores in the low 40s. The attack was to claim
    `plate`, declare a private radius ladder and waive the one metric it fails,
    which took it to 85.6/B - clearing a hard 70 gate with edge_break_coverage
    at 0.0.
    """
    body = cq.Workplane("XY").rect(220.0, 150.0).extrude(9.0).edges("|Z").fillet(11.0)
    for cx, depth in ((-66.0, 6.0), (0.0, 4.0), (66.0, 2.0)):
        tool = (
            cq.Workplane("XY")
            .center(cx, 0.0)
            .rect(62.0, 118.0)
            .extrude(depth + 1.0)
            .edges("|Z")
            .fillet(7.5)
            .translate((0, 0, 9.0 - depth))
        )
        body = body.cut(tool)
    holes = [(x, y) for y in (-65.0, 65.0) for x in (-90.0, -45.0, 0.0, 45.0, 90.0)]
    return body.faces(">Z").workplane(origin=(0, 0, 9.0)).pushPoints(holes).hole(6.0)


def test_a_part_with_no_broken_edge_cannot_reach_a_passing_band():
    """
    THE DECISIVE STRUCTURAL FIX. Every other guard in this module is a
    contribution to a weighted mean, and a mean can be arbitraged: pick the role
    whose column is lightest where you are weak and spend one waiver. A floor is
    a hard minimum on a SINGLE metric, checked outside the mean, so none of that
    reaches it.
    """
    shape = _knife_slab()
    for role in (None, "plate", "cover", "bracket", "sheet", "structural"):
        cfg = {"min_score": 70.0, "severity": "hard"}
        if role:
            cfg["role"] = role
        rep = review_shape(shape, config=cfg)
        assert rep["metrics"]["edge_break_coverage"]["score"] == 0.0, rep["metrics"]
        assert "edge_break_coverage" in rep["floor_failures"], role
        assert rep["band"] == dr.FLOOR_BAND_CAP, (role, rep["score"], rep["band"])
        assert dr._BAND_RANK[rep["band"]] > dr._BAND_RANK["B"], "band D must be below band B"

        checks = design_review_checks(rep, cfg)
        floor_id = "design_review.floor.edge_break_coverage"
        floor_check = next(c for c in checks if c["id"] == floor_id)
        assert floor_check["status"] == "FAIL" and floor_check["severity"] == "hard"
        score_check = next(c for c in checks if c["id"] == "design_review.score")
        assert score_check["status"] == "FAIL", "an unmet floor must fail the score check too"


def test_metric_severity_never_reaches_a_floor():
    """
    `metric_severity` is the author saying which METRICS matter to them, and
    "this metric does not matter to me" is precisely the claim a floor exists to
    refuse - so it does not reach one, per-metric `severity` does not either,
    and the floor is emitted at the OVERALL severity instead.

    `severity` is a different question - whether this build is gated on design
    at all - and it is deliberately NOT the floor's to answer: a part predating
    the gate must still only warn. What is guaranteed is that whenever the
    design gate is hard, the floor is hard, which is what the audit's part was
    clearing. Both halves are asserted.
    """
    shape = _knife_slab()

    soft_metrics = {
        "severity": "hard",
        "metric_severity": "soft",
        "metrics": {"edge_break_coverage": {"severity": "soft", "min_score": 95}},
        "min_score": 70.0,
    }
    floor_check = next(
        c
        for c in design_review_checks(review_shape(shape, config=soft_metrics), soft_metrics)
        if c["id"].startswith("design_review.floor.")
    )
    assert floor_check["severity"] == "hard", "metric_severity must not soften a floor"
    assert floor_check["status"] == "FAIL"

    # an advisory review still cannot report a passing band, it just does not
    # break a build that never opted in
    advisory = {"severity": "soft", "metric_severity": "soft"}
    rep = review_shape(shape, config=advisory)
    checks = design_review_checks(rep, advisory)
    assert rep["band"] == dr.FLOOR_BAND_CAP
    assert next(c for c in checks if c["id"] == "design_review.score")["status"] == "FAIL"
    assert next(c for c in checks if c["id"].startswith("design_review.floor."))["status"] == "FAIL"


def test_a_spec_may_raise_a_floor_and_cannot_express_lowering_one():
    """
    Every route by which a part could talk a floor down is a config ERROR, not
    a silently-outranked number: a floor a part can waive, disable or lower is
    not a floor, and an agent who writes one of these and sees no complaint will
    believe it worked.
    """
    shape = _knife_slab()
    mid = "edge_break_coverage"
    floor = dr.RUBRIC_FLOORS[mid].score

    for cfg, key in (
        ({"waivers": {mid: "sealed by the mating flange"}}, f"waivers.{mid}"),
        ({"metrics": {mid: {"enabled": False, "reason": "prototype"}}}, f"metrics.{mid}.enabled"),
        ({"metrics": {mid: {"min_score": floor - 1}}}, f"metrics.{mid}.min_score"),
    ):
        rep = review_shape(shape, config=cfg)
        assert [e["key"] for e in rep["config_errors"]] == [key], cfg
        # ... and it had no effect: the metric still ran and the floor still bit
        assert rep["metrics"][mid]["status"] == dr.SCORED
        assert mid in rep["floor_failures"]
        assert rep["band"] == dr.FLOOR_BAND_CAP

    # RAISING it is fine and needs no reason, exactly like any other gate
    rep = review_shape(shape, config={"metrics": {mid: {"min_score": floor + 40}}})
    assert rep["config_errors"] == []


def test_no_good_corpus_case_trips_a_floor():
    """
    A floor that fires on a legitimately good part is worse than no floor: it
    teaches agents that the gate is noise. Every floor level in RUBRIC_FLOORS is
    calibrated against the lowest `good` case in tests/design_corpus.py under
    its own role, and this asserts that calibration against the real solids
    rather than against a remembered number.
    """
    from tests.design_corpus import CASES, review  # noqa: PLC0415

    checked = 0
    for case in CASES:
        if case.klass != "good" or case.slow:
            continue
        rep = review(case)
        assert rep.get("floor_failures") == [], (
            f"{case.id} (role {case.role}) trips a floor: "
            f"{[f for f in rep['floors'] if not f['met']]}"
        )
        assert rep["band"] == rep["band_uncapped"]
        checked += 1
    assert checked >= 5, f"only {checked} good cases were actually checked"


def test_an_errored_floored_metric_does_not_clear_its_floor(monkeypatch):
    """
    Under the error invariant an unmeasured metric already costs its full weight
    at zero. A floor it could not be measured against must not read as cleared,
    or breaking the measurement becomes cheaper than passing it - which is the
    exact trade the error invariant exists to close.
    """
    monkeypatch.setattr(
        dr, "_metric_edge_break", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kernel"))
    )
    rep = review_shape(rung5_fasteners())
    assert rep["metrics"]["edge_break_coverage"]["status"] == dr.METRIC_ERROR
    assert "edge_break_coverage" in rep["floor_failures"]
    assert rep["band"] == dr.FLOOR_BAND_CAP


# ---------------------------------------------------------------------------
# G1/G2: the body term and the rim term must never substitute for each other
# ---------------------------------------------------------------------------
def _raw_box_with_deburred_bores():
    """
    A raw prism: not one body corner broken, every bore mouth deburred.

    This is G1. The composite is 0.85 body + 0.15 rim, so the rim term alone was
    worth 15.0 against a composite floor of 10.0 - and the floor is named after
    exactly the defect this part has.
    """
    body = cq.Workplane("XY").box(90.0, 60.0, 30.0).val()
    for x, y in ((-36, -22), (-12, -22), (12, -22), (36, -22), (-36, 22), (36, 22), (0, 0)):
        body = body.cut(cq.Solid.makeCylinder(4.0, 60.0, cq.Vector(x, y, -30)))
        for z, d in ((15.0, (0, 0, -1)), (-15.0, (0, 0, 1))):
            body = body.cut(cq.Solid.makeCone(5.0, 4.0, 1.0, cq.Vector(x, y, z), cq.Vector(*d)))
    return body


def test_deburring_the_bores_cannot_clear_the_edge_break_floor():
    """
    G1. Measured on this exact solid: rim coverage 100%, body coverage 0.0%,
    composite 15.0 - which used to clear a floor of 10.0 set on the composite.
    The floor now reads the BODY term, which is 0.0.
    """
    rep = review_shape(_raw_box_with_deburred_bores())
    m = rep["metrics"]["edge_break_coverage"]
    assert m["status"] == dr.SCORED
    assert m["rim_score"] == pytest.approx(100.0), m
    assert m["body_score"] == pytest.approx(0.0), m
    assert m["score"] > dr.RUBRIC_FLOORS["edge_break_coverage"].score, (
        "the premise of the test is that the COMPOSITE still clears the old floor"
    )
    assert "edge_break_coverage" in rep["floor_failures"], m
    # the cap only ever LOWERS a band, so at or below it, never above
    assert dr._BAND_RANK[rep["band"]] >= dr._BAND_RANK[dr.FLOOR_BAND_CAP], rep["band"]
    floor = next(f for f in rep["floors"] if f["metric"] == "edge_break_coverage")
    assert floor["score"] == pytest.approx(0.0) and "body term" in floor["detail"]
    assert any(f["id"] == "rim_carrying_body" for f in rep["findings"]), rep["findings"]


def test_the_floor_is_held_against_the_body_term_not_the_composite():
    """The floor's key is data, not a coincidence of the current numbers."""
    floor = dr.RUBRIC_FLOORS["edge_break_coverage"]
    assert floor.key == "body_score"
    assert dr.RUBRIC_FLOORS["sharp_edge_length"].key == "score"


def test_a_flat_blank_cannot_claim_the_sheet_perimeter_exclusion():
    """
    G2a. `sheet` deletes the whole blanked perimeter from the edge population,
    so on a flat blank the body population is empty and the metric collapsed
    onto its rim term: a raw 120 x 80 x 2 blank with four countersunk rivet
    holes measured edge_break_coverage 55.6 as sheet, and sharp_edge_length is
    not in that role's rubric at all, so neither floor applied.

    The exclusion is paid for by the formed radii the part is judged on instead.
    A blank has none, so the claim is false and the part is re-judged as an
    enclosure - where both floors apply and both fail.

    What "has none" MEANS was itself too weak at first: the test read any small
    blend cylinder, so four plan radii milled into the outline of a solid blank
    read as forming. It now reads `Topology.bend_pairs()` - a coaxial pair of
    cylinders separated by the material thickness. See tests/test_role_guards.py.
    """
    blank = cq.Workplane("XY").box(120.0, 80.0, 2.0)
    rep = review_shape(blank, config={"role": "sheet"})
    assert rep["role"] == "enclosure"
    assert "no bend at all" in rep["role_error"], rep["role_error"]
    assert set(rep["floor_failures"]) == {"edge_break_coverage", "sharp_edge_length"}

    # ... and a part that really is formed still gets the role it claims
    formed = review_shape(_formed_sheet_bracket(), config={"role": "sheet"})
    assert formed["role"] == "sheet" and formed.get("role_error") is None


def test_a_body_of_revolution_is_judged_on_its_own_silhouette():
    """
    G2b. is_bore_wall used to mean "any cylindrical face that is not a blend",
    which swept in the OD of every turned part: the body population emptied to
    zero and the composite renormalised onto the rim, so one chamfered socket
    mouth scored edge_break_coverage 100.0 on a raw turned blank.

    The OD of a body of revolution is silhouette. A turned part with its corners
    broken scores high, and the same part with only its bore mouths deburred
    scores the rim term and fails the floor.
    """
    raw = review_shape(_turned(breaks=False))["metrics"]["edge_break_coverage"]
    assert raw["status"] == dr.SCORED
    assert raw["body_broken_mm"] + raw["body_sharp_mm"] > 100.0, (
        f"a turned part has a silhouette and the metric must see it: {raw}"
    )
    assert raw["rim_score"] == pytest.approx(100.0) and raw["body_score"] == pytest.approx(0.0)
    assert raw["score"] < 20.0, raw

    good = review_shape(_turned(breaks=True))["metrics"]["edge_break_coverage"]
    assert good["body_score"] == pytest.approx(100.0), good
    assert review_shape(_turned(breaks=True))["floor_failures"] == []


def test_a_boss_on_a_prismatic_part_is_still_a_rim_not_a_silhouette():
    """
    The barrel rule is scoped to bodies of revolution ON PURPOSE. Promoting the
    outside of EVERY cylinder to the silhouette was measured to take the corpus
    exemplar from edge_break_coverage 92.9 to 55.6 and the sheet bracket from
    20.6 to 0.3, for a defect neither part has.
    """
    body = cq.Workplane("XY").box(L, W, H).edges("|Z").fillet(R_PLAN)
    body = body.faces(">Z").workplane().circle(8.0).extrude(6.0)
    topo = dr.Topology(body.val())
    assert topo.revolution_axis() is None
    boss = [
        i
        for i, rec in enumerate(topo.faces)
        if rec["kind"] == "cylinder" and abs((rec["radius"] or 0) - 8.0) < 1e-6
    ]
    assert boss, "the boss barrel is missing from the topology"
    for fi in boss:
        assert topo.is_bore_wall(fi) and not topo.is_barrel_face(fi)


# ---------------------------------------------------------------------------
# G3: a vocabulary has to be APPLIED, not just coherent
# ---------------------------------------------------------------------------
def test_one_chamfer_is_not_a_radius_vocabulary():
    """
    G3. radius_vocabulary was area-weighted over the break faces with the break
    faces as their own denominator, so a raw billet with ONE on-ladder chamfer
    scored a flat 100.0 at weight 0.11-0.14.
    """
    billet = cq.Workplane("XY").box(90.0, 60.0, 30.0).edges(">Z and >X").chamfer(2.5)
    m = review_shape(billet)["metrics"]["radius_vocabulary"]
    assert m["value"] == pytest.approx(1.0), "the premise: the one chamfer IS on the ladder"
    assert [d["on_ladder"] for d in m["distinct"]] == [True]
    assert m["applied"] < 0.10, m
    assert m["score"] < 30.0, m
    # and the score is exactly conformance x the coverage gate, nothing hidden
    assert m["score"] == pytest.approx(100.0 * m["value"] * m["applied_factor"], abs=0.5)


def test_the_applied_gate_saturates_for_a_part_that_breaks_its_silhouette():
    """
    The gate is a gate, not a second edge-coverage metric: past
    VOCAB_APPLIED_FULL it stops discounting entirely, so a part that has done
    the work is judged on coherence alone.
    """
    box = cq.Workplane("XY").box(L, W, H).edges().chamfer(BREAK)
    m = review_shape(box)["metrics"]["radius_vocabulary"]
    assert m["applied"] >= dr.VOCAB_APPLIED_FULL and m["applied_factor"] == pytest.approx(1.0)
    assert m["score"] == pytest.approx(100.0)


def test_a_cone_chamfer_on_a_turned_part_is_seen_as_break_geometry():
    """
    Every chamfer on a body of revolution is a CONE, and the land test was
    "planar and narrow" - so a turned spacer with all four corners broken to one
    1.0 mm rung reported "no fillet or chamfer geometry anywhere" at full weight.
    A countersink stays out: its size is set by the screw standard, not by this
    repo's ladder.
    """
    m = review_shape(_turned(breaks=True))["metrics"]["radius_vocabulary"]
    assert m["status"] == dr.SCORED
    assert [d["size"] for d in m["distinct"]] == [pytest.approx(1.0, abs=0.05)], m
    assert m["score"] == pytest.approx(100.0)

    csk = cq.Workplane("XY").box(L, W, H).edges().chamfer(BREAK)
    csk = csk.faces(">Z").workplane().pushPoints([(-15, 0), (0, 0), (15, 0)])
    csk = csk.cskHole(4.0, 8.0, 82.0)
    sizes = [d["size"] for d in review_shape(csk)["metrics"]["radius_vocabulary"]["distinct"]]
    assert sizes == [pytest.approx(BREAK, abs=0.05)], (
        f"a countersink cone must not enter the ladder vocabulary: {sizes}"
    )


# ---------------------------------------------------------------------------
# G4: a part with no business carrying a bolt pattern is not defective,
# G5: and geometry may not buy a renormalisation for saying so
# ---------------------------------------------------------------------------
def test_a_turned_part_is_not_told_to_add_holes_it_does_not_need():
    """
    G4, and the gate's worst miscoaching. feature_composition and
    pattern_discipline together are 0.28 of the enclosure rubric, and both
    reported ABSENT - 0.0 at full weight - on every shaft, spacer, standoff,
    bushing, knob, gland and spool, because none of them has a bolt pattern.
    The behaviour that teaches is "add holes you do not need".

    THIS TEST USED TO ASSERT NOT_REQUIRED FOR BOTH METRICS, and that assertion
    was the G4 defect written down. See
    test_a_turned_part_may_not_renormalise_a_third_of_the_rubric_away below for
    what excusing them on GEOMETRIC grounds was worth (a three-line bored
    cylinder at 97.8/A, outranking this repo's own exemplar at 83.1), and
    lib/design_review._metric_profile_composition for the principle. What this
    test is FOR - a turned part is not defective for having no bolt pattern, and
    is never coached towards one - is asserted here at full strength, on a
    scored number rather than on an exemption.

    THE GATE CLAIM MOVED, AND IT MOVED ONTO A PART THAT EARNS IT. This test used
    to finish by asserting that _turned() - a plain 30 x 40 bored barrel with
    one blanket .chamfer() - scores over 70. That assertion was resting on a
    measurement that had not happened: face_composition read PLANAR faces only,
    so the barrel, which is 94% of what anyone can see of this part, was
    invisible to it and it scored the two end annuli 91.8 at full weight. Read
    developed, the barrel is a 38 x 94 mm blank panel and scores 0.3, and the
    part measures 58.4/C rather than 75.8/B. That is the right answer for a
    bored bar with its corners knocked off, and the corpus agrees - it is the
    same geometry as gamed_turned_blank_tube. The claim this test exists to make
    is asserted below on every profile measurement plus a part that is composed.
    """
    rep = review_shape(_turned(breaks=True))
    for mid in ("feature_composition", "pattern_discipline"):
        m = rep["metrics"][mid]
        assert m["status"] == dr.SCORED, (mid, m)
        assert isinstance(m["score"], float), (mid, m)
        assert m["mode"] == "profile", (mid, m)
    assert rep["absent"] == [], rep["absent"]
    # STRONGER than "at least MIN_COVERAGE": nothing is excused at all, so the
    # whole rubric is measured and the thin 0.72 margin G4 left is gone.
    assert rep["coverage"] == pytest.approx(1.0), rep["coverage"]
    assert rep["status"] == "ok", rep["message"]
    # ... and what holds this part down is its BLANK BARREL, not the two metrics
    # that used to report ABSENT on it. Both of them score, and the composition
    # finding is about surface, never about missing holes.
    assert rep["metrics"]["feature_composition"]["score"] > 0.0, rep["metrics"]
    assert rep["metrics"]["face_composition"]["score"] < 10.0, (
        "a 38 x 94 mm unbroken barrel is a blank panel, whatever it is wrapped around"
    )
    # A TURNED PART THAT IS COMPOSED CLEARS THE GATE, which is the whole of what
    # "not defective for having no bolt pattern" has to mean. Neither of these
    # carries a single fastener.
    for name, solid in (("gland", _turned_gland()), ("knob", _turned_crowned_knob())):
        composed = review_shape(solid)
        assert composed["status"] == "ok" and composed["score"] > 70.0, f"{name}: {composed}"
    # a role was never declared: this is decided by geometry
    assert rep["role"] == "enclosure" and rep["role_declared"] is None

    # ... and no finding anywhere in the report asks it to drill anything. The
    # two findings that would - and that G4 was created to silence - are named,
    # so this cannot go quiet if the ids are renamed.
    fired = {f["id"] for f in rep["findings"]}
    assert "scattered_features" not in fired and "no_fastener_pattern" not in fired, fired
    assert {"undifferentiated_profile", "unrelieved_shoulders"} <= fired, fired
    for f in rep["findings"]:
        assert "bolt_pattern" not in (f.get("builder") or ""), f


def test_a_turned_part_may_not_renormalise_a_third_of_the_rubric_away():
    """
    G5. Excusing the two composition metrics on a body of revolution
    renormalised 0.28 of the enclosure rubric OUT of the weighted mean, and
    every metric that remained is free on a solid of revolution: it is perfectly
    symmetric, it has no large empty PLANAR region, its proportion is ideal, and
    one .chamfer() call maxes edge_break_coverage, sharp_edge_length and
    radius_vocabulary at once.

    Measured under G4: this exact three-line part scored 97.8 / band A and
    outranked the reference exemplar's 83.1, and a bare stepped cylinder reached
    100.0. Geometry must not buy a renormalisation - what a turned part's
    refinement consists of has to be measured, not deleted.
    """
    trivial = (
        cq.Workplane("XY").circle(15).extrude(40).faces(">Z").hole(12).edges("%CIRCLE").chamfer(1.0)
    )
    rep = review_shape(trivial)
    assert dr.Topology(trivial.val()).revolution_pure() is True
    assert rep["band"] != "A", rep["message"]
    assert rep["score"] < 83.1, f"a three-line bored cylinder outranks the exemplar: {rep['score']}"
    # ... and it is the profile measurements that hold it down, not an error
    assert rep["errored"] == [] and rep["coverage"] == pytest.approx(1.0)
    assert rep["metrics"]["pattern_discipline"]["score"] == pytest.approx(0.0), (
        "a bar with its ends broken has no shoulder, groove or register anywhere"
    )
    assert rep["metrics"]["feature_composition"]["score"] < 50.0, "two diameters is not a profile"


def test_a_turned_profile_is_scored_on_what_turned_parts_are_refined_with():
    """
    Both ends of the calibration, on real solids exported and re-imported.

    TRIVIAL - none may reach band A and none may outrank the exemplar's 83.1:
    a bored cylinder with one chamfer call, an arbitrary stepped cylinder, a
    plain billet with one chamfer, and a stepped shaft with every edge chamfered
    and nothing else.

    COMPOSED - all must clear the gate, be judged fairly and trip no rubric
    floor: a stepped, bored and counterbored gland, a spool with radiused web
    roots, and a crowned knob turned to two diameters over a relieved shoulder.

    PLAIN - legitimate parts that are nonetheless undifferentiated, and the
    calibration between the two: a one-diameter drum knob and a bored spacer
    with its corners broken. Both must be measured, error nothing, trip no
    floor, and land clear of the crude billet below them and clear of the gland
    above them - but neither clears the gate, and the reason is the same in both
    cases and is now measurable. Their whole visible surface is one unbroken
    barrel. Before face_composition could develop a curved face it scored the
    end annuli only and reported 80.7 and 80.1 at full weight, which floated the
    drum knob to 77.3/B and the spacer to 73.6/B; developed they read 33.5 and
    44.7, and the parts read 68.4 and 66.8. The move that fixes either of them
    is the one a machinist would make anyway - a second diameter, a knurl, a
    flute, a register or a groove - and _turned_crowned_knob makes exactly that
    move and clears the gate at 81.5.
    """
    trivial = {
        "bored_cylinder": cq.Workplane("XY")
        .circle(15)
        .extrude(40)
        .faces(">Z")
        .hole(12)
        .edges("%CIRCLE")
        .chamfer(1.0),
        "stepped_cylinder": _stepped_cylinder(),
        "billet": cq.Workplane("XY").circle(16).extrude(45).edges(">Z").chamfer(1.0),
        "stepped_shaft": _stepped_shaft(),
    }
    for name, solid in trivial.items():
        rep = review_shape(solid)
        assert rep["band"] != "A", f"{name} reads as band A: {rep['message']}"
        assert rep["score"] < 83.1, f"{name} outranks the exemplar at {rep['score']}"

    composed = {
        "gland": _turned_gland(),
        "spool": _turned_spool(),
        "crowned_knob": _turned_crowned_knob(),
    }
    for name, solid in composed.items():
        rep = review_shape(solid)
        assert rep["status"] == "ok", f"{name}: {rep['message']}"
        assert rep["floor_failures"] == [], f"{name} trips a floor: {rep['message']}"
        assert rep["errored"] == [], f"{name} errored a metric: {rep['errored']}"
        assert rep["score"] >= 70.0, f"{name} fails the gate at {rep['score']}: {rep['message']}"

    billet = review_shape(cq.Workplane("XY").circle(16).extrude(45).edges(">Z").chamfer(1.0))
    gland = review_shape(_turned_gland())
    plain = {
        "drum_knob": _turned_knob(),
        "spacer": _turned(od=24.0, bore=6.4, length=10.0, breaks=True),
    }
    for name, solid in plain.items():
        rep = review_shape(solid)
        assert rep["status"] == "ok", f"{name}: {rep['message']}"
        assert rep["floor_failures"] == [], f"{name} trips a floor: {rep['message']}"
        assert rep["errored"] == [], f"{name} errored a metric: {rep['errored']}"
        assert rep["coverage"] == pytest.approx(1.0), f"{name}: {rep['coverage']}"
        # measured, not deleted: an undifferentiated barrel is a real reading and
        # it sits between a bar of stock and a composed part, in that order
        assert billet["score"] + 15.0 < rep["score"] < gland["score"] - 15.0, (
            f"{name} at {rep['score']} does not sit between the billet at "
            f"{billet['score']} and the gland at {gland['score']}"
        )
        assert rep["metrics"]["face_composition"]["score"] < 50.0, (
            f"{name}: an unbroken barrel is the largest empty region on the part"
        )
    # and the ordering the eye agrees with: a finished spool and a bored,
    # counterbored gland are BETTER turned parts than a bar with chamfers
    assert review_shape(_turned_spool())["score"] > review_shape(trivial["bored_cylinder"])["score"]
    assert gland["score"] > review_shape(trivial["stepped_shaft"])["score"]


def test_a_chamfered_root_is_worth_half_a_radiused_one_and_a_square_one_nothing():
    """
    The turned discipline population is the CONCAVE profile corners, because
    they are the ones nothing else in this module can see: edge_break_coverage
    and sharp_edge_length are convex-only, so a stepped shaft with every outside
    corner chamfered and every root left square scores 100 on both.
    """
    square = _shaft_roots(None)
    chamfered = _shaft_roots("chamfer")
    radiused = _shaft_roots("fillet")
    scores = {}
    for name, solid in (("square", square), ("chamfer", chamfered), ("fillet", radiused)):
        m = review_shape(solid)["metrics"]["pattern_discipline"]
        assert m["status"] == dr.SCORED and m["mode"] == "profile", (name, m)
        scores[name] = m["score"]
    assert scores["square"] == pytest.approx(0.0), scores
    assert scores["chamfer"] == pytest.approx(100.0 * dr.SHOULDER_CHAMFER_CREDIT), scores
    assert scores["fillet"] == pytest.approx(100.0), scores
    # The convex-only metrics cannot tell a chamfered root from a radiused one -
    # both score a flat 100 on each - which is exactly why this population is
    # worth measuring rather than assuming edge_break_coverage covers it.
    for mid in ("edge_break_coverage", "sharp_edge_length"):
        pair = [review_shape(s)["metrics"][mid]["score"] for s in (chamfered, radiused)]
        assert pair == [pytest.approx(100.0), pytest.approx(100.0)], (mid, pair)
    # ... and relieving the roots properly is never punished elsewhere: the
    # journal between two root fillets used to be read as "a fillet of R9"
    assert review_shape(radiused)["metrics"]["radius_vocabulary"]["score"] == pytest.approx(100.0)
    assert review_shape(radiused)["score"] > review_shape(chamfered)["score"]


def test_a_rounded_outside_corner_is_not_shoulder_relief():
    """
    The per-edge convexity probe is exactly degenerate for a TANGENT edge: both
    faces share a normal there and the sign is decided by second-order
    curvature. Measured on the turned spool, it read the convex ROUND-OVER of a
    flange corner as smooth_concave - so rounding an OUTSIDE corner would have
    banked shoulder relief, which is the opposite of the move being asked for.
    Topology._corner_sense measures across the whole treatment face instead.
    """
    body = cq.Workplane("XY").circle(20).extrude(10)
    body = body.faces(">Z").workplane().circle(12).extrude(14)
    outside = body.edges(cq.selectors.BoxSelector((-1e4, -1e4, 23.6), (1e4, 1e4, 24.4))).fillet(2.5)
    profile = dr.Topology(outside.val()).revolution_profile()
    assert profile is not None
    blends = [c for c in profile["corners"] if c["treatment"] == "blend"]
    assert blends, "the round-over is missing from the profile"
    assert all(c["sense"] == "convex" for c in blends), blends
    assert review_shape(outside)["metrics"]["pattern_discipline"]["score"] == pytest.approx(0.0)


def _shoulder(chamfer: bool = False):
    """A two-diameter turned body, optionally with a chamfer at the concave root."""
    pts = (
        [(0, 0), (15, 0), (15, 20), (10.5, 20), (9, 21.5), (9, 32), (0, 32)]
        if chamfer
        else [(0, 0), (15, 0), (15, 20), (9, 20), (9, 32), (0, 32)]
    )
    wp = cq.Workplane("XZ").moveTo(*pts[0])
    for p in pts[1:]:
        wp = wp.lineTo(*p)
    return wp.close().revolve()


def test_deburring_a_chamfer_does_not_make_its_corner_unmeasurable():
    """
    _corner_sense read the treatment face's immediate NEIGHBOURS as the flanks
    that turn the corner, which stops being true the moment the chamfer is
    itself deburred - the neighbours are then the deburr blends, and OCC hands
    one of them back as a nameless surface of revolution with no axis, so it is
    not even a profile member. The sense came back None, the corner was counted
    unresolved, and pattern_discipline ERRORED at full weight on a part that is
    better made than the one beside it.

    The walk steps through break-sized treatment to the flank, so a deburred
    chamfer measures as the shoulder chamfer it is.
    """
    plain = _shoulder(chamfer=True)
    deburred = plain.edges(cq.selectors.BoxSelector((-1e4, -1e4, 19.9), (1e4, 1e4, 21.6))).fillet(
        0.3
    )

    profile = dr.Topology(deburred.val()).revolution_profile()
    assert profile is not None
    assert profile["unresolved"] == 0, profile
    roots = [c for c in profile["corners"] if c["sense"] == "concave"]
    assert roots, "the shoulder root vanished from the profile"
    assert {c["treatment"] for c in roots} == {"blend", "chamfer"}, roots

    m = review_shape(deburred)["metrics"]["pattern_discipline"]
    assert m["status"] == dr.SCORED and m["mode"] == "profile", m
    assert m["score"] > 0.0, m
    assert m["unmeasured_fraction"] == pytest.approx(0.0), m
    # and breaking the chamfer's own edges is never worth LESS than leaving them
    assert review_shape(deburred)["score"] >= review_shape(plain)["score"]


def test_the_corner_walk_will_not_cross_a_face_that_is_not_a_break():
    """
    A wrong flank is worse than an unresolved corner, so the walk is timid: it
    crosses only break-sized faces and only when exactly one way on exists.
    A raw shoulder, whose treatment faces are none at all, is unchanged by it.
    """
    topo = dr.Topology(_shoulder().val())
    profile = topo.revolution_profile()
    assert profile["unresolved"] == 0, profile
    assert all(c["treatment"] == "raw" for c in profile["corners"]), profile
    members = {i: True for i in range(len(topo.faces))}
    # the big cylinder is not break-sized, so no walk may pass through it
    body = next(
        i
        for i, rec in enumerate(topo.faces)
        if rec["kind"] == "cylinder" and (rec["radius"] or 0) > 14.0
    )
    assert topo.faces[body]["width"] > topo.break_cap
    edge = next(e for e in topo.face_edges[body] if e["mid"] is not None)
    start = next(x for x in edge["faces"] if x != body)
    assert topo._walk_to_flank(start, edge, body, {}) is None
    # ... and with the cylinder a legitimate flank it is returned immediately
    assert topo._walk_to_flank(start, edge, body, members)[0] == body


def test_the_turned_exemption_is_geometric_and_does_not_excuse_scatter():
    """
    It must not re-open the hole ABSENT was created to close. Only the part that
    is ENTIRELY its own profile takes the profile branch; an off-axis hole on a
    turned part is a layout decision and is judged like any other, so "holes
    exist but form no pattern" is still a defect.
    """
    import math  # noqa: PLC0415

    flange = cq.Workplane("XY").circle(40.0).extrude(10.0)
    flange = flange.faces(">Z").workplane().hole(20.0)
    body = flange.edges().chamfer(1.0).val()
    for a, r, d in ((0.4, 21.0, 2.5), (1.9, 33.0, 3.0), (3.3, 26.0, 4.0), (5.1, 30.0, 2.5)):
        body = body.cut(
            cq.Solid.makeCylinder(d / 2.0, 30.0, cq.Vector(r * math.cos(a), r * math.sin(a), -5.0))
        )
    rep = review_shape(body)
    topo = dr.Topology(body)
    assert topo.revolution_axis() is not None, "still a turned flange"
    assert topo.revolution_pure() is False, "four off-axis drillings are not on the profile"
    assert rep["metrics"]["pattern_discipline"]["status"] == dr.ABSENT
    assert rep["metrics"]["feature_composition"]["status"] == dr.SCORED
    assert rep["metrics"]["feature_composition"]["score"] < 40.0
    assert rep["score"] < 70.0, rep["message"]

    # and a prismatic part with scattered holes is untouched by any of this
    box = cq.Workplane("XY").box(L, W, H).edges("|Z").fillet(R_PLAN).val()
    for x, y, d in ((-18.0, -9.0, 5.0), (4.0, 11.0, 6.5), (21.0, -4.0, 8.0)):
        box = box.cut(cq.Solid.makeCylinder(d / 2.0, 60.0, cq.Vector(x, y, -30.0)))
    scattered = review_shape(box)
    assert dr.Topology(box).revolution_axis() is None
    assert scattered["metrics"]["pattern_discipline"]["status"] == dr.ABSENT


# ---------------------------------------------------------------------------
# aggregate configuration accounting
# ---------------------------------------------------------------------------
def test_the_report_says_how_much_of_the_score_is_configuration():
    """
    Every knob was accounted for individually and nothing added them up, so
    "nothing in the report says the geometry did not change" was literally true.
    config_delta scores the SAME measurements under the default rubric with
    nothing excused and publishes the difference.
    """
    shape = _knife_slab()
    plain = review_shape(shape)
    assert plain["config_delta"]["delta"] == 0.0, "no knobs, no delta"
    assert plain["config_delta"]["knobs"] == []

    configured = review_shape(shape, config={"role": "plate"})
    cd = configured["config_delta"]
    assert cd["knobs"] == ["role=plate"]
    assert cd["default_score"] == plain["score"], (
        "the default-rubric pass must reproduce the unconfigured review exactly"
    )
    assert cd["configured_score"] == configured["score"]
    assert cd["delta"] == pytest.approx(configured["score"] - plain["score"], abs=0.11)
    assert cd["delta"] > 0.0, "the role is worth points here, and the report must say so"
    assert cd["within_cap"] is True
    # THE SPLIT. A role and a waiver are not the same kind of claim - a role is
    # checked against the B-rep, a waiver is checked against nothing - so the
    # report prices them apart and the two halves must add back up.
    assert cd["role_delta"] == pytest.approx(cd["delta"], abs=1e-9), "no waivers, no waiver delta"
    assert cd["waiver_delta"] == pytest.approx(0.0, abs=1e-9)
    assert cd["role_cap"] == dr.ROLE_DELTA_ALLOWANCE["plate"]
    assert cd["waiver_cap"] == dr.MAX_CONFIG_DELTA


def test_the_role_and_the_waivers_are_priced_apart():
    """
    B6: the single cap was the arithmetic bound on what WAIVERS can buy, and it
    was applied to the sum of the waivers and the role. The role with the widest
    legitimate delta is `sheet`, so an honest formed bracket that correctly
    declared role=sheet was refused as a configuration statement.

    Here the two terms are measured separately on one part that carries both a
    role and a waiver, and the split is asserted to reconstruct the total.
    """
    shape = _knife_slab()
    cfg = {"role": "plate", "waivers": {"symmetry": "a deliberately one-sided test fixture"}}
    rep = review_shape(shape, config=cfg)
    cd = rep["config_delta"]
    assert cd["knobs"] == ["role=plate", "waiver:symmetry"]
    assert cd["role_delta"] + cd["waiver_delta"] == pytest.approx(cd["delta"], abs=0.11)
    assert cd["role_only_score"] is not None, "the middle pass must actually have run"
    # and the role term is bounded by what the role's own weights can produce,
    # which is a property of ROLE_RUBRICS rather than of any sample
    assert cd["role_delta"] <= dr.ROLE_DELTA_ALLOWANCE["plate"] + 1e-9
    assert dr.ROLE_DELTA_ALLOWANCE["enclosure"] == 0.0, (
        "the default rubric buys nothing, so declaring it must get no role budget"
    )


def test_a_configuration_delta_over_the_cap_is_an_error(monkeypatch):
    """
    The cap is a BACKSTOP for the next knob, not a fix for the last one, so it
    is exercised by lowering it rather than by inventing a knob that clears it.
    """
    monkeypatch.setattr(dr, "config_delta_caps", lambda role: (1.0, 1.0))
    cfg = {"role": "plate", "severity": "hard"}
    rep = review_shape(_knife_slab(), config=cfg)
    assert rep["config_delta"]["within_cap"] is False
    assert any(e["key"] == "config_delta" for e in rep["config_errors"])
    check = next(
        c
        for c in design_review_checks(rep, cfg)
        if c["id"].startswith("design_review.config") and "config_delta" in c["message"]
    )
    assert check["status"] == "ERROR" and check["severity"] == "hard"
    assert "not about the part" in check["message"]


def test_design_review_checks_refuses_a_foreign_report():
    checks = design_review_checks({"schema": "part-eval/1"})
    assert [c["status"] for c in checks] == ["ERROR"]
    assert "unexpected report schema" in checks[0]["message"]
    assert design_review_checks({"schema": SCHEMA}, {"enabled": False}) == []


def test_config_from_spec_distinguishes_absent_from_default():
    assert config_from_spec(None) is None
    assert config_from_spec({}) is None, "no block means do not review at all"
    assert config_from_spec({"design_review": {"enabled": False}}) is None
    assert config_from_spec({"design_review": {}}) == {}, "an empty block means defaults"
    assert config_from_spec({"design_review": {"min_score": 70}}) == {"min_score": 70}
    with pytest.raises(ValueError, match="must be an object"):
        config_from_spec({"design_review": 70})


# ---------------------------------------------------------------------------
# CLI: exit 0 at/above threshold, 1 below, 2 on error
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def steps(tmp_path_factory):
    d = tmp_path_factory.mktemp("dr_cli")
    sharp, refined = d / "sharp.step", d / "refined.step"
    cq.exporters.export(rung1_sharp(), str(sharp))
    cq.exporters.export(rung3_edge_breaks(), str(refined))
    corrupt = d / "corrupt.step"
    corrupt.write_text("this is not a STEP file")
    return {
        "dir": d,
        "sharp": sharp,
        "refined": refined,
        "corrupt": corrupt,
        "missing": d / "does_not_exist.step",
    }


def test_cli_exit_zero_at_or_above_threshold(steps):
    assert dr.main([str(steps["refined"]), "--min-score", "20", "--quiet"]) == 0
    assert dr.main([str(steps["sharp"]), "--quiet"]) == 0, (
        "no threshold means report only, never fail"
    )


def test_cli_exit_one_below_threshold(steps):
    assert dr.main([str(steps["sharp"]), "--min-score", "50", "--quiet"]) == 1


@pytest.mark.parametrize("key", ["corrupt", "missing"])
def test_cli_exit_two_when_it_cannot_review(steps, key):
    assert dr.main([str(steps[key]), "--quiet"]) == 2


def test_cli_exit_two_on_an_unreadable_config(steps):
    assert (
        dr.main(
            [str(steps["sharp"]), "--config", str(steps["dir"] / "no_such_config.json"), "--quiet"]
        )
        == 2
    )


def test_cli_reads_the_config_block_and_writes_json(steps, tmp_path):
    cfg = tmp_path / "spec.json"
    cfg.write_text(json.dumps({"design_review": {"min_score": 95}}))
    out = tmp_path / "report.json"
    rc = dr.main([str(steps["refined"]), "--config", str(cfg), "--json", str(out), "--quiet"])
    assert rc == 1, "the threshold must come from the spec.json block"
    rep = json.loads(out.read_text())
    assert rep["schema"] == SCHEMA and rep["source"] == str(steps["refined"])
    assert rep["score"] is not None
    # an explicit --min-score wins over the file
    assert (
        dr.main([str(steps["refined"]), "--config", str(cfg), "--min-score", "10", "--quiet"]) == 0
    )


def test_cli_process_exit_code_and_console_report(steps):
    """The exit code a Makefile or CI step actually sees."""
    proc = subprocess.run(
        [sys.executable, "-m", "lib.design_review", str(steps["sharp"]), "--min-score", "50"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 1
    assert "Design review" in proc.stdout
    assert "edge_break_coverage" in proc.stdout


# ---------------------------------------------------------------------------
# G6: face_composition must READ A CURVED SURFACE, and no metric may score a
#     part it did not look at
# ---------------------------------------------------------------------------
def _tube(length: float = 60.0, od: float = 40.0, bore: float = 24.0):
    """A plain bored tube with every rim broken on one ladder rung."""
    b = cq.Workplane("XY").circle(od / 2.0).extrude(length)
    b = b.faces(">Z").workplane().hole(bore)
    return b.edges("%CIRCLE").chamfer(0.4)


def _tube_cbore_groove():
    """
    THE SIX-LINE TUBE. Bored, counterbored, one arbitrary ring groove, every
    rim chamfered on one rung. Measured 94.0 / band A while face_composition
    read planar faces only, outranking this repo's own exemplar at 83.1.
    """
    b = cq.Workplane("XY").circle(20.0).extrude(60.0)
    b = b.faces(">Z").workplane().cboreHole(24.0, 30.0, 8.0)
    groove = cq.Workplane("XY").workplane(offset=28.0).circle(21.0).circle(18.5).extrude(3.0)
    return b.cut(groove).edges("%CIRCLE").chamfer(0.4)


def _tube_blanket_fillet():
    """A bored tube with NO feature on it and one blanket .fillet(1.0)."""
    b = cq.Workplane("XY").circle(20.0).extrude(60.0)
    b = b.faces(">Z").workplane().hole(24.0)
    return b.edges().fillet(1.0)


def _blind_pocket_tube(angle: float):
    """
    A tall thin barrel with ONE blind radial pocket, at `angle` about the axis.

    The pocket is the only thing bounding the empty region circumferentially,
    so where it sits relative to the kernel's seam is the whole question. The
    part is identical at every angle; a reviewer that cuts the developed strip
    at the seam says otherwise.
    """
    body = cq.Workplane("XY").circle(8.0).extrude(60.0)
    tool = cq.Solid.makeCylinder(3.0, 10.0, cq.Vector(9, 0, 30.0), cq.Vector(-1, 0, 0))
    tool = tool.moved(cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), angle))
    return cq.Workplane("XY").newObject([body.val().cut(tool)])


def test_a_bare_barrel_is_a_blank_panel_and_is_measured_as_one():
    """
    G6, the defect. face_composition built its population from faces of kind
    "plane", so on a body of revolution the entire visible skin was invisible
    to it and it scored the two end faces - which on a thin-walled turned part
    are narrow annuli that can never contain a large empty circle.

    Measured on the real round trip, build -> export -> re-import -> review:
    the six-line tube scored face_composition 100.0 at full weight having
    examined 14% of its own exterior (3.7% on a 2 mm wall), for 94.0 / band A
    overall; the same tube with no feature at all and one blanket .fillet(1.0)
    scored 77.3 / B and CLEARED the 70.0 advisory gate unassisted.

    The bar here is stated the way the defect was: the grooved tube may not
    read as band A, and the featureless one may not clear the gate. Both are
    proved on the exported STEP, and the whole reason they now fail is that
    their barrels are read as the blank panels a render shows them to be.
    """
    grooved = review_shape(_tube_cbore_groove())
    assert grooved["band"] != "A", f"the six-line tube reads band A at {grooved['score']}"
    # 83.1 is what the exemplar scored on the day this defect was found. It has
    # since moved to 89.9 under a rework of radius_vocabulary and symmetry, so
    # the bar is kept where it was rather than raised to follow it.
    assert grooved["score"] < 83.1, "... and it outranks the exemplar as it stood"

    blanket = review_shape(_tube_blanket_fillet())
    assert blanket["score"] < 70.0, (
        f"a bored tube with one blanket fillet clears the gate at {blanket['score']}"
    )
    # and it fails for the RIGHT reason - not an error, not a missing metric
    assert blanket["errored"] == [] and blanket["coverage"] == pytest.approx(1.0)
    fc = blanket["metrics"]["face_composition"]
    assert fc["status"] == dr.SCORED and fc["score"] < 10.0, fc
    assert fc["developed_faces"] >= 1, "the barrel must be in the population at all"


def test_the_curved_population_is_the_skin_and_the_metric_says_how_much_it_saw():
    """
    The population widened, and the report says so. On a turned part nearly all
    of the exterior is curved, so `examined_fraction` must be near 1.0 - it was
    0.14 on this geometry when the skin was filtered out.
    """
    rep = review_shape(_tube())
    fc = rep["metrics"]["face_composition"]
    assert fc["examined_fraction"] > 0.9, fc
    assert fc["relevant"] > 0 and fc["examined"] > 0, fc
    assert fc["developed_faces"] >= 1, fc
    # the barrel is the worst face, and it is named as curved skin
    worst = fc["faces"][0]
    assert worst["developed"] is True and worst["periodic"] is True, worst


def test_a_groove_on_a_barrel_punches_a_real_hole_in_the_developed_face():
    """
    The point of developing rather than skipping: a feature on a curved surface
    has to COUNT, the same way a pocket counts on a lid. Cutting a plain barrel
    in two with a ring groove halves the tallest unbroken band, and the empty
    region must halve with it.
    """
    plain = review_shape(_tube())
    grooved_solid = _tube().cut(
        cq.Workplane("XY").workplane(offset=28.0).circle(21.0).circle(18.5).extrude(3.0).val()
    )
    grooved = review_shape(grooved_solid)
    assert (
        grooved["metrics"]["face_composition"]["void_worst"]
        < 0.7 * plain["metrics"]["face_composition"]["void_worst"]
    ), "a ring groove must break the barrel's empty region, not decorate it"
    assert (
        grooved["metrics"]["face_composition"]["score"]
        > plain["metrics"]["face_composition"]["score"]
    ), "and the score must move in the direction the geometry did"


@pytest.mark.parametrize("angle", [0.0, 90.0, 180.0, 217.0])
def test_an_empty_region_wraps_the_seam_instead_of_being_cut_by_it(angle):
    """
    A cylinder is PERIODIC. The kernel has to put the seam somewhere, and where
    it puts it is not a property of the part - so a feature's angular position
    relative to it may not change the score.

    Measured on this exact solid with the developed strip taken as ONE period
    instead of tiled: largest empty circle R23.00 with the pocket on the seam,
    R18.83 at a quarter turn and R15.03 at a half turn - three different
    answers for one part, rotated. Tiled across the period it is R23.00 at every
    angle, which is the physical answer: the empty region runs round the back.
    """
    ref = review_shape(_blind_pocket_tube(0.0))["metrics"]["face_composition"]
    rot = review_shape(_blind_pocket_tube(angle))["metrics"]["face_composition"]
    assert rot["void_worst"] == pytest.approx(ref["void_worst"], abs=0.01), (
        f"rotating the part {angle} deg about its own axis moved the empty region: "
        f"{rot['void_worst']} vs {ref['void_worst']}"
    )
    assert rot["faces"][0]["periodic"] is True and rot["faces"][0]["tiles"] >= 3


def test_developing_a_curved_face_over_states_it_and_never_flatters_it():
    """
    The map is (u, v) -> (su * u, sv * v) with su and sv the LARGEST scale
    factors on the face. On a cylinder both are exact; on a cone, torus, sphere
    or general surface of revolution the circumferential one varies with v and
    the widest circle is used.

    That direction is load-bearing. A wider developed polygon spreads the
    features apart and lets a LARGER empty circle fit, which LOWERS the score:
    an approximation that can flatter a part is a hole in the gate. Asserted on
    a cone, whose two ends differ by design.
    """
    cone = cq.Solid.makeCone(6.0, 18.0, 40.0, cq.Vector(0, 0, 0), cq.Vector(0, 0, 1))
    topo = dr.Topology(cq.Workplane("XY").newObject([cone]).val())
    conical = [i for i, r in enumerate(topo.faces) if r["kind"] == "cone"]
    assert conical, "the fixture must actually be a cone"
    dev = topo.developed(conical[0])
    assert dev is not None, topo.develop_failure(conical[0])
    # the widest circle, not the mean and not the narrow end
    assert dev.su == pytest.approx(18.0, abs=0.05), dev
    assert dev.u_distortion == pytest.approx(3.0, rel=0.1), dev
    # v is arc length along the generatrix, so it is exact
    assert dev.sv == pytest.approx(1.0, abs=1e-6), dev


def test_a_metric_may_not_score_a_part_it_did_not_look_at():
    """
    THE COVERAGE INVARIANT, on the geometry that exposed it. The population a
    metric builds has to BE the part; face_composition's was two end annuli.

    Proved by putting the old filter back: with curved faces excluded from the
    population, the metric examines 14% of a tube's exterior and must refuse to
    return a number rather than reporting a flattering one at full weight. And
    refusing must cost - the errored weight stays in the denominator and out of
    `coverage`, so the score can only fall.
    """
    solid = _tube()
    honest = review_shape(solid)
    assert honest["metrics"]["face_composition"]["status"] == dr.SCORED

    real = dr._composable_faces

    def planar_only(topo, rubric):
        cands, unreadable, relevant = real(topo, rubric)
        return [i for i in cands if topo.faces[i]["kind"] == "plane"], unreadable, relevant

    try:
        dr._composable_faces = planar_only
        blind = review_shape(solid)
    finally:
        dr._composable_faces = real

    fc = blind["metrics"]["face_composition"]
    assert fc["status"] == dr.METRIC_ERROR, fc
    assert fc["score"] is None, "an unmeasured metric never produces a number"
    assert fc["examined_fraction"] < dr.EXAMINED_MIN["face_composition"], fc
    assert "examined only" in fc["message"], fc["message"]
    # the error invariant holds through this door too: breaking the measurement
    # is never worth more than making it
    assert blind["score"] <= honest["score"] + 1e-9, (blind["score"], honest["score"])
    assert blind["coverage"] < honest["coverage"], (blind["coverage"], honest["coverage"])
    assert "face_composition" in blind["errored"]


def test_every_population_metric_reports_what_it_examined():
    """
    The invariant is only worth anything if it is visible. Every metric that
    works over a population carries `examined`, `relevant` and
    `examined_fraction`; the two that have no population - symmetry over the
    whole solid, proportion over the bounding box - carry none, and saying so
    is the audit.
    """
    rep = review_shape(_broken_body())
    for mid in ("face_composition", "edge_break_coverage", "sharp_edge_length"):
        m = rep["metrics"][mid]
        assert "examined_fraction" in m, mid
        assert 0.0 <= m["examined_fraction"] <= 1.0, (mid, m)
        assert m["examined_fraction"] >= dr.EXAMINED_MIN[mid], (mid, m)
    for mid in ("symmetry", "proportion"):
        assert "examined_fraction" not in rep["metrics"][mid], mid


def test_a_curved_chamfer_band_may_not_dilute_the_composition_it_is_not_part_of():
    """
    A chamfer band round a barrel develops to 2*pi*R by its own width, so it
    sails past the FACE_MIN_SHARE filter that keeps a planar chamfer land out -
    and being narrow it always scores a perfect void. Left in the population,
    adding chamfers would raise a part's own area-weighted mean, which is a
    metric that pays for styling instead of composition.
    """
    topo = dr.Topology(_tube().val())
    cands, _unreadable, _relevant = dr._composable_faces(topo, dr.ROLE_RUBRICS["enclosure"])
    for i in cands:
        assert not (topo.is_break_face(i) or topo.is_blend_face(i)), (
            f"face {i} ({topo.faces[i]['kind']}) is break/blend geometry and is in the "
            "composition population"
        )
    assert any(topo.faces[i]["kind"] == "cylinder" for i in cands), "the barrel must be in it"


def _blend_heavy_body():
    """A 60 x 44 x 26 block whose R7 plan corners and R4 lid break make roughly a
    fifth of its exterior tangent blend - the shape of part the denominator hole
    flattered most."""
    return (
        cq.Workplane("XY")
        .box(60, 44, 26)
        .edges("|Z")
        .fillet(7.0)
        .edges(">Z")
        .fillet(4.0)
        .faces(">Z")
        .workplane()
        .rect(30, 18)
        .cutBlind(-5)
    )


def test_break_and_blend_skin_leaves_the_candidates_but_stays_in_the_denominator():
    """
    THE COVERAGE INVARIANT'S OWN DENOMINATOR. Curved break and blend faces are
    rightly refused as candidates - a chamfer band develops to a long thin strip
    that always scores a perfect void and would dilute the area-weighted mean
    upwards - but they used to leave `relevant` by the same door, which is the
    error invariant's original sin one level up: subtracting from the
    DENOMINATOR instead of from the MEASUREMENT.

    So the metric could report examined_fraction 0.77 on a body whose exterior
    it had composed 0.38 of (measured on the corpus's gamed_soap_bar), and the
    invariant - "a metric may not return a score for a part it did not look at"
    - was not true of the metric it was written for. The blend skin is exterior
    a reader sees, so the denominator counts it and examined_fraction tells the
    truth about the shortfall.
    """
    shape = _blend_heavy_body().val()
    topo = dr.Topology(shape)
    rubric = dr.ROLE_RUBRICS["enclosure"]
    cands, _unreadable, relevant = dr._composable_faces(topo, rubric)

    skin = [
        i
        for i, rec in enumerate(topo.faces)
        if rec["kind"] in dr._DEVELOPABLE_KINDS
        and topo.is_exterior(i) is not False
        and (topo.is_break_face(i) or topo.is_blend_face(i))
    ]
    blend_area = sum(topo.faces[i]["area"] for i in skin)
    assert blend_area > 0.10 * relevant, (
        f"fixture is not blend-heavy enough to test this: {blend_area:.1f} of {relevant:.1f} mm2"
    )
    # refused as candidates, exactly as before
    assert not set(skin) & set(cands)
    # and still counted as exterior the metric is answerable for
    assert relevant > sum(topo.faces[i]["area"] for i in cands) + blend_area - 1e-6

    fc = dr.review_shape(shape)["metrics"]["face_composition"]
    assert fc["status"] == dr.SCORED, fc
    # (the report rounds to 4 dp, hence the tolerance rather than a bare <=)
    tol = 1e-3 * fc["relevant"]
    assert fc["examined"] + blend_area <= fc["relevant"] + tol, fc
    # the shortfall is real and visible rather than divided away
    assert fc["examined_fraction"] <= 1.0 - blend_area / relevant + 1e-3, fc
    assert fc["examined_fraction"] < 0.9, "the blend skin has to move the number, not just the text"


# ---------------------------------------------------------------------------
# A CHAMFER THAT CROSSES A ROUNDED CORNER IS A CONE
# ---------------------------------------------------------------------------
def test_a_conical_chamfer_land_is_measured_and_lands_on_its_own_rung():
    """
    The land the metric could not see, and the width formula that mismeasured it.

    `_chamfer_leg` used to return None for every conical land. The caller then
    SUBTRACTED that face's area from the population, so an exterior cone break
    vanished from the vocabulary AND from `unmeasured_fraction` - a loss with
    nothing anywhere to show for it, which is precisely the accounting the
    degradation contract exists to forbid. It could only ever flatter.

    Fixing that alone is not enough. A cone's leg is its slant width times the
    cosine of its half-angle, and the slant width must be read off the face's
    own v-parameter range: the stored rec["width"] is area / (perimeter / 2),
    which is a documented 5% under-read on a flat strip and far worse on a
    curved band whose two bounding arcs differ in length. Measured on this
    fixture, that formula reports 0.85 for a 1.0 mm chamfer - off the ladder by
    twice its own tolerance, a manufactured finding on a part that did nothing
    wrong.
    """
    body = (
        cq.Workplane("XY")
        .box(L, W, H)
        .edges("|Z")
        .fillet(5.0)  # four rounded plan corners
        .faces(">Z")
        .chamfer(1.0)  # ... so the top chamfer runs across them as CONES
        .faces("<Z")
        .chamfer(1.0)
    )
    shape = body.val()
    topo = dr.Topology(shape)
    cones = [
        i
        for i, rec in enumerate(topo.faces)
        if rec["kind"] == "cone" and topo.is_break_face(i) and not topo.is_rim_break_face(i)
    ]
    assert len(cones) == 8, f"expected 8 corner cone lands (4 corners x 2 ends): {len(cones)}"

    for i in cones:
        leg = dr._chamfer_leg(topo, i)
        assert leg is not None, f"face {i}: a cone land must be measurable, not dropped"
        assert leg == pytest.approx(1.0, abs=0.02), (
            f"face {i}: a 1.0 mm chamfer across a fillet is a 1.0 mm chamfer, measured {leg}"
        )

    m = dr.review_shape(shape)["metrics"]["radius_vocabulary"]
    assert [d["size"] for d in m["distinct"]] == [1.0, 5.0], m["distinct"]
    assert all(d["on_ladder"] for d in m["distinct"]), m["distinct"]
    # the eight cone lands are IN the count, not silently removed from it
    assert next(d for d in m["distinct"] if d["size"] == 1.0)["faces"] == 16, m["distinct"]
    assert m["score"] == pytest.approx(100.0), m["message"]


def test_a_reclassified_land_is_reported_rather_than_silently_subtracted():
    """
    The only path in this module that shrinks a denominator must say so.

    A narrow planar face that fails the strip test is not a break, so removing
    it is right - but removing it INVISIBLY is how the missing cone branch
    stayed hidden for as long as it did. The count and the area are now in the
    report where a reader can see what left.
    """
    m = dr.review_shape(_broken_body().val())["metrics"]["radius_vocabulary"]
    assert "reclassified_faces" in m and "reclassified_mm2" in m, sorted(m)
    assert m["reclassified_faces"] >= 0 and m["reclassified_mm2"] >= 0.0


# ---------------------------------------------------------------------------
# THE SIDEWAYS PROBE MUST NOT BE A COIN FLIP
# ---------------------------------------------------------------------------
def test_the_sideways_probe_does_not_pick_its_axis_by_round_off():
    """
    A boss standing on a face is perpendicular to TWO frame axes at once.

    `min(axes, key=|dot|)` therefore chose between them on round-off - measured
    on parts/_template the two |cos| values were 4.7e-20 and 3.9e-06 at the
    origin and 1.3e-05 and 3.9e-06 after a 30 degree rotation, so the probe left
    along a different axis in the two orientations, one boss flipped from
    blocked to reachable, and the score moved 0.90 points on a part that had not
    changed.

    There is nothing to break the tie WITH, so it is not broken: every axis as
    perpendicular as the best one is probed and any escape counts.
    """
    topo = dr.Topology(_broken_body().val())
    axis3 = topo.frame.axes[2]
    sides = dr._frame_sides(topo, axis3)
    assert len(sides) == 2, (
        f"a direction along one frame axis is perpendicular to the other two, so both must be "
        f"probed: got {len(sides)}"
    )
    for s in sides:
        assert abs(s.dot(axis3)) < 1e-9, "each probe direction must be exactly perpendicular"
    assert abs(sides[0].dot(sides[1])) < 1e-6, "and they must not be the same direction twice"

    # an oblique direction has one clear answer and must still get exactly one
    oblique = (topo.frame.axes[0] * 0.6 + topo.frame.axes[1] * 0.8).normalized()
    assert len(dr._frame_sides(topo, oblique)) == 1
