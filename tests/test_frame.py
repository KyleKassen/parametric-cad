"""
The ruler itself: what `lib/frame.py` promises about the frame it returns.

tests/test_invariance.py asserts the CONSEQUENCE - that a score does not move
when the part does. This file asserts the CAUSE, one property at a time, so a
regression in the frame names itself instead of arriving as a two-point wobble
in eight metrics.

The properties, in the order they matter:

1. An axis-aligned part gets the world axes back, EXACTLY. This is what let the
   frame land without recalibrating every score in the repo, and it is the one
   that must hold to the last bit rather than to a tolerance.
2. Extents, diagonal and projected areas are invariant under rigid motion.
3. A part states its own basis, and the report can name it: `faces` when the
   surfaces fix all three axes, `axis` when they fix one, `obb` when they fix
   none, `world` only when OCCT itself failed.
4. A body of revolution's in-plane pair comes from the part's own off-axis
   features rather than from a tessellation - the case the oriented bounding
   box gets wrong, and the reason `_inplane_marks` exists.

Units: mm.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import cadquery as cq
import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.frame import Frame, frame_record, reference_frame  # noqa: E402

ROTATIONS = [
    ("z5", (0, 0, 1), 5.0),
    ("z37", (0, 0, 1), 37.0),
    ("x30", (1, 0, 0), 30.0),
    ("oblique30", (1, 1, 1), 30.0),
    ("oblique77", (0.3, -0.7, 0.5), 77.0),
]
TRANSLATIONS = [
    ("t_awkward", (13.7, -4.2, 91.3)),
    ("t_far", (500.0, -500.0, 500.0)),
    ("t_absurd", (5000.0, 5000.0, -5000.0)),
]


def worked_box() -> cq.Shape:
    """A prismatic housing: plan radii, a hole grid, a broken lid rim."""
    return (
        cq.Workplane("XY")
        .box(150, 90, 34)
        .edges("|Z")
        .fillet(6)
        .faces(">Z")
        .workplane()
        .rarray(40, 30, 3, 2)
        .hole(5)
        .edges(">Z")
        .chamfer(0.5)
        .val()
    )


def turned_hub() -> cq.Shape:
    """A flanged hub: one dominant direction, and a six-hole bolt circle."""
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


def plain_tube() -> cq.Shape:
    """Nothing off its axis at all: the case where no in-plane mark exists."""
    return cq.Workplane("XY").circle(20).extrude(60).faces(">Z").workplane().hole(28).val()


def sphere() -> cq.Shape:
    """No planar face and no axis: the oriented bounding box's own case."""
    return cq.Workplane("XY").sphere(25).val()


SHAPES = {
    "worked_box": worked_box,
    "turned_hub": turned_hub,
    "plain_tube": plain_tube,
}


# --------------------------------------------------------------------------- #
# 1. an axis-aligned part is measured exactly where it always was
# --------------------------------------------------------------------------- #
def test_an_axis_aligned_part_keeps_the_world_axes_exactly():
    """
    The property the whole port rests on. If this drifts by microns then every
    calibrated number in tests/design_corpus.py drifts with it, and the frame
    stops being a change that can be reasoned about.
    """
    frame = reference_frame(worked_box())
    assert frame.basis == "faces"
    assert frame.is_world_aligned()
    for axis, expected in zip(frame.axes, ((1, 0, 0), (0, 1, 0), (0, 0, 1))):
        assert (axis.x, axis.y, axis.z) == pytest.approx(expected, abs=1e-12)
    # ordered by extent, longest first - and equal to the world bounding box
    assert frame.size == pytest.approx((150.0, 90.0, 34.0), abs=1e-9)
    bb = worked_box().BoundingBox()
    assert (bb.xlen, bb.ylen, bb.zlen) == pytest.approx(frame.size, abs=1e-9)


def test_the_frame_box_projected_area_matches_the_bounding_box_on_an_aligned_part():
    frame = reference_frame(worked_box())
    x, y, z = frame.size
    assert frame.projected_area(cq.Vector(0, 0, 1)) == pytest.approx(x * y)
    assert frame.projected_area(cq.Vector(1, 0, 0)) == pytest.approx(y * z)
    assert frame.surface == pytest.approx(2.0 * (x * y + y * z + z * x))


