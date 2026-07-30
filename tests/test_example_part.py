"""
Tests for the example sensor enclosure - the `make new-part` scaffold.

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
    from parts._template.model import create_part

    result = create_part()
    assert result is not None

    # The result should be a valid solid
    solid = result.val()
    assert solid is not None


def test_example_part_is_solid():
    """The result should be a proper solid (not a shell or wire)."""
    from parts._template.model import create_part

    result = create_part()
    solid = result.val()

    # Check it has volume (i.e., it's a real 3D solid)
    volume = solid.Volume()
    assert volume > 0, f"Expected positive volume, got {volume}"


def test_example_part_dimensions():
    """The bounding box should match the declared dimensions (within tolerance)."""
    from parts._template.model import create_part, load_params

    params = load_params()
    dims = params["dimensions"]

    result = create_part(params)
    bb = result.val().BoundingBox()

    # X is longer than the declared envelope: the connector land stands proud
    # of the +X face. Bounding boxes measure the artifact, not the intent -
    # spec.json records the same 153.0 for the same reason.
    expected_x = dims["length"] + params["features"]["connector"]["land_raised"]

    tolerance = 0.1  # mm
    assert abs(bb.xlen - expected_x) < tolerance, (
        f"X dimension: expected ~{expected_x}, got {bb.xlen}"
    )
    assert abs(bb.ylen - dims["width"]) < tolerance, (
        f"Y dimension: expected ~{dims['width']}, got {bb.ylen}"
    )
    assert abs(bb.zlen - dims["height"]) < tolerance, (
        f"Z dimension: expected ~{dims['height']}, got {bb.zlen}"
    )


def test_example_part_custom_params():
    """Building with overridden parameters should work."""
    from parts._template.model import create_part, load_params

    params = load_params()

    # Raise the enclosure. Nothing dimensional is hardcoded in model.py, so a
    # params-only change has to propagate all the way to the bounding box.
    params["dimensions"]["height"] = 44.0

    result = create_part(params)
    bb = result.val().BoundingBox()

    tolerance = 0.1
    assert abs(bb.zlen - 44.0) < tolerance, f"Z dimension: expected ~44.0, got {bb.zlen}"


def test_example_part_has_holes():
    """
    The part should have fewer faces than a plain box (holes add faces).
    A plain box has 6 faces; holes and fillets add more.
    """
    from parts._template.model import create_part

    result = create_part()
    solid = result.val()

    face_count = len(solid.Faces())
    # A box has 6 faces. Our part has holes and fillets, so it should have more.
    assert face_count > 6, f"Expected more than 6 faces (holes + fillets), got {face_count}"
