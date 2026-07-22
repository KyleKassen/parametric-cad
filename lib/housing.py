"""
Keep-out / silhouette primitives for wrapping housings around imported parts.

Philosophy: never re-measure a part by hand. Import its STEP solid (the B-rep
is exact), derive a clearance "keep-out" volume from the geometry itself, and
subtract that from housing stock. Because the part's own solid drives the
cavity, handedness comes along for free — a mirrored vendor variant (OZ510 TX
vs RX) produces a mirrored cavity automatically instead of a wrong-sided one.

Building blocks
---------------
silhouette(shape, axis)       2D outline of the shape projected along an axis:
                              tessellate -> union the projected triangles
                              (shapely) -> fill interior holes -> buffer by the
                              clearance. This is the "silhouette" concept done
                              on exact geometry instead of traced pixels.
keepout_prism(shape, axis)    that silhouette extruded over the shape's span —
                              an insertable cavity (the part drops in along the
                              axis), ideal for milled pockets and printed trays.
prism_from_silhouette(...)    extrude any silhouette between two stations —
                              e.g. a connector's silhouette pushed through a
                              wall as a perfectly-shaped panel cutout.
interference(a, b)            boolean overlap volume in mm^3, for fit checks.

Tessellation chord error is absorbed by the clearance: keep clearance well
above ~0.2 mm (coarse tessellation under-sizes curved silhouettes slightly).

Units: mm.
"""

from __future__ import annotations

from functools import reduce

import cadquery as cq
from shapely import union_all
from shapely.geometry import Polygon

# projection-plane (u, v) coordinate indices and extrusion vector per axis
_UV = {"X": (1, 2), "Y": (0, 2), "Z": (0, 1)}
_AXIS_IDX = {"X": 0, "Y": 1, "Z": 2}


def _shape(obj) -> cq.Shape:
    """Accept a Workplane or a Shape."""
    return obj.val() if hasattr(obj, "val") else obj


def _embed(u: float, v: float, axis: str, station: float) -> tuple:
    """Lift 2D projection coords back into 3D at a station along the axis."""
    if axis == "Z":
        return (u, v, station)
    if axis == "Y":
        return (u, station, v)
    return (station, u, v)


def silhouette(
    shape,
    axis: str = "Z",
    clearance: float = 0.0,
    tess_tol: float = 0.8,
    ang_tol: float = 0.5,
    simplify_tol: float = 0.05,
):
    """
    The shape's true outline projected along +axis, as a shapely (Multi)Polygon.

    Interior holes are filled (a cavity must clear them anyway) and the result
    is grown by `clearance`. tess_tol/ang_tol trade accuracy for speed; the
    chord error they introduce is far below any practical clearance.
    """
    shape = _shape(shape)
    if axis not in _UV:
        raise ValueError(f"axis must be one of X/Y/Z, got {axis!r}")
    iu, iv = _UV[axis]

    verts, tris = shape.tessellate(tess_tol, ang_tol)
    pts = [(v.x, v.y, v.z) for v in verts]

    polys = []
    for a, b, c in tris:
        tri = tuple((pts[i][iu], pts[i][iv]) for i in (a, b, c))
        # cross-product area — skip edge-on (degenerate) triangles
        area2 = abs((tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1])
                    - (tri[2][0] - tri[0][0]) * (tri[1][1] - tri[0][1]))
        if area2 > 1e-9:
            polys.append(Polygon(tri))

    merged = union_all(polys)
    parts = [merged] if merged.geom_type == "Polygon" else list(merged.geoms)
    filled = union_all([Polygon(p.exterior) for p in parts])  # fill holes
    if clearance:
        filled = filled.buffer(clearance)
    return filled.simplify(simplify_tol)


def prism_from_silhouette(sil, axis: str = "Z", start: float = 0.0,
                          end: float = 10.0) -> cq.Shape:
    """Extrude a silhouette (from silhouette()) between two stations on the axis."""
    geoms = [sil] if sil.geom_type == "Polygon" else list(sil.geoms)
    height = end - start
    direction = cq.Vector(*_embed(0, 0, axis, height)) - cq.Vector(*_embed(0, 0, axis, 0))

    solids = []
    for g in geoms:
        ring = list(g.exterior.coords)  # closed: first point == last point
        wire = cq.Wire.makePolygon([cq.Vector(*_embed(u, v, axis, start))
                                    for u, v in ring])
        solids.append(cq.Solid.extrudeLinear(wire, [], direction))
    return reduce(lambda a, b: a.fuse(b), solids)


def keepout_prism(
    shape,
    axis: str = "Z",
    clearance: float = 1.0,
    extend_neg: float = 0.0,
    extend_pos: float = 0.0,
    tess_tol: float = 0.8,
) -> cq.Shape:
    """
    An insertable keep-out cavity: the shape's silhouette (grown by clearance)
    extruded over its full span along the axis, plus optional extensions —
    e.g. extend_pos up to the lid so the part can be dropped in from above.
    """
    shape = _shape(shape)
    sil = silhouette(shape, axis, clearance=clearance, tess_tol=tess_tol)
    bb = shape.BoundingBox()
    lo = (bb.xmin, bb.ymin, bb.zmin)[_AXIS_IDX[axis]] - clearance - extend_neg
    hi = (bb.xmax, bb.ymax, bb.zmax)[_AXIS_IDX[axis]] + clearance + extend_pos
    return prism_from_silhouette(sil, axis, lo, hi)


def interference(a, b) -> float:
    """Boolean overlap volume between two shapes/workplanes, in mm^3."""
    a, b = _shape(a), _shape(b)
    try:
        return abs(a.intersect(b).Volume())
    except Exception:
        return 0.0