# --------------------------------------------------------------------------- #
# 2. rigid motion does not change the ruler
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", sorted(SHAPES))
def test_extents_survive_rotation(name):
    base = SHAPES[name]()
    reference = reference_frame(base)
    for label, axis, angle in ROTATIONS:
        moved = reference_frame(base.rotate((0, 0, 0), axis, angle))
        assert moved.size == pytest.approx(reference.size, abs=5e-4), (
            f"{name} at {label}: the part's own extents changed when the file did"
        )
        assert moved.diagonal == pytest.approx(reference.diagonal, abs=5e-4)


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_extents_survive_translation(name):
    base = SHAPES[name]()
    reference = reference_frame(base)
    for label, offset in TRANSLATIONS:
        moved = reference_frame(base.translate(offset))
        assert moved.size == pytest.approx(reference.size, abs=1e-6), (
            f"{name} at {label}: a part 500 mm from the origin is the same part"
        )


def _rotated(v: cq.Vector, axis: tuple, degrees: float) -> cq.Vector:
    """Rodrigues, because cq.Vector rotates shapes and not itself."""
    k = cq.Vector(*axis).normalized()
    theta = math.radians(degrees)
    return (
        v * math.cos(theta)
        + k.cross(v) * math.sin(theta)
        + k * (k.dot(v) * (1.0 - math.cos(theta)))
    )


#: How closely each shape's frame must follow a rotation, and why it is not
#: always all three axes. A prismatic part has no continuous symmetry, so every
#: axis is pinned. A hub's in-plane pair is pinned only up to the symmetry of its
#: own bolt circle - six marks 60 degrees apart, and choosing a different one
#: describes the same solid. A plain tube's in-plane pair is not pinned at all,
#: because the tube is unchanged by any rotation about its axis; only the axis
#: itself is a claim about the part.
FOLLOWS = {
    "worked_box": (0, 1, 2),
    "turned_hub": (2,),  # the 80 x 80 x 30 hub's short axis IS the revolution axis
    "plain_tube": (0,),  # the 40 x 40 x 60 tube's long axis
}


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_the_frame_turns_with_the_part(name):
    """
    Not merely "the extents are the same": the axes the part actually FIXES must
    follow the rotation, or every layout measurement taken in the frame is taken
    in the wrong one.
    """
    base = SHAPES[name]()
    reference = reference_frame(base)
    for label, axis, angle in ROTATIONS:
        moved = reference_frame(base.rotate((0, 0, 0), axis, angle))
        for i in FOLLOWS[name]:
            turned = _rotated(reference.axes[i], axis, angle)
            aligned = abs(turned.dot(moved.axes[i]))
            assert aligned > math.cos(math.radians(1.5)), (
                f"{name} at {label}: frame axis {i} is "
                f"{math.degrees(math.acos(min(1.0, aligned))):.2f} deg from where the "
                f"rotation put it"
            )


def test_a_bolt_circles_in_plane_axis_follows_the_part_up_to_its_own_symmetry():
    """
    The hub's in-plane axis is not free: it is one of the six directions its bolt
    circle marks out, so a rotation must move it by the rotation angle modulo the
    array's 60 degree symmetry. Under the oriented bounding box it was free, and
    a 5 degree turn moved feature_composition by 52.8 points.
    """
    base = turned_hub()
    reference = reference_frame(base)
    for label, axis, angle in (("z5", (0, 0, 1), 5.0), ("z37", (0, 0, 1), 37.0)):
        moved = reference_frame(base.rotate((0, 0, 0), axis, angle))
        turned = _rotated(reference.axes[0], axis, angle)
        offset = math.degrees(math.acos(min(1.0, abs(turned.dot(moved.axes[0])))))
        # unsigned directions, so the marks repeat every 60 degrees and the
        # nearest one is never more than 30 degrees away
        residual = min(abs(offset - 60.0 * k) for k in range(4))
        assert residual < 1.5, (
            f"at {label}: the in-plane axis is {offset:.2f} deg from where the rotation "
            f"put it, which is {residual:.2f} deg off the nearest bolt-circle mark"
        )


