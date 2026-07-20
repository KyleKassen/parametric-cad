"""
Common geometry helpers shared across parts.

Add reusable parametric building blocks here so individual part scripts
stay clean and focused on their specific geometry.

Units: mm (all dimensions unless noted)
"""

import cadquery as cq


def bolt_pattern_rect(
    workplane: cq.Workplane,
    spacing_x: float,
    spacing_y: float,
    hole_diameter: float,
    counterbore_diameter: float | None = None,
    counterbore_depth: float | None = None,
) -> cq.Workplane:
    """
    Add a rectangular bolt hole pattern centered on the current workplane.

    Parameters
    ----------
    workplane : cq.Workplane
        The workplane to add holes to (should already be on the target face).
    spacing_x, spacing_y : float
        Center-to-center distance between holes in X and Y.
    hole_diameter : float
        Through-hole diameter.
    counterbore_diameter, counterbore_depth : float, optional
        If both are provided, creates counterbored holes instead of plain through holes.
    """
    wp = workplane.rect(spacing_x, spacing_y, forConstruction=True).vertices()

    if counterbore_diameter and counterbore_depth:
        return wp.cboreHole(hole_diameter, counterbore_diameter, counterbore_depth)
    else:
        return wp.hole(hole_diameter)


def fillet_vertical_edges(result: cq.Workplane, radius: float) -> cq.Workplane:
    """Fillet all edges parallel to the Z axis."""
    return result.edges("|Z").fillet(radius)


def chamfer_top_edges(result: cq.Workplane, size: float) -> cq.Workplane:
    """Chamfer all edges on the top face."""
    return result.faces(">Z").edges().chamfer(size)


def mounting_standoff(
    diameter: float,
    height: float,
    hole_diameter: float,
    base_fillet: float = 0.5,
) -> cq.Workplane:
    """
    Create a cylindrical mounting standoff with a through-hole.

    Parameters
    ----------
    diameter : float
        Outer diameter of the standoff.
    height : float
        Total height.
    hole_diameter : float
        Through-hole diameter (e.g. for M3 = 3.4mm clearance).
    base_fillet : float
        Fillet at the base for stress relief.
    """
    result = (
        cq.Workplane("XY")
        .circle(diameter / 2)
        .extrude(height)
        .faces(">Z")
        .workplane()
        .hole(hole_diameter)
    )

    if base_fillet > 0:
        result = result.edges("<Z").fillet(base_fillet)

    return result
