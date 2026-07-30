"""
The part's own reference frame, so a measurement does not depend on how the
part happens to be oriented in the file.

The failure this prevents
-------------------------
Every measurement in `lib/design_review.py` used to be taken against the world
axis-aligned bounding box: `Topology.bb = shape.BoundingBox()` fed bbox_size,
bbox_centre, bbox_surface, bbox_projected_area, align_tol, break_cap and
blend_cap; `_metric_symmetry` mirrored about the world XY/YZ/XZ planes; and
`_feature_centres` projected feature axes onto world directions. That box is a
property of the FILE, not of the part.

The consequence was measured on this repo's own artifacts before the port:
`parts/_template` scored 86.8 as modelled and 64.6 after a 37 degree rotation
about Z, with `symmetry` collapsing from 88 to 0 and `pattern_discipline` from
93 to 30. Nothing about the part changed. Only the ruler did.

A gate whose central claim is that the artifact is what is tested cannot ship a
ruler that reads differently depending on which way you hold it.

What this module measures
-------------------------
`reference_frame(shape)` returns three orthonormal axes and the extents of the
solid along them. The axes come from the part's own geometry, in this order of
preference:

1. **faces** - the area-weighted dominant directions of the solid's own planar
   face normals and cylindrical/conical axes. For a prismatic mechanical part
   this recovers exactly the axes the designer modelled on, which is why an
   axis-aligned part measures identically before and after this change: the
   frame comes out equal to the world axes and every calibrated score is
   preserved to the last decimal.
2. **obb** - OCCT's oriented bounding box, for a solid with too few flat or
   turned surfaces to vote (a sphere, a loft, an organic blend).
3. **world** - the world axes, only if OCCT itself fails. Recorded as such.

The basis that was used is carried on the result and written into the report,
because a measurement that cannot name its own reference frame is not evidence.

The OBB is taken of the shape MOVED TO ITS OWN BBOX CENTRE, which is not a
detail. OCCT's DiTO oriented-bounding-box builder samples the tessellation, and
the sampling drifts as the coordinate magnitudes grow, so the in-plane axis of a
turned hub read 0.0026 rad at the origin and 0.4719 rad (28.2 degrees) at
(500, -500, 500) - a pure translation moving a score. Centring first removes the
magnitude and the same axis reads within a degree out to 5000 mm.

Invariance
----------
The extents, the diagonal and the projected areas are invariant under rigid
motion. Axis SIGNS are chosen to line up with the world axes where that is
meaningful, purely so a finding on an axis-aligned part still says "+Z face"
rather than "axis 3". No score depends on a sign - every metric that uses an
axis uses abs() of a dot product or a symmetric distance - so the sign
convention is cosmetic and is allowed to follow the file.

Units: mm throughout, as everywhere in this repo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cadquery as cq
from OCP.Bnd import Bnd_OBB
from OCP.BRepBndLib import BRepBndLib
from OCP.gp import gp_Trsf

#: Two directions closer than this are the same design direction. A degree and
#: a half is far tighter than any modelling sloppiness and far looser than the
#: 1e-7 an exported STEP reproduces a right angle to.
CLUSTER_TOL_DEG = 1.5

#: A direction carrying less than this share of the total voting area is noise
#: - a chamfer land, a rib flank - and may not seed a candidate frame.
MIN_CLUSTER_SHARE = 0.01

#: How many of the heaviest directions may seed candidate frames. Every
#: perpendicular pair among them is tried, so this is quadratic; six is ample
#: for a mechanical part, whose surfaces almost always vote for three axes.
MAX_SEEDS = 6

#: Below this much of the surface explained (see `_explained`), the part's own
#: surfaces do not agree on a frame and the oriented bounding box is used.
MIN_EXPLAINED = 0.55


def _canonical(v: cq.Vector) -> cq.Vector:
    """
    Fold a direction onto one hemisphere so that ``n`` and ``-n`` agree.

    A face and the face opposite it are the same design direction, and a box
    would otherwise cast six votes for three axes with the pairs cancelling.
    """
    x, y, z = v.x, v.y, v.z
    for c in (z, y, x):
        if abs(c) > 1e-9:
            return cq.Vector(-x, -y, -z) if c < 0 else cq.Vector(x, y, z)
    return cq.Vector(x, y, z)


@dataclass(frozen=True)
class Frame:
    """
    An orthonormal right-handed frame fixed to the part, plus its extents.

    `axes` are ordered by extent, longest first, so the frame is canonical: two
    files holding the same solid in different orientations produce the same
    `size`, `diagonal` and `surface` whatever the modelling order was.
    """

    axes: tuple[cq.Vector, cq.Vector, cq.Vector]
    size: tuple[float, float, float]
    centre: cq.Vector
    basis: str
    #: Share of surface area this frame accounts for - see `_explained`.
    #: 0.0 when the frame did not come from faces.
    explained: float
    #: Why a weaker basis was used, or None when the face vote carried it.
    fallback_reason: str | None = None

    @property
    def diagonal(self) -> float:
        return math.sqrt(sum(d * d for d in self.size))

    @property
    def surface(self) -> float:
        """Surface area of the frame box, the denominator of feature density."""
        x, y, z = self.size
        return 2.0 * (x * y + y * z + z * x)

    def projected_area(self, normal: cq.Vector) -> float:
        """
        Exact area of the frame box projected along a world-space direction.

        This is the silhouette a face is judged against in the empty-area terms.
        The normal arrives in world space and is resolved into the frame here,
        so callers never have to know the frame exists.
        """
        c = self.to_frame_direction(normal)
        x, y, z = self.size
        return abs(c[0]) * y * z + abs(c[1]) * x * z + abs(c[2]) * x * y

    def to_frame_direction(self, v) -> tuple[float, float, float]:
        """A world direction resolved into frame components."""
        vec = v if isinstance(v, cq.Vector) else cq.Vector(*v)
        return tuple(a.dot(vec) for a in self.axes)  # type: ignore[return-value]

    def to_frame_point(self, p) -> tuple[float, float, float]:
        """A world point in frame coordinates, measured from the frame centre."""
        vec = p if isinstance(p, cq.Vector) else cq.Vector(*p)
        d = vec - self.centre
        return tuple(a.dot(d) for a in self.axes)  # type: ignore[return-value]

    def to_world_point(self, local) -> cq.Vector:
        """A frame-space point back in world coordinates."""
        return (
            self.centre
            + self.axes[0] * local[0]
            + self.axes[1] * local[1]
            + self.axes[2] * local[2]
        )

    def extents_of(self, shape: cq.Shape) -> tuple[float, float, float]:
        """
        Extents of another solid measured along THIS frame's axes.

        Used for the pieces of a mirror difference: a lump's aspect ratio decides
        whether it is charged as a sliver or excused as a compact interface, and
        taking that aspect from the world box made it a function of the file.
        """
        size, _centre = _extents(shape, self.axes)
        return size

    def is_world_aligned(self, tol_deg: float = CLUSTER_TOL_DEG) -> bool:
        """
        Whether every frame axis lies on a world axis.

        Findings name faces "+Z" or "-Y" when this holds and fall back to naming
        the frame axis when it does not, because "the +Z face" is a lie about a
        part modelled at 30 degrees.
        """
        limit = math.cos(math.radians(tol_deg))
        return all(max(abs(a.x), abs(a.y), abs(a.z)) >= limit for a in self.axes)


def _direction_votes(shape: cq.Shape) -> list[tuple[cq.Vector, float]]:
    """
    Every direction the solid's own surfaces vote for, with the area behind it.

    A planar face votes for its normal. A cylinder or cone votes for its axis,
    which is what gives a turned part - a shaft, a hub, a coupler - a real
    primary axis when it has no flat faces to speak of.
    """
    votes: list[list] = []
    for f in shape.Faces():
        kind = f.geomType()
        try:
            area = f.Area()
            if area <= 1e-9:
                continue
            if kind == "PLANE":
                direction = f.normalAt()
            elif kind in ("CYLINDER", "CONE"):
                from OCP.BRepAdaptor import BRepAdaptor_Surface

                surf = BRepAdaptor_Surface(f.wrapped)
                ax = surf.Cylinder().Axis() if kind == "CYLINDER" else surf.Cone().Axis()
                d = ax.Direction()
                direction = cq.Vector(d.X(), d.Y(), d.Z())
            else:
                continue
            direction = _canonical(cq.Vector(direction).normalized())
        except Exception:
            # A degenerate face votes for nothing. It never votes for a guess.
            continue
        votes.append([direction, area])

    # Heaviest first, so the biggest surface seeds its cluster instead of a
    # sliver an arbitrary traversal order happened to reach first.
    votes.sort(key=lambda v: -v[1])

    limit = math.cos(math.radians(CLUSTER_TOL_DEG))
    clusters: list[list] = []
    for direction, area in votes:
        for c in clusters:
            if abs(c[0].dot(direction)) >= limit:
                sign = 1.0 if c[0].dot(direction) >= 0 else -1.0
                total = c[1] + area
                c[0] = cq.Vector(
                    (c[0].x * c[1] + sign * direction.x * area) / total,
                    (c[0].y * c[1] + sign * direction.y * area) / total,
                    (c[0].z * c[1] + sign * direction.z * area) / total,
                ).normalized()
                c[1] = total
                break
        else:
            clusters.append([direction, area])
    clusters.sort(key=lambda c: -c[1])
    return [(c[0], c[1]) for c in clusters]


def _jacobi_eigenvectors(m: list[list[float]]) -> list[cq.Vector]:
    """
    Eigenvectors of a symmetric 3x3, by cyclic Jacobi rotation.

    Hand-rolled rather than pulled from numpy because numpy is only present here
    transitively, through CadQuery, and a measurement primitive should not depend
    on a package this project does not declare.
    """
    a = [row[:] for row in m]
    v = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for _ in range(50):
        off = abs(a[0][1]) + abs(a[0][2]) + abs(a[1][2])
        if off < 1e-14:
            break
        for p, q in ((0, 1), (0, 2), (1, 2)):
            if abs(a[p][q]) < 1e-18:
                continue
            theta = (a[q][q] - a[p][p]) / (2.0 * a[p][q])
            t = math.copysign(1.0, theta) / (abs(theta) + math.sqrt(theta * theta + 1.0))
            c = 1.0 / math.sqrt(t * t + 1.0)
            s = t * c
            for k in range(3):
                akp, akq = a[k][p], a[k][q]
                a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
            for k in range(3):
                apk, aqk = a[p][k], a[q][k]
                a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
            for k in range(3):
                vkp, vkq = v[k][p], v[k][q]
                v[k][p], v[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    return [cq.Vector(v[0][j], v[1][j], v[2][j]).normalized() for j in range(3)]


def _tensor_axes(clusters: list[tuple[cq.Vector, float]]) -> list[cq.Vector] | None:
    """
    The principal directions of the area-weighted orientation tensor
    ``sum(area * n (x) n)``.

    This is what recovers the true axes of a TAPERED part, and it is why the
    frame is not simply the heaviest surface direction. On the corpus's sculpted
    structural arm the two tapered flanks each carry more area than either end
    face, so picking the heaviest direction fixes the frame a few degrees off the
    part's real centreline - and the arm, which is exactly symmetric about that
    centreline, then measures asymmetric and loses its bolt pattern's mirror
    partners. The flanks are a mirror pair about the true axis, so their
    off-diagonal tensor contributions cancel and the tensor lands on the
    centreline that neither flank points along.
    """
    if not clusters:
        return None
    m = [[0.0] * 3 for _ in range(3)]
    for d, area in clusters:
        comps = (d.x, d.y, d.z)
        for i in range(3):
            for j in range(3):
                m[i][j] += area * comps[i] * comps[j]
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace <= 1e-9:
        return None
    return _jacobi_eigenvectors(m)


def _triad(d1: cq.Vector, d2: cq.Vector) -> tuple[cq.Vector, cq.Vector, cq.Vector] | None:
    """An orthonormal triad from two directions, or None if they are parallel."""
    z = d1.normalized()
    residual = d2 - z * z.dot(d2)
    if residual.Length < 1e-6:
        return None
    x = residual.normalized()
    return (x, z.cross(x), z)


def _explained(clusters: list[tuple[cq.Vector, float]], axes) -> float:
    """
    The share of surface area this frame accounts for.

    Each direction is credited with cos^2 of its angle to the nearest frame axis,
    so a surface exactly on an axis counts fully, one a few degrees off counts
    nearly fully, and one at 45 degrees counts half. Summed over area and
    normalised, it answers "how much of this part is organised along these three
    axes" - and maximising it over the candidates is what picks the frame.

    Not a tolerance test. A hard angular cutoff would make the choice of frame
    jump discontinuously as a taper angle crossed it; cos^2 is smooth, is the
    natural quadratic form of the orientation tensor, and needs no threshold.
    """
    total = 0.0
    score = 0.0
    for d, area in clusters:
        total += area
        best = max(abs(a.dot(d)) for a in axes)
        score += area * best * best
    return score / total if total > 1e-9 else 0.0


def _face_axes(
    shape: cq.Shape,
) -> tuple[tuple[cq.Vector, cq.Vector, cq.Vector], float, str] | None:
    """
    The orthonormal triad that best explains the part's own surfaces, and the
    basis name that describes how much of it the surfaces actually fixed.

    Candidates are the orientation tensor's principal directions plus every
    perpendicular pair among the heaviest surface directions. The winner is the
    one that accounts for the most surface area - a fit, not a greedy pick.

    A BODY OF REVOLUTION VOTES FOR ONE DIRECTION AND ONE ONLY - every planar
    face and every cylinder on a hub, a spool or a gland is normal to or coaxial
    with the same axis - and that used to disqualify the face vote entirely and
    hand the whole frame to OCCT's oriented bounding box. That was the worst of
    both: the axis the part states exactly was thrown away, and the in-plane
    pair, which the part does not state at all, was taken from a tessellation
    whose sampling moves with the coordinates. Measured on a 80 mm flanged hub,
    that cost 0.0053 points of face_composition for a pure 500 mm translation.

    So a single cluster now fixes the axis from the orientation tensor, which is
    a function of face normals and areas alone and is therefore exact under any
    rigid motion, and the frame says `axis` rather than `faces` - because the
    two in-plane directions are genuinely arbitrary and the report should not
    imply the part chose them.
    """
    clusters = _direction_votes(shape)
    if not clusters:
        return None
    total = sum(a for _, a in clusters)
    if total <= 1e-9:
        return None

    if len(clusters) < 2:
        # The one cluster IS the axis, exactly - it is the area-weighted mean of
        # face normals and cylinder axes and nothing else. The pair across it is
        # seeded from a world direction here purely so there is a triad to
        # return; `_fix_inplane` is what decides it, and it decides it from the
        # part.
        axis = clusters[0][0]
        seed = cq.Vector(0, 0, 1) if abs(axis.z) < 0.9 else cq.Vector(1, 0, 0)
        triad = _triad(axis, axis.cross(seed))
        if triad is None:  # pragma: no cover - seed is never parallel to axis
            return None
        return triad, _explained(clusters, triad), "axis"

    candidates: list[tuple[cq.Vector, cq.Vector, cq.Vector]] = []
    tensor = _tensor_axes(clusters)
    if tensor is not None:
        triad = _triad(tensor[0], tensor[1])
        if triad is not None:
            candidates.append(triad)

    perpendicular = math.cos(math.radians(90.0 - CLUSTER_TOL_DEG))
    seeds = [(d, a) for d, a in clusters if a >= MIN_CLUSTER_SHARE * total][:MAX_SEEDS]
    for i, (d1, _) in enumerate(seeds):
        for d2, _ in seeds[i + 1 :]:
            if abs(d1.dot(d2)) >= perpendicular:
                continue
            triad = _triad(d1, d2)
            if triad is not None:
                candidates.append(triad)

    if not candidates:
        return None
    scored = [(_explained(clusters, c), c) for c in candidates]
    # Ties are resolved by candidate order, which puts the tensor first: for a
    # cube or a square plate every candidate explains the part equally and they
    # differ only by a relabelling the metrics cannot see.
    best = max(range(len(scored)), key=lambda i: scored[i][0])
    return scored[best][1], scored[best][0], "faces"


def _obb_axes(shape: cq.Shape) -> tuple[cq.Vector, cq.Vector, cq.Vector] | None:
    """
    OCCT's oriented bounding box axes, or None if it could not build one.

    The shape is REBUILT at its own bbox centre first. OCCT's DiTO builder
    samples the tessellation and its sampling drifts with coordinate magnitude,
    so the axes it returns for a part sitting away from the origin are not the
    axes it returns for the same part at the origin. Measured here on a 60 mm
    turned hub with a six-hole bolt circle, whose in-plane axis is the only one
    the envelope does not fix:

        translation      raw    .moved()   .translate()
        (0,0,0)        0.00 deg  0.04 deg   0.05 deg
        (100,100,100) 83.01 deg 87.59 deg   0.06 deg
        (500,-500,500)45.03 deg 50.69 deg   0.11 deg
        (5000,...)    76.68 deg 80.75 deg   0.33 deg

    NOTE THE MIDDLE COLUMN. Centring with `Shape.moved` does NOT fix this and is
    not the fix: `moved` composes a TopLoc location onto geometry that is still
    a thousand millimetres from the origin, and the mesher still meshes it
    there. `Shape.translate` goes through BRepBuilderAPI_Transform with copy, so
    the geometry itself is rebuilt at the origin, and that is what collapses the
    drift by three orders of magnitude.
    """
    try:
        try:
            bb = shape.BoundingBox()
            centred = shape.translate(
                (
                    -(bb.xmin + bb.xmax) / 2.0,
                    -(bb.ymin + bb.ymax) / 2.0,
                    -(bb.zmin + bb.zmax) / 2.0,
                )
            )
        except Exception:
            centred = shape
        box = Bnd_OBB()
        BRepBndLib.AddOBB_s(centred.wrapped, box, True, True, True)
        if box.IsVoid():
            return None
        out = []
        for d in (box.XDirection(), box.YDirection(), box.ZDirection()):
            out.append(cq.Vector(d.X(), d.Y(), d.Z()).normalized())
        return (out[0], out[1], out[2])
    except Exception:
        return None


def _inplane_marks(shape: cq.Shape, axis: cq.Vector, centre: cq.Vector) -> list[cq.Vector]:
    """
    Every in-plane direction the part's own EXACT geometry marks out, around
    `axis`.

    A body of revolution states its axis to the last bit and says nothing at all
    about the two directions across it, so those had to come from OCCT's
    oriented bounding box - and DiTO reads a tessellation, which moves with the
    coordinates. Measured on a flanged hub: 0.10 degrees of in-plane wander for
    a pure 500 mm translation.

    But a hub is not featureless across its axis. Its bolt circle marks six
    directions, and a spanner flat or a cross-drilling marks one, and all of
    them are exact: a face normal is exact, and a bore's axis foot is exact to
    the same tolerance as the solid. These are those directions, unsigned (a
    mark and its opposite give the same in-plane basis), each with the area
    behind it so the biggest feature is considered first.

    Returned in world space, heaviest first, otherwise in the B-rep's own face
    order - which rigid motion preserves, and which is therefore the only stable
    way to choose between marks of exactly equal weight. Empty for a part that
    really is featureless across its axis - a plain tube - where there is
    nothing to be stable ABOUT.
    """
    marks: list[tuple[cq.Vector, float]] = []
    for f in shape.Faces():
        try:
            area = f.Area()
            if area <= 1e-9:
                continue
            kind = f.geomType()
            if kind == "PLANE":
                n = cq.Vector(f.normalAt())
                d = n - axis * axis.dot(n)
            elif kind in ("CYLINDER", "CONE"):
                from OCP.BRepAdaptor import BRepAdaptor_Surface

                surf = BRepAdaptor_Surface(f.wrapped)
                ax = surf.Cylinder().Axis() if kind == "CYLINDER" else surf.Cone().Axis()
                loc = ax.Location()
                offset = cq.Vector(loc.X(), loc.Y(), loc.Z()) - centre
                d = offset - axis * axis.dot(offset)
            else:
                continue
            if d.Length < 1e-6:
                continue
            marks.append((_canonical(d.normalized()), area))
        except Exception:
            continue
    marks.sort(key=lambda m: -m[1])
    return [d for d, _ in marks]


def _is_identity(axes: tuple[cq.Vector, cq.Vector, cq.Vector]) -> bool:
    """Whether these axes are the world axes, in order, to within round-off."""
    rows = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    return all(
        abs(a.x - r[0]) < 1e-12 and abs(a.y - r[1]) < 1e-12 and abs(a.z - r[2]) < 1e-12
        for a, r in zip(axes, rows)
    )


def _extents(
    shape: cq.Shape, axes: tuple[cq.Vector, cq.Vector, cq.Vector]
) -> tuple[tuple[float, float, float], cq.Vector]:
    """
    Extents and centre of the solid measured along `axes`.

    The shape is rotated into the frame and bounded there rather than having its
    vertices projected, because a cylinder's silhouette runs wider than any of
    its vertices and a vertex projection would under-report every round part.
    """
    x, y, z = axes
    if _is_identity(axes):
        # An axis-aligned part is bounded where it always was, to the last
        # decimal. Going through the transform anyway shifts the extents by a
        # few microns, and a change that is supposed to leave calibrated scores
        # untouched should leave them untouched exactly.
        bb = shape.BoundingBox()
    else:
        # World -> frame is the rotation whose ROWS are the frame axes. Built
        # with SetValues rather than a quaternion because gp_Quaternion's
        # three-argument form is (from, to, help-cross) and not a basis, which
        # silently leaves the shape unrotated and hands back the axis-aligned
        # box this module exists to replace.
        trsf = gp_Trsf()
        trsf.SetValues(x.x, x.y, x.z, 0.0, y.x, y.y, y.z, 0.0, z.x, z.y, z.z, 0.0)
        bb = shape.moved(cq.Location(trsf)).BoundingBox()
    centre_local = cq.Vector(
        (bb.xmin + bb.xmax) / 2.0, (bb.ymin + bb.ymax) / 2.0, (bb.zmin + bb.zmax) / 2.0
    )
    centre = axes[0] * centre_local.x + axes[1] * centre_local.y + axes[2] * centre_local.z
    return (bb.xlen, bb.ylen, bb.zlen), centre


def _order(
    axes: tuple[cq.Vector, cq.Vector, cq.Vector], size: tuple[float, float, float]
) -> tuple[tuple[cq.Vector, cq.Vector, cq.Vector], tuple[float, float, float]]:
    """
    Sort the axes by extent, longest first, and keep the frame right-handed.

    This is what makes the frame canonical rather than merely oriented: which
    dominant direction happened to carry the most area is an accident of the
    modelling, but "the long axis" is a property of the solid.

    THE COMPARISON IS SCALE-RELATIVE. A disc, a square plate and a cube have two
    or three extents that are equal by construction, and after a rotation they
    are equal only to about 1e-11 of the part - so an exact comparison let a
    round-off in the eleventh digit swap two axes and rotate the whole in-plane
    basis by 90 degrees. On a six-hole bolt circle that is a 30 degree rotation
    of the pattern relative to its own measuring basis, which is a different
    answer about the same part. Equal extents are treated as equal and the
    incoming order decides, which is the only tie-break that does not invent
    information the envelope does not carry.
    """
    grain = 1e-9 * max(max(size), 1.0)
    order = sorted(range(3), key=lambda i: (-round(size[i] / grain), i))
    a = [axes[i] for i in order]
    if a[0].cross(a[1]).dot(a[2]) < 0:
        a[2] = a[2] * -1.0
    return (a[0], a[1], a[2]), (size[order[0]], size[order[1]], size[order[2]])


def _orient_to_world(
    axes: tuple[cq.Vector, cq.Vector, cq.Vector],
) -> tuple[cq.Vector, cq.Vector, cq.Vector]:
    """
    Flip axis signs to point the world's way where that is unambiguous.

    Cosmetic only: it exists so that a finding on an axis-aligned part still
    reads "the +Z and +X faces" instead of "axis 1 and axis 3". Handedness is
    restored afterwards, and no metric reads a sign.
    """
    world = (cq.Vector(1, 0, 0), cq.Vector(0, 1, 0), cq.Vector(0, 0, 1))
    out = list(axes)
    for i, a in enumerate(out):
        best = max(world, key=lambda w: abs(w.dot(a)))
        if best.dot(a) < 0:
            out[i] = a * -1.0
    if out[0].cross(out[1]).dot(out[2]) < 0:
        out[2] = out[2] * -1.0
    return (out[0], out[1], out[2])


def _fix_inplane(
    shape: cq.Shape, axes: tuple[cq.Vector, cq.Vector, cq.Vector]
) -> tuple[tuple[cq.Vector, cq.Vector, cq.Vector], bool]:
    """
    Replace a revolution frame's arbitrary in-plane pair with the part's own.

    `axes` arrives from the orientation tensor: its third vector is the part's
    real axis and the other two are whatever Jacobi returned for a degenerate
    eigenvalue, which is exact under any rigid motion but does not TURN with the
    part - a hub rotated about its own axis kept the old in-plane basis and its
    bolt circle read as scatter, worth 52.8 points of feature_composition.

    So the in-plane direction is taken from the part's own biggest off-axis
    feature instead - a spanner flat, a cross-drilling, the first hole of a bolt
    circle. That is exact under translation, turns with the part under rotation,
    and needs no tessellation.

    THE TIE-BREAK IS THE B-REP'S OWN FACE ORDER, and it has to be something of
    that kind. A six-hole bolt circle marks six directions of exactly equal
    area, and no function of the direction SET can prefer one of six equally
    spaced directions - that is what six-fold symmetry means. Rigid motion
    preserves face order, so taking the first is stable; and the alternatives it
    is choosing between are one symmetry of the part apart, so choosing
    differently would describe the same solid anyway.

    An oriented bounding box was tried as the seed for this and is why the rule
    is not "snap the OBB to the nearest mark": which of the OBB's two in-plane
    axes came back first flipped under a pure translation, and a 90 degree flip
    snaps to a different mark - 60 degrees away on the hub, which is not a
    symmetry of the frame box even though it is one of the part.

    Returns the frame and whether the part had a mark to use.
    """
    axis = axes[2]
    _size, centre = _extents(shape, axes)
    marks = _inplane_marks(shape, axis, centre)
    if not marks:
        return axes, False
    triad = _triad(axis, marks[0])
    if triad is None:  # pragma: no cover - marks are perpendicular to axis
        return axes, False
    return triad, True


def reference_frame(shape) -> Frame:
    """
    The part's own frame, measured from the part.

    Never raises. When the geometry cannot supply a frame this falls back and
    says so on the result, in the same way `Topology.is_exterior` returns None
    rather than a plausible number.
    """
    if hasattr(shape, "val"):  # a Workplane
        shape = shape.val()
    basis = "faces"
    reason: str | None = None
    share = 0.0

    found = _face_axes(shape)
    if found is not None and found[1] >= MIN_EXPLAINED:
        axes, share, basis = found
        if basis == "axis":
            axes, marked = _fix_inplane(shape, axes)
            reason = (
                "one dominant surface direction and no second: the axis is the part's "
                "own, and the two directions across it are "
                + (
                    "set by the nearest feature the part marks out across it"
                    if marked
                    else "not fixed by any surface or feature the part has"
                )
            )
    else:
        if found is None:
            reason = "no dominant surface direction at all"
        else:
            share = found[1]
            reason = (
                f"the best frame explains only {share * 100:.0f}% of the surface, "
                f"below the {MIN_EXPLAINED * 100:.0f}% needed to fix one from faces"
            )
        obb = _obb_axes(shape)
        if obb is not None:
            axes, basis, share = obb, "obb", 0.0
        else:
            axes = (cq.Vector(1, 0, 0), cq.Vector(0, 1, 0), cq.Vector(0, 0, 1))
            basis = "world"
            reason = (reason or "") + "; oriented bounding box also unavailable"

    size, centre = _extents(shape, axes)
    axes, size = _order(axes, size)
    axes = _orient_to_world(axes)
    return Frame(
        axes=axes,
        size=size,
        centre=centre,
        basis=basis,
        explained=round(share, 4),
        fallback_reason=reason,
    )


def frame_record(frame: Frame) -> dict:
    """The frame as it appears in a report - the basis a score was measured in."""
    record = {
        "basis": frame.basis,
        "size_mm": [round(v, 3) for v in frame.size],
        "diagonal_mm": round(frame.diagonal, 3),
        "axes": [[round(c, 6) for c in (a.x, a.y, a.z)] for a in frame.axes],
        "world_aligned": frame.is_world_aligned(),
    }
    if frame.basis in ("faces", "axis"):
        record["explained"] = frame.explained
    if frame.fallback_reason:
        record["fallback_reason"] = frame.fallback_reason
    return record