def test_translation_does_not_move_a_body_of_revolutions_in_plane_axis():
    """
    The defect `_inplane_marks` exists for. A hub states its axis exactly and
    says nothing about the two directions across it, so those used to come from
    OCCT's oriented bounding box - which reads a tessellation and therefore
    reads differently as the coordinates grow. Measured before the fix: 0.10 deg
    of wander at 500 mm and a 90 degree flip of which in-plane axis came back
    first, which on a six-hole bolt circle is a different measuring basis for an
    unchanged part.
    """
    base = turned_hub()
    reference = reference_frame(base)
    assert reference.basis == "axis"
    for label, offset in TRANSLATIONS:
        moved = reference_frame(base.translate(offset))
        for i, (a, b) in enumerate(zip(reference.axes, moved.axes)):
            assert abs(a.dot(b)) > 1.0 - 1e-9, (
                f"at {label}: frame axis {i} moved by "
                f"{math.degrees(math.acos(min(1.0, abs(a.dot(b))))):.4f} deg for a "
                f"pure translation"
            )


# --------------------------------------------------------------------------- #
# 3. the frame says what it is
# --------------------------------------------------------------------------- #
def test_the_basis_is_reported_and_names_what_fixed_the_frame():
    assert reference_frame(worked_box()).basis == "faces"
    assert reference_frame(turned_hub()).basis == "axis"
    assert reference_frame(plain_tube()).basis == "axis"
    assert reference_frame(sphere()).basis == "obb"


def test_a_weaker_basis_always_states_a_reason():
    """A fallback with no reason is an unfixed measurement wearing a badge."""
    for build in (turned_hub, plain_tube, sphere):
        frame = reference_frame(build())
        assert frame.basis != "faces"
        assert frame.fallback_reason, f"{build.__name__} fell back without saying why"
        assert len(frame.fallback_reason) > 30


def test_a_part_with_no_in_plane_feature_says_so_rather_than_inventing_one():
    """
    A plain tube genuinely has no direction across its axis. The frame is
    allowed to pick one - it has to - but it must not claim the part chose it.
    """
    frame = reference_frame(plain_tube())
    assert "not fixed by any surface or feature" in (frame.fallback_reason or "")
    hub = reference_frame(turned_hub())
    assert "set by the nearest feature" in (hub.fallback_reason or "")


def test_the_record_is_publishable_and_carries_no_path():
    record = frame_record(reference_frame(turned_hub()))
    assert record["basis"] == "axis"
    assert len(record["axes"]) == 3 and len(record["size_mm"]) == 3
    assert record["world_aligned"] in (True, False)
    assert "explained" in record
    blob = repr(record)
    assert "/" not in blob.replace("mm", ""), "the frame record must not carry a filesystem path"


# --------------------------------------------------------------------------- #
# 4. the frame's own coordinate conversions
# --------------------------------------------------------------------------- #
def test_frame_coordinates_round_trip():
    frame = reference_frame(worked_box().rotate((0, 0, 0), (1, 1, 1), 30))
    for point in (cq.Vector(0, 0, 0), cq.Vector(12.5, -3.0, 40.0)):
        local = frame.to_frame_point(point)
        back = frame.to_world_point(local)
        assert (back.x, back.y, back.z) == pytest.approx((point.x, point.y, point.z), abs=1e-9)


def test_the_frame_is_orthonormal_and_right_handed():
    for build in (worked_box, turned_hub, plain_tube, sphere):
        frame: Frame = reference_frame(build())
        a, b, c = frame.axes
        for axis in (a, b, c):
            assert axis.Length == pytest.approx(1.0, abs=1e-9)
        assert a.dot(b) == pytest.approx(0.0, abs=1e-9)
        assert b.dot(c) == pytest.approx(0.0, abs=1e-9)
        assert a.cross(b).dot(c) == pytest.approx(1.0, abs=1e-9)
        assert frame.size[0] >= frame.size[1] >= frame.size[2] - 1e-9


def test_extents_of_another_solid_are_taken_in_this_frame():
    """
    What `_diff_extent` needs: a mirror difference's lump is judged sliver or
    chunk by its aspect ratio, and an aspect taken from the world box is a fact
    about the file.
    """
    frame = reference_frame(worked_box())
    slab = cq.Workplane("XY").box(60, 40, 2).val()
    assert sorted(frame.extents_of(slab), reverse=True) == pytest.approx(
        [60.0, 40.0, 2.0], abs=1e-9
    )
    turned = reference_frame(worked_box().rotate((0, 0, 0), (0, 0, 1), 45))
    rotated_slab = slab.rotate((0, 0, 0), (0, 0, 1), 45)
    assert sorted(turned.extents_of(rotated_slab), reverse=True) == pytest.approx(
        [60.0, 40.0, 2.0], abs=1e-6
    ), "a slab turned with the part is still the same slab"
