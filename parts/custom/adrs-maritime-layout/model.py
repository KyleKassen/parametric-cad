"""
ADRS maritime layout — the aluminium scaffold that creates the upper tier(s).

Everything here is stock-section fabrication, deliberately: cut lengths of
extruded angle and channel, plus flat plate shelves with folded lips. No part
needs more than a saw, a drill and a press brake, because this gets built once
in a shop that is not a machine shop.

Frame is the enclosure frame (see layout.py):
    +Y up, subpanel mounting face at Z = -109.22, door at Z = +131.10.

`build_member(spec)` is the entry point layout.py calls for any placement whose
source is "scaffold"; the spec's "kind" selects the primitive below.
"""

from __future__ import annotations

import cadquery as cq

# 6061-T6 stock we are willing to specify
STOCK = {
    "angle_25":   {"leg": 25.0, "t": 3.0},
    "angle_32":   {"leg": 31.75, "t": 3.18},
    "angle_38":   {"leg": 38.1, "t": 3.18},
    "channel_40": {"w": 40.0, "h": 20.0, "t": 3.0},
}

PLATE_T = 3.0        # shelf plate thickness, mm
LIP_H = 20.0         # folded stiffening lip height, mm
BEND_R = 3.0         # inside bend radius, mm


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def angle_bar(length: float, leg: float = 25.0, t: float = 3.0,
              root_r: float = 2.0) -> cq.Workplane:
    """
    L-section bar running along +X, with the corner at the local origin.
    One leg lies in the XY plane (+Y), the other in the XZ plane (+Z).

    Only the re-entrant root is radiused — that is the one real extruded angle
    always has, and filleting the sharp toes as well overconstrains the kernel
    on thin sections.
    """
    profile = (
        cq.Workplane("YZ")
        .polyline([(0, 0), (leg, 0), (leg, t), (t, t), (t, leg), (0, leg)])
        .close()
    )
    bar = profile.extrude(length)
    if root_r:
        root = [
            e for e in bar.edges("|X").vals()
            if abs(e.Center().y - t) < 1e-6 and abs(e.Center().z - t) < 1e-6
        ]
        if root:
            try:
                bar = bar.newObject(root).fillet(min(root_r, t * 0.9))
            except Exception:
                pass  # a sharp root is the conservative shape for a keep-out model
    return bar


def channel_bar(length: float, w: float = 40.0, h: float = 20.0,
                t: float = 3.0) -> cq.Workplane:
    """U-channel running along +X, opening toward +Z, web centred on the origin."""
    profile = (
        cq.Workplane("YZ")
        .polyline([
            (-w / 2, 0), (w / 2, 0), (w / 2, h), (w / 2 - t, h),
            (w / 2 - t, t), (-w / 2 + t, t), (-w / 2 + t, h), (-w / 2, h),
        ])
        .close()
    )
    return profile.extrude(length)


def shelf_plate(width: float, depth: float, t: float = PLATE_T,
                lip: float = LIP_H, lips: str = "both",
                corner_r: float = 6.0) -> cq.Workplane:
    """
    A flat shelf in the XY plane with folded lips turned down (-Z) along its
    +/-Y edges. `lips`: "both" | "front" | "back" | "none".

    Modelled as square-cornered folds — a press brake gives a real radius, but
    for a layout/keep-out model the sharp version is the conservative one.
    """
    plate = (
        cq.Workplane("XY")
        .box(width, depth, t, centered=(True, True, False))
    )
    if corner_r:
        plate = plate.edges("|Z").fillet(corner_r)

    if lips != "none" and lip > 0:
        edges = {"both": (1, -1), "front": (-1,), "back": (1,)}[lips]
        for sy in edges:
            wall = (
                cq.Workplane("XY")
                .box(width, t, lip, centered=(True, True, False))
                .translate((0, sy * (depth / 2 - t / 2), -lip))
            )
            plate = plate.union(wall)
    return plate


def standoff(height: float, od: float = 12.0, id_: float = 4.3) -> cq.Workplane:
    """Hex-equivalent round standoff, drilled through."""
    return (
        cq.Workplane("XY")
        .circle(od / 2).extrude(height)
        .faces(">Z").workplane().hole(id_)
    )


def gusset(size: float = 40.0, t: float = 3.0, hole: float = 0.0) -> cq.Workplane:
    """Triangular brace in the XZ plane, right angle at the origin."""
    tri = (
        cq.Workplane("XZ")
        .polyline([(0, 0), (size, 0), (0, size)])
        .close()
        .extrude(t)
    )
    if hole:
        tri = tri.faces(">Y").workplane().center(size / 3, size / 3).hole(hole)
    return tri


# ---------------------------------------------------------------------------
# Dispatch used by layout.py
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Fasteners — ISO 4762 socket head cap screws, so the model shows real hardware
# ---------------------------------------------------------------------------
#            thread  head_d  head_h  clearance  washer_d  nut_h
SCREWS = {
    "M3": (3.0, 5.5, 3.0, 3.4, 7.0, 2.4),
    "M4": (4.0, 7.0, 4.0, 4.5, 9.0, 3.2),
    "M5": (5.0, 8.5, 5.0, 5.5, 10.0, 4.0),
    "M6": (6.0, 10.0, 6.0, 6.6, 12.0, 5.0),
}


