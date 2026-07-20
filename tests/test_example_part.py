"""
Tests for the example mounting plate.

These validate that parametric changes produce geometrically valid parts.
Run with: make test  (or: pytest tests/)
"""

import sys
from pathlib import Path

# Add the project root to sys.path so we can import parts
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_example_part_builds():
    """The example part should build without errors."""
    from parts.example_part.model import create_part

    result = create_part()
    assert result is not None

    # The result should be a valid solid
    solid = result.val()
    assert solid is not None


def test_example_part_is_solid():
    """The result should be a proper solid (not a shell or wire)."""
    from parts.example_part.model import create_part

    result = create_part()
    solid = result.val()

    # Check it has volume (i.e., it's a real 3D solid)
    volume = solid.Volume()
    assert volume > 0, f"Expected positive volume, got {volume}"


def test_example_part_dimensions():
    """The bounding box should match the declared dimensions (within tolerance)."""
    from parts.example_part.model import create_part, load_params

    params = load_params()
    dims = params["dimensions"]

    result = create_part(params)
    bb = result.val().BoundingBox()

    # Bounding box should match declared dimensions (fillets shrink it slightly)
    tolerance = 0.1  # mm
    assert abs(bb.xlen - dims["length"]) < tolerance, (
        f"X dimension: expected ~{dims['length']}, got {bb.xlen}"
    )
    assert abs(bb.ylen - dims["width"]) < tolerance, (
        f"Y dimension: expected ~{dims['width']}, got {bb.ylen}"
    )
    assert abs(bb.zlen - dims["thickness"]) < tolerance, (
        f"Z dimension: expected ~{dims['thickness']}, got {bb.zlen}"
    )


def test_example_part_custom_params():
    """Building with overridden parameters should work."""
    from parts.example_part.model import create_part, load_params

    params = load_params()

    # Double the thickness
    params["dimensions"]["thickness"] = 12.0

    result = create_part(params)
    bb = result.val().BoundingBox()

    tolerance = 0.1
    assert abs(bb.zlen - 12.0) < tolerance, (
        f"Z dimension: expected ~12.0, got {bb.zlen}"
    )


def test_example_part_has_holes():
    """
    The part should have fewer faces than a plain box (holes add faces).
    A plain box has 6 faces; holes and fillets add more.
    """
    from parts.example_part.model import create_part

    result = create_part()
    solid = result.val()

    face_count = len(solid.Faces())
    # A box has 6 faces. Our part has holes and fillets, so it should have more.
    assert face_count > 6, (
        f"Expected more than 6 faces (holes + fillets), got {face_count}"
    )
