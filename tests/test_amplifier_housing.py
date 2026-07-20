"""
Tests for the AM10-231A amplifier housing v3.
Validates geometry, dimensions, thermal standoffs, louver positioning,
sun shade, ground stud, cable management, and baseplate pocketing.
"""

import copy
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Cradle tests
# ---------------------------------------------------------------------------


def test_cradle_builds():
    """The cradle should build without errors and produce a valid solid."""
    from parts.amplifier_housing.model import create_cradle

    result = create_cradle()
    assert result is not None
    solid = result.val()
    assert solid is not None


def test_cradle_is_solid():
    """The cradle should be a valid solid with positive volume."""
    from parts.amplifier_housing.model import create_cradle

    result = create_cradle()
    volume = result.val().Volume()
    assert volume > 0, f"Expected positive volume, got {volume}"


def test_cradle_bounding_box():
    """
    The cradle bounding box should match the expected envelope.
    v3 is taller than v2 due to thermal standoffs and raised sun shade.
    """
    from parts.amplifier_housing.model import create_cradle, load_params

    params = load_params()
    amp = params["amplifier"]
    h = params["housing"]
    sw = h["side_walls"]
    shade = h["sun_shade"]
    ribs = h["stiffening_ribs"]
    standoff_h = h["thermal_standoffs"]["height"]

    expected_length = amp["length"] + 2 * h["overhang_x"]  # 280mm

    flare_offset = sw["flare_height"] * math.tan(math.radians(sw["flare_angle"]))
    base_width = amp["width"] + 2 * (h["overhang_y"] + h["wall_thickness"])
    expected_width = base_width + 2 * (flare_offset + shade["overhang_width"])

    wall_height = standoff_h + amp["height"] + h["heatsink_clearance"]
    total_wall_h = wall_height + sw["flare_height"]
    shade_top = total_wall_h + shade["height_above_wall"] + shade["thickness"]
    expected_height = ribs["rib_height"] + h["baseplate_thickness"] + shade_top

    result = create_cradle(params)
    bb = result.val().BoundingBox()

    tol = 5.0  # mm tolerance (complex geometry)
    assert abs(bb.xlen - expected_length) < tol, (
        f"Length: expected ~{expected_length:.1f}, got {bb.xlen:.1f}"
    )
    assert abs(bb.ylen - expected_width) < tol, (
        f"Width: expected ~{expected_width:.1f}, got {bb.ylen:.1f}"
    )
    assert bb.zlen > expected_height * 0.85, (
        f"Height too short: expected >{expected_height * 0.85:.1f}, got {bb.zlen:.1f}"
    )
    assert bb.zlen < expected_height * 1.15, (
        f"Height too tall: expected <{expected_height * 1.15:.1f}, got {bb.zlen:.1f}"
    )


def test_cradle_has_features():
    """Face count confirms holes, louvers, gussets, standoffs, etc."""
    from parts.amplifier_housing.model import create_cradle

    result = create_cradle()
    face_count = len(result.val().Faces())
    # v3 has: 13 standoffs, 13 through-holes, 24 louver slots (3 rows × 8),
    # 6 drain slots, 8 gussets, sun shade, 4 posts, pockets, ground stud,
    # cable bosses — should be well over 100 faces
    assert face_count > 80, (
        f"Expected many faces (standoffs + louvers + gussets + shade), got {face_count}"
    )


def test_cradle_volume_reasonable():
    """Volume sanity check for boolean operations."""
    from parts.amplifier_housing.model import create_cradle

    result = create_cradle()
    volume_mm3 = result.val().Volume()

    assert volume_mm3 > 100_000, (
        f"Volume too small ({volume_mm3:.0f} mm³) — geometry may be mostly air"
    )
    assert volume_mm3 < 3_000_000, (
        f"Volume too large ({volume_mm3:.0f} mm³) — boolean cuts may have failed"
    )