def clearance_dia(size: str) -> float:
    return SCREWS[size][3]


def socket_head_screw(size: str = "M4", length: float = 12.0,
                      washer: bool = True) -> cq.Workplane:
    """
    Socket head cap screw on the +Z axis: head occupies Z = -head_h .. 0, the
    shank runs Z = 0 .. length. Place it with Z=0 on the bearing surface and
    +Z pointing INTO the joint, so the head sits proud on the access side.
    """
    d, hd, hh, _, wd, _ = SCREWS[size]
    s = cq.Workplane("XY").circle(hd / 2).extrude(-hh)
    # hex socket, so it reads as a cap screw rather than a plain pin
    s = s.faces("<Z").workplane().polygon(6, d * 0.62).cutBlind(hh * 0.55)
    s = s.union(cq.Workplane("XY").circle(d / 2).extrude(length))
    if washer:
        s = s.union(
            cq.Workplane("XY").circle(wd / 2).extrude(-1.0).faces(">Z")
            .workplane().hole(SCREWS[size][3])
            .translate((0, 0, 0))
        )
    return s


def standoff_hex(size: str = "M4", height: float = 12.0,
                 across_flats: float = 8.0) -> cq.Workplane:
    """Female-female hex standoff, tapped through — the spacer under every plate."""
    s = cq.Workplane("XY").polygon(6, across_flats / 0.866).extrude(height)
    return s.faces(">Z").workplane().hole(SCREWS[size][0] * 0.82)


def plate_box(dx: float, dy: float, dz: float, corner_r: float = 0.0) -> cq.Workplane:
    """
    A plate stated directly in ENCLOSURE axes — no rotation to reason about.

    Structural members are plates, and a plate is a box; saying so directly
    removes a whole class of orientation error from the placement file. Real
    bend/gusset detail belongs in the fabrication notes, not in a layout model.
    """
    b = cq.Workplane("XY").box(dx, dy, dz, centered=(True, True, False))
    if corner_r and min(dx, dy) > 2 * corner_r:
        axis = {"x": "|X", "y": "|Y", "z": "|Z"}[min(
            (("x", dx), ("y", dy), ("z", dz)), key=lambda kv: kv[1])[0]]
        try:
            b = b.edges(axis).fillet(corner_r)
        except Exception:
            pass
    return b


def drill(shape: cq.Shape, holes: list[dict]) -> cq.Shape:
    """
    Cut holes through a placed shape. Each hole is {x, y, z, dia, axis, depth?}
    in ENCLOSURE coordinates — the same numbers the fastener will use, so a
    plate's holes cannot drift out of line with the part it carries.
    """
    if not holes:
        return shape
    axes = {"X": (1, 0, 0), "Y": (0, 1, 0), "Z": (0, 0, 1)}
    cutters = []
    for h in holes:
        d = axes[h.get("axis", "Z")]
        depth = h.get("depth", 400.0)
        r = h["dia"] / 2.0
        start = cq.Vector(h["x"], h["y"], h["z"]) - cq.Vector(*d) * (depth / 2.0)
        cutters.append(
            cq.Solid.makeCylinder(r, depth, start, cq.Vector(*d))
        )
    cut = cutters[0]
    for c in cutters[1:]:
        cut = cut.fuse(c)
    return shape.cut(cut)


_KINDS = {
    "box": lambda p: plate_box(p["dx"], p["dy"], p["dz"], p.get("corner_r", 0.0)),
    "angle": lambda p: angle_bar(p["length"], p.get("leg", 25.0), p.get("t", 3.0)),
    "channel": lambda p: channel_bar(p["length"], p.get("w", 40.0),
                                     p.get("h", 20.0), p.get("t", 3.0)),
    "shelf": lambda p: shelf_plate(p["width"], p["depth"], p.get("t", PLATE_T),
                                   p.get("lip", LIP_H), p.get("lips", "both"),
                                   p.get("corner_r", 6.0)),
    "standoff": lambda p: standoff(p["height"], p.get("od", 12.0), p.get("id", 4.3)),
    "gusset": lambda p: gusset(p.get("size", 40.0), p.get("t", 3.0), p.get("hole", 0.0)),
    "plate": lambda p: shelf_plate(p["width"], p["depth"], p.get("t", PLATE_T),
                                   0, "none", p.get("corner_r", 6.0)),
}


def build_member(spec: dict) -> cq.Shape:
    """Build one scaffold member from its placement spec."""
    params = spec.get("params", {})
    kind = spec.get("kind")
    if kind not in _KINDS:
        raise ValueError(f"unknown scaffold kind {kind!r}; have {sorted(_KINDS)}")
    wp = _KINDS[kind](params)
    return wp.val() if isinstance(wp, cq.Workplane) else wp


if __name__ == "__main__":
    for name, spec in (
        ("angle 300", {"kind": "angle", "params": {"length": 300}}),
        ("shelf 300x200", {"kind": "shelf", "params": {"width": 300, "depth": 200}}),
        ("channel 300", {"kind": "channel", "params": {"length": 300}}),
    ):
        s = build_member(spec)
        b = s.BoundingBox()
        print(f"  {name:<16} {b.xlen:6.1f} x {b.ylen:6.1f} x {b.zlen:6.1f} mm")
