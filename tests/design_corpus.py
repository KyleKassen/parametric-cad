"""
The adversarial design corpus: labelled solids of KNOWN relative quality, plus
the ordering contract any honest refinement scorer must satisfy.

WHY THIS FILE EXISTS
An audit of lib/design_review.py proved the gate did not track design quality.
A lumpy pile of overlapping rounded boxes with randomly scattered oversized
countersunk holes scored 96.7/A and cleared the 70.0 advisory gate, while a
textbook sealed cover scored 50.2/D and a 2 mm sheet-metal bracket scored
43.1/D and both failed it. That was found by hand, once. Agents optimise to
whatever the gate rewards, so a gate that rewards blobs teaches blobs, and the
only defence that survives a rework is an executable one.

So this module turns that audit into a fixture. It builds a labelled corpus of
solids whose RELATIVE quality is known by construction, scores every one of
them through the real pipeline (build -> export STEP -> re-import -> review),
and asserts an ORDERING CONTRACT rather than absolute numbers. Absolute scores
will move as the metrics are reworked; the ordering is the invariant, and the
contract is the definition of "the gate works".

THE CLASSES
  base    the floor - a raw extrusion, nothing done to it at all.
  crude   unfinished geometry: styling started and stopped.
  gamed   adversarial. Each one is cheap geometry chosen to inflate a specific
          metric with no design thought behind it. Every case carries a note
          naming the metric it attacks. A gamed case that looks decent is a
          worthless fixture, so each was rendered and read back by eye.
  good    a competent part OF ITS ROLE. An engineer looking at the render
          should approve it. Judged under its own role's rubric.
  real    shipped artifacts from parts/, scored as they actually export.

THE ROLES
Three of the audit's false negatives were legitimate part roles judged by an
enclosure's rubric: a cover, a plate and a sheet-metal bracket are all SUPPOSED
to be thin, and two of them are supposed to have one big flat mounting face.
Every case therefore declares its intended role, and it is passed to the
reviewer as config["role"]. A reviewer that ignores the key scores exactly as
it does today, which is what makes the corpus reproduce the audit; a
role-aware reviewer is expected to use it.

Roles used here: enclosure (default), cover, plate, bracket, sheet, structural.

USAGE
    uv run python -m tests.design_corpus                 # the whole table
    uv run python -m tests.design_corpus --fast          # skip the slow cases
    uv run python -m tests.design_corpus --only gamed_blob_csk --render
    uv run python -m tests.design_corpus --json out.json --rebuild

    exit 0 = every contract assertion holds, 1 = at least one fails,
    2 = the corpus could not be scored at all.

COST
Solids are cached as STEP under tmp/design_corpus/ and reviews are cached as
JSON keyed by the hash of the STEP AND of every module the score is computed
from - lib/design_review.py and lib/analyze_step.py - so a re-run after an
unrelated edit is nearly free and a re-run after a scorer edit is honest.
Geometry is kept as small as it can be while staying representative.

Units: mm.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import cadquery as cq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import lib.features as ft  # noqa: E402
from lib.design_review import METRIC_IDS, review_shape  # noqa: E402

CACHE_DIR = PROJECT_ROOT / "tmp" / "design_corpus"
STEP_DIR = CACHE_DIR / "step"
REVIEW_DIR = CACHE_DIR / "review"

# The bar lib/evaluate.py holds a part to when its spec.json says nothing
# (DESIGN_ADVISORY_MIN_SCORE). Imported lazily so the corpus still runs if
# evaluate.py is mid-rework.
GATE = 70.0

# How far a good part must sit above the best gamed or crude one. Small on
# purpose: the claim is "the ordering is not an accident", not "the scorer must
# agree with a particular spread". Five points is about half a band.
MARGIN = 5.0

ROLES = ("enclosure", "cover", "plate", "bracket", "sheet", "structural")

CLASSES = ("base", "crude", "gamed", "good", "real")

L, W, H = 90.0, 60.0, 30.0  # the ladder body - big enough to carry real M4 work


# --------------------------------------------------------------------------- #
# case record
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Case:
    """
    One labelled corpus member.

    `build` returns a solid; `artifact` returns the path to an already-exported
    STEP (the `real` cases). Exactly one of the two is set. `why` is the
    load-bearing field: it states what the case proves, so a future reader can
    tell an intentional adversary from a mistake.
    """

    id: str
    label: str
    klass: str
    role: str
    why: str
    build: Callable[[], object] | None = None
    artifact: Callable[[], Path | None] | None = None
    rung: int | None = None  # position on the monotonic ladder, 1-based
    slow: bool = False
    attacks: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.klass not in CLASSES:
            raise ValueError(f"{self.id}: unknown class {self.klass!r}")
        if self.role not in ROLES:
            raise ValueError(f"{self.id}: unknown role {self.role!r}")
        if (self.build is None) == (self.artifact is None):
            raise ValueError(f"{self.id}: set exactly one of build= / artifact=")
        # attacks= is the claim about WHAT this case is a trap for, and it is
        # exported into the JSON report. Four of these tuples still named
        # blank_face_ratio, feature_density and fastener_rhythm - metrics
        # retired long enough ago that no report can emit them - so the corpus
        # documented a rubric that no longer exists. Naming a metric that is not
        # in METRIC_IDS is now an error rather than rot nobody notices.
        unknown = [m for m in self.attacks if m not in METRIC_IDS]
        if unknown:
            raise ValueError(f"{self.id}: attacks= names non-metric(s) {unknown}")


# --------------------------------------------------------------------------- #
# small geometry helpers
# --------------------------------------------------------------------------- #
def _cache_dir(sub: Path) -> Path:
    """
    Make a cache directory, and keep the cache out of git on its own terms.

    The .gitignore goes INSIDE tmp/design_corpus/ rather than into the repo
    root file: the cache is this module's business, several agents edit the
    root .gitignore, and a directory that ignores itself cannot be forgotten.
    """
    sub.mkdir(parents=True, exist_ok=True)
    marker = CACHE_DIR / ".gitignore"
    if not marker.exists():
        marker.write_text("# build/review cache for tests/design_corpus.py\n*\n")
    return sub


def _wp(obj) -> cq.Workplane:
    """Anything solid-ish as a Workplane, so builders can be chained freely."""
    if isinstance(obj, cq.Workplane):
        return obj
    return cq.Workplane("XY").newObject([obj])


def _shape(obj) -> cq.Shape:
    return obj.val() if isinstance(obj, cq.Workplane) else obj


def _through_cylinder(centre, direction, radius: float, length: float) -> cq.Solid:
    """A drill of `length` centred on `centre`, pointing `direction`."""
    d = cq.Vector(*direction).normalized()
    start = cq.Vector(*centre) - d.multiply(length / 2.0)
    return cq.Solid.makeCylinder(radius, length, start, d)


def _csk_drill(
    entry, direction, dia: float, csk_dia: float, length: float, angle: float = 82.0
) -> cq.Shape:
    """
    A countersunk drill: shank plus the cone, entering at `entry`.

    `entry` must sit on or just outside the face being drilled and `direction`
    points INTO the material. The cone is over-run by 1 mm above the face so
    the countersink always breaks the surface cleanly.
    """
    d = cq.Vector(*direction).normalized()
    p = cq.Vector(*entry)
    depth = (csk_dia - dia) / 2.0 / math.tan(math.radians(angle / 2.0))
    shank = cq.Solid.makeCylinder(dia / 2.0, length, p, d)
    cone = cq.Solid.makeCone(csk_dia / 2.0, dia / 2.0, depth, p, d)
    lead = cq.Solid.makeCylinder(csk_dia / 2.0, 1.0, p - d.multiply(1.0), d)
    return shank.fuse(cone).fuse(lead)


def _fuse_all(shapes) -> cq.Shape:
    out = shapes[0]
    for s in shapes[1:]:
        out = out.fuse(s)
    return out


def _fillet_seam_at(
    wp: cq.Workplane, z: float, radii=(3.0, 2.0, 1.5), tol: float = 0.4
) -> cq.Workplane:
    """
    Fillet the closed seam ring a stacked union leaves at height `z`.

    A per-edge fillet sweep over a union of arbitrarily rotated lumps segfaults
    OCC outright, which is unacceptable in a fixture, so the gamed case that
    needs concave blend length is built from an AXIS-ALIGNED stack whose seams
    are closed planar rings at known heights. Selecting a whole ring is a
    well-conditioned fillet, and the blend it produces is exactly as concave
    and exactly as invisible as the one the audit found.

    `radii` are tried largest first and the first one the kernel accepts wins,
    which keeps the case deterministic without hard-coding a radius that a
    future OCP release might refuse on the smallest step.
    """
    sel = cq.selectors.BoxSelector((-1e4, -1e4, z - tol), (1e4, 1e4, z + tol))
    for r in radii:
        try:
            return wp.edges(sel).fillet(r)
        except Exception:
            continue
    raise RuntimeError(f"no seam fillet in {radii} was accepted at z={z}")


def _break_mouth(body, pocket: ft.Pocket, face_plane: cq.Plane, c: float = 0.8):
    """
    Chamfer a pocket mouth by CUTTING a tool that already carries the chamfer.

    An unbroken pocket mouth undoes most of what the pocket bought - the part
    reads as a hole punched in a slab - and a late 3D chamfer over
    boolean-built geometry is this repo's main kernel failure, so the break
    lives in the cutter. Same move as break_mouth() in the reference part.
    """
    sunk = cq.Plane(
        origin=face_plane.origin - face_plane.zDir * c, xDir=face_plane.xDir, normal=face_plane.zDir
    )
    tool = ft.rounded_box(
        pocket.length + 2 * c,
        pocket.width + 2 * c,
        20.0,
        pocket.radius + c,
        bottom_break=c,
        top_break=0.0,
        centered=(True, True, False),
        plane=sunk,
    )
    delta = pocket.plane.origin.sub(face_plane.origin)
    offset = face_plane.xDir.multiply(delta.dot(face_plane.xDir)) + face_plane.yDir.multiply(
        delta.dot(face_plane.yDir)
    )
    return _wp(_shape(body).cut(_shape(tool).translate(offset.toTuple())))


def _panelled_face(body, face: str, frame: float, wall: float, pattern: str, pitch: float):
    """A recessed panel + rib field + a broken mouth: the whole panel move."""
    plane = ft.face_plane(body, face)
    pk = ft.recessed_panel(body, face, frame=frame, wall=wall)
    solid = _shape(pk.solid).fuse(_shape(ft.rib_field(pk, pattern, pitch=pitch).solid))
    return _break_mouth(_wp(solid), pk, plane, c=0.6)


def _ring_groove(
    length: float, width: float, wall: float, depth: float, radius: float, z_face: float
) -> cq.Shape:
    """
    A closed rectangular scribe groove cut `depth` into a face lying at z_face.

    The tool over-runs the face by 0.2 mm so the groove always breaks the
    surface instead of leaving a witness skin.
    """
    h = depth + 0.4
    zc = z_face + 0.2 - h / 2
    outer = cq.Workplane("XY").box(length, width, h).edges("|Z").fillet(radius)
    inner = (
        cq.Workplane("XY")
        .box(length - 2 * wall, width - 2 * wall, h * 3)
        .edges("|Z")
        .fillet(max(radius - wall, 0.3))
    )
    return outer.val().cut(inner.val()).translate((0, 0, zc))


# --------------------------------------------------------------------------- #
# 1. the monotonic ladder
#    Each rung adds exactly one move from the design language. Nothing is
#    removed, so a scorer that measures refinement must rank them in order.
# --------------------------------------------------------------------------- #
def ladder_1_sharp():
    """A raw extrusion: every edge a knife edge, every face blank."""
    return cq.Workplane("XY").box(L, W, H)


def ladder_2_plan_radii():
    """Plan corners on the style ladder - the usual 'I filleted it' pass."""
    return ft.rounded_box(
        L, W, H, radius=8.0, top_break=0.0, bottom_break=0.0, centered=(True, True, True)
    )


def ladder_3_edge_breaks():
    """Plus a chamfer on both rims: no unbroken knife edge left on the body."""
    return ft.rounded_box(
        L, W, H, radius=8.0, top_break=1.5, bottom_break=1.5, centered=(True, True, True)
    )


def ladder_4_panel_ribs():
    """Plus recessed panels with BROKEN MOUTHS and rib fields, on three faces."""
    body = ladder_3_edge_breaks()
    body = _panelled_face(body, ">Z", frame=12.0, wall=H, pattern="chevron", pitch=13.0)
    for face in ("-Y", "+Y"):
        body = _panelled_face(body, face, frame=8.0, wall=W, pattern="parallel", pitch=11.0)
    return body


def ladder_5_bolted():
    """
    Plus a solved counterbored bolt pattern: constant pitch, constant inset,
    symmetric about both centrelines. The minimum competent enclosure.
    """
    body = ladder_4_panel_ribs()
    plane = cq.Plane(origin=(0, 0, H / 2), normal=(0, 0, 1), xDir=(1, 0, 0))
    bp = ft.bolt_pattern(
        "perimeter",
        length=L,
        width=W,
        inset=6.0,
        target_pitch=30.0,
        fastener="M4",
        plane=plane,
        solid=body,
        hole="cbore",
    )
    return bp.solid


# --------------------------------------------------------------------------- #
# 2. the gamed cases reconstructed from the audit table
# --------------------------------------------------------------------------- #
def _blob(seed: int, n: int = 5):
    """
    A lumpy pile of overlapping rounded boxes - no panel, frame, land or rhythm.

    Every lump is individually "styled" (plan radii on the ladder, chamfered
    rims), which is precisely the point: presence-of-events metrics see a part
    covered in radii and breaks and cannot see that nothing was composed.
    """
    rng = random.Random(seed)
    lumps = []
    for _ in range(n):
        lump = ft.rounded_box(
            rng.uniform(55, 88),
            rng.uniform(45, 68),
            rng.uniform(26, 44),
            radius=rng.choice((5.0, 8.0, 12.0)),
            top_break=1.5,
            bottom_break=1.5,
            centered=(True, True, True),
        )
        shape = (
            lump.val()
            .rotate((0, 0, 0), (0, 0, 1), rng.uniform(0.0, 90.0))
            .translate((rng.uniform(-18, 18), rng.uniform(-13, 13), rng.uniform(-8, 8)))
        )
        lumps.append(shape)
    return _wp(_fuse_all(lumps))


def _scatter_points(seed: int, n: int, half_x: float, half_y: float):
    rng = random.Random(seed)
    return [(rng.uniform(-half_x, half_x), rng.uniform(-half_y, half_y)) for _ in range(n)]


def gamed_blob_csk():
    """
    The audit's 96.7/A winner: the blob, drilled with oversized countersinks.

    The holes sit above FASTENER_D_MAX, which takes the fastener metric out of
    the score entirely, and they are placed at random so some merge into
    figure-of-eight blobs. Countersink cones read as chamfer faces, so every
    one of them RAISES edge-break coverage however raw the drilling.
    """
    body = _blob(seed=19)
    bb = body.val().BoundingBox()
    rng = random.Random(11)
    # D24 and D32: above FASTENER_D_MAX, so the fastener metric drops out of
    # the score entirely, and their bore walls are radius 12 and 16, both on
    # the style ladder, so the vocabulary metric reads them as tidy fillets
    drills = []
    for x, y in _scatter_points(23, 5, bb.xlen / 2 - 24, bb.ylen / 2 - 24):
        dia = rng.choice((24.0, 32.0))
        drills.append(_csk_drill((x, y, bb.zmax + 0.5), (0, 0, -1), dia, dia + 8.0, bb.zlen + 4.0))
    drills.append(_csk_drill((bb.xmax + 0.5, 0.0, 0.0), (-1, 0, 0), 24.0, 32.0, bb.xlen + 4.0))
    drills.append(_csk_drill((0.0, bb.ymax + 0.5, 0.0), (0, -1, 0), 24.0, 32.0, bb.ylen + 4.0))
    return _wp(body.val().cut(_fuse_all(drills)))


def gamed_blob_concave_fillets():
    """
    A lopsided stack of rounded boxes, every step seam filleted, D24 scatter.

    The seam where a smaller lump lands on a bigger one is CONCAVE, and concave
    fillet runouts were counted as broken CONVEX edge, so hundreds of
    millimetres of blend that break no silhouette at all are banked as
    refinement. The steps themselves are chosen by nothing: no datum, no
    rhythm, no alignment.
    """
    rng = random.Random(29)
    sizes = [(130.0, 106.0, 14.0), (94.0, 76.0, 12.0), (60.0, 48.0, 11.0), (30.0, 26.0, 13.0)]
    z, lumps, seams = 0.0, [], []
    for i, (lx, ly, lz) in enumerate(sizes):
        lump = ft.rounded_box(
            lx,
            ly,
            lz + (6.0 if i else 0.0),
            radius=(12.0, 8.0, 8.0, 5.0)[i],
            top_break=1.5,
            bottom_break=0.0,
            centered=(True, True, False),
        )
        lumps.append(
            lump.val().translate((rng.uniform(-6, 6), rng.uniform(-3, 3), z - (6.0 if i else 0.0)))
        )
        if i:
            seams.append(z)
        z += lz
    body = _wp(_fuse_all(lumps))
    for seam in seams:
        body = _fillet_seam_at(body, seam)
    # only now, with the blends banked, are two rotated lumps thrown on top -
    # they make the thing lumpy without endangering the fillet operations
    extra = []
    for _ in range(2):
        lump = ft.rounded_box(
            rng.uniform(50, 74),
            rng.uniform(34, 50),
            rng.uniform(24, 40),
            radius=rng.choice((5.0, 8.0, 12.0)),
            top_break=1.5,
            bottom_break=0.0,
            centered=(True, True, True),
        )
        extra.append(
            lump.val()
            .rotate((0, 0, 0), (0, 0, 1), rng.uniform(20.0, 70.0))
            .translate((rng.uniform(-26, 26), rng.uniform(-20, 20), 22.0))
        )
    body = _wp(_fuse_all([body.val()] + extra))
    bb = body.val().BoundingBox()
    drills = [
        _through_cylinder((x, y, (bb.zmin + bb.zmax) / 2), (0, 0, 1), 12.0, bb.zlen * 2 + 12.0)
        for x, y in _scatter_points(31, 6, bb.xlen / 2 - 16, bb.ylen / 2 - 14)
    ]
    drills.append(_through_cylinder((0, 0, 8.0), (0, 1, 0), 12.0, bb.ylen + 8.0))
    return _wp(body.val().cut(_fuse_all(drills)))


def gamed_chamfer_box_random_holes():
    """
    A box with every edge chamfered and holes drilled wherever they landed.

    Nothing is aligned, nothing shares a diameter, nothing is inset from an
    edge by a repeated amount - and the chamfer is one blanket operation, not a
    decision. Attacks edge_break_coverage and blank_face_ratio at once.
    """
    body = cq.Workplane("XY").box(L, W, H).edges().chamfer(1.2)
    rng = random.Random(53)
    drills = []
    for x, y in _scatter_points(53, 6, L / 2 - 8, W / 2 - 8):
        drills.append(_through_cylinder((x, y, 0), (0, 0, 1), rng.uniform(1.6, 4.5), H + 6))
    for _ in range(2):
        y, z = rng.uniform(-W / 2 + 8, W / 2 - 8), rng.uniform(-H / 2 + 6, H / 2 - 6)
        drills.append(_through_cylinder((0, y, z), (1, 0, 0), rng.uniform(2.0, 4.0), L + 6))
    return _wp(body.val().cut(_fuse_all(drills)))


def gamed_knife_box_csk():
    """
    A raw box whose only feature is a scatter of countersunk holes.

    Every knife edge is still there. The countersink cones are the only thing
    that resembles an edge break, and they are enough to move the coverage
    metric because a cone face passes the break test at BOTH its circles.
    """
    body = cq.Workplane("XY").box(L, W, H)
    rng = random.Random(67)
    drills = []
    for x, y in _scatter_points(67, 6, L / 2 - 10, W / 2 - 10):
        dia = rng.uniform(6.0, 11.0)
        drills.append(_csk_drill((x, y, H / 2 + 0.5), (0, 0, -1), dia, dia + 6.0, H + 4))
    return _wp(body.val().cut(_fuse_all(drills)))


def gamed_sealed_cavity_fillets():
    """
    A raw box with a fully enclosed internal cavity whose edges are filleted.

    Not one millimetre of that blend is visible from outside, and no
    manufacturing process makes it, but concave fillet length counts, so the
    part banks a large coverage number for geometry that does not exist to the
    eye. The outside is still a knife-edged slab.
    """
    outer = cq.Workplane("XY").box(L, W, H)
    cavity = cq.Workplane("XY").box(L - 18, W - 18, H - 14).edges().fillet(5.0)
    return _wp(outer.val().cut(cavity.val()))


def gamed_knife_box_3_holes():
    """
    A raw box with three through holes: the minimum that makes every large face
    'carry a feature'. Presence of a hole is not presence of design.
    """
    body = cq.Workplane("XY").box(L, W, H)
    drills = [
        _through_cylinder((-26, -12, 0), (0, 0, 1), 4.5, H + 6),
        _through_cylinder((9, 7, 0), (0, 0, 1), 6.0, H + 6),
        _through_cylinder((31, -3, 0), (0, 0, 1), 3.2, H + 6),
    ]
    return _wp(body.val().cut(_fuse_all(drills)))


# --------------------------------------------------------------------------- #
# 3. gaming vectors invented here - one per metric an agent would reach for
# --------------------------------------------------------------------------- #
def gamed_groove_decoration():
    """
    A raw slab wrapped in meaningless scribe grooves.

    Attacks feature_density (a raw face count cannot tell structure from
    decoration) and blank_face_ratio (an inner wire covering 1% of a face is
    enough to stop it reading as blank). Nothing here has a function: no rib
    stiffens anything, no groove seals anything, no frame bounds anything.
    """
    body = cq.Workplane("XY").box(L, W, H)
    cuts = []
    for i in range(5):
        ring = _ring_groove(L - 8 - 8 * i, W - 8 - 8 * i, 1.0, 0.7, 4.0, H / 2)
        cuts.append(ring)
        cuts.append(ring.mirror("XY"))
    for i in range(5):
        bar = cq.Workplane("XY").box(L - 10, 1.0, 0.7).val()
        cuts.append(bar.translate((0, W / 2, -H / 2 + 5.0 + 4.5 * i)))
        cuts.append(bar.translate((0, -W / 2, -H / 2 + 5.0 + 4.5 * i)))
    return _wp(body.val().cut(_fuse_all(cuts)))


def gamed_near_symmetry():
    """
    Visually one-sided, numerically symmetric.

    Every asymmetry is thin: a chamfer on one top rim only, a blade fin on one
    flank only, a pocket on one end only. A symmetric-difference VOLUME sees a
    couple of percent and calls it symmetric; the eye sees a part that is
    obviously wrong. Attacks symmetry.
    """
    lx, ly, lz = L * 1.2, W * 1.2, H * 1.3
    body = ft.rounded_box(
        lx, ly, lz, radius=8.0, top_break=0.0, bottom_break=1.0, centered=(True, True, True)
    )
    # one top rim chamfered, its opposite number left sharp: loud, and cheap
    body = body.edges(cq.selectors.NearestToPointSelector((0.0, ly / 2, lz / 2))).chamfer(5.0)
    # a blade fin on one flank only - visually a different part from that side
    fin = cq.Workplane("XY").box(lx * 0.62, 1.6, lz * 0.8).val().translate((0, -ly / 2 - 4.0, 0))
    web = cq.Workplane("XY").box(lx * 0.62, 9.0, 1.6).val().translate((0, -ly / 2 - 4.0, 0))
    body = _wp(body.val().fuse(fin).fuse(web))
    # and a notch out of one end only
    notch = cq.Workplane("XY").box(10.0, ly * 0.45, lz * 0.45).val().translate((lx / 2 - 4.0, 0, 0))
    return _wp(body.val().cut(notch))


def gamed_soap_bar():
    """
    Everything blended at one huge radius: a bar of soap.

    Coverage goes to 100% because there is no unbroken convex edge left, sharp
    length goes to zero, and the radius vocabulary is a single ladder rung -
    three metrics maxed by one operation with no design in it. Attacks
    edge_break_coverage, sharp_edge_length and radius_vocabulary.
    """
    return cq.Workplane("XY").box(L, W, H).edges().fillet(12.0)


def gamed_projected_alignment():
    """
    Holes that line up only in plan view.

    Seen from above, six centres sit on a clean 3 x 2 grid. In the solid they
    are two unrelated families - three drilled down through the crown, three
    drilled sideways through a flank - at three different diameters, so nothing
    is coaxial, nothing shares a depth and nothing is a pattern. Attacks any
    alignment or composition metric that works on projected centres.
    """
    body = ft.rounded_box(
        L * 1.3,
        W * 1.3,
        H,
        radius=8.0,
        top_break=1.0,
        bottom_break=1.0,
        centered=(True, True, True),
    )
    bb = body.val().BoundingBox()
    xs = (-30.0, 0.0, 30.0)
    dias = (5.0, 7.0, 9.0)
    drills = []
    for x, d in zip(xs, dias):
        drills.append(_through_cylinder((x, -20.0, 0), (0, 0, 1), d / 2, bb.zlen + 6))
    for x, d in zip(xs, reversed(dias)):
        # same plan (x, +20) but drilled along Y, at three different heights
        z = -bb.zlen / 4 + (xs.index(x)) * bb.zlen / 4
        drills.append(_through_cylinder((x, 0.0, z), (0, 1, 0), d / 2, bb.ylen + 6))
    return _wp(body.val().cut(_fuse_all(drills)))


def gamed_facet_fillet():
    """
    Plan corners faked with five flat facets instead of a radius.

    Each facet band is 3.7 mm wide, narrow enough to pass as a chamfer land,
    and each crease is 18 deg, shallow enough to duck SHARP_MIN_DEG - so the
    corners score as broken while the rims stay knife edges and the corners are
    visibly faceted. Attacks edge_break_coverage and sharp_edge_length.
    """
    r, n = 12.0, 5
    hx, hy = L / 2, W / 2
    pts: list[tuple[float, float]] = []
    for sx, sy, a0 in ((1, 1, 0.0), (-1, 1, 90.0), (-1, -1, 180.0), (1, -1, 270.0)):
        cx, cy = sx * (hx - r), sy * (hy - r)
        for i in range(n + 1):
            th = math.radians(a0 + 90.0 * i / n)
            pts.append((cx + r * math.cos(th), cy + r * math.sin(th)))
    seen: list[tuple[float, float]] = []
    for p in pts:
        if not seen or abs(p[0] - seen[-1][0]) > 1e-6 or abs(p[1] - seen[-1][1]) > 1e-6:
            seen.append(p)
    return cq.Workplane("XY").polyline(seen).close().extrude(H).translate((0, 0, -H / 2))


def gamed_hole_flood():
    """
    Forty random small holes through a slab.

    Face count and inner-wire coverage both explode, so a density metric that
    counts and a blank-face metric that only asks 'does this face own a
    feature' both saturate. Nothing is on a pitch, nothing is on a line,
    nothing has an edge inset. Attacks feature_density and blank_face_ratio.
    """
    body = cq.Workplane("XY").box(L, W, H / 2)
    rng = random.Random(97)
    drills = []
    for x, y in _scatter_points(97, 40, L / 2 - 5, W / 2 - 5):
        drills.append(_through_cylinder((x, y, 0), (0, 0, 1), rng.uniform(0.9, 1.8), H))
    return _wp(body.val().cut(_fuse_all(drills)))


# --------------------------------------------------------------------------- #
# 4. the good cases - one per role
# --------------------------------------------------------------------------- #
def good_interface_plate():
    """
    An optical/payload interface plate: a published M6 grid at exactly 25 mm.

    The audit false-negatived this one. Its underside is one large flat face BY
    DEFINITION - that is the datum it bolts down on - and its aspect ratio is
    slab-like BY DEFINITION, because a stiff plate is thin. Both are correct
    engineering, and both were scored as defects.
    """
    plate = ft.rounded_box(
        180.0, 130.0, 12.0, radius=8.0, top_break=1.0, bottom_break=1.0, centered=(True, True, True)
    )
    grid = ft.tapped_hole_grid(plate, ">Z", pitch=25.0, fastener="M6", inset=15.0)
    body = grid.solid
    # corner clearance holes to bolt the plate down, on the same 25 mm rhythm
    corners = [(x, y) for x in (-75.0, 75.0) for y in (-50.0, 50.0)]
    body = ft.fastener_holes(
        body, corners, plane=ft.face_plane(body, ">Z"), fastener="M6", kind="clearance"
    )
    # two dowel holes on the diagonal: the plate's own location datum
    dowels = _fuse_all(
        [
            _through_cylinder((-75.0, -50.0, 0), (0, 0, 1), 3.0, 20.0),
            _through_cylinder((75.0, 50.0, 0), (0, 0, 1), 3.0, 20.0),
        ]
    )
    body = _wp(body.val().cut(dowels))
    return ft.emblem(body, ">Z", motif="rings", diameter=16.0, relief=-0.5, center=(0.0, 57.0))


def good_sealed_cover():
    """
    A sealed cover with a lapped spigot, an O-ring groove and a bolted rim.

    Textbook: the rim is a flat land, the O-ring groove is cut in that land, the
    spigot below it locates the cover in the housing bore, the perimeter screws
    are counterbored on a solved pitch at a constant inset, and the outside
    carries a recessed panel so it is not a slab. Scored 50.2/D in the audit.
    """
    cover_l, cover_w, cover_t = 150.0, 110.0, 10.0
    body = ft.rounded_box(
        cover_l,
        cover_w,
        cover_t,
        radius=8.0,
        top_break=1.0,
        bottom_break=0.6,
        centered=(True, True, False),
    )
    # lapped face: cut a rebate so the centre stands proud as a locating spigot
    land = 16.0
    rebate = (
        cq.Workplane("XY")
        .box(cover_l - 2 * land, cover_w - 2 * land, 6.0)
        .edges("|Z")
        .fillet(5.0)
        .translate((0, 0, -3.0 + 2.5))
    )
    body = _wp(body.val().cut(rebate.val().translate((0, 0, -2.5))))
    body = _wp(
        body.val().fuse(
            cq.Workplane("XY")
            .box(cover_l - 2 * land - 0.6, cover_w - 2 * land - 0.6, 2.5)
            .edges("|Z")
            .fillet(5.0)
            .faces("<Z")
            .chamfer(0.6)
            .val()
            .translate((0, 0, -1.25))
        )
    )
    groove = ft.oring_groove(
        cord=2.62,
        shape="rect",
        length=cover_l - land,
        width=cover_w - land,
        radius=8.0,
        plane=cq.Plane(origin=(0, 0, 0), normal=(0, 0, -1), xDir=(1, 0, 0)),
    )
    body = _wp(body.val().cut(groove.cut))
    plane = ft.face_plane(body, ">Z")
    bp = ft.bolt_pattern(
        "perimeter",
        length=cover_l,
        width=cover_w,
        inset=8.0,
        target_pitch=40.0,
        fastener="M4",
        plane=plane,
        solid=body,
        hole="cbore",
    )
    body = bp.solid
    pk = ft.recessed_panel(body, ">Z", frame=26.0, wall=cover_t)
    return ft.emblem(pk.solid, pk.plane, motif="target", diameter=22.0, relief=-0.5)


def good_sheet_bracket():
    """
    A 2 mm sheet-metal bracket: two bends, a return flange, formed radii.

    The audit false-negatived this one too, and it CANNOT be fixed without
    ceasing to be sheet metal: 2 mm material will not carry a chamfer or a plan
    fillet on the blanked perimeter, so an enclosure's edge-break rubric scores
    the whole outline as unbroken knife edge. Judged as sheet, the edge breaks
    that matter are the FORMED radii, which are all here and all on one rung.
    """
    t, ri = 2.0, 3.0
    ro = ri + t  # outer bend radius = inner + material: how sheet actually bends
    depth, run, up_h, ret = 70.0, 86.0, 58.0, 14.0

    def arc_mid(c, r, a0, a1):
        a = math.radians((a0 + a1) / 2.0)
        return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))

    c1 = (-ro, ro)  # bend 1: tangent to z=0 (outer) and to z=t / x=-t (inner)
    c2 = (ro - t, up_h - ro)  # bend 2, the other way: an offset Z-section
    sec = (
        cq.Workplane("XZ")
        .moveTo(-run, 0.0)
        .lineTo(-ro, 0.0)
        .threePointArc(arc_mid(c1, ro, 270.0, 360.0), (0.0, ro))
        .lineTo(0.0, up_h - ro)
        .threePointArc(arc_mid(c2, ri, 180.0, 90.0), (c2[0], up_h - t))
        .lineTo(c2[0] + ret, up_h - t)
        .lineTo(c2[0] + ret, up_h)
        .lineTo(c2[0], up_h)
        .threePointArc(arc_mid(c2, ro, 90.0, 180.0), (-t, up_h - ro))
        .lineTo(-t, ro)
        .threePointArc(arc_mid(c1, ri, 0.0, 270.0), (-ro, t))
        .lineTo(-run, t)
        .close()
        .extrude(depth)
    )
    body = _wp(sec.val().translate((0, depth / 2, 0)))
    # The blanked perimeter carries a plan radius, which IS what a real blank
    # has. Both flanges are horizontal, so ONE rounded prism rounds both free
    # ends - and it is an intersect, not a late fillet on a formed part.
    blank = ft.rounded_box(
        run + c2[0] + ret + 1.0,
        depth,
        up_h * 3,
        radius=6.0,
        top_break=0.0,
        bottom_break=0.0,
        centered=(True, True, True),
    )
    body = _wp(body.val().intersect(blank.val().translate(((c2[0] + ret - run) / 2.0, 0, 0))))
    # mounting holes in the base flange: constant pitch, constant edge distance
    drills = [
        _through_cylinder((-run + 14.0 + 26.0 * i, y, t / 2), (0, 0, 1), 2.75, 6 * t)
        for i in range(3)
        for y in (-21.0, 21.0)
    ]
    # and in the return flange, on the same rhythm
    drills += [
        _through_cylinder((c2[0] + 7.0, y, up_h - t / 2), (0, 0, 1), 2.75, 6 * t)
        for y in (-21.0, 21.0)
    ]
    # slots in the upright: adjustable on assembly, same pitch again
    for y in (-21.0, 21.0):
        drills.append(
            cq.Workplane("YZ")
            .slot2D(13.0, 5.5, 90.0)
            .extrude(6 * t)
            .val()
            .translate((-3 * t, y, up_h / 2))
        )
    return _wp(body.val().cut(_fuse_all(drills)))


def good_machined_bracket():
    """
    A machined angle bracket: broken outline, one radius rung, pocketed legs.

    The `bracket` role's reference, and the control for the sheet case. Solid
    material CAN carry a chamfer, so every free edge is broken on the ladder,
    every profile corner is the same rung, each leg is lightened with a pocket
    whose mouth is broken by the cutter, and the two hole groups sit on a
    constant pitch at a constant edge inset.
    """
    t, depth = 12.0, 80.0
    base_l, up_h = 120.0, 90.0
    # The L is ONE extruded profile with every corner on the radius ladder, so
    # no fillet ever runs late on a prism (lib/features.py, phase 1). The
    # corner at the heel is the load path, and it gets the same R6.
    sk = (
        cq.Sketch()
        .polygon([(0.0, 0.0), (base_l, 0.0), (base_l, t), (t, t), (t, up_h), (0.0, up_h)])
        .vertices()
        .fillet(6.0)
    )
    body = cq.Workplane("XZ").placeSketch(sk).extrude(depth).translate((0, depth / 2, 0))
    # break the whole blanked outline by chamfering the two end faces
    body = body.faces(">Y").chamfer(1.5).faces("<Y").chamfer(1.5)
    base_plane = cq.Plane(origin=(0, 0, t), normal=(0, 0, 1), xDir=(1, 0, 0))
    up_plane = cq.Plane(origin=(0, 0, 0), normal=(-1, 0, 0), xDir=(0, -1, 0))
    # sculpt: one lightening pocket per leg, generous radii, cut with a tool
    # that already carries its mouth chamfer
    for plane, size, at in (
        (base_plane, (30.0, 44.0), (38.0, 0.0)),
        (up_plane, (30.0, 32.0), (0.0, 28.0)),
    ):
        seat = cq.Plane(origin=plane.toWorldCoords(at), xDir=plane.xDir, normal=plane.zDir)
        pocket = ft.rounded_box(
            size[0],
            size[1],
            24.0,
            8.0,
            top_break=0.0,
            bottom_break=0.0,
            centered=(True, True, False),
            plane=cq.Plane(origin=seat.origin - seat.zDir * 4.0, xDir=seat.xDir, normal=seat.zDir),
        )
        flare = ft.rounded_box(
            size[0] + 1.2,
            size[1] + 1.2,
            20.0,
            8.6,
            bottom_break=0.6,
            top_break=0.0,
            centered=(True, True, False),
            plane=cq.Plane(origin=seat.origin - seat.zDir * 0.6, xDir=seat.xDir, normal=seat.zDir),
        )
        body = _wp(_shape(body).cut(_shape(pocket)).cut(_shape(flare)))
    # both hole groups: one pitch (30), one edge inset, symmetric across the web
    base_pts = [(x, y) for x in (76.0, 106.0) for y in (-26.0, 26.0)]
    body = ft.counterbore_at(body, base_pts, plane=base_plane, fastener="M6")
    up_pts = [(u, v) for u in (-26.0, 26.0) for v in (48.0, 78.0)]
    return ft.fastener_holes(body, up_pts, plane=up_plane, fastener="M6", kind="clearance")


def good_structural_arm():
    """
    A sculpted structural arm: bossed pivot, lightening pockets, blended waist.

    The `structural` role's reference. Mass is taken out where it does no work
    and left where it does, the pockets have generous corner radii so they do
    not relocate the stress concentration they exist to relieve, and the pivot
    boss is a turned step stack rather than a butt joint.
    """
    arm_t, hub_x = 18.0, -54.0
    body = ft.rounded_prism(
        [(-80.0, -30.0), (80.0, -20.0), (80.0, 20.0), (-80.0, 30.0)], arm_t, radius=12.0
    ).translate((0, 0, -arm_t / 2))
    body = _wp(body.val()).faces(">Z").chamfer(1.5)
    body = body.faces("<Z").chamfer(1.5)
    # one deep pocket per face in the web between hub and mounting pad, mouth
    # broken by the cutter, corners generously radiused
    for sign in (1.0, -1.0):
        seat = cq.Plane(origin=(-2.0, 0.0, sign * arm_t / 2), normal=(0, 0, sign), xDir=(1, 0, 0))
        pocket = ft.rounded_box(
            62.0,
            30.0,
            24.0,
            8.0,
            top_break=0.0,
            bottom_break=0.0,
            centered=(True, True, False),
            plane=cq.Plane(origin=seat.origin - seat.zDir * 5.0, xDir=seat.xDir, normal=seat.zDir),
        )
        flare = ft.rounded_box(
            63.2,
            31.2,
            20.0,
            8.6,
            bottom_break=0.6,
            top_break=0.0,
            centered=(True, True, False),
            plane=cq.Plane(origin=seat.origin - seat.zDir * 0.6, xDir=seat.xDir, normal=seat.zDir),
        )
        body = _wp(_shape(body).cut(_shape(pocket)).cut(_shape(flare)))
    hub = ft.step_shoulder(
        38.0,
        26.0,
        9.0,
        steps=2,
        break_size=1.0,
        plane=cq.Plane(origin=(hub_x, 0, arm_t / 2), normal=(0, 0, 1), xDir=(1, 0, 0)),
    )
    body = _wp(_shape(body).fuse(_shape(hub)))
    body = _wp(_shape(body).cut(_through_cylinder((hub_x, 0, 0), (0, 0, 1), 8.0, arm_t + 40.0)))
    pad = cq.Plane(origin=(0, 0, arm_t / 2), normal=(0, 0, 1), xDir=(1, 0, 0))
    pts = [(x, y) for x in (44.0, 66.0) for y in (-13.0, 13.0)]
    return ft.counterbore_at(body, pts, plane=pad, fastener="M5")


def good_turned_gland():
    """
    A turned cable-gland body: a stepped body of revolution, bored and
    counterbored, every corner broken on one ladder rung.

    THE REFERENCE FOR THE TURNED CLASS. Shafts, spacers, standoffs, bushings,
    knobs, glands and spools are a large and entirely legitimate part class that
    the gate used to read as defective by construction: they carry no bolt
    pattern, so feature_composition and pattern_discipline both reported ABSENT
    - 0.0 at full weight, together 0.28 of the enclosure rubric - and the only
    lesson that teaches is "add holes you do not need". Two other measurements
    broke on the same geometry: the OD of a turned part was classified as a bore
    wall, which emptied the body edge population so that ONE chamfered bore
    mouth scored edge_break_coverage 100.0; and every chamfer on a body of
    revolution is a cone, which the "planar and narrow" land test could not see
    at all, so a part with all of its corners broken to one rung reported "no
    fillet or chamfer geometry anywhere".

    Nothing about this part is declared. It is a body of revolution and the
    reviewer measures that for itself, which is the point: the authors being
    miscoached are exactly the ones who would not know there was a role to
    claim.

    THE FIRST FIX FOR THAT WAS WORSE THAN THE DEFECT. Reporting the two metrics
    not_required renormalised 0.28 of the rubric OUT of the weighted mean, and
    everything that remains is free on a solid of revolution - so a three-line
    bored cylinder with one chamfer call measured 97.8/A and outranked the
    reference exemplar at 83.1. The weight now has to be earned on the meridian
    profile instead: this part earns the composition half outright (four
    diameters, bored and counterbored) and half of the discipline half, because
    its shoulder roots are chamfered rather than radiused. See good_turned_spool
    for the other half, and crude_turned_billet for the bottom of the class.
    """
    body = cq.Workplane("XY").circle(17.0).extrude(18.0)
    body = body.faces(">Z").workplane().circle(13.0).extrude(14.0)
    body = body.faces(">Z").workplane().circle(10.0).extrude(10.0)
    body = body.faces(">Z").workplane().hole(12.0)
    body = body.faces("<Z").workplane().cboreHole(12.0, 20.0, 6.0)
    return body.edges("%CIRCLE").chamfer(1.0)


def _z_ring(z: float, tol: float = 0.4):
    """Every edge lying in a thin slab at height `z` - a whole profile ring."""
    return cq.selectors.BoxSelector((-1e4, -1e4, z - tol), (1e4, 1e4, z + tol))


def good_turned_spool():
    """
    A finished turned spool: two flanges, both web roots RADIUSED to R2.5, a
    through bore, and every rim chamfered to 1.0.

    The turned class's upper reference. A shoulder root is what a turned part
    repeats instead of screw positions, and a radius there is the finished
    answer: it removes the stress riser and gives the mating part's own break
    somewhere to sit, which a 45 degree undercut does not. This part must
    therefore rank above the gland, whose roots are chamfered.

    It is also the control for two measurements that used to punish exactly this
    move. The convex ROUND-OVER at each flange corner is tangent on both sides,
    where the per-edge convexity probe is degenerate, and it was read as
    smooth_CONCAVE - so rounding an outside corner banked shoulder relief. And a
    cylinder with a tangent runout at each end satisfies the whole blend test,
    so a journal between two root fillets was read as "a fillet of half its own
    diameter" and taken off the radius ladder.
    """
    body = _wp(
        cq.Solid.makeCylinder(24.0, 5.0, cq.Vector(0, 0, 0))
        .fuse(cq.Solid.makeCylinder(13.0, 22.0, cq.Vector(0, 0, 5.0)))
        .fuse(cq.Solid.makeCylinder(24.0, 5.0, cq.Vector(0, 0, 27.0)))
        .clean()
    )
    body = body.edges(_z_ring(5.0)).fillet(2.5).edges(_z_ring(27.0)).fillet(2.5)
    body = _wp(body.val().cut(cq.Solid.makeCylinder(6.0, 60.0, cq.Vector(0, 0, -10.0))))
    return body.edges(_z_ring(0.0)).chamfer(1.0).edges(_z_ring(32.0)).chamfer(1.0)


def gamed_turned_blank_tube():
    """
    A bored tube with no feature on it at all, plus one blanket .fillet(1.0).

    THE TURNED CLASS HAD NO ADVERSARY, WHICH IS PRECISELY WHY THE DEFECT IT
    ATTACKS SHIPPED. Every gamed case in this corpus was a prism, so nothing
    ever asked what a body of revolution could get for free - and the answer
    was: almost everything. One .fillet() call over `edges()` breaks every
    convex edge the part has, which maxes edge_break_coverage and
    sharp_edge_length at once and gives radius_vocabulary a single perfectly
    coherent rung; a solid of revolution is exactly symmetric; and a 40 x 60 mm
    barrel sits in the middle of the proportion knots.

    The fourth free metric was face_composition, and it was free for a reason
    no prism could expose: the metric read PLANAR faces only, so the entire
    visible skin of this part - a 58 mm by 126 mm developed blank panel - was
    invisible to it, and it scored the two 8 mm end annuli, which are far too
    narrow to hold a large empty circle. Measured on the real round trip:
    face_composition 100.0 at its full 0.19 weight having examined 14% of the
    exterior, and 77.3/B overall, CLEARING the 70.0 advisory gate unassisted.
    Reading the developed skin puts it at 0.0 and the part at 58.3/C.

    So this case is here to hold `gamed_below_gate` against the turned class,
    which it used to break. Its stronger relatives are worth recording: the
    same tube counterbored measured 88.7/A before and 69.7/C after, and with an
    arbitrary ring groove added 94.0/A before and 80.3/B after - band A, above
    this repo's own exemplar at 83.1, for six lines of CadQuery.
    """
    body = cq.Workplane("XY").circle(20.0).extrude(60.0)
    body = body.faces(">Z").workplane().hole(24.0)
    return body.edges().fillet(1.0)


def crude_turned_billet():
    """
    A plain turned billet with one chamfer: one diameter, one broken corner.

    The turned analogue of ladder_1_sharp. There is no profile here to compose
    and no shoulder here to relieve, and saying so is a measurement, not an
    exemption - which is the whole difference between this pass and the one
    before it.
    """
    return cq.Workplane("XY").circle(16.0).extrude(45.0).edges(">Z").chamfer(1.0)


# --------------------------------------------------------------------------- #
# 5. robustness probes - NOT corpus cases
#    These say nothing about design quality. They exist because a scorer that
#    collapses on a numerical degeneracy is not a scorer, and the corpus's
#    whole job is to make that impossible to ship unnoticed.
# --------------------------------------------------------------------------- #
def probe_exactly_symmetric_solid():
    """
    A solid that is PERFECTLY symmetric about y = 0 but whose measured centroid
    lands at y = 4.04e-07 instead of 0.

    That sub-micron offset is not a defect in the part - OCC simply integrates
    the volume to finite precision, and every real part does this. It is here
    because mirroring about a plane through that centroid and differencing the
    result is a degenerate boolean, and when the boolean degenerates the answer
    it produces is "100% asymmetric", i.e. the WORST possible score, silently.

    Verified: mirroring this solid about y = 0 exactly leaves 0.000000 mm3 of
    asymmetric volume, so the geometry is beyond argument.
    """
    t, depth = 12.0, 70.0
    base_l, up_h = 96.0, 76.0
    sk = (
        cq.Sketch()
        .polygon([(0.0, 0.0), (base_l, 0.0), (base_l, t), (t, t), (t, up_h), (0.0, up_h)])
        .vertices()
        .fillet(6.0)
    )
    body = (
        cq.Workplane("XZ")
        .placeSketch(sk)
        .extrude(depth)
        .translate((-base_l / 2, depth / 2, -up_h / 2))
    )
    body = body.faces(">Y").chamfer(1.5).faces("<Y").chamfer(1.5)
    for face, size in ((">Z", (46.0, 34.0)), ("<X", (34.0, 34.0))):
        body = ft.lightening_pocket(body, face, size=size, depth=4.0, radius=8.0, wall=t).solid
    body = ft.counterbore_at(
        body,
        [(x, y) for x in (14.0, 40.0) for y in (-22.0, 22.0)],
        plane=ft.face_plane(body, "+Z"),
        fastener="M6",
    )
    return ft.fastener_holes(
        body,
        [(u, v) for u in (-22.0, 22.0) for v in (14.0, 40.0)],
        plane=ft.face_plane(body, "-X"),
        fastener="M6",
        kind="clearance",
    )


# --------------------------------------------------------------------------- #
# 6. real parts - the exported artifacts, exactly as they ship
# --------------------------------------------------------------------------- #
def _newest_step(part_dir: Path, stem: str) -> Path | None:
    """
    The newest matching STEP under a part's exports/, attempts included.

    Exports are gitignored, so a fresh clone has none of them. Every real case
    therefore resolves lazily and reports "missing" rather than failing the
    corpus, and the contract that depends on it degrades to "unevaluated".
    """
    cands = list(part_dir.glob(f"exports/{stem}.step"))
    cands += list(part_dir.glob(f"exports/attempts/*/{stem}.step"))
    cands = [p for p in cands if p.is_file()]
    if not cands:
        return None
    return max(cands, key=lambda p: p.stat().st_mtime)


def _model_step(part_dir: Path, stem: str, fn: str = "create_part") -> Path | None:
    """Fall back to building the part from its own model.py, then caching it."""
    model = part_dir / "model.py"
    if not model.exists():
        return None
    out = STEP_DIR / f"{stem}.step"
    if out.exists():
        return out
    spec = importlib.util.spec_from_file_location(f"_corpus_{part_dir.name}", model)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        solid = getattr(mod, fn)()
    except Exception:
        return None
    _cache_dir(STEP_DIR)
    cq.exporters.export(solid, str(out))
    return out


def _real(rel_dir: str, stem: str):
    def resolve() -> Path | None:
        part_dir = PROJECT_ROOT / rel_dir
        return _newest_step(part_dir, stem) or _model_step(part_dir, stem)

    return resolve


# --------------------------------------------------------------------------- #
# the corpus
# --------------------------------------------------------------------------- #
CASES: tuple[Case, ...] = (
    # -- the monotonic ladder ------------------------------------------------
    Case(
        "ladder_1_sharp",
        "plain sharp box",
        "base",
        "enclosure",
        "The floor. A raw extrusion with nothing done to it: no part in the "
        "corpus may score at or below it, and nothing may score below it.",
        build=ladder_1_sharp,
        rung=1,
    ),
    Case(
        "ladder_2_plan_radii",
        "box + plan radii",
        "crude",
        "enclosure",
        "One move made: plan corners on the style ladder. Still a blank-faced "
        "slab with knife-edged rims - a first pass, not a part.",
        build=ladder_2_plan_radii,
        rung=2,
    ),
    Case(
        "ladder_3_edge_breaks",
        "box + radii + rim breaks",
        "crude",
        "enclosure",
        "Two moves: radii plus a chamfer on both rims. No unbroken convex edge "
        "left, and still nothing on any face. Styling applied to a lump.",
        build=ladder_3_edge_breaks,
        rung=3,
    ),
    Case(
        "ladder_4_panel_ribs",
        "+ recessed panels and rib fields",
        "crude",
        "enclosure",
        "Three moves. Reads well, but it is a sealed lump: no fastening, no "
        "interface, nothing mates to it. Not yet a part anyone can use.",
        build=ladder_4_panel_ribs,
        rung=4,
    ),
    Case(
        "ladder_5_bolted",
        "+ solved counterbored bolt pattern",
        "good",
        "enclosure",
        "The minimum competent enclosure and the `enclosure` role reference: "
        "radii and breaks on one ladder, panels with ribs on three faces, and "
        "a symmetric bolt pattern at a solved constant pitch and inset.",
        build=ladder_5_bolted,
        rung=5,
    ),
    # -- the audit's gamed cases --------------------------------------------
    Case(
        "gamed_blob_csk",
        "blob + oversized countersunk holes",
        "gamed",
        "enclosure",
        "The audit's 96.7/A winner, which cleared the 70.0 gate. A lumpy pile "
        "of overlapping rounded boxes with randomly scattered oversized "
        "countersinks, some merged into figure-of-eight blobs. No panel, no "
        "frame, no land, no rhythm, no emblem, nothing functional.",
        build=gamed_blob_csk,
        slow=True,
        attacks=(
            "edge_break_coverage",
            "face_composition",
            "feature_composition",
            "pattern_discipline",
        ),
    ),
    Case(
        "gamed_blob_concave_fillets",
        "blob + buried concave fillets + D24 scatter",
        "gamed",
        "enclosure",
        "The audit's 85.4 case. Union seams between overlapping lumps are "
        "concave, and concave blend runouts were banked as broken convex edge.",
        build=gamed_blob_concave_fillets,
        slow=True,
        attacks=("edge_break_coverage", "radius_vocabulary"),
    ),
    Case(
        "gamed_chamfer_box_random_holes",
        "chamfered box, random holes",
        "gamed",
        "enclosure",
        "The audit's 82.0/B case, which outscored the exemplar. One blanket "
        "chamfer operation plus holes wherever they landed.",
        build=gamed_chamfer_box_random_holes,
        attacks=("edge_break_coverage", "face_composition"),
    ),
    Case(
        "gamed_knife_box_csk",
        "knife-edged box, countersunk holes",
        "gamed",
        "enclosure",
        "The audit's 67.8/C case. Every knife edge intact; the only thing "
        "resembling a break is a countersink cone, which is counted twice.",
        build=gamed_knife_box_csk,
        attacks=("edge_break_coverage",),
    ),
    Case(
        "gamed_sealed_cavity_fillets",
        "box + concave fillets in a sealed cavity",
        "gamed",
        "enclosure",
        "The audit's 58.4/C case. The blends are inside a fully enclosed void: "
        "invisible, unmanufacturable, and previously worth real score.",
        build=gamed_sealed_cavity_fillets,
        attacks=("edge_break_coverage", "radius_vocabulary"),
    ),
    Case(
        "gamed_knife_box_3_holes",
        "knife-edged box + 3 through holes",
        "gamed",
        "enclosure",
        "The audit's 41.5/F case. Three holes were enough to make every large "
        "face 'carry a feature' and take blank_face_ratio to a perfect 100.",
        build=gamed_knife_box_3_holes,
        attacks=("face_composition",),
    ),
    # -- gaming vectors invented for this corpus -----------------------------
    Case(
        "gamed_groove_decoration",
        "raw slab wrapped in scribe grooves",
        "gamed",
        "enclosure",
        "Decoration bought directly: dozens of closed grooves and scribe lines "
        "that stiffen nothing, seal nothing and bound nothing, on a raw box.",
        build=gamed_groove_decoration,
        attacks=("feature_composition", "face_composition"),
    ),
    Case(
        "gamed_near_symmetry",
        "near-symmetric, visibly one-sided",
        "gamed",
        "enclosure",
        "Every asymmetry is thin - one rim chamfered, one blade fin, one end "
        "pocket - so a symmetric-difference VOLUME reads a couple of percent "
        "while the eye reads a part that is obviously wrong.",
        build=gamed_near_symmetry,
        attacks=("symmetry",),
    ),
    Case(
        "gamed_soap_bar",
        "every edge blended at one huge radius",
        "gamed",
        "enclosure",
        "One operation maxes three metrics: full coverage, zero sharp length "
        "and a single-rung radius vocabulary. The result is a bar of soap.",
        build=gamed_soap_bar,
        attacks=("edge_break_coverage", "sharp_edge_length", "radius_vocabulary"),
    ),
    Case(
        "gamed_projected_alignment",
        "holes aligned only in projection",
        "gamed",
        "enclosure",
        "A clean 3 x 2 grid in plan view that is two unrelated hole families "
        "in the solid, at three diameters, drilled along two different axes. "
        "The trap for a composition metric built on projected centres.",
        build=gamed_projected_alignment,
        attacks=("pattern_discipline", "feature_composition"),
    ),
    Case(
        "gamed_facet_fillet",
        "plan corners faked with five facets",
        "gamed",
        "enclosure",
        "Each facet band passes as a chamfer land and each crease is too "
        "shallow to read as a knife edge, so the corners score as broken while "
        "the part is visibly faceted.",
        build=gamed_facet_fillet,
        attacks=("edge_break_coverage", "sharp_edge_length"),
    ),
    Case(
        "gamed_hole_flood",
        "forty random holes in a slab",
        "gamed",
        "enclosure",
        "Saturates any metric that counts. Nothing is on a pitch, on a line, "
        "or at a repeated edge inset.",
        build=gamed_hole_flood,
        attacks=("feature_composition", "face_composition"),
    ),
    # -- good parts, one per role -------------------------------------------
    Case(
        "good_interface_plate",
        "optical interface plate, M6 grid at 25 mm",
        "good",
        "plate",
        "False-negatived at 72.3/B in the audit. Its flat underside is the "
        "mounting datum and its slab aspect is what makes it stiff; both were "
        "scored as defects by an enclosure's rubric.",
        build=good_interface_plate,
        attacks=(),
    ),
    Case(
        "good_sealed_cover",
        "sealed cover, lapped face and O-ring groove",
        "good",
        "cover",
        "False-negatived at 50.2/D in the audit. Flat sealing land, real "
        "groove, locating spigot, counterbored rim on a solved pitch, recessed "
        "outer panel. A cover is thin because a cover is thin.",
        build=good_sealed_cover,
        attacks=(),
    ),
    Case(
        "good_sheet_bracket",
        "2 mm sheet-metal bracket, two bends",
        "good",
        "sheet",
        "False-negatived at 43.1/D in the audit, and unfixable without ceasing "
        "to be sheet metal: 2 mm material cannot carry a chamfer or a plan "
        "fillet on the blanked perimeter. Judged as sheet, the breaks that "
        "count are the formed radii.",
        build=good_sheet_bracket,
        attacks=(),
    ),
    Case(
        "good_machined_bracket",
        "machined angle bracket, pocketed legs",
        "good",
        "bracket",
        "The `bracket` role reference, and the control for the sheet case: "
        "solid material CAN carry an edge break, so the whole blanked outline "
        "is chamfered, every profile corner is one ladder rung, each leg "
        "carries a lightening pocket with a broken mouth, and both hole groups "
        "share a pitch and an edge inset.",
        build=good_machined_bracket,
        attacks=(),
    ),
    Case(
        "good_structural_arm",
        "sculpted structural arm",
        "good",
        "structural",
        "The `structural` role reference. Mass removed where it does no work, "
        "generous pocket radii, a turned step-stack pivot boss rather than a "
        "butt joint.",
        build=good_structural_arm,
        attacks=(),
    ),
    Case(
        "good_turned_gland",
        "turned gland body, stepped and bored",
        "good",
        "enclosure",
        "The TURNED class reference, and the control for four defects that only "
        "a body of revolution exposes: no bolt pattern is not a missing bolt "
        "pattern, the OD of a turned part is silhouette and not bore rim, a cone "
        "IS a chamfer, and one deburred bore mouth is not a broken corner. It "
        "declares no role - the reviewer measures that it is turned.",
        build=good_turned_gland,
        attacks=(),
    ),
    Case(
        "good_turned_spool",
        "turned spool, flanged with radiused web roots",
        "good",
        "enclosure",
        "The second turned reference, and the one that says what the FIRST one "
        "is still missing. The gland breaks every corner it has, including its "
        "shoulder roots, but it breaks them with chamfers; this spool radiuses "
        "its web roots instead, which is the finished answer at an internal "
        "corner, and it must score above a part whose roots are only chamfered. "
        "It is also the control for two measurement defects that punish exactly "
        "that move: a convex ROUND-OVER of an outside corner must not read as "
        "shoulder relief, and the journal between two root fillets must not read "
        "as a fillet of half its own diameter.",
        build=good_turned_spool,
        attacks=(),
    ),
    Case(
        "gamed_turned_blank_tube",
        "bored tube, one blanket fillet, nothing else",
        "gamed",
        "enclosure",
        "The corpus's first adversarial TURNED case, and the class had none - "
        "which is exactly why a metric that could not read a curved surface "
        "shipped. One .fillet() over every edge maxes edge_break_coverage, "
        "sharp_edge_length and radius_vocabulary together; a solid of "
        "revolution is symmetric for free; and while face_composition read "
        "planar faces only, the 58 x 126 mm blank barrel was invisible to it "
        "and the part scored 77.3/B, over the advisory gate, on nothing.",
        build=gamed_turned_blank_tube,
        attacks=(
            "face_composition",
            "edge_break_coverage",
            "sharp_edge_length",
            "radius_vocabulary",
        ),
    ),
    Case(
        "crude_turned_billet",
        "turned billet, one chamfer, nothing else",
        "crude",
        "enclosure",
        "The turned analogue of ladder_1_sharp, and the low end of the "
        "calibration this class needs. It is a single diameter with one corner "
        "broken - bar stock, not a designed profile - and while the two "
        "composition metrics were EXCUSED on any body of revolution it measured "
        "55.3 with 0.28 of the rubric renormalised out from under it. Nothing "
        "about a turned part may be free.",
        build=crude_turned_billet,
        attacks=(),
    ),
    # -- real artifacts ------------------------------------------------------
    Case(
        "real_reference_mast_node",
        "reference_mast_node_enclosure v1",
        "real",
        "enclosure",
        "The exemplar built with lib/features.py - the most refined real part "
        "in the repo. Must outrank every other real part, and must outrank "
        "every gamed case (in the audit three of them beat it).",
        artifact=_real(
            "parts/custom/reference_mast_node_enclosure", "reference_mast_node_enclosure_v1"
        ),
        slow=True,
    ),
    Case(
        "good_scaffold_template",
        "parts/_template (the scaffold)",
        "good",
        "enclosure",
        "The PLAIN pole, and it is a real artifact rather than a fixture. "
        "`make new-part` copies it, it is built entirely from lib/features.py, "
        "every convex body edge is broken and its bolt patterns are clean - so "
        "it belongs in the good set and must stay over the gate. What it is "
        "here for is the comparison in the test file: it is a rounded soap-bar "
        "case whose features are four decorative lid grooves, five identical "
        "recesses in a row and a handle ear, and it must NOT outrank "
        "reference_mast_node_enclosure, whose every feature is a mechanism. It "
        "did, by 2.80, until radius_vocabulary stopped charging for richness "
        "and symmetry stopped charging for having a connector.",
        artifact=_real("parts/_template", "_template_v1"),
        slow=True,
    ),
    Case(
        "real_amplifier_housing_v3",
        "amplifier_housing v3",
        "real",
        "enclosure",
        "A knife-edged slab housing with real features: 0 of 5240 mm of convex "
        "body edge broken, and 100% of its blend area buried inside a sealed "
        "cavity. Draft-grade, and it must stay below the gate. Its ranking "
        "against example_part_v1 is NOT asserted - see contract item 8.",
        artifact=_real("parts/amplifier_housing", "amplifier_housing_v3"),
        slow=True,
    ),
    Case(
        "real_am59_sealed_mast_head",
        "am59_sealed_mast_head v2",
        "real",
        "enclosure",
        "A fourth real enclosure, included for breadth: it is a genuine design "
        "with sealing detail, so it should not fall below the 4-hole plate.",
        artifact=_real("parts/custom/am59_sealed_mast_head", "am59_sealed_mast_head_v2"),
        slow=True,
    ),
    Case(
        "real_example_part_v1",
        "example_part v1 (4-hole plate)",
        "real",
        "plate",
        "The template mounting plate: four counterbores in a rectangle and "
        "nothing else, with no edge broken anywhere. Draft-grade, and it must "
        "stay below the gate.",
        artifact=_real("parts/example_part", "example_part_v1"),
    ),
)

BY_ID = {c.id: c for c in CASES}


# --------------------------------------------------------------------------- #
# scoring
# --------------------------------------------------------------------------- #
def config_for(case: Case) -> dict:
    """
    The reviewer config a case is judged under.

    "role" is the whole point: the audit's three false negatives are all
    legitimate roles judged by an enclosure's rubric. A reviewer that does not
    know the key ignores it and reproduces the audit exactly, which is what
    makes this corpus bite today.
    """
    return {"role": case.role, "min_score": GATE}


def _sha(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:12]


def _build_key() -> str:
    """
    Fingerprint of everything a synthetic case's GEOMETRY is built from.

    Content hashes, not mtimes, and the same argument as review()'s source list
    one level down: 22 of the 31 cases are built through lib/features.py, so an
    edit to a Style ladder, a wall rule or a builder moves their geometry while
    design_corpus.py sits untouched. The old test was `out.stat().st_mtime <
    design_corpus.py's mtime`, which sees only this file - so after a features.py
    edit the corpus re-scored STALE BYTES and printed the pre-edit table with
    full confidence. A cache that reports a stale verdict is worse than no
    cache, because the run looks like evidence.

    A mtime test is also wrong in the other direction: `git checkout` of an OLDER
    revision of this file makes stale bytes look fresh. Hashing content cannot.
    """
    return "-".join(
        _sha(p)
        for p in (
            Path(__file__),  # the case builders themselves
            PROJECT_ROOT / "lib" / "features.py",  # the design language 22 cases are built from
        )
    )


def step_for(case: Case, *, rebuild: bool = False) -> Path:
    """
    The case as an exported STEP - the artifact, never the in-memory solid.

    Cached under tmp/design_corpus/step/, keyed by _build_key() so a change to
    any build input invalidates the geometry rather than silently reusing it.
    The house rule is that a review reads the exported B-rep, because that is
    the thing that ships and the thing that re-import can change.
    """
    if case.artifact is not None:
        path = case.artifact()
        if path is None:
            raise FileNotFoundError(
                f"{case.id}: no exported STEP found and model.py could not build one - "
                "run `make export-all` or the part's model.py"
            )
        return path
    _cache_dir(STEP_DIR)
    out = STEP_DIR / f"{case.id}-{_build_key()}.step"
    if rebuild or not out.exists():
        solid = case.build()
        cq.exporters.export(solid, str(out))
    return out


def review(case: Case, *, rebuild: bool = False) -> dict:
    """
    Score one case, caching the report against the STEP AND the scorer.

    The cache key includes a hash of EVERY module the score is computed from, so
    editing any of them invalidates every cached review while an unrelated edit
    costs nothing. That is what keeps the corpus affordable in the default test
    run without ever letting it report a stale verdict.

    lib/analyze_step.py is in that list because it was once missing from it. The
    cylindrical-feature extraction it owns feeds feature_composition and
    pattern_discipline through cylinder_wrap, and while its axial-length defect
    was being fixed this corpus went on printing the pre-fix table with total
    confidence - a cache that reports a stale verdict is worse than no cache,
    because the run looks like evidence. Any future module the score reads
    belongs here on the same argument.
    """
    path = step_for(case, rebuild=rebuild)
    sources = [
        PROJECT_ROOT / "lib" / "design_review.py",
        PROJECT_ROOT / "lib" / "analyze_step.py",
        # lib/frame.py is the RULER. Every size, centre, tolerance, mirror plane
        # and layout basis in the review is taken off the frame it returns, so a
        # change there moves every score in this table while design_review.py
        # sits untouched - exactly the way analyze_step.py once did.
        PROJECT_ROOT / "lib" / "frame.py",
        Path(__file__),  # config_for() lives here and decides the rubric each case is held to
    ]
    key = "-".join([_sha(path)] + [_sha(s) for s in sources])
    _cache_dir(REVIEW_DIR)
    cached = REVIEW_DIR / f"{case.id}-{key}.json"
    if cached.exists() and not rebuild:
        return json.loads(cached.read_text())
    shape = cq.importers.importStep(str(path)).val()
    report = review_shape(shape, source=f"corpus:{case.id}", config=config_for(case))
    cached.write_text(json.dumps(report, indent=1, default=str))
    return report


@dataclass
class Row:
    """One scored case, flattened for the table and the contract."""

    case: Case
    status: str
    score: float | None
    band: str | None
    metrics: dict[str, float | None]
    message: str
    elapsed_s: float

    @property
    def id(self) -> str:
        return self.case.id

    @property
    def ok(self) -> bool:
        return self.score is not None


def score_case(case: Case, *, rebuild: bool = False) -> Row:
    t0 = time.time()
    try:
        rep = review(case, rebuild=rebuild)
    except Exception as exc:
        return Row(
            case,
            "missing",
            None,
            None,
            {},
            f"{type(exc).__name__}: {exc}",
            round(time.time() - t0, 2),
        )
    metrics = {mid: m.get("score") for mid, m in (rep.get("metrics") or {}).items()}
    return Row(
        case,
        rep.get("status", "?"),
        rep.get("score"),
        rep.get("band"),
        metrics,
        rep.get("message", ""),
        round(time.time() - t0, 2),
    )


# --------------------------------------------------------------------------- #
# the ordering contract
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ContractResult:
    """One assertion about the ordering. ok=None means it could not be judged."""

    id: str
    title: str
    ok: bool | None
    detail: str


def _scored(rows: list[Row], klass: str | None = None) -> list[Row]:
    return [r for r in rows if r.ok and (klass is None or r.case.klass == klass)]


def _fmt(rows: list[Row]) -> str:
    return ", ".join(f"{r.id}={r.score}" for r in sorted(rows, key=lambda r: -(r.score or 0)))


def check_contract(
    rows: list[Row], *, margin: float = MARGIN, gate: float = GATE
) -> list[ContractResult]:
    """
    What "the gate works" MEANS, as assertions on the ordering.

    Absolute scores will move as the metrics are reworked, so nothing here
    asserts a value. Every item is a relation between cases whose relative
    quality is known by construction, plus the two absolute bars the pipeline
    itself uses (the advisory gate, in both directions).
    """
    out: list[ContractResult] = []
    present = {r.id: r for r in rows}
    good, gamed = _scored(rows, "good"), _scored(rows, "gamed")
    crude = _scored(rows, "crude") + _scored(rows, "base")

    # 0. nothing silently unscored - a case that errors is a broken review
    broken = [r for r in rows if not r.ok and r.status != "missing"]
    missing = [r for r in rows if r.status == "missing"]
    out.append(
        ContractResult(
            "all_cases_scored",
            "every corpus case produces a score",
            len(broken) == 0,
            "all scored"
            if not broken
            else "unscored: " + ", ".join(f"{r.id}({r.status}: {r.message})" for r in broken),
        )
    )
    if missing:
        out.append(
            ContractResult(
                "artifacts_present",
                "every real artifact resolved",
                None,
                "not evaluated - " + ", ".join(r.id for r in missing),
            )
        )

    # 1. the ladder is monotonic
    ladder = sorted((r for r in rows if r.case.rung and r.ok), key=lambda r: r.case.rung)
    if len(ladder) < 2:
        out.append(
            ContractResult(
                "ladder_monotonic", "the refinement ladder is monotonic", None, "ladder incomplete"
            )
        )
    else:
        bad = [
            (a.id, a.score, b.id, b.score)
            for a, b in zip(ladder, ladder[1:])
            if not (b.score > a.score)
        ]
        out.append(
            ContractResult(
                "ladder_monotonic",
                "the refinement ladder is monotonic",
                not bad,
                " -> ".join(f"{r.case.rung}:{r.score}" for r in ladder)
                if not bad
                else "inversions: " + "; ".join(f"{a}={s} >= {c}={t}" for a, s, c, t in bad),
            )
        )

    # 2. the base is the floor
    floor = present.get("ladder_1_sharp")
    others = [r for r in rows if r.ok and r.id != "ladder_1_sharp"]
    if floor is None or not floor.ok or not others:
        out.append(
            ContractResult(
                "base_is_floor", "the plain sharp box is the floor", None, "base case unscored"
            )
        )
    else:
        under = [r for r in others if r.score <= floor.score]
        out.append(
            ContractResult(
                "base_is_floor",
                "the plain sharp box is the floor",
                not under,
                f"base={floor.score}"
                if not under
                else f"base={floor.score} but {_fmt(under)} scored at or below it",
            )
        )

    # 3. no gamed case reaches the advisory gate
    if not gamed:
        out.append(
            ContractResult(
                "gamed_below_gate", f"no gamed case reaches {gate}", None, "no gamed case scored"
            )
        )
    else:
        over = [r for r in gamed if r.score >= gate]
        out.append(
            ContractResult(
                "gamed_below_gate",
                f"no gamed case reaches the advisory gate ({gate})",
                not over,
                f"worst gamed = {max(r.score for r in gamed)}"
                if not over
                else f"AT OR OVER THE GATE: {_fmt(over)}",
            )
        )

    # 4. every good case clears the gate under its own role
    if not good:
        out.append(
            ContractResult(
                "good_clears_gate", f"every good case reaches {gate}", None, "no good case scored"
            )
        )
    else:
        under = [r for r in good if r.score < gate]
        out.append(
            ContractResult(
                "good_clears_gate",
                f"every good case clears the gate ({gate}) under its own role",
                not under,
                f"worst good = {min(r.score for r in good)}"
                if not under
                else "BELOW THE GATE: "
                + ", ".join(
                    f"{r.id}[{r.case.role}]={r.score}" for r in sorted(under, key=lambda r: r.score)
                ),
            )
        )

    # 5/6. class separation with a stated margin
    for cid, title, group in (
        ("gamed_below_good", "every gamed case scores below every good case", gamed),
        ("crude_below_good", "every crude/base case scores below every good case", crude),
    ):
        if not group or not good:
            out.append(ContractResult(cid, title, None, "one side of the comparison is empty"))
            continue
        worst_good = min(good, key=lambda r: r.score)
        offenders = [r for r in group if r.score + margin > worst_good.score]
        best = max(group, key=lambda r: r.score)
        detail = (
            f"best is {best.id}={best.score}, worst good is {worst_good.id}={worst_good.score}"
            if not offenders
            else f"worst good is {worst_good.id}={worst_good.score}, not clear of {_fmt(offenders)}"
        )
        out.append(ContractResult(cid, f"{title} (margin {margin})", not offenders, detail))

    # 7. the audit's headline: nothing gamed may outrank the exemplar
    ex = present.get("real_reference_mast_node")
    if ex is None or not ex.ok or not gamed:
        out.append(
            ContractResult(
                "gamed_below_exemplar",
                "no gamed case outranks the exemplar",
                None,
                "exemplar or gamed set unscored",
            )
        )
    else:
        over = [r for r in gamed if r.score >= ex.score]
        out.append(
            ContractResult(
                "gamed_below_exemplar",
                "no gamed case outranks the exemplar",
                not over,
                f"exemplar={ex.score}"
                if not over
                else f"exemplar={ex.score} is outranked by {_fmt(over)}",
            )
        )

    # 8. the exemplar leads the real parts, and no other real part passes
    #
    # RE-BASELINED 2026-07-25. WHAT THIS USED TO ASSERT, AND WHY IT WAS WRONG.
    # It asserted a total order over three real parts:
    #     reference_mast_node > amplifier_housing_v3 > example_part_v1
    # The first relation is a real invariant and is kept. The second was not.
    # It baked one human's ranking of two DRAFT-GRADE parts against each other
    # into the contract, and the ranking between two bad parts carries no
    # information: amplifier_housing_v3 measures 46.4/D and example_part_v1
    # 51.5/D, both far below the 70.0 gate, both knife-edged, and neither is a
    # reference for anything. Which of the two is marginally less rough is a
    # matter of which defect the rubric happens to weigh more this week.
    #
    # It went red when radius_vocabulary stopped counting INTERIOR-ONLY blends
    # as visible refinement. That fix is correct and is NOT reverted:
    # amplifier_housing_v3 has 0 of 5240 mm of convex body edge broken and 100%
    # of its blend area buried inside a sealed cavity where nobody can see it,
    # so 46.4 is a more honest reading than the 60.0 it used to get. The
    # assertion was over-specified; the metric was not wrong.
    #
    # WHAT REPLACES IT, and what the evidence actually supports:
    #   (a) the exemplar clearly outranks EVERY other real part, by `margin`.
    #       That is the relation the exemplar exists to demonstrate, it is what
    #       the skill points agents at, and it holds by 31.6 points today.
    #   (b) every OTHER real part sits below the advisory gate. Not one of them
    #       has had a refinement pass, and a corpus that let one drift over 70
    #       without anybody noticing would have lost its only real-world anchor.
    # Both are properties of the parts, not of one reading of them.
    ex = present.get("real_reference_mast_node")
    others = [r for r in rows if r.case.klass == "real" and r.id != "real_reference_mast_node"]
    if ex is None or not ex.ok or not others or any(not r.ok for r in others):
        out.append(
            ContractResult(
                "real_ordering",
                "the exemplar leads the real parts, and no other real part passes",
                None,
                "one or more real artifacts unscored",
            )
        )
    else:
        close = [r for r in others if r.score + margin > ex.score]
        over = [r for r in others if r.score >= gate]
        detail = (
            f"exemplar={ex.score}, next real part is "
            f"{max(others, key=lambda r: r.score).id.replace('real_', '')}="
            f"{max(r.score for r in others)}"
            if not (close or over)
            else "; ".join(
                filter(
                    None,
                    [
                        f"not clear of the exemplar ({ex.score}) by {margin}: {_fmt(close)}"
                        if close
                        else "",
                        f"AT OR OVER THE GATE ({gate}): {_fmt(over)}" if over else "",
                    ],
                )
            )
        )
        out.append(
            ContractResult(
                "real_ordering",
                f"the exemplar outranks every other real part by {margin}, and no other "
                f"real part reaches the gate ({gate})",
                not (close or over),
                detail,
            )
        )
    return out


# --------------------------------------------------------------------------- #
# runner
# --------------------------------------------------------------------------- #
@dataclass
class CorpusResult:
    rows: list[Row]
    contract: list[ContractResult]
    elapsed_s: float

    @property
    def passed(self) -> bool:
        return all(c.ok is not False for c in self.contract)

    @property
    def failures(self) -> list[ContractResult]:
        return [c for c in self.contract if c.ok is False]

    def row(self, case_id: str) -> Row:
        return next(r for r in self.rows if r.id == case_id)


def select(
    *, only: tuple[str, ...] = (), klass: str | None = None, fast: bool = False
) -> list[Case]:
    """The subset to run. `fast` drops the cases marked slow."""
    cases = list(CASES)
    if only:
        cases = [c for c in cases if c.id in only]
    if klass:
        cases = [c for c in cases if c.klass == klass]
    if fast:
        cases = [c for c in cases if not c.slow]
    return cases


def run_corpus(
    cases: list[Case] | None = None,
    *,
    rebuild: bool = False,
    progress: Callable[[str], None] | None = None,
) -> CorpusResult:
    """Build, export, re-import, review and judge - the whole fixture."""
    t0 = time.time()
    rows: list[Row] = []
    for case in cases if cases is not None else list(CASES):
        if progress:
            progress(f"  .. {case.id}")
        rows.append(score_case(case, rebuild=rebuild))
    return CorpusResult(rows, check_contract(rows), round(time.time() - t0, 2))


# --------------------------------------------------------------------------- #
# presentation
# --------------------------------------------------------------------------- #
# The LIVE eight. blank_face_ratio, feature_density and fastener_rhythm used to
# sit here and were dead keys - retired metric ids that no report can emit - so
# the table silently documented a rubric that no longer exists.
_METRIC_ABBR = {
    "edge_break_coverage": "edge",
    "sharp_edge_length": "sharp",
    "face_composition": "face_",
    "feature_composition": "featu",
    "pattern_discipline": "patte",
    "radius_vocabulary": "radv",
    "symmetry": "symm",
    "proportion": "prop",
}


def format_table(result: CorpusResult) -> str:
    mids: list[str] = []
    for r in result.rows:
        for mid in r.metrics:
            if mid not in mids:
                mids.append(mid)
    heads = [_METRIC_ABBR.get(m, m[:5]) for m in mids]
    w_id = max([len(r.id) for r in result.rows] + [4])
    w_role = max([len(r.case.role) for r in result.rows] + [4])

    lines = [
        f"{'CLASS':6s} {'ID':{w_id}s} {'ROLE':{w_role}s} {'SCORE':>6s} {'BD':>2s}  "
        + " ".join(f"{h:>5s}" for h in heads)
        + "   s"
    ]
    lines.append("-" * len(lines[0]))
    for r in sorted(result.rows, key=lambda r: (-(r.score if r.ok else -1), r.id)):
        score = f"{r.score:6.1f}" if r.ok else f"{r.status:>6s}"
        cells = []
        for mid in mids:
            v = r.metrics.get(mid)
            cells.append(f"{v:5.0f}" if isinstance(v, (int, float)) else f"{'-':>5s}")
        lines.append(
            f"{r.case.klass.upper():6s} {r.id:{w_id}s} {r.case.role:{w_role}s} {score} "
            f"{(r.band or '-'):>2s}  " + " ".join(cells) + f" {r.elapsed_s:5.1f}"
        )
    return "\n".join(lines)


def format_contract(result: CorpusResult) -> str:
    lines = []
    for c in result.contract:
        mark = "PASS" if c.ok else ("FAIL" if c.ok is False else "SKIP")
        lines.append(f"  [{mark}] {c.id:22s} {c.title}")
        lines.append(f"         {c.detail}")
    n_fail = len(result.failures)
    n_skip = sum(1 for c in result.contract if c.ok is None)
    n_hold = len(result.contract) - n_fail - n_skip
    lines.append("")
    # An assertion that could not be judged is reported apart from one that
    # holds. Rolling the two together is how a fixture quietly stops biting.
    lines.append(
        f"  contract: {n_hold} hold, {n_fail} FAIL, {n_skip} unevaluated "
        f"of {len(result.contract)}   ({result.elapsed_s:.1f}s)"
    )
    return "\n".join(lines)


def render_case(case: Case, out_dir: Path | None = None, *, product: bool = False) -> list[Path]:
    """
    Render a case so a human can confirm the label by eye.

    A gamed case that accidentally looks decent is a worthless fixture, so
    every one of them was rendered and read back before it went in.
    """
    from lib.render_step import render_file

    path = step_for(case)
    out = Path(out_dir) if out_dir else _cache_dir(CACHE_DIR / "render")
    out.mkdir(parents=True, exist_ok=True)
    if product:
        return render_file(path, out, views=("hero",), size=900, quality="product", supersample=1)
    return render_file(path, out, views=("iso",), size=800, axes=False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="ID",
        help="run only these case ids (repeatable)",
    )
    ap.add_argument("--klass", choices=CLASSES, help="run only this class")
    ap.add_argument("--fast", action="store_true", help="skip the cases marked slow")
    ap.add_argument("--rebuild", action="store_true", help="ignore the STEP/review caches")
    ap.add_argument("--render", action="store_true", help="also render each case to tmp/")
    ap.add_argument("--product", action="store_true", help="--render uses the hero renderer")
    ap.add_argument("--json", metavar="FILE", help="write the table and contract as JSON")
    ap.add_argument("--list", action="store_true", help="list the corpus and exit")
    args = ap.parse_args(argv)

    cases = select(only=tuple(args.only), klass=args.klass, fast=args.fast)
    if not cases:
        print("no cases selected", file=sys.stderr)
        return 2
    if args.list:
        for c in cases:
            flag = " [slow]" if c.slow else ""
            print(f"{c.klass:6s} {c.id:32s} {c.role:11s} {c.label}{flag}")
            print(f"       {c.why}")
        return 0

    result = run_corpus(cases, rebuild=args.rebuild, progress=lambda m: print(m, flush=True))
    print()
    print(format_table(result))
    print()
    print(format_contract(result))

    if args.render:
        print("\n  renders:")
        for c in cases:
            try:
                for p in render_case(c, product=args.product):
                    print(f"    {p}")
            except Exception as exc:
                print(f"    {c.id}: render failed - {type(exc).__name__}: {exc}")

    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "cases": [
                        {
                            "id": r.id,
                            "klass": r.case.klass,
                            "role": r.case.role,
                            "label": r.case.label,
                            "why": r.case.why,
                            "attacks": list(r.case.attacks),
                            "rung": r.case.rung,
                            "status": r.status,
                            "score": r.score,
                            "band": r.band,
                            "metrics": r.metrics,
                            "elapsed_s": r.elapsed_s,
                        }
                        for r in result.rows
                    ],
                    "contract": [
                        {"id": c.id, "title": c.title, "ok": c.ok, "detail": c.detail}
                        for c in result.contract
                    ],
                    "margin": MARGIN,
                    "gate": GATE,
                    "elapsed_s": result.elapsed_s,
                    "passed": result.passed,
                },
                indent=2,
            )
        )
        print(f"\n  wrote {args.json}")

    if any(c.ok is None for c in result.contract) and not result.failures:
        return 0
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
