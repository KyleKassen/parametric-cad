"""
The industrial-design language as code - refined geometry made cheap to build.

Why this module exists
----------------------
Models in this repo were mechanically sound but visually unrefined: knife-edged
extrusions, blank slab faces, scattered fasteners, abrupt prism-to-cylinder butt
joints. Not because anyone preferred that, but because the refined choice was
expensive. A recessed panel with a chevron rib field is ~60 lines of workplane
math done by hand; a plain box is one. Cost decided the outcome.

So the fix is economic, not exhortative: make the refined choice the CHEAP
choice. Every element of the design language in DESIGN_LANGUAGE.md is a call
here, parametric and kernel-safe. `recessed_panel(body, ">Z")` is now shorter
than the box it replaces.

Three ideas run through the module
----------------------------------
1. ONE radius vocabulary. Plan-corner radii come from a discrete ladder
   (3/5/8/12/16/24 mm) via `Style.plan_radius(size)`, which picks the rung that
   suits a part of that size. Two parts of similar size therefore get the same
   radius, and a repo of parts reads as one product family instead of a pile of
   arbitrary numbers. The same applies to edge breaks, fastener metrics and
   panel proportions. Override a rung deliberately; never invent one casually.

2. GUARDS make styling structurally safe. A recess is only styling until it
   eats the wall behind it. Every material-removing builder here measures the
   wall it is cutting into - by shooting a ray through the real B-rep, not by
   trusting a parameter - and RAISES if the remainder would fall below the
   style minimum. An agent cannot accidentally style a part into failure; it
   gets a WallGuardError naming the numbers instead. That guard is what makes
   it safe to apply this vocabulary aggressively.

3. Builders return MEASUREMENTS, not just solids. `louver_bank` reports free
   area in mm^2 measured off the cut geometry, `fin_bank` reports added wetted
   area, `oring_groove` reports squeeze and fill percentage, `bolt_pattern`
   reports the pitch it solved for and whether it landed in band. Refinement
   claims are then checkable by lib/design_review.py rather than asserted.

ORDER OF OPERATIONS (the rule that keeps the kernel alive)
----------------------------------------------------------
CadQuery/OCCT fails almost exclusively when a fillet or chamfer is asked for on
an edge that a previous boolean created. The safe order, which `Build` below
enforces mechanically:

  1. BASE     Build each primitive as a LONE simple solid with its plan radii
              already baked in (rounded_box, base_flange, tapped_boss ...).
              Radii come from the 2D profile, so no 3D fillet ever runs on a
              prism. Edge breaks on a lone primitive are safe HERE and only
              here, because its edges are still the ones the modeller made.
  2. BOOLEAN  Union/cut the primitives together. Every edge created from this
              point on is a boolean edge: fragile to select, fragile to fillet.
  3. POCKET   Cut recesses and lightening pockets. Rounded pocket corners come
              from the cutting prism's own 2D profile - again never a late
              fillet. Wall guards run here.
  4. RIB      Union rib/fin solids back into the pockets, clipped by the pocket
              volume. Ribs go in AFTER the pocket exists so they can be clipped
              to its rounded boundary.
  5. HOLE     Counterbores, taps, apertures. Last of the material removal, so
              a boolean failure cannot be blamed on a hole that is not there
              yet, and so counterbores land on flat lands that already exist.
  6. BREAK    Only now, late edge breaks - and only on edges you can name
              precisely and that a boolean did not create. If a chamfer is
              wanted on a boolean edge, the answer is almost always to build it
              into the profile back at step 1 instead.

Going backwards (a pocket after a hole, a fillet after a union) is the failure
mode. `Build` raises BuildOrderError rather than letting it reach the kernel.

Units: mm, degrees. Angles named *_deg. Areas mm^2, volumes mm^3.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field, replace
from functools import reduce
from typing import Callable, Iterable, Sequence

import cadquery as cq

__all__ = [
    "FeatureError",
    "WallGuardError",
    "BuildOrderError",
    "WallSpec",
    "Fastener",
    "Style",
    "STYLE",
    "FASTENERS",
    "WALLS",
    "CORD_TABLE",
    "EMBED",
    "Pocket",
    "RibField",
    "FinBank",
    "LouverBank",
    "BoltPattern",
    "ConnectorLand",
    "Plate",
    "ORingGroove",
    "rounded_box",
    "rounded_prism",
    "recessed_panel",
    "lightening_pocket",
    "rib_field",
    "fin_bank",
    "louver_bank",
    "bolt_pattern",
    "fastener_holes",
    "counterbore_at",
    "tapped_hole_grid",
    "tapped_boss",
    "standoff_boss",
    "connector_land",
    "base_flange",
    "step_shoulder",
    "blend_transition",
    "oring_groove",
    "drip_edge",
    "emblem",
    "text_mark",
    "face_plane",
    "wall_at",
    "Build",
]


# --------------------------------------------------------------------------- #
# errors
# --------------------------------------------------------------------------- #


class FeatureError(ValueError):
    """A feature cannot be built as asked. The message states the numbers."""


class WallGuardError(FeatureError):
    """Styling would take the remaining wall below the structural minimum."""


class BuildOrderError(FeatureError):
    """A Build step was requested out of the kernel-safe phase order."""


# --------------------------------------------------------------------------- #
# the proportion ladders
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class WallSpec:
    """Wall-thickness guidance for one manufacturing process."""

    process: str
    minimum: float  # absolute floor - below this the process cannot hold form
    nominal: float  # what to design to when nothing else drives it
    per_span: float  # add this fraction of the unsupported span
    note: str = ""

    def for_span(self, span: float = 0.0) -> float:
        """Recommended wall for an unsupported span (mm), rounded to 0.1."""
        return round(max(self.nominal, span * self.per_span), 1)


WALLS: dict[str, WallSpec] = {
    "machined-aluminium": WallSpec(
        "machined-aluminium",
        1.5,
        2.5,
        0.020,
        "3-axis milled 6061/7075; 1.5 is cutter-deflection limited",
    ),
    "cast-aluminium": WallSpec(
        "cast-aluminium",
        3.0,
        4.0,
        0.030,
        "A356 sand/gravity cast; needs draft and generous fillets",
    ),
    "sheet-metal": WallSpec(
        "sheet-metal",
        1.0,
        1.5,
        0.008,
        "formed sheet; bend radius >= thickness",
    ),
    "printed-fdm": WallSpec(
        "printed-fdm",
        1.2,
        2.4,
        0.020,
        "0.4 nozzle, 6 perimeters at 2.4",
    ),
    "printed-sls": WallSpec(
        "printed-sls",
        0.8,
        2.0,
        0.015,
        "PA12; thin walls warp on long spans",
    ),
}


@dataclass(frozen=True)
class Fastener:
    """
    Metric socket-head cap screw hardware, ISO 4762 heads, coarse-pitch taps.

    Every number an enclosure needs for one screw size, so nobody re-derives a
    counterbore depth from a table again. `min_edge` is hole-centre to part
    edge (cbore radius + a wall); `pitch_band` is the spacing range over which
    a run of these screws reads as deliberate rhythm rather than as either
    loneliness or a zipper.
    """

    name: str
    thread: float
    clearance: float  # medium-fit clearance drill
    head_dia: float  # socket head OD
    head_height: float
    cbore_dia: float  # counterbore diameter (head + working clearance)
    cbore_depth: float  # head fully sunk + 0.4 below flush
    tap_drill: float  # coarse-pitch tap drill
    boss_dia: float  # recommended boss OD around a tapped hole
    min_edge: float  # minimum hole-centre to edge distance
    pitch_band: tuple[float, float]

    @property
    def min_tap_depth(self) -> float:
        """Minimum thread engagement in aluminium: 2x nominal diameter."""
        return 2.0 * self.thread


FASTENERS: dict[str, Fastener] = {
    "M3": Fastener("M3", 3.0, 3.4, 5.5, 3.0, 6.5, 3.4, 2.5, 8.0, 5.0, (18.0, 32.0)),
    "M4": Fastener("M4", 4.0, 4.5, 7.0, 4.0, 8.0, 4.4, 3.3, 10.0, 6.5, (24.0, 45.0)),
    "M5": Fastener("M5", 5.0, 5.5, 8.5, 5.0, 10.0, 5.4, 4.2, 12.0, 8.0, (30.0, 55.0)),
    "M6": Fastener("M6", 6.0, 6.6, 10.0, 6.0, 11.0, 6.4, 5.0, 14.0, 9.5, (36.0, 65.0)),
    "M8": Fastener("M8", 8.0, 9.0, 13.0, 8.0, 15.0, 8.4, 6.8, 18.0, 12.5, (48.0, 90.0)),
}


# AS568-style cord diameter -> static face-seal groove (width, depth), mm.
# Depth is chosen for 24-28% squeeze and the width for 75-85% groove fill,
# which is the band a static face seal wants: enough squeeze to seal, enough
# free volume for the cord to swell into without extruding.
CORD_TABLE: dict[float, tuple[float, float]] = {
    1.02: (1.40, 0.73),
    1.27: (1.75, 0.91),
    1.78: (2.40, 1.30),
    2.62: (3.55, 1.93),
    3.53: (4.70, 2.62),
    5.33: (7.10, 4.00),
    6.99: (9.30, 5.28),
}


@dataclass(frozen=True)
class Style:
    """
    One coherent proportion system, scaled by part size - not a bag of numbers.

    The ladders are deliberately short. A discrete set of allowed radii is what
    makes a family of parts look designed: `plan_radius(140)` and
    `plan_radius(155)` return the same rung, so two enclosures that differ by
    10% do not differ by 10% in corner radius. `*_fraction` is the target as a
    proportion of the governing dimension; the ladder then quantises it.

    Copy-and-tweak with `replace(STYLE, rib_thickness=2.5)` (dataclasses.replace)
    or `STYLE.tuned(rib_thickness=2.5)` rather than editing STYLE in place -
    it is frozen and shared.
    """

    name: str = "ataero-industrial"

    # plan-corner radii
    radius_ladder: tuple[float, ...] = (3.0, 5.0, 8.0, 12.0, 16.0, 24.0)
    radius_fraction: float = 0.12

    # rim / lip edge breaks
    break_ladder: tuple[float, ...] = (0.4, 0.6, 1.0, 1.5, 2.5, 4.0)
    break_fraction: float = 0.015

    # structural floor used by every material-removal guard
    min_wall: float = 1.6

    # recessed panels
    recess_depth: float = 1.8
    recess_depth_fraction: float = 0.45  # of the wall being recessed
    frame_width: float = 8.0
    frame_fraction: float = 0.07  # of the governing face dimension

    # ribs
    rib_thickness: float = 2.0
    rib_draft_deg: float = 2.0
    rib_relief: float = 0.4  # rib crest sits this far below the outer face
    rib_pitch: float = 14.0

    # fins
    fin_thickness: float = 2.0
    fin_pitch: float = 6.0
    fin_draft_deg: float = 1.5

    # louvers
    louver_angle_deg: float = 35.0
    louver_pitch: float = 7.0

    # identity marks
    emblem_relief: float = 0.6
    emblem_relief_max: float = 1.0

    # compare=False keeps Style hashable despite the dict fields, so it can be
    # a cached-function argument without a surprise TypeError
    walls: dict[str, WallSpec] = field(default_factory=lambda: dict(WALLS), compare=False)
    fasteners: dict[str, Fastener] = field(default_factory=lambda: dict(FASTENERS), compare=False)

    # ---- selectors ------------------------------------------------------- #

    def plan_radius(
        self, size: float, other: float | None = None, *, cap_fraction: float = 0.45
    ) -> float:
        """
        The ladder rung for a part whose governing plan dimension is `size`.

        Pass both plan dimensions and the smaller governs, which is what stops
        a long thin part from getting a radius that eats its width. The result
        is capped at `cap_fraction` of the governing dimension so the rounded
        rectangle always stays buildable (a radius of exactly half the width
        degenerates to a slot end; beyond that the kernel refuses outright).
        """
        gov = size if other is None else min(size, other)
        if gov <= 0:
            raise FeatureError(f"plan_radius needs a positive size, got {gov}")
        target = gov * self.radius_fraction
        rung = min(self.radius_ladder, key=lambda r: (abs(r - target), r))
        cap = gov * cap_fraction
        if rung > cap:
            lower = [r for r in self.radius_ladder if r <= cap]
            rung = lower[-1] if lower else round(cap, 2)
        return rung

    def edge_break(self, size: float, wall: float | None = None) -> float:
        """
        The chamfer rung for a rim on a part of this size, capped by the wall.

        A break bigger than ~40% of the wall it sits on stops being a break and
        starts being a knife edge again from the other side, so `wall` clamps.
        """
        if size <= 0:
            raise FeatureError(f"edge_break needs a positive size, got {size}")
        target = size * self.break_fraction
        rung = min(self.break_ladder, key=lambda b: (abs(b - target), b))
        if wall is not None:
            cap = wall * 0.4
            if rung > cap:
                lower = [b for b in self.break_ladder if b <= cap]
                rung = lower[-1] if lower else round(cap, 2)
        return rung

    def wall(self, process: str = "machined-aluminium", span: float = 0.0) -> float:
        """Recommended wall thickness for a process over an unsupported span."""
        return self.wall_spec(process).for_span(span)

    def wall_spec(self, process: str) -> WallSpec:
        try:
            return self.walls[process]
        except KeyError:
            raise FeatureError(
                f"unknown process {process!r}; known: {sorted(self.walls)}"
            ) from None

    def fastener(self, name: str | Fastener) -> Fastener:
        """Look up fastener metrics by name ('M4'), or pass one straight back."""
        if isinstance(name, Fastener):
            return name
        try:
            return self.fasteners[name.upper()]
        except (KeyError, AttributeError):
            raise FeatureError(
                f"unknown fastener {name!r}; known: {sorted(self.fasteners)}"
            ) from None

    def pitch(self, name: str | Fastener) -> float:
        """Mid-band fastener pitch - the default rhythm for that screw size."""
        f = self.fastener(name)
        return round(sum(f.pitch_band) / 2, 1)

    def edge_inset(self, name: str | Fastener) -> float:
        """
        Recommended hole-centre inset from a part edge, to the nearest 0.5.

        Above the strength minimum: a counterbore wants visible material around
        it, and a constant inset across a part is what makes a bolt pattern
        read as a frame rather than as holes that happened to fit.
        """
        f = self.fastener(name)
        return round(max(f.min_edge, f.cbore_dia * 1.1) * 2) / 2

    def recess(self, wall: float) -> float:
        """Panel recess depth for a given wall - proportional, then clamped."""
        return round(min(self.recess_depth, wall * self.recess_depth_fraction), 2)

    def frame(self, size: float, other: float | None = None) -> float:
        """Proud perimeter frame width for a face of this size."""
        gov = size if other is None else min(size, other)
        return round(max(self.frame_width, gov * self.frame_fraction), 1)

    def tuned(self, **changes) -> Style:
        """A copy with fields overridden - Style is frozen and shared."""
        return replace(self, **changes)


STYLE = Style()


# --------------------------------------------------------------------------- #
# result records
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Pocket:
    """
    A cut recess plus everything needed to decorate it.

    `void` is the removed volume - hand it to `rib_field` and ribs get clipped
    to the pocket's rounded boundary for free. `plane` sits ON THE POCKET FLOOR
    with +Z pointing out of the part, so anything built on it grows toward the
    opening.
    """

    solid: cq.Workplane
    void: cq.Shape
    plane: cq.Plane
    length: float
    width: float
    depth: float
    radius: float
    wall_before: float
    wall_after: float


@dataclass(frozen=True)
class RibField:
    """Rib solids already clipped to their pocket, ready to union back in."""

    solid: cq.Workplane
    pattern: str
    count: int
    thickness: float
    height: float
    volume_mm3: float


@dataclass(frozen=True)
class FinBank:
    """
    A constant-pitch fin bank and the heat-transfer area it actually bought.

    `added_area_mm2` is the NET gain in wetted area: the fins' own surface less
    their root footprints and less the base area they cover. That is the number
    a thermal calculation wants; `solid.Area()` on its own overstates it.
    """

    solid: cq.Workplane
    count: int
    pitch: float
    thickness: float
    height: float
    span: float
    added_area_mm2: float
    root_area_mm2: float


@dataclass(frozen=True)
class LouverBank:
    """
    A louver bank: what to cut, what to add, and the ventilation it provides.

    `free_area_mm2` is measured off the cut solid in the plane of the wall (the
    standard louver definition). `throat_area_mm2` is the smaller perpendicular
    section through the tilted slots - the number that actually limits flow.
    """

    cut: cq.Shape
    add: cq.Shape | None
    free_area_mm2: float
    throat_area_mm2: float
    count: int
    pitch: float
    gap: float
    blade_angle_deg: float


@dataclass(frozen=True)
class BoltPattern:
    """
    Solved fastener positions plus the rhythm they landed on.

    `points` are plane-local (u, v) so they can be reused - for bosses on the
    inside of the same wall, for a mating part, for a spec.json fit block.
    `in_band` reports whether the achieved pitch sits inside the fastener's
    recommended spacing range; a False here is the difference between rhythm
    and scatter, and lib/design_review.py can see it.
    """

    points: tuple[tuple[float, float], ...]
    points3d: tuple[tuple[float, float, float], ...]
    plane: cq.Plane
    kind: str
    count: int
    pitch: float
    pitch_v: float | None
    fastener: Fastener
    in_band: bool
    solid: cq.Workplane | None = None


@dataclass(frozen=True)
class ConnectorLand:
    """A flat land for a connector, its screw pattern and its aperture area."""

    solid: cq.Workplane
    plane: cq.Plane
    screw_points: tuple[tuple[float, float], ...]
    length: float
    width: float
    aperture_area_mm2: float


@dataclass(frozen=True)
class Plate:
    """A flat plate (flange, interface plate) and the hole pattern on it."""

    solid: cq.Workplane
    plane: cq.Plane
    points: tuple[tuple[float, float], ...]
    length: float
    width: float
    thickness: float


@dataclass(frozen=True)
class ORingGroove:
    """
    A seal groove and the proof that it seals.

    `squeeze_pct` is cord compression (want 20-30% for a static face seal) and
    `fill_pct` is how much of the groove the cord occupies at rest (want
    75-85%; above ~90% the cord has nowhere to go when it swells or heats and
    the joint jacks itself open).
    """

    cut: cq.Shape
    plane: cq.Plane
    cord_dia: float
    groove_width: float
    groove_depth: float
    path_length: float
    squeeze_pct: float
    fill_pct: float


# --------------------------------------------------------------------------- #
# private helpers
# --------------------------------------------------------------------------- #


def _shape(obj) -> cq.Shape:
    """
    The complete solid geometry of a part, correctly downcast.

    Two traps this exists to avoid, both of which lose geometry SILENTLY:

    * `Workplane.val()` returns only the FIRST item on the stack. After a
      union that leaves two objects there, half the part disappears from any
      boolean that used .val().
    * an OCCT boolean run against a Solid handle that has not been downcast
      can return a Compound holding zero solids - and that shape still answers
      True to isValid(). A part can therefore evaporate and still pass a
      validity check. Taking .Solids() first and re-compounding avoids it.

    Every boolean in this module goes through here for that reason.
    """
    if isinstance(obj, cq.Shape):
        shapes = [obj]
    elif hasattr(obj, "vals"):
        shapes = [v for v in obj.vals() if isinstance(v, cq.Shape)]
    elif hasattr(obj, "val"):
        shapes = [obj.val()]
    else:
        raise FeatureError(f"expected a Workplane or Shape, got {type(obj).__name__}")
    if not shapes:
        raise FeatureError("no geometry on this Workplane")
    solids = [s for sh in shapes for s in sh.Solids()]
    if not solids:
        return shapes[0] if len(shapes) == 1 else cq.Compound.makeCompound(shapes)
    if len(solids) == 1:
        return solids[0]
    return cq.Compound.makeCompound(solids)


def _wp(obj) -> cq.Workplane:
    """Accept a Workplane or a Shape and give back a Workplane."""
    if hasattr(obj, "val"):
        return obj
    return cq.Workplane("XY").newObject([obj])


# How far additive features sink below the face they sit on. A feature whose
# base is exactly COPLANAR with the parent surface is only tangent to it, and
# OCCT may fuse the pair into two disjoint solids that still report isValid().
# The part then looks right, exports fine, and falls apart in the importer. A
# fifth of a millimetre of genuine overlap removes the whole failure class.
EMBED = 0.2


def _checked(result: cq.Shape, op: str) -> cq.Shape:
    """Refuse to hand back a boolean result that lost all of its solids."""
    if not result.Solids():
        raise FeatureError(
            f"{op} produced no solid geometry - the operands probably do not "
            "overlap the way you expect, or the boolean failed. Check placement "
            "before assuming the kernel is at fault."
        )
    return result


def _cut(base, tool: cq.Shape, op: str = "cut") -> cq.Workplane:
    return _wp(_checked(_shape(base).cut(tool), op))


def _add(base, tool: cq.Shape, op: str = "union", *, welded: bool = False) -> cq.Workplane:
    """
    Fuse `tool` onto `base`. `welded=True` asserts the two must end up as ONE
    solid - use it whenever the tool is meant to sit on the parent's surface,
    so a tangency that failed to weld is reported instead of exported.
    """
    before = len(_shape(base).Solids())
    out = _checked(_shape(base).fuse(tool), op)
    after = len(out.Solids())
    if welded and after > before:
        raise FeatureError(
            f"{op} left {after} disjoint solids where {before} were expected - "
            "the added feature is only touching the parent, not overlapping it. "
            f"Sink it into the face by ~{EMBED} mm."
        )
    return _wp(out)


def _fuse(shapes: Sequence[cq.Shape]) -> cq.Shape:
    if not shapes:
        raise FeatureError("nothing to fuse")
    return reduce(lambda a, b: a.fuse(b), shapes)


def _as_plane(spec: cq.Plane | str) -> cq.Plane:
    return cq.Plane.named(spec) if isinstance(spec, str) else spec


def _place(shape: cq.Shape, plane: cq.Plane) -> cq.Shape:
    """
    Map a shape built in local XYZ onto a plane's frame.

    Local +X -> plane.xDir, local +Y -> plane.yDir, local +Z -> plane.zDir
    (the outward normal). On a side face plane.yDir is world "up", which is why
    every builder here can be written once in a flat local frame and still come
    out the right way up on a vertical wall.
    """
    return shape.moved(cq.Location(plane))


_AXES: dict[str, cq.Vector] = {
    "X": cq.Vector(1, 0, 0),
    "Y": cq.Vector(0, 1, 0),
    "Z": cq.Vector(0, 0, 1),
}


def _widest_face(solid, spec: str) -> cq.Face:
    """
    The largest planar face pointing a given way, wherever it sits.

    CadQuery's ">Z" means HIGHEST, not "the big flat top". Add one boss and
    ">Z" silently becomes a 10 mm boss crown, and every feature placed on it
    lands in the wrong place - at the right height, so it looks deliberate.
    "+Z" asks the question people actually mean.
    """
    axis = _AXES[spec[1].upper()] * (1.0 if spec[0] == "+" else -1.0)
    best: cq.Face | None = None
    best_area = 0.0
    for f in _wp(solid).faces().vals():
        if f.geomType() != "PLANE":
            continue
        if f.normalAt().dot(axis) < 0.999:
            continue
        area = f.Area()
        if area > best_area:
            best, best_area = f, area
    if best is None:
        raise FeatureError(f"no planar face points along {spec!r}")
    return best


def _resolve_face(solid, face: cq.Plane | str | cq.Face):
    """A selector/Face/Plane -> the concrete face (or Plane) to work from."""
    if isinstance(face, (cq.Plane, cq.Face)):
        return face
    if not isinstance(face, str):
        raise FeatureError(f"face must be a selector, cq.Face or cq.Plane, got {face!r}")
    if len(face) == 2 and face[0] in "+-" and face[1].upper() in _AXES:
        return _widest_face(solid, face)
    faces = _wp(solid).faces(face).vals()
    if not faces:
        raise FeatureError(f"no face matched selector {face!r}")
    return max(faces, key=lambda f: f.Area())


def face_plane(solid, face: cq.Plane | str | cq.Face = ">Z") -> cq.Plane:
    """
    The working plane of a named face: origin at its bounding-box centre,
    +Z along its outward normal, +Y "up" wherever that is meaningful.

    Because every builder here works in that frame, a feature written once
    comes out right way up on a lid and on a vertical wall alike.

    `face` may be:
      ">Z", "<X", ...  a CadQuery selector - the EXTREME face in that direction
                       (ties broken by area). Note that ">Z" means highest, so
                       once bosses exist it will find a boss crown.
      "+Z", "-Y", ...  the WIDEST planar face pointing that way, wherever it
                       sits. Usually what you meant, and stable as the part
                       grows features.
      a cq.Face        used directly
      a cq.Plane       returned unchanged
    """
    if isinstance(face, cq.Plane):
        return face
    target = _resolve_face(solid, face)
    return _wp(solid).newObject([target]).workplane(centerOption="CenterOfBoundBox").plane


def _face_extents(solid, plane: cq.Plane, face: cq.Plane | str | cq.Face) -> tuple[float, float]:
    """(u, v) extents of a face measured in its own plane."""
    target = _resolve_face(solid, face)
    if isinstance(target, cq.Plane):
        bb = plane.toLocalCoords(_shape(solid)).BoundingBox()
        return bb.xlen, bb.ylen
    bb = plane.toLocalCoords(target).BoundingBox()
    return bb.xlen, bb.ylen


def _rounded_rect(length: float, width: float, radius: float) -> cq.Sketch:
    """
    A rounded rectangle as a 2D sketch - the radius is IN THE PROFILE.

    This is the whole plan-radius strategy in one function: corners exist
    before the solid does, so no 3D fillet ever runs on a prism and the main
    kernel failure mode never gets a chance.
    """
    if length <= 0 or width <= 0:
        raise FeatureError(f"rounded rect needs positive sides, got {length} x {width}")
    sk = cq.Sketch().rect(length, width)
    limit = min(length, width) / 2
    r = min(radius, limit - 1e-6) if radius > 0 else 0.0
    if r > 1e-6:
        sk = sk.vertices().fillet(r)
    return sk


def _prism(
    plane: cq.Plane,
    length: float,
    width: float,
    radius: float,
    depth: float,
    center: tuple[float, float] = (0.0, 0.0),
) -> cq.Shape:
    """
    A rounded-corner prism on `plane`. Negative depth grows into the part.
    """
    if abs(depth) < 1e-9:
        raise FeatureError("prism depth must be non-zero")
    sk = _rounded_rect(length, width, radius)
    solid = cq.Workplane("XY").placeSketch(sk).extrude(abs(depth)).val()
    dz = 0.0 if depth > 0 else depth
    return _place(solid.translate((center[0], center[1], dz)), plane)


def _offset_plane(plane: cq.Plane, du: float = 0.0, dv: float = 0.0, dn: float = 0.0) -> cq.Plane:
    """A parallel/translated copy of a plane, offset in its own axes."""
    origin = plane.origin + plane.xDir * du + plane.yDir * dv + plane.zDir * dn
    return cq.Plane(origin=origin, xDir=plane.xDir, normal=plane.zDir)


def _ray_hits(shape: cq.Shape, origin: cq.Vector, direction: cq.Vector) -> list[float]:
    """Sorted, de-duplicated ray/solid intersection parameters."""
    from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt

    inter = BRepIntCurveSurface_Inter()
    line = gp_Lin(
        gp_Pnt(origin.x, origin.y, origin.z),
        gp_Dir(direction.x, direction.y, direction.z),
    )
    inter.Init(shape.wrapped, line, 1e-6)
    hits: list[float] = []
    while inter.More():
        hits.append(inter.W())
        inter.Next()
    hits.sort()
    out: list[float] = []
    for h in hits:
        if not out or abs(h - out[-1]) > 1e-4:
            out.append(h)
    return out


def wall_at(solid, plane: cq.Plane, uv: tuple[float, float] = (0.0, 0.0)) -> float | None:
    """
    Measured material thickness straight down from a point on a face, in mm.

    Shoots a ray through the real B-rep and returns the distance between the
    first two surfaces it crosses - i.e. the actual wall under that point,
    hollow or solid, however the part got built. Returns None when the ray
    finds fewer than two crossings (an open or grazing spot), which callers
    must treat as "unknown", never as "thick enough".

    This is what lets the pocket guards be honest: they check the wall the part
    really has, not the wall a parameter claimed it had.
    """
    shape = _shape(solid)
    bb = shape.BoundingBox()
    standoff = bb.DiagonalLength + 10.0
    start = plane.toWorldCoords((uv[0], uv[1])) + plane.zDir * standoff
    hits = _ray_hits(shape, start, plane.zDir * -1.0)
    if len(hits) < 2:
        return None
    return hits[1] - hits[0]


def _guard_wall(
    solid,
    plane: cq.Plane,
    depth: float,
    wall: float | None,
    min_wall: float | None,
    style: Style,
    probes: Iterable[tuple[float, float]] = ((0.0, 0.0),),
    what: str = "pocket",
) -> tuple[float, float]:
    """
    Refuse to cut a pocket that would leave less than the structural minimum.

    Returns (wall_before, wall_after). `wall` overrides the measurement when
    the caller knows better; when neither a measurement nor an override is
    available this RAISES, because an unmeasurable wall is not a safe wall.
    """
    floor = style.min_wall if min_wall is None else min_wall
    if wall is None:
        measured = [wall_at(solid, plane, uv) for uv in probes]
        good = [m for m in measured if m is not None]
        if not good:
            raise WallGuardError(
                f"cannot measure the wall under this {what} (ray found <2 surfaces); "
                "pass wall=<mm> explicitly if you know it"
            )
        wall = min(good)
    after = wall - depth
    if after < floor - 1e-6:
        raise WallGuardError(
            f"{what} {depth:.2f} mm deep into a {wall:.2f} mm wall leaves "
            f"{after:.2f} mm, below the {floor:.2f} mm minimum - "
            "reduce depth, thicken the wall, or lower min_wall deliberately"
        )
    return wall, after


def _solve_run(
    run: float, target_pitch: float, min_count: int = 2, exact: bool = False
) -> tuple[int, float]:
    """
    Count and pitch for a symmetric run of holes spanning `run`.

    Default (exact=False): holes land on both ends and divide the run evenly,
    so the pattern is symmetric about the centreline by construction and the
    pitch lands wherever it must. That is the point - a clean count at a
    slightly-off pitch reads as designed, the target pitch with a ragged
    remainder does not.

    exact=True holds the pitch and lets the leftover fall into the margin
    instead, for a PUBLISHED interface (a 25 mm payload grid is 25 mm or the
    accessory does not bolt on) where the number is the contract.
    """
    if run <= 1e-9:
        return 1, 0.0
    if target_pitch <= 0:
        raise FeatureError(f"target_pitch must be positive, got {target_pitch}")
    if exact:
        n = max(min_count, int(math.floor(run / target_pitch + 1e-9)) + 1)
        return n, target_pitch
    n = max(min_count, int(round(run / target_pitch)) + 1)
    return n, run / (n - 1)


def _cyl(
    radius: float, depth: float, uv: tuple[float, float], plane: cq.Plane, start: float = 0.0
) -> cq.Shape:
    """A cylinder cutter sunk into a face from `start` above it."""
    origin = plane.toWorldCoords((uv[0], uv[1])) + plane.zDir * start
    return cq.Solid.makeCylinder(radius, depth, origin, plane.zDir * -1.0)


def _through_depth(solid, plane: cq.Plane) -> float:
    """How deep a cutter must go from `plane` to clear the whole solid."""
    bb = plane.toLocalCoords(_shape(solid)).BoundingBox()
    return abs(bb.zmin) + 2.0


# --------------------------------------------------------------------------- #
# 1. base solids - radii baked into the profile
# --------------------------------------------------------------------------- #


def rounded_box(
    length: float,
    width: float,
    height: float,
    radius: float | None = None,
    *,
    centered: tuple[bool, bool, bool] = (True, True, False),
    top_break: float | None = None,
    bottom_break: float | None = None,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> cq.Workplane:
    """
    The default enclosure primitive: a box that is never a raw extrusion.

    Plan radii come from the profile, so this is safe as a base solid no matter
    what gets unioned to it later. `top_break`/`bottom_break` chamfer the flat
    rims; leave them None for the style rung, pass 0.0 to suppress. Those
    chamfers run here, on a lone simple solid, because this is the only place
    in the pipeline where they are free of boolean edges (see the module
    docstring, phase 1).

    `centered` follows cq.Workplane.box, but defaults to base-at-origin because
    enclosures stack upward from a mounting face.
    """
    if height <= 0:
        raise FeatureError(f"rounded_box needs a positive height, got {height}")
    r = style.plan_radius(length, width) if radius is None else radius
    sk = _rounded_rect(length, width, r)
    solid = cq.Workplane("XY").placeSketch(sk).extrude(height)

    tb = style.edge_break(min(length, width)) if top_break is None else top_break
    bb_ = style.edge_break(min(length, width)) if bottom_break is None else bottom_break
    if tb and tb > 0:
        solid = solid.faces(">Z").chamfer(min(tb, height / 2 - 1e-3))
    if bb_ and bb_ > 0:
        solid = solid.faces("<Z").chamfer(min(bb_, height / 2 - 1e-3))

    dx = 0.0 if centered[0] else length / 2
    dy = 0.0 if centered[1] else width / 2
    dz = -height / 2 if centered[2] else 0.0
    shape = solid.val().translate((dx, dy, dz))
    return _wp(_place(shape, _as_plane(plane)))


def rounded_prism(
    profile: Sequence[tuple[float, float]],
    height: float,
    radius: float | None = None,
    *,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> cq.Workplane:
    """
    An arbitrary closed 2D outline with every corner rounded, then extruded.

    For the shapes a box cannot express - L-brackets, tapered arms, sculpted
    structural members. Same contract as rounded_box: the radius lives in the
    profile, so the result is a safe base solid.

    `profile` is a list of (x, y) in the plane; do not repeat the first point.
    """
    pts = [tuple(p) for p in profile]
    if len(pts) < 3:
        raise FeatureError(f"rounded_prism needs >= 3 profile points, got {len(pts)}")
    if height <= 0:
        raise FeatureError(f"rounded_prism needs a positive height, got {height}")
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    span = min(max(xs) - min(xs), max(ys) - min(ys))
    r = style.plan_radius(span) if radius is None else radius

    sk = cq.Sketch().polygon(pts)
    if r > 1e-6:
        try:
            sk = sk.vertices().fillet(r)
        except Exception as exc:  # a radius the outline cannot hold
            raise FeatureError(
                f"radius {r} does not fit this outline ({exc}); "
                "pass a smaller radius or soften the profile"
            ) from None
    shape = cq.Workplane("XY").placeSketch(sk).extrude(height).val()
    return _wp(_place(shape, _as_plane(plane)))


def base_flange(
    length: float,
    width: float,
    thickness: float,
    *,
    radius: float | None = None,
    edge: str = "chamfer",
    edge_size: float | None = None,
    step_height: float | None = None,
    fastener: str | Fastener = "M6",
    inset: float | None = None,
    holes: str = "corners",
    target_pitch: float | None = None,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> Plate:
    """
    The mounting flange every mast- or floor-mounted assembly ends in.

    Large plan radii, a chamfered or stepped edge so it never presents a knife
    rim, and a bolt pattern that is part of the composition. `edge="step"`
    gives the machined two-level look (a proud upper pad on a wider lower
    plate); `edge="chamfer"` gives the simpler broken rim.

    `holes`: "corners" (4, at the pattern corners), "perimeter" (rhythm-solved
    around the edge), or "none" when the mating pattern is not released yet -
    which is better than inventing one.
    """
    if thickness <= 0:
        raise FeatureError(f"base_flange needs a positive thickness, got {thickness}")
    r = style.plan_radius(length, width) if radius is None else radius
    f = style.fastener(fastener)
    ins = style.edge_inset(f) if inset is None else inset

    if edge == "step":
        step = min(thickness * 0.45, 4.0) if step_height is None else step_height
        lower = _prism(_as_plane("XY"), length, width, r, thickness - step)
        inset_xy = max(2.0, min(length, width) * 0.06)
        upper = _prism(
            _offset_plane(_as_plane("XY"), dn=thickness - step),
            length - 2 * inset_xy,
            width - 2 * inset_xy,
            max(r - inset_xy, 1.0),
            step,
        )
        solid = _add(lower, upper, "base_flange step")
    elif edge == "chamfer":
        c = style.edge_break(min(length, width), thickness) if edge_size is None else edge_size
        solid = rounded_box(
            length,
            width,
            thickness,
            r,
            top_break=min(c, thickness * 0.4),
            bottom_break=min(c, thickness * 0.4),
            style=style,
        )
    else:
        raise FeatureError(f"edge must be 'chamfer' or 'step', got {edge!r}")

    top = _offset_plane(_as_plane("XY"), dn=thickness)
    if holes == "none":
        pts: tuple[tuple[float, float], ...] = ()
    elif holes == "corners":
        a, b = length / 2 - ins, width / 2 - ins
        pts = ((-a, -b), (a, -b), (-a, b), (a, b))
        solid = fastener_holes(solid, pts, plane=top, fastener=f, kind="clearance", style=style)
    elif holes == "perimeter":
        bp = bolt_pattern(
            "perimeter",
            length=length,
            width=width,
            inset=ins,
            fastener=f,
            target_pitch=target_pitch,
            plane=top,
            solid=solid,
            hole="clearance",
            style=style,
        )
        pts, solid = bp.points, bp.solid
    else:
        raise FeatureError(f"holes must be corners/perimeter/none, got {holes!r}")

    target = _as_plane(plane)
    moved = _place(_shape(solid), target)
    return Plate(
        solid=_wp(moved),
        plane=_offset_plane(target, dn=thickness),
        points=tuple(pts),
        length=length,
        width=width,
        thickness=thickness,
    )


# --------------------------------------------------------------------------- #
# 3. pockets - recessed panels and lightening
# --------------------------------------------------------------------------- #


def _cut_pocket(
    solid,
    face: cq.Plane | str | cq.Face,
    length: float,
    width: float,
    depth: float,
    radius: float,
    center: tuple[float, float],
    wall: float | None,
    min_wall: float | None,
    style: Style,
    what: str,
) -> Pocket:
    plane = face_plane(solid, face)
    probes = [
        (center[0], center[1]),
        (center[0] + length * 0.3, center[1]),
        (center[0] - length * 0.3, center[1]),
        (center[0], center[1] + width * 0.3),
        (center[0], center[1] - width * 0.3),
    ]
    before, after = _guard_wall(solid, plane, depth, wall, min_wall, style, probes, what)

    # start the cutter a little proud of the face so the cut is clean
    void_full = _prism(
        _offset_plane(plane, dn=0.05), length, width, radius, -(depth + 0.05), center
    )
    cut = _cut(solid, void_full, f"{what} cut")
    floor = _offset_plane(plane, du=center[0], dv=center[1], dn=-depth)
    void = _prism(_offset_plane(plane, du=center[0], dv=center[1]), length, width, radius, -depth)
    return Pocket(
        solid=cut,
        void=void,
        plane=floor,
        length=length,
        width=width,
        depth=depth,
        radius=radius,
        wall_before=before,
        wall_after=after,
    )


def recessed_panel(
    solid,
    face: cq.Plane | str | cq.Face = ">Z",
    *,
    size: tuple[float, float] | None = None,
    frame: float | None = None,
    depth: float | None = None,
    radius: float | None = None,
    center: tuple[float, float] = (0.0, 0.0),
    wall: float | None = None,
    min_wall: float | None = None,
    style: Style = STYLE,
) -> Pocket:
    """
    Turn a blank slab face into a panel: a shallow rounded pocket inside a
    proud perimeter frame.

    This is the single highest-value move in the whole vocabulary. A large flat
    face is the thing that makes a part read as a first draft; a recess with a
    frame around it reads as a machined product, costs one line, and stiffens
    the panel edge into the bargain.

    The pocket is sized from the face's own extents less `frame` on each side
    unless `size` overrides. Depth defaults to a proportion of the MEASURED
    wall, and the guard refuses outright if what is left would fall below
    `min_wall` (default `style.min_wall`) - so styling can never quietly eat
    the structure. Pass `wall=` to skip the measurement when you know better.

    Returns a Pocket; feed `.void` to `rib_field` to fill it, and carry on from
    `.solid`.
    """
    plane = face_plane(solid, face)
    fu, fv = _face_extents(solid, plane, face)
    fr = style.frame(fu, fv) if frame is None else frame
    if size is None:
        length, width = fu - 2 * fr, fv - 2 * fr
    else:
        length, width = size
    if length <= 0 or width <= 0:
        raise FeatureError(
            f"frame {fr} leaves no panel on a {fu:.1f} x {fv:.1f} face - "
            "use a smaller frame or an explicit size"
        )
    if depth is None:
        measured = wall if wall is not None else wall_at(solid, plane, center)
        depth = style.recess(measured) if measured else style.recess_depth
    r = style.plan_radius(length, width) if radius is None else radius
    return _cut_pocket(
        solid, face, length, width, depth, r, center, wall, min_wall, style, "recessed panel"
    )


def lightening_pocket(
    solid,
    face: cq.Plane | str | cq.Face = ">Z",
    *,
    size: tuple[float, float],
    depth: float,
    radius: float | None = None,
    center: tuple[float, float] = (0.0, 0.0),
    wall: float | None = None,
    min_wall: float | None = None,
    style: Style = STYLE,
) -> Pocket:
    """
    A deep rounded pocket for sculpting mass out of a structural member.

    Same guard as recessed_panel, and it matters more here: this is the feature
    people use to hit a mass target, which is exactly when a wall gets thinned
    past what it can carry. Corners are generously rounded because a lightening
    pocket with sharp internal corners just relocates the stress concentration
    it was supposed to relieve.
    """
    length, width = size
    r = style.plan_radius(length, width) if radius is None else radius
    return _cut_pocket(
        solid, face, length, width, depth, r, center, wall, min_wall, style, "lightening pocket"
    )


# --------------------------------------------------------------------------- #
# 4. ribs and fins
# --------------------------------------------------------------------------- #


def _rib_segments(
    pattern: str, a: float, b: float, pitch: float, count: int | None
) -> list[tuple[float, float, float, float]]:
    """
    (cx, cy, angle_deg, length) rib centrelines in pocket-local coordinates.

    Segments are made deliberately overlong; `rib_field` clips them to the
    pocket, which is both simpler and more robust than trying to solve each
    intersection with a rounded boundary analytically.
    """
    over = 2.0 * math.hypot(a, b)
    segs: list[tuple[float, float, float, float]] = []

    if pattern == "parallel":
        n = count if count else max(2, int(round(2 * a / pitch)) + 1)
        step = (2 * a) / (n - 1) if n > 1 else 0.0
        for i in range(n):
            segs.append((-a + i * step, 0.0, 90.0, over))

    elif pattern == "diagonal-grid":
        reach = (a + b) / math.sqrt(2)
        for ang, nx, ny in ((45.0, -1, 1), (-45.0, 1, 1)):
            n = max(1, int(round(2 * reach / pitch)))
            step = (2 * reach) / n
            for i in range(n + 1):
                d = -reach + i * step
                segs.append((d * nx / math.sqrt(2), d * ny / math.sqrt(2), ang, over))

    elif pattern == "x":
        ang = math.degrees(math.atan2(2 * b, 2 * a))
        diag = math.hypot(2 * a, 2 * b)
        segs.append((0.0, 0.0, ang, diag))
        segs.append((0.0, 0.0, -ang, diag))

    elif pattern == "chevron":
        arm = math.hypot(b, b) * 1.2
        n = count if count else max(2, int(round(2 * a / pitch)))
        step = (2 * a) / n
        for i in range(n + 1):
            apex = -a + i * step
            segs.append((apex - b / 2, b / 2, 135.0, arm))
            segs.append((apex - b / 2, -b / 2, -135.0, arm))

    elif pattern == "triangulated":
        n = count if count else max(2, int(round(2 * a / pitch)))
        step = (2 * a) / n
        arm = math.hypot(step, 2 * b) * 1.1
        for i in range(n):
            x0, x1 = -a + i * step, -a + (i + 1) * step
            y0, y1 = (-b, b) if i % 2 == 0 else (b, -b)
            ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
            segs.append(((x0 + x1) / 2, (y0 + y1) / 2, ang, arm))
        segs.append((0.0, 0.0, 0.0, over))  # spine along the load path

    else:
        raise FeatureError(
            f"unknown rib pattern {pattern!r}; use chevron, x, triangulated, "
            "parallel or diagonal-grid"
        )
    return segs


def rib_field(
    pocket: Pocket,
    pattern: str = "chevron",
    *,
    thickness: float | None = None,
    height: float | None = None,
    pitch: float | None = None,
    count: int | None = None,
    draft_deg: float | None = None,
    relief: float | None = None,
    margin: float = 0.0,
    style: Style = STYLE,
) -> RibField:
    """
    Fill a pocket with a stiffening rib field, clipped to its rounded boundary.

    This is the second half of the panel move: the recess stops the face being
    a slab, the ribs stop the recess being a hole. Ribs are drafted so the part
    stays castable and their crests sit `relief` below the outer face, so the
    frame still reads as the highest surface and nothing rubs when the part is
    laid face-down on a bench.

    Patterns: 'chevron', 'x', 'triangulated', 'parallel', 'diagonal-grid'.
    Union the result back into `pocket.solid`; it is already clipped to the
    pocket volume, so it cannot spill onto the frame.
    """
    t = style.rib_thickness if thickness is None else thickness
    rel = style.rib_relief if relief is None else relief
    h = (pocket.depth - rel) if height is None else height
    draft = style.rib_draft_deg if draft_deg is None else draft_deg
    p = style.rib_pitch if pitch is None else pitch
    if h <= 0:
        raise FeatureError(
            f"rib height {h:.2f} <= 0: a {pocket.depth:.2f} mm pocket cannot "
            f"hold ribs with {rel:.2f} mm relief"
        )

    a = pocket.length / 2 - margin
    b = pocket.width / 2 - margin
    if a <= 0 or b <= 0:
        raise FeatureError(f"margin {margin} leaves no room in the pocket")

    segs = _rib_segments(pattern, a, b, p, count)
    grow = 2.0 * (h * math.tan(math.radians(draft)) + 1.0)

    solids: list[cq.Shape] = []
    for cx, cy, ang, length in segs:
        strip = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, ang), offset=(cx, cy, 0))
            .rect(length + grow, t)
            .extrude(h, taper=draft)
            .val()
        )
        solids.append(strip)

    ribs = _fuse(solids)
    clipped = _place(ribs, pocket.plane).intersect(pocket.void)
    vol = sum(abs(s.Volume()) for s in clipped.Solids())
    if vol <= 0:
        raise FeatureError(f"rib pattern {pattern!r} produced no material in this pocket")
    return RibField(
        solid=_wp(clipped),
        pattern=pattern,
        count=len(segs),
        thickness=t,
        height=h,
        volume_mm3=vol,
    )


def fin_bank(
    *,
    height: float,
    base: str = "flat",
    length: float = 0.0,
    radius: float = 0.0,
    count: int | None = None,
    span: float | None = None,
    pitch: float | None = None,
    thickness: float | None = None,
    draft_deg: float | None = None,
    embed: float = EMBED,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> FinBank:
    """
    Constant-pitch cooling fins with radiused tips - flat blades or annular.

    `base="flat"` gives blades of `length` standing on the plane, spaced along
    the plane's X. `base="cylinder"` gives annular fins around a cylinder of
    `radius`, stacked along the plane's Z - the ring stack seen on sensor pods.

    Tips are radiused rather than square: a knife-edged fin looks unfinished,
    damages easily and does nothing extra for convection. The profile carries
    the tip arc and the draft directly, so no 3D fillet is ever attempted on a
    fin - which is what makes a 30-fin bank build reliably.

    Give `count` or `span` (with `pitch`); the other is solved. `added_area_mm2`
    on the result is the net wetted-area gain, not the raw surface area.

    Fin roots run `embed` below the mounting plane so the union with the wall
    is a real overlap; set embed=0 only when the bank is a standalone solid.
    """
    t = style.fin_thickness if thickness is None else thickness
    p = style.fin_pitch if pitch is None else pitch
    draft = style.fin_draft_deg if draft_deg is None else draft_deg
    if height <= 0 or t <= 0 or p <= 0:
        raise FeatureError(f"fin height/thickness/pitch must be positive: {height}/{t}/{p}")
    if p <= t:
        raise FeatureError(f"fin pitch {p} must exceed fin thickness {t} - fins would merge")

    if count is None:
        if span is None:
            raise FeatureError("fin_bank needs count or span")
        count = max(1, int(round(span / p)) + 1)
        p = span / (count - 1) if count > 1 else 0.0
    total_span = (count - 1) * p

    tip = max(0.4 * t, t - 2 * height * math.tan(math.radians(draft)))
    tip = min(tip, t * 0.98)
    straight = height - tip / 2
    if straight <= 0:
        raise FeatureError(f"fin height {height} is too short for a {tip:.2f} mm radiused tip")

    e = max(embed, 0.0)
    solids: list[cq.Shape] = []
    if base == "flat":
        if length <= 0:
            raise FeatureError("flat fin_bank needs a positive length")
        blade = (
            cq.Workplane("XZ")
            .moveTo(-t / 2, -e)
            .lineTo(-t / 2, 0)
            .lineTo(-tip / 2, straight)
            .radiusArc((tip / 2, straight), tip / 2)
            .lineTo(t / 2, 0)
            .lineTo(t / 2, -e)
            .close()
            .extrude(length)
            .val()
            .translate((0, length / 2, 0))
        )
        for i in range(count):
            solids.append(blade.translate((-total_span / 2 + i * p, 0, 0)))
        root_area = count * t * length
    elif base == "cylinder":
        if radius <= 0:
            raise FeatureError("cylindrical fin_bank needs a positive radius")
        ring = (
            cq.Workplane("XZ")
            .moveTo(max(radius - e, 0.01), -t / 2)
            .lineTo(radius + straight, -tip / 2)
            .radiusArc((radius + straight, tip / 2), -tip / 2)
            .lineTo(max(radius - e, 0.01), t / 2)
            .close()
            .revolve(360, (0, 0, 0), (0, 1, 0))
            .val()
        )
        for i in range(count):
            solids.append(ring.translate((0, 0, -total_span / 2 + i * p)))
        root_area = count * 2 * math.pi * radius * t
    else:
        raise FeatureError(f"fin base must be 'flat' or 'cylinder', got {base!r}")

    fins = _fuse(solids)
    # Measure the area on the EXPOSED side only: trim the buried embed stub
    # away first, then take off the root footprint twice - once for the fin's
    # own flat root, which the union consumes, and once for the base area the
    # fin now covers. What is left is the true increase in wetted area.
    exposed = fins
    if e > 0:
        if base == "flat":
            keep = cq.Solid.makeBox(
                4 * (total_span + t + 2),
                2 * length + 4,
                4 * height + 4,
                cq.Vector(-2 * (total_span + t + 2), -length - 2, 0.0),
            )
        else:
            keep = cq.Solid.makeCylinder(
                radius + straight + tip,
                2 * (total_span + t + 4),
                cq.Vector(0, 0, -(total_span + t + 4)),
            ).cut(
                cq.Solid.makeCylinder(
                    radius,
                    2 * (total_span + t + 8),
                    cq.Vector(0, 0, -(total_span + t + 8)),
                )
            )
        exposed = _checked(fins.intersect(keep), "fin_bank area trim")
    added = exposed.Area() - 2 * root_area
    placed = _place(fins, _as_plane(plane))
    return FinBank(
        solid=_wp(placed),
        count=count,
        pitch=p,
        thickness=t,
        height=height,
        span=total_span,
        added_area_mm2=added,
        root_area_mm2=root_area,
    )


def louver_bank(
    solid,
    face: cq.Plane | str | cq.Face = ">Z",
    *,
    width: float,
    height: float,
    center: tuple[float, float] = (0.0, 0.0),
    count: int | None = None,
    pitch: float | None = None,
    gap: float | None = None,
    blade_angle_deg: float | None = None,
    wall: float | None = None,
    shape: str = "blade",
    lip: float = 0.0,
    style: Style = STYLE,
) -> LouverBank:
    """
    Weather-shedding ventilation: a bank of tilted slots over an aperture.

    The slots slope DOWN toward the outside, so the outer opening sits lower
    than the inner one and water would have to run uphill to get in. That is
    the whole reason a louver is not just a row of holes, and it is why
    `blade_angle_deg` is not decoration.

    `shape="scallop"` rounds each slot to a near-semicircular end (the softer
    cast look); `"blade"` keeps a light corner radius. `lip` adds a drip
    overhang above the bank - union `.add` if you use it.

    Returns free area measured off the real cut geometry, so a ventilation
    claim can be checked instead of asserted.
    """
    plane = face_plane(solid, face)
    ang = style.louver_angle_deg if blade_angle_deg is None else blade_angle_deg
    p = style.louver_pitch if pitch is None else pitch
    if width <= 0 or height <= 0:
        raise FeatureError(f"louver bank needs positive width/height, got {width}/{height}")
    if not 0 < ang < 80:
        raise FeatureError(f"blade_angle_deg must be in (0, 80), got {ang}")

    if count is None:
        count = max(1, int(height // p))
        if count < 1:
            raise FeatureError(f"a {height} mm tall bank cannot hold a louver at pitch {p}")
    else:
        p = height / count

    g = min(p * 0.55, p - 1.0) if gap is None else gap
    if g <= 0 or g >= p:
        raise FeatureError(f"louver gap {g} must be in (0, pitch={p})")

    thickness = wall if wall is not None else wall_at(solid, plane, center)
    if thickness is None:
        raise FeatureError("cannot measure the wall for the louver bank; pass wall=<mm>")
    if shape not in ("blade", "scallop"):
        raise FeatureError(f"louver shape must be blade/scallop, got {shape!r}")
    depth = (thickness + 3.0) / math.cos(math.radians(ang)) + 2.0
    corner = g * 0.49 if shape == "scallop" else g * 0.2

    cutters: list[cq.Shape] = []
    for i in range(count):
        v = center[1] - height / 2 + p / 2 + i * p
        sk = _rounded_rect(width, g, corner)
        slot = cq.Workplane("XY").placeSketch(sk).extrude(-depth).val()
        slot = slot.translate((0, 0, depth / 2))
        # tilt about the horizontal axis of the face: travelling inward the
        # slot rises, so the outer mouth is the LOW end and water runs back out
        slot = slot.rotate((0, 0, 0), (1, 0, 0), ang)
        slot = slot.translate((center[0], v, 0))
        cutters.append(_place(slot, plane))

    cut = _fuse(cutters)

    eps = 0.02
    slab = _prism(_offset_plane(plane, dn=eps / 2), width * 2 + 20, height * 2 + 20, 0.0, -eps)
    section = cut.intersect(slab)
    free = sum(abs(s.Volume()) for s in section.Solids()) / eps

    add: cq.Shape | None = None
    if lip > 0:
        add = _shape(
            drip_edge(
                length=width + 2 * lip,
                projection=lip,
                thickness=max(2.0, lip * 0.8),
                plane=_offset_plane(plane, du=center[0], dv=center[1] + height / 2 + lip * 0.6),
                style=style,
            )
        )

    return LouverBank(
        cut=cut,
        add=add,
        free_area_mm2=free,
        throat_area_mm2=free * math.cos(math.radians(ang)),
        count=count,
        pitch=p,
        gap=g,
        blade_angle_deg=ang,
    )


# --------------------------------------------------------------------------- #
# 5. fastener rhythm and hardware
# --------------------------------------------------------------------------- #


def bolt_pattern(
    kind: str = "perimeter",
    *,
    length: float = 0.0,
    width: float = 0.0,
    diameter: float = 0.0,
    inset: float | None = None,
    target_pitch: float | None = None,
    count: int | None = None,
    fastener: str | Fastener = "M4",
    start_angle: float = 0.0,
    multiple_of: int = 4,
    exact_pitch: bool = False,
    plane: cq.Plane | str = "XY",
    solid=None,
    hole: str | None = None,
    depth: float | None = None,
    style: Style = STYLE,
) -> BoltPattern:
    """
    Fastener RHYTHM: solve for the count that divides the run evenly.

    This is the function that turns scattered screws into composition. You give
    an edge inset and the pitch you would LIKE; it solves for the whole number
    of screws that lands on a symmetric, evenly-divided run and reports the
    pitch it actually achieved. The result is always symmetric about both
    centrelines, which is the property the eye reads as "designed".

    kinds:
      "perimeter"  a rectangular ring inset from a length x width face
      "grid"       a full rectangular array (payload/interface plates)
      "line"       a single run of `length` along the plane's X
      "circle"     a bolt circle of `diameter`, count rounded to a multiple of
                   `multiple_of` (default 4) so it stays symmetric

    `exact_pitch=True` holds the requested pitch and widens the margin instead
    of adjusting the spacing - for a published interface, where the pitch is
    the contract (see tapped_hole_grid).

    Pass `solid` and `hole` ("cbore", "clearance" or "tap") to apply the
    pattern as well as return it; `.solid` then carries the drilled part.
    `.points` are plane-local (u, v) and are meant to be reused - the same list
    drives the bosses inside the lid, the mating holes in the base, and any fit
    check that has to prove the two agree.

    `.in_band` compares the achieved pitch against the fastener's STRUCTURAL
    spacing band. An interface grid deliberately runs tighter than that, so a
    False from tapped_hole_grid is expected, not a defect.
    """
    f = style.fastener(fastener)
    pitch = style.pitch(f) if target_pitch is None else target_pitch
    ins = style.edge_inset(f) if inset is None else inset
    pl = _as_plane(plane)

    pitch_v: float | None = None
    if kind == "perimeter":
        a, b = length / 2 - ins, width / 2 - ins
        if a <= 0 or b <= 0:
            raise FeatureError(f"inset {ins} leaves no perimeter on {length} x {width}")
        nx, px = _solve_run(2 * a, pitch, exact=exact_pitch)
        ny, py = _solve_run(2 * b, pitch, exact=exact_pitch)
        pts = []
        for i in range(nx):
            x = -a + i * px
            pts.append((x, -b))
            pts.append((x, b))
        for j in range(1, ny - 1):
            y = -b + j * py
            pts.append((-a, y))
            pts.append((a, y))
        achieved, pitch_v = px, py
    elif kind == "grid":
        a, b = length / 2 - ins, width / 2 - ins
        if a <= 0 or b <= 0:
            raise FeatureError(f"inset {ins} leaves no grid on {length} x {width}")
        nx, px = _solve_run(2 * a, pitch, exact=exact_pitch)
        ny, py = _solve_run(2 * b, pitch, exact=exact_pitch)
        ox, oy = (nx - 1) * px / 2, (ny - 1) * py / 2
        pts = [(-ox + i * px, -oy + j * py) for i in range(nx) for j in range(ny)]
        achieved, pitch_v = px, py
    elif kind == "line":
        run = length - 2 * ins
        if run <= 0:
            raise FeatureError(f"inset {ins} leaves no run on length {length}")
        if count is None:
            n, px = _solve_run(run, pitch, exact=exact_pitch)
        else:
            n, px = count, run / max(count - 1, 1)
        pts = [(-(n - 1) * px / 2 + i * px, 0.0) for i in range(n)]
        achieved = px
    elif kind == "circle":
        if diameter <= 0:
            raise FeatureError("circle bolt pattern needs a positive diameter")
        circ = math.pi * diameter
        if count is None:
            n = max(multiple_of, int(round(circ / pitch)))
            if multiple_of > 1:
                n = int(math.ceil(n / multiple_of) * multiple_of)
        else:
            n = count
        r = diameter / 2
        pts = []
        for i in range(n):
            th = math.radians(start_angle + i * 360.0 / n)
            pts.append((r * math.cos(th), r * math.sin(th)))
        achieved = circ / n
    else:
        raise FeatureError(
            f"unknown bolt pattern kind {kind!r}; use perimeter, grid, line or circle"
        )

    pts = tuple(sorted({(round(x, 6), round(y, 6)) for x, y in pts}))
    lo, hi = f.pitch_band
    checks = [achieved] + ([pitch_v] if pitch_v else [])
    in_band = all(lo - 1e-6 <= c <= hi + 1e-6 for c in checks)

    applied = None
    if solid is not None and hole:
        applied = fastener_holes(
            solid, pts, plane=pl, fastener=f, kind=hole, depth=depth, style=style
        )

    return BoltPattern(
        points=pts,
        points3d=tuple(pl.toWorldCoords(p).toTuple() for p in pts),
        plane=pl,
        kind=kind,
        count=len(pts),
        pitch=round(achieved, 4),
        pitch_v=round(pitch_v, 4) if pitch_v else None,
        fastener=f,
        in_band=in_band,
        solid=applied,
    )


def fastener_holes(
    solid,
    points: Sequence[tuple[float, float]],
    *,
    plane: cq.Plane | str = "XY",
    fastener: str | Fastener = "M4",
    kind: str = "cbore",
    depth: float | None = None,
    cbore_depth: float | None = None,
    style: Style = STYLE,
) -> cq.Workplane:
    """
    Drill a point list on a face: counterbored, clearance or tapped.

    Counterbores must land on a FLAT land - a counterbore on a curved or ribbed
    wall gives a crescent-shaped seat that no screw head can sit on. Build the
    land first (`connector_land`, `base_flange`, a recess frame), then drill.

    kinds: "cbore" (through clearance + sunk socket head), "clearance"
    (through), "tap" (blind tap drill, default depth 2x nominal + 1.5).
    """
    if not points:
        return _wp(solid)
    f = style.fastener(fastener)
    pl = _as_plane(plane)
    through = _through_depth(solid, pl)

    cutters: list[cq.Shape] = []
    for uv in points:
        if kind == "clearance":
            cutters.append(_cyl(f.clearance / 2, through + 1.0, uv, pl, start=1.0))
        elif kind == "cbore":
            cd = f.cbore_depth if cbore_depth is None else cbore_depth
            cutters.append(_cyl(f.clearance / 2, through + 1.0, uv, pl, start=1.0))
            cutters.append(_cyl(f.cbore_dia / 2, cd + 1.0, uv, pl, start=1.0))
        elif kind == "tap":
            d = (f.min_tap_depth + 1.5) if depth is None else depth
            cutters.append(_cyl(f.tap_drill / 2, d + 0.5, uv, pl, start=0.5))
        else:
            raise FeatureError(f"hole kind must be cbore/clearance/tap, got {kind!r}")
    return _cut(solid, _fuse(cutters), f"{kind} holes")


def counterbore_at(
    solid,
    points: Sequence[tuple[float, float]],
    *,
    plane: cq.Plane | str = "XY",
    fastener: str | Fastener = "M4",
    cbore_depth: float | None = None,
    style: Style = STYLE,
) -> cq.Workplane:
    """Counterbored socket-head screw holes at a point list on a flat land."""
    return fastener_holes(
        solid,
        points,
        plane=plane,
        fastener=fastener,
        kind="cbore",
        cbore_depth=cbore_depth,
        style=style,
    )


def tapped_hole_grid(
    solid,
    face: cq.Plane | str | cq.Face = ">Z",
    *,
    pitch: float = 25.0,
    fastener: str | Fastener = "M6",
    size: tuple[float, float] | None = None,
    inset: float | None = None,
    depth: float | None = None,
    style: Style = STYLE,
) -> BoltPattern:
    """
    The payload-plate interface grid: tapped holes at a constant pitch.

    An interface plate's job is to accept things nobody has designed yet, so
    the grid is deliberately regular and deliberately labelled by its pitch -
    it becomes the published interface. Defaults to M6 at 25 mm, the common
    optical/payload breadboard rhythm.

    The pitch is held EXACTLY (the leftover goes into the margin) because the
    number is what mating hardware is built to. A grid that quietly came out at
    24.0 mm because that divided the plate evenly is a grid nothing bolts to.
    """
    plane = face_plane(solid, face)
    fu, fv = _face_extents(solid, plane, face)
    length, width = (fu, fv) if size is None else size
    return bolt_pattern(
        "grid",
        length=length,
        width=width,
        inset=inset,
        target_pitch=pitch,
        fastener=fastener,
        plane=plane,
        solid=solid,
        hole="tap",
        depth=depth,
        exact_pitch=True,
        style=style,
    )


def _boss(
    outer: float,
    height: float,
    base_fillet: float,
    plane: cq.Plane | str,
    embed: float = EMBED,
) -> cq.Workplane:
    """
    A cylindrical boss whose base fillet is revolved, never filleted late.

    The profile starts `embed` below the mounting plane as a plain cylinder,
    so the boss overlaps its parent instead of merely touching it, and the
    fillet still starts exactly at the parent's surface where it does its job.
    """
    r = outer / 2
    f = min(base_fillet, r * 0.9, height * 0.45)
    e = max(embed, 0.0)
    pts = [(0.0, -e), (r + f, -e)]
    if f > 1e-6:
        profile = (
            cq.Workplane("XZ")
            .moveTo(*pts[0])
            .lineTo(*pts[1])
            .lineTo(r + f, 0)
            .radiusArc((r, f), -f)
            .lineTo(r, height)
            .lineTo(0, height)
            .close()
        )
    else:
        profile = (
            cq.Workplane("XZ")
            .moveTo(0, -e)
            .lineTo(r, -e)
            .lineTo(r, height)
            .lineTo(0, height)
            .close()
        )
    solid = profile.revolve(360, (0, 0, 0), (0, 1, 0)).val()
    return _wp(_place(solid, _as_plane(plane)))


def tapped_boss(
    height: float,
    *,
    fastener: str | Fastener = "M4",
    outer: float | None = None,
    base_fillet: float | None = None,
    depth: float | None = None,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> cq.Workplane:
    """
    A boss with a blind tapped hole and a filleted root.

    The root fillet is revolved into the profile rather than filleted onto a
    union, which is the difference between a boss that builds every time and
    one that fails once it has neighbours. The fillet is not cosmetic: a boss
    meeting a wall at a sharp corner is a crack starter, and this is the part
    of an enclosure that gets torqued.
    """
    f = style.fastener(fastener)
    od = f.boss_dia if outer is None else outer
    fil = max(1.0, od * 0.12) if base_fillet is None else base_fillet
    d = (f.min_tap_depth + 1.5) if depth is None else depth
    if d >= height:
        raise FeatureError(
            f"tap depth {d:.1f} does not fit in a {height:.1f} mm boss - "
            "raise the boss or shorten the engagement"
        )
    boss = _boss(od, height, fil, plane)
    pl = _as_plane(plane)
    hole = _cyl(f.tap_drill / 2, d + 0.5, (0.0, 0.0), _offset_plane(pl, dn=height), start=0.5)
    return _cut(boss, hole, "tapped_boss bore")


def standoff_boss(
    height: float,
    *,
    fastener: str | Fastener = "M3",
    outer: float | None = None,
    base_fillet: float | None = None,
    counterbore: bool = False,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> cq.Workplane:
    """
    A boss with a through clearance hole - a board standoff or spacer.

    `counterbore=True` sinks the screw head at the top face, for the case where
    the standoff is what the fastener lands on rather than what it passes by.
    """
    f = style.fastener(fastener)
    od = f.boss_dia if outer is None else outer
    fil = max(1.0, od * 0.12) if base_fillet is None else base_fillet
    boss = _boss(od, height, fil, plane)
    pl = _as_plane(plane)
    top = _offset_plane(pl, dn=height)
    cutters = [_cyl(f.clearance / 2, height + 2.0, (0.0, 0.0), top, start=1.0)]
    if counterbore:
        cutters.append(_cyl(f.cbore_dia / 2, f.cbore_depth + 1.0, (0.0, 0.0), top, start=1.0))
    return _cut(boss, _fuse(cutters), "standoff_boss bore")


# --------------------------------------------------------------------------- #
# 6. connector lands
# --------------------------------------------------------------------------- #


def connector_land(
    solid,
    face: cq.Plane | str | cq.Face = ">Z",
    *,
    length: float,
    width: float,
    center: tuple[float, float] = (0.0, 0.0),
    raised: float = 1.5,
    radius: float | None = None,
    aperture: float | tuple[float, float] | None = None,
    aperture_radius: float | None = None,
    fastener: str | Fastener = "M3",
    screw_inset: float | None = None,
    screw_kind: str | None = "tap",
    break_size: float | None = None,
    wall: float | None = None,
    min_wall: float | None = None,
    style: Style = STYLE,
) -> ConnectorLand:
    """
    A dedicated flat land for a connector - never punch one through a wall.

    A circular connector cut straight through a ribbed or curved wall gives a
    gasket face that is neither flat nor square to the connector, so it leaks,
    and it looks like an afterthought because it was one. A land fixes both: a
    machined flat with a chamfered boundary, its own 4-screw pattern and a
    clean aperture.

    `raised > 0` proudens the land off the face; `raised < 0` recesses it (and
    then the wall guard applies, since a recessed land removes material).
    `aperture` is a diameter (float) or (length, width) for a rectangular one.
    """
    plane = face_plane(solid, face)
    r = style.plan_radius(length, width) if radius is None else radius
    brk = style.edge_break(min(length, width), abs(raised)) if break_size is None else break_size
    f = style.fastener(fastener)
    result = _wp(solid)

    if raised > 0:
        pad = rounded_box(
            length,
            width,
            raised + EMBED,
            r,
            top_break=min(brk, raised * 0.45),
            bottom_break=0.0,
            style=style,
        )
        pad_shape = _place(_shape(pad).translate((center[0], center[1], -EMBED)), plane)
        result = _add(result, pad_shape, "connector land pad", welded=True)
        land = _offset_plane(plane, du=center[0], dv=center[1], dn=raised)
    elif raised < 0:
        depth = -raised
        pocket = _cut_pocket(
            result, plane, length, width, depth, r, center, wall, min_wall, style, "connector land"
        )
        result = pocket.solid
        # break the pocket mouth with a short tapered collar cut
        if brk > 0:
            mouth = (
                cq.Workplane("XY")
                .placeSketch(_rounded_rect(length + 2 * brk, width + 2 * brk, r + brk))
                .extrude(-brk, taper=-45)
                .val()
                .translate((center[0], center[1], 0))
            )
            result = _cut(result, _place(mouth, plane), "land mouth break")
        land = pocket.plane
    else:
        land = _offset_plane(plane, du=center[0], dv=center[1])

    ap_area = 0.0
    if aperture is not None:
        through = _through_depth(result, land) + abs(raised) + 2.0
        if isinstance(aperture, (int, float)):
            cutter = _cyl(float(aperture) / 2, through, (0.0, 0.0), land, start=1.0)
            ap_area = math.pi * (float(aperture) / 2) ** 2
        else:
            al, aw = aperture
            ar = (min(al, aw) * 0.15) if aperture_radius is None else aperture_radius
            cutter = _prism(_offset_plane(land, dn=1.0), al, aw, ar, -through)
            ap_area = al * aw - (4 - math.pi) * ar**2
        result = _cut(result, cutter, "connector aperture")

    ins = style.edge_inset(f) if screw_inset is None else screw_inset
    a, b = length / 2 - ins, width / 2 - ins
    if a <= 0 or b <= 0:
        raise FeatureError(f"screw inset {ins} leaves no room on a {length} x {width} land")
    pts = ((-a, -b), (a, -b), (-a, b), (a, b))
    if screw_kind:
        result = fastener_holes(result, pts, plane=land, fastener=f, kind=screw_kind, style=style)

    return ConnectorLand(
        solid=result,
        plane=land,
        screw_points=pts,
        length=length,
        width=width,
        aperture_area_mm2=ap_area,
    )


# --------------------------------------------------------------------------- #
# 7. cylinder-to-prism transitions
# --------------------------------------------------------------------------- #


def step_shoulder(
    lower_dia: float,
    upper_dia: float,
    height: float,
    *,
    steps: int = 2,
    break_size: float | None = None,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> cq.Workplane:
    """
    A concentric step ring stack between two diameters - the machined look.

    Where a cylinder meets a wider hub, an abrupt butt joint reads as two parts
    that happen to touch. A stack of concentric steps, each with its own broken
    edge, reads as one turned component. Every edge is in the revolved profile,
    so nothing is filleted after the fact.
    """
    if steps < 1:
        raise FeatureError(f"step_shoulder needs at least one step, got {steps}")
    if height <= 0:
        raise FeatureError(f"step_shoulder needs a positive height, got {height}")
    r_lo, r_hi = lower_dia / 2, upper_dia / 2
    if abs(r_lo - r_hi) < 1e-6:
        raise FeatureError("step_shoulder needs two different diameters")

    sh = height / steps
    c = style.edge_break(max(lower_dia, upper_dia)) if break_size is None else break_size
    c = min(c, sh * 0.4, abs(r_lo - r_hi) / steps * 0.4)

    pts = [(0.0, 0.0)]
    z = 0.0
    for i in range(steps):
        r = r_lo + (r_hi - r_lo) * i / steps
        pts.append((r, z))
        if c > 1e-6:
            pts.append((r, z + sh - c))
            pts.append((r - math.copysign(c, r - r_hi), z + sh))
        else:
            pts.append((r, z + sh))
        z += sh
    pts.append((r_hi, z))
    pts.append((0.0, z))

    sk = cq.Sketch().polygon(pts)
    solid = cq.Workplane("XZ").placeSketch(sk).revolve(360, (0, 0, 0), (0, 1, 0)).val()
    return _wp(_place(solid, _as_plane(plane)))


def blend_transition(
    lower_dia: float,
    upper_dia: float,
    height: float,
    *,
    kind: str = "fillet",
    fillet: float | None = None,
    facets: int = 8,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> cq.Workplane:
    """
    The smooth version of the same transition: a blended or faceted collar.

    kind="fillet"  a tangent shoulder - straight at the bottom, an arc sweeping
                   into the upper diameter. The large-radius casting look.
    kind="cone"    a plain frustum with broken ends, for machined parts.
    kind="facet"   an octagonal (or n-sided) collar, drafted - the faceted
                   collar seen where a pod meets its yoke.

    Never leave a cylinder butted onto a prism; this is the cheap alternative.
    """
    if height <= 0:
        raise FeatureError(f"blend_transition needs a positive height, got {height}")
    r_lo, r_hi = lower_dia / 2, upper_dia / 2

    if kind == "facet":
        if facets < 3:
            raise FeatureError(f"facet collar needs >= 3 facets, got {facets}")
        taper = math.degrees(math.atan2(r_lo - r_hi, height))
        solid = cq.Workplane("XY").polygon(facets, lower_dia).extrude(height, taper=taper).val()
        return _wp(_place(solid, _as_plane(plane)))

    if kind == "cone":
        c = style.edge_break(max(lower_dia, upper_dia))
        c = min(c, height * 0.3)
        pts = [(0.0, 0.0), (r_lo, 0.0), (r_hi, height - c), (r_hi - c, height), (0.0, height)]
        sk = cq.Sketch().polygon(pts)
        solid = cq.Workplane("XZ").placeSketch(sk).revolve(360, (0, 0, 0), (0, 1, 0)).val()
        return _wp(_place(solid, _as_plane(plane)))

    if kind != "fillet":
        raise FeatureError(f"blend kind must be fillet/cone/facet, got {kind!r}")

    dr = r_lo - r_hi
    f = abs(dr) * 1.2 if fillet is None else fillet
    f = max(f, abs(dr) + 1e-3, 0.5)
    straight = height - f
    if straight < 0:
        raise FeatureError(f"a {f:.2f} mm blend does not fit in {height:.2f} mm of height")
    concave = dr > 0  # narrowing upward: material curves inward
    arc_r = -f if concave else f
    profile = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(r_lo, 0)
        .lineTo(r_lo, straight)
        .radiusArc((r_hi, height), arc_r)
        .lineTo(0, height)
        .close()
    )
    solid = profile.revolve(360, (0, 0, 0), (0, 1, 0)).val()
    return _wp(_place(solid, _as_plane(plane)))


# --------------------------------------------------------------------------- #
# 8. sealing and weather
# --------------------------------------------------------------------------- #


def oring_groove(
    *,
    cord: float = 2.62,
    shape: str = "rect",
    length: float = 0.0,
    width: float = 0.0,
    diameter: float = 0.0,
    radius: float | None = None,
    groove_width: float | None = None,
    depth: float | None = None,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> ORingGroove:
    """
    A real face-seal groove, sized from a standard cord diameter.

    "Sealed enclosure" is a claim, and a groove that squeezes the cord too
    little leaks while one that squeezes it too much extrudes it and jacks the
    joint open. The AS568-style table here gives width and depth for 24-28%
    squeeze and 75-85% fill, and the returned record reports both so the claim
    can be checked rather than asserted.

    shape="rect" gives a rounded-rectangle groove for a lid (the centreline
    rectangle is `length` x `width`); shape="circle" gives a circular groove of
    `diameter`. Cut it from a FLAT sealing land - a groove that crosses a
    boolean seam has a leak path along the seam.
    """
    if cord not in CORD_TABLE and (groove_width is None or depth is None):
        raise FeatureError(
            f"cord {cord} is not in the table {sorted(CORD_TABLE)}; "
            "pass groove_width= and depth= to use a non-standard cord"
        )
    tw, td = CORD_TABLE.get(cord, (0.0, 0.0))
    w = tw if groove_width is None else groove_width
    d = td if depth is None else depth
    if w <= 0 or d <= 0:
        raise FeatureError(f"groove width/depth must be positive, got {w}/{d}")
    pl = _as_plane(plane)

    if shape == "rect":
        if length <= 0 or width <= 0:
            raise FeatureError("rect groove needs positive length and width")
        r = style.plan_radius(length, width) if radius is None else radius
        r = max(r, w)  # the groove must be able to turn its own corner
        if min(length, width) <= w:
            raise FeatureError(f"a {w} mm groove does not fit a {length} x {width} centreline")
        outer = _prism(_offset_plane(pl, dn=0.01), length + w, width + w, r + w / 2, -(d + 0.01))
        inner = _prism(
            _offset_plane(pl, dn=0.02), length - w, width - w, max(r - w / 2, 0.1), -(d + 0.03)
        )
        cut = outer.cut(inner)
        path = 2 * (length - 2 * r) + 2 * (width - 2 * r) + 2 * math.pi * r
    elif shape == "circle":
        if diameter <= w:
            raise FeatureError(f"circle groove diameter {diameter} must exceed width {w}")
        origin = pl.origin + pl.zDir * 0.01
        outer = cq.Solid.makeCylinder(diameter / 2 + w / 2, d + 0.01, origin, pl.zDir * -1.0)
        inner = cq.Solid.makeCylinder(
            diameter / 2 - w / 2, d + 0.03, origin + pl.zDir * 0.01, pl.zDir * -1.0
        )
        cut = outer.cut(inner)
        path = math.pi * diameter
    else:
        raise FeatureError(f"groove shape must be rect/circle, got {shape!r}")

    cord_area = math.pi * cord**2 / 4
    return ORingGroove(
        cut=cut,
        plane=pl,
        cord_dia=cord,
        groove_width=w,
        groove_depth=d,
        path_length=path,
        squeeze_pct=round((cord - d) / cord * 100, 1),
        fill_pct=round(cord_area / (w * d) * 100, 1),
    )


def drip_edge(
    *,
    length: float,
    projection: float = 5.0,
    thickness: float = 3.0,
    shed_deg: float = 8.0,
    kerf: float = 1.2,
    kerf_depth: float = 0.8,
    radius: float | None = None,
    plane: cq.Plane | str = "XY",
    style: Style = STYLE,
) -> cq.Workplane:
    """
    An overhang that makes water let go before it reaches the aperture below.

    Two things do the work. The shed angle tips the top surface outward so
    nothing pools, and the kerf on the underside breaks surface tension - water
    running back along the soffit reaches the groove and drips instead of
    wicking to the wall and down over the connector. A flat lip with no kerf is
    decoration; this is not.

    Built in the given plane's frame: it projects along +Z (out of the wall),
    spans `length` along +X, and sheds toward -Y ("down" on a side face).
    Union it onto the wall.
    """
    if length <= 0 or projection <= 0 or thickness <= 0:
        raise FeatureError(
            f"drip_edge needs positive length/projection/thickness, "
            f"got {length}/{projection}/{thickness}"
        )
    drop = projection * math.tan(math.radians(shed_deg))
    pts = [
        (0.0, 0.0),
        (-drop, projection),
        (-drop - thickness, projection),
        (-thickness, 0.0),
    ]
    lip = cq.Workplane("YZ").polyline(pts).close().extrude(length).val()
    lip = lip.translate((-length / 2, 0, 0))

    if kerf > 0 and kerf_depth > 0:
        z = projection - kerf - 0.6
        if z > 0.5:
            y_bottom = -thickness - drop * (z / projection)
            groove = cq.Solid.makeBox(
                length + 2.0,
                kerf_depth,
                kerf,
                cq.Vector(-length / 2 - 1.0, y_bottom, z),
            )
            lip = lip.cut(groove)

    brk = min(style.edge_break(length), projection * 0.25) if radius is None else radius
    if brk > 0.05:
        try:
            lip = _shape(_wp(lip).edges("|X").chamfer(min(brk, thickness * 0.3)))
        except Exception:
            pass  # a lone-solid chamfer that will not take is not worth failing over
    return _wp(_place(lip, _as_plane(plane)))


# --------------------------------------------------------------------------- #
# 9. identity marks
# --------------------------------------------------------------------------- #


def emblem(
    solid,
    face: cq.Plane | str | cq.Face = ">Z",
    *,
    motif: str = "rings",
    diameter: float = 20.0,
    relief: float | None = None,
    rings: int = 3,
    line_width: float = 0.9,
    center: tuple[float, float] = (0.0, 0.0),
    style: Style = STYLE,
) -> cq.Workplane:
    """
    One shallow identity mark: concentric rings, a crosshair, or both.

    At most one emblem per face and never more than ~1 mm of relief. Depth is
    what separates a machined identity detail from a novelty: past a millimetre
    it stops reading as a mark on a surface and starts reading as a feature
    that must have a function, which it does not.

    Negative `relief` engraves instead of embossing. motif: "rings",
    "crosshair", "target".
    """
    rel = style.emblem_relief if relief is None else relief
    if abs(rel) > style.emblem_relief_max + 1e-9:
        raise FeatureError(
            f"emblem relief {rel} exceeds the {style.emblem_relief_max} mm limit - "
            "an emblem is a surface mark, not a feature"
        )
    if diameter <= 0 or line_width <= 0:
        raise FeatureError("emblem needs a positive diameter and line width")
    plane = face_plane(solid, face)
    base = _offset_plane(plane, du=center[0], dv=center[1])
    # embossed marks start EMBED below the face so the fuse is a real overlap;
    # engraved ones start EMBED above it so the cut breaks the surface cleanly
    up = _offset_plane(base, dn=-EMBED if rel > 0 else EMBED)
    h = abs(rel) + EMBED

    parts: list[cq.Shape] = []
    if motif in ("rings", "target"):
        for i in range(rings):
            r_out = diameter / 2 * (1 - i / max(rings, 1))
            r_in = r_out - line_width
            if r_in <= 0.05:
                continue
            o = cq.Solid.makeCylinder(r_out, h, up.origin, up.zDir * (1 if rel > 0 else -1))
            n = cq.Solid.makeCylinder(
                r_in, h + 0.02, up.origin - up.zDir * 0.01, up.zDir * (1 if rel > 0 else -1)
            )
            parts.append(o.cut(n))
    if motif in ("crosshair", "target"):
        arm = diameter / 2 * (1.15 if motif == "crosshair" else 0.55)
        for ang in (0.0, 90.0):
            bar = (
                cq.Workplane("XY")
                .transformed(rotate=(0, 0, ang))
                .rect(2 * arm, line_width)
                .extrude(h if rel > 0 else -h)
                .val()
            )
            parts.append(_place(bar, up))
    if motif not in ("rings", "crosshair", "target"):
        raise FeatureError(f"motif must be rings/crosshair/target, got {motif!r}")
    if not parts:
        raise FeatureError("emblem produced no geometry - diameter too small for line_width")

    mark = _fuse(parts)
    if rel > 0:
        return _add(solid, mark, "emblem", welded=True)
    return _cut(solid, mark, "emblem")


def text_mark(
    solid,
    face: cq.Plane | str | cq.Face = ">Z",
    *,
    text: str,
    size: float = 8.0,
    relief: float | None = None,
    center: tuple[float, float] = (0.0, 0.0),
    font: str | None = None,
    font_path: str | None = None,
    rotate_deg: float = 0.0,
    style: Style = STYLE,
    strict: bool = False,
) -> cq.Workplane:
    """
    An embossed or engraved wordmark, and it degrades instead of crashing.

    cq.text() depends on fonts present on the machine, so it can fail on a CI
    box that built the same part fine locally. A missing typeface must not take
    a whole enclosure with it: on failure this warns and returns the solid
    unchanged, so the part still builds and the miss is visible in the log.
    Pass `strict=True` where the mark is contractual and silence would be worse.
    """
    rel = style.emblem_relief if relief is None else relief
    if abs(rel) > style.emblem_relief_max + 1e-9:
        raise FeatureError(f"text relief {rel} exceeds {style.emblem_relief_max} mm")
    if not text:
        return _wp(solid)
    plane = face_plane(solid, face)
    base = _offset_plane(plane, du=center[0], dv=center[1])

    try:
        kwargs = {}
        if font:
            kwargs["font"] = font
        if font_path:
            kwargs["fontPath"] = font_path
        h = abs(rel) + EMBED
        glyphs = (
            cq.Workplane("XY")
            .transformed(rotate=(0, 0, rotate_deg))
            .text(text, size, h if rel > 0 else -h, combine=False, **kwargs)
        )
        marks = glyphs.vals()
        if not marks:
            raise FeatureError("text produced no glyphs")
        seat = _offset_plane(base, dn=-EMBED if rel > 0 else EMBED)
        mark = _place(_fuse(marks), seat)
    except Exception as exc:
        if strict:
            raise FeatureError(f"text mark {text!r} failed: {exc}") from None
        warnings.warn(
            f"text_mark({text!r}) skipped - {type(exc).__name__}: {exc}. "
            "The part is unchanged; check fonts on this machine.",
            RuntimeWarning,
            stacklevel=2,
        )
        return _wp(solid)

    try:
        if rel > 0:
            return _add(solid, mark, "text mark", welded=True)
        return _cut(solid, mark, "text mark")
    except Exception as exc:
        if strict:
            raise FeatureError(f"text mark {text!r} boolean failed: {exc}") from None
        warnings.warn(f"text_mark({text!r}) boolean failed: {exc}", RuntimeWarning, stacklevel=2)
        return _wp(solid)


# --------------------------------------------------------------------------- #
# 10. composition - the order of operations, mechanically enforced
# --------------------------------------------------------------------------- #


class Build:
    """
    A pipeline that will not let you build a part in an order the kernel hates.

    Agents do not usually fail here by choosing a bad feature; they fail by
    choosing a good feature at the wrong moment - a fillet after a union, a
    pocket after the holes. Those produce "BRep_API: command not done" with no
    hint of which operation was at fault. `Build` gives the failure a name
    before it reaches OCCT.

    Phases run in this order and never backwards (see the module docstring for
    why each one sits where it does):

        base -> boolean -> pocket -> rib -> hole -> break

    `pocket` and `rib` share a rank, so they may interleave freely: pocket the
    front face, rib it, pocket the rear face, rib that. Nothing about that is
    unsafe - each rib field is clipped to its own pocket and they never meet -
    and forbidding it would make the guard something to work around rather than
    something to rely on. Everything else is strictly monotonic, which is what
    catches the two orderings that actually break the kernel: a pocket cut
    after the holes are in (face selectors go ambiguous, cutters clip
    counterbores into slivers) and an edge break after anything at all.

    Usage:

        b = Build(rounded_box(120, 90, 40), "stock")
        b.boolean(lambda s: s.union(other), "lid_lip")
        p = b.pocket(lambda s: recessed_panel(s, ">Z", frame=10), "panel")
        b.rib(lambda s: s.union(rib_field(p, "chevron").solid), "ribs")
        b.hole(lambda s: counterbore_at(s, pts, plane=top), "lid_screws")
        part = b.result

    A step callable takes the current Workplane and returns either a Workplane
    or a result record with a `.solid` (Pocket, ConnectorLand, Plate ...), so
    the builders in this module drop straight in.

    `stages()` yields (name, workplane) for every completed step, which is
    exactly the protocol lib/debug_build.py bisects on - so a part written with
    Build gets stage bisection for free.
    """

    PHASES: tuple[str, ...] = ("base", "boolean", "pocket", "rib", "hole", "break")
    RANKS: dict[str, int] = {
        "base": 0,
        "boolean": 1,
        "pocket": 2,
        "rib": 2,
        "hole": 3,
        "break": 4,
    }

    def __init__(self, solid, name: str = "base", style: Style = STYLE) -> None:
        self.style = style
        self._solid = _wp(solid)
        self._phase = "base"
        self._stages: list[tuple[str, cq.Workplane]] = [(name, self._solid)]

    # ---- core ------------------------------------------------------------ #

    def step(self, phase: str, fn: Callable, name: str | None = None):
        """Run one step in `phase`, refusing to go backwards through PHASES."""
        if phase not in self.RANKS:
            raise BuildOrderError(f"unknown phase {phase!r}; expected one of {self.PHASES}")
        if self.RANKS[phase] < self.RANKS[self._phase]:
            raise BuildOrderError(
                f"cannot run a {phase!r} step after {self._phase!r} - "
                f"the order is {' -> '.join(self.PHASES)}. "
                "Move this step earlier, or bake the feature into the base profile."
            )
        before = len(_shape(self._solid).Solids())
        out = fn(self._solid)
        solid = getattr(out, "solid", out)
        self._solid = _wp(solid)
        after = len(_shape(self._solid).Solids())
        if after > before:
            warnings.warn(
                f"stage {name or phase!r} left {after} disjoint solids (was {before}). "
                "Something added is only touching the part, not overlapping it - it "
                "will re-import as a loose body. Sink it into the face it sits on.",
                RuntimeWarning,
                stacklevel=3,
            )
        self._phase = phase
        self._stages.append((name or phase, self._solid))
        return out

    # ---- phase shorthands ------------------------------------------------ #

    def boolean(self, fn: Callable, name: str | None = None):
        """Union or cut another solid in."""
        return self.step("boolean", fn, name)

    def pocket(self, fn: Callable, name: str | None = None):
        """Cut a recess or lightening pocket. Returns the Pocket record."""
        return self.step("pocket", fn, name)

    def rib(self, fn: Callable, name: str | None = None):
        """Union rib or fin material back in."""
        return self.step("rib", fn, name)

    def hole(self, fn: Callable, name: str | None = None):
        """Drill counterbores, taps, apertures."""
        return self.step("hole", fn, name)

    def edge_break(self, fn: Callable, name: str | None = None):
        """Late chamfers - only on edges no boolean created."""
        return self.step("break", fn, name)

    # ---- output ---------------------------------------------------------- #

    @property
    def result(self) -> cq.Workplane:
        return self._solid

    @property
    def phase(self) -> str:
        return self._phase

    def stages(self):
        """Yield (name, workplane) per completed step - the build_stages protocol."""
        yield from self._stages

    def report(self) -> dict:
        """Volume and face count per stage, for logs and design review."""
        out = []
        for name, wp in self._stages:
            shape = _shape(wp)
            out.append(
                {
                    "stage": name,
                    "volume_mm3": round(sum(abs(s.Volume()) for s in shape.Solids()), 3),
                    "faces": len(shape.Faces()),
                    "solids": len(shape.Solids()),
                }
            )
        return {"phase": self.phase, "stages": out}