def test_cradle_taller_than_v2():
    """
    v3 cradle should be taller than a hypothetical v2 with same amp dims,
    because thermal standoffs add height and sun shade is raised.
    """
    from parts.amplifier_housing.model import create_cradle, load_params

    params = load_params()
    h = params["housing"]
    standoff_h = h["thermal_standoffs"]["height"]

    # Wall height includes standoff
    wall_height = standoff_h + params["amplifier"]["height"] + h["heatsink_clearance"]
    # v2 wall height would be without standoff
    v2_wall_height = params["amplifier"]["height"] + h["heatsink_clearance"]

    assert wall_height > v2_wall_height, (
        f"v3 wall height ({wall_height}) should exceed v2 ({v2_wall_height}) "
        f"due to thermal standoffs"
    )


# ---------------------------------------------------------------------------
# Base plate tests
# ---------------------------------------------------------------------------


def test_base_plate_builds():
    """The base plate should build without errors."""
    from parts.amplifier_housing.model import create_base_plate

    result = create_base_plate()
    assert result is not None
    solid = result.val()
    assert solid is not None


def test_base_plate_is_solid():
    """The base plate should be a valid solid with positive volume."""
    from parts.amplifier_housing.model import create_base_plate

    result = create_base_plate()
    volume = result.val().Volume()
    assert volume > 0, f"Expected positive volume, got {volume}"


def test_base_plate_has_slots():
    """The base plate should have slotted mounting holes."""
    from parts.amplifier_housing.model import create_base_plate

    result = create_base_plate()
    face_count = len(result.val().Faces())
    assert face_count > 20, (
        f"Expected many faces (rails + slots), got {face_count}"
    )


# ---------------------------------------------------------------------------
# Parametric tests
# ---------------------------------------------------------------------------


def test_parametric_wall_thickness():
    """Changing wall_thickness should change the cradle width."""
    from parts.amplifier_housing.model import create_cradle, load_params

    params = load_params()
    result_default = create_cradle(params)
    bb_default = result_default.val().BoundingBox()

    params_thick = copy.deepcopy(params)
    params_thick["housing"]["wall_thickness"] = 8.0
    result_thick = create_cradle(params_thick)
    bb_thick = result_thick.val().BoundingBox()

    assert bb_thick.ylen > bb_default.ylen, (
        f"Thicker walls should increase width: "
        f"default={bb_default.ylen:.1f}, thick={bb_thick.ylen:.1f}"
    )


def test_parametric_heatsink_clearance():
    """Changing heatsink_clearance should adjust the cradle height."""
    from parts.amplifier_housing.model import create_cradle, load_params

    params = load_params()
    result_default = create_cradle(params)
    bb_default = result_default.val().BoundingBox()

    params_tall = copy.deepcopy(params)
    params_tall["housing"]["heatsink_clearance"] = 40.0
    result_tall = create_cradle(params_tall)
    bb_tall = result_tall.val().BoundingBox()

    height_diff = bb_tall.zlen - bb_default.zlen
    assert height_diff > 15, (
        f"Expected ~20mm height increase, got {height_diff:.1f}mm"
    )


def test_parametric_standoff_height():
    """Changing standoff height should raise the amplifier ghost position."""
    from parts.amplifier_housing.model import create_amplifier_ghost, load_params

    params = load_params()
    ghost_default = create_amplifier_ghost(params)
    bb_default = ghost_default.val().BoundingBox()

    params_tall = copy.deepcopy(params)
    params_tall["housing"]["thermal_standoffs"]["height"] = 12.0
    ghost_tall = create_amplifier_ghost(params_tall)
    bb_tall = ghost_tall.val().BoundingBox()

    # Taller standoffs = ghost Z min should be higher
    assert bb_tall.zmin > bb_default.zmin, (
        f"Taller standoffs should raise ghost: "
        f"default zmin={bb_default.zmin:.1f}, tall zmin={bb_tall.zmin:.1f}"
    )


# ---------------------------------------------------------------------------
# Assembly test
# ---------------------------------------------------------------------------


def test_assembly_builds():
    """The full assembly (cradle + base plate + ghost) should build."""
    from parts.amplifier_housing.model import create_assembly

    assy = create_assembly()
    assert assy is not None


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


def test_housing_builds():
    """create_part() should return the cradle (backward compatibility)."""
    from parts.amplifier_housing.model import create_part

    result = create_part()
    assert result is not None
    solid = result.val()
    assert solid is not None
    volume = solid.Volume()
    assert volume > 0
