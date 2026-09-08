"""
The MEAN WELL NSP-1600 mounting interface, as measured — shared by every variant.

Every geometric number here was taken off the vendor B-rep
(`parts/vendor/meanwell-nsp-1600/NSP-1600_0417.stp`) with `lib/analyze_step.py`
plus axial and ring probes, then cross-checked against the Case No. 296A drawing
in the NSP-1600 datasheet (2026-06-15). Where the two disagree, the kernel wins
and the disagreement is written down. Thread sizes, penetration limits, torques,
mass and the qualified attitude come from the datasheet — a STEP cannot carry
them.

THE MOUNT FRAME
---------------
The vendor frame translated by (-66.787, -354.15, -1.5). A pure translation, so
there is no handedness trap: the vendor solid drops in with

    origin  = centre of the unit's width, on its BOTTOM face, at the TERMINAL face
    +X      = across the unit (the AC block is at -X, the DC blades at +X)
    +Y      = out of the terminal face, along the blades. The body is at Y <= 0.
    +Z      = up, out of the bottom face

In this frame the datasheet's own dimensions appear verbatim: the bottom M3s at
(+/-35, -16.1) and (0, -280.8); the side M4s at Y = -5.8 and -257.8 (252 apart),
Z = 22.8; the body 85 x 300.6 x 41.

Units: mm, kg, N.
"""

from __future__ import annotations

import os
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
VENDOR_DIR = PROJECT_ROOT / "parts" / "vendor" / "meanwell-nsp-1600"
VENDOR_STEP_NAME = "NSP-1600_0417.stp"

# vendor frame -> mount frame
VENDOR_TO_MOUNT = (-66.787, -354.15, -1.5)

# ---------------------------------------------------------------------------
# The body
# ---------------------------------------------------------------------------
HALF_W = 42.5                 # X: measured 24.287..109.287 = 85.000 wide
BODY_Y = (-300.598, 0.0)      # fan-guard face .. terminal face (datasheet 300)
BODY_Z = (0.0, 41.0)          # bottom face .. top cover (datasheet 41)
FAN_FACE_Y = BODY_Y[0]
TERMINAL_FACE_Y = BODY_Y[1]
CHASSIS_START_Y = 88.352 - 354.15   # -265.8: where the U-channel shell begins;
                                    # the last 35.2 mm to the fan face is the fan bracket
SHELL_T = 1.2                 # steel U-channel wall, measured 24.287 -> 25.487
BOTTOM_CORNER_R = 1.3         # outer radius of the bottom/side edge (a Y-axis R1.3 face)
TOP_COVER_PLAIN = True        # Z = 41 face: 24462 mm2, zero openings
SIDES_PLAIN = True            # +/-X faces carry only flush countersunk vendor screws;
                              # nothing stands proud of X = +/-42.5 anywhere

# Two 40 x 40 x 28 fans at the -Y end, axes along Y, exhausting OUT of the fan face.
FAN_CENTRES_XZ = ((-21.7, 20.0), (21.7, 20.0))
FAN_SIZE = 40.0
FAN_DEPTH = 28.0
AIRFLOW = "in at the terminal-face louvres (+Y), out through the fans (-Y)"

# ---------------------------------------------------------------------------
# Fixings — the entire external set
# ---------------------------------------------------------------------------
# Bottom: 3x M3 in extruded (flanged) holes in the 1.2 mm bottom sheet.
# Measured: minor dia 2.65, thread material Z 0.5..2.1 above the outer face; the
# PCB underside is at Z = +4.5 (vendor Z 6.0) and the short blade's foot sits
# straight above the +35 hole from Z = 7.4. Datasheet: M3, L = 4 mm max,
# 6-8 kgf.cm.
BOTTOM_M3_XY = ((-35.0, -16.098), (35.0, -16.098), (0.0, -280.798))
BOTTOM_M3_THREAD = "M3x0.5"
BOTTOM_M3_MAX_PENETRATION = 4.0      # datasheet hard limit
BOTTOM_M3_MEASURED_FREE = 4.5        # first material on the axis above the hole (PCB)
BOTTOM_M3_TORQUE_NM = (0.59, 0.78)   # 6-8 kgf.cm

# Sides: 2x M4 per side, 252 apart, 22.8 above the bottom face. Datasheet: M4,
# L = 5 mm max, 7-10 kgf.cm. This is the pattern MEAN WELL's own bracket kit
# (PGG2MHS013A, "M4*4 combination screw") hangs the unit from.
#   terminal-end station (Y = -5.8): a dia 4.54 threaded cross-tube (minor 3.1)
#       spans the full width between the walls - the thread is real in the STEP.
#   fan-end station (Y = -257.8): the STEP shows only a dia 5.0 CLEARANCE opening
#       in each 1.2 mm wall and NOTHING behind it. The thread the datasheet
#       promises is not modelled. Verify on a physical unit before relying on it.
SIDE_M4_YZ = ((-5.798, 22.8), (-257.798, 22.8))
SIDE_M4_X = HALF_W
SIDE_M4_THREAD = "M4x0.7"
SIDE_M4_MAX_PENETRATION = 5.0        # datasheet hard limit
SIDE_M4_MIN_ENGAGEMENT = 3.0
SIDE_M4_TORQUE_NM = (0.69, 0.98)     # 7-10 kgf.cm
SIDE_M4_FAN_END_VERIFIED = False     # see above

# Vendor-only side features: 2x dia 2.8 at Z = 16.8 on the same two stations. The
# terminal-end pair has the end plate's 0.8 mm flange behind it; the fan-end pair
# has nothing behind it. Assembly features. DO NOT USE.
SIDE_PIN_YZ = ((-5.798, 16.8), (-257.798, 16.8))

# ---------------------------------------------------------------------------
# The terminal face (+Y): everything that stands proud of Y = 0, measured
# ---------------------------------------------------------------------------
# DC output blades. 2.0 mm thick, in the YZ plane, dia 6.5 lug hole each. The
# datasheet top view labels the 38 mm blade -Vo and the 28 mm blade +Vo; check
# the label on the unit before wiring - the mount does not care.
BLADES = {
    "long": {"x": (12.5, 14.5), "y": (0.0, 38.002), "z": (15.45, 28.45),
             "hole_yz": (30.002, 21.95), "hole_d": 6.5},
    "short": {"x": (33.0, 35.0), "y": (0.0, 27.95), "z": (23.45, 36.45),
              "hole_yz": (19.952, 29.95), "hole_d": 6.5},
}
# AC input terminal block (FG / AC-N / AC-L, M3.5 screws along +Y).
AC_BLOCK = {"x": (-36.7, -2.27), "y": (0.0, 7.96), "z": (5.96, 21.05)}
# Signal / indication on the terminal plate (window extents, mount frame).
CN1_WINDOW = {"x": (11.1, 31.4), "z": (4.55, 12.1), "plug_depth": 22.0}   # 16-way DF11
CN2_WINDOW = {"x": (31.2, 35.2), "z": (13.5, 17.5), "plug_depth": 22.0}   # 8-way DF11
LED_XZ = (6.6, 9.85)          # dia 5.5, must stay VISIBLE
SVR_XZ = (6.0, 16.05)         # 7.55 x 5.5 trim-pot window, needs a screwdriver along -Y
# Intake louvres, 8 x 5.5 slots (X centre, Z centre): 14 of them, plus five
# 8 x 1.6 slots along the bottom edge. Total open area ~ 680 mm2.
LOUVRES_XZ = tuple((x, z) for x in (-33.6, -23.6, -13.6, -3.6) for z in (28.75, 35.75)) + \
    tuple((23.2, z) for z in (15.5, 21.75, 28.75, 35.75)) + ((33.2, 15.5), (33.2, 21.75))
LOUVRE_OPEN_AREA = 14 * 8.0 * 5.5 + 5 * 8.0 * 1.6

# ---------------------------------------------------------------------------
# Mass, loads, qualification
# ---------------------------------------------------------------------------
MASS_KG = 1.8                 # datasheet
CG_PROXY = (0.0, -150.3, 20.5)  # geometric centre of the body - a stand-in
DESIGN_SHOCK_G = 20           # same figure the Bedrock (1.6 kg) family is worked to
DESIGN_LOAD_N = MASS_KG * 9.81 * DESIGN_SHOCK_G     # 353 N
VENDOR_VIBRATION = "10-500 Hz, 2 G, 10 min/cycle, 60 min per axis (datasheet)"
QUALIFIED_ATTITUDES = ("horizontal",)
ATTITUDE_NOTE = (
    "The datasheet's derating curve is labelled HORIZONTAL and no other curve is "
    "published. MEAN WELL's enclosed-type installation manual, item 3: mounting "
    "orientations other than the standard one 'will require a de-rating in output "
    "current' and refer you to the spec sheet - which has none. Horizontal, bottom "
    "face down, is therefore the only attitude this family builds for."
)

# ---------------------------------------------------------------------------
# Keep-outs (mount frame)
# ---------------------------------------------------------------------------
FAN_CLEAR = 60.0              # exhaust plume - no solid in front of the fan face
INTAKE_CLEAR = 60.0           # intake + connections - no METAL in front of the terminal face
LUG_HARDWARE_OUT = 9.5        # M6 bolt head/nut + washer stack, per side of a blade


def keepouts() -> dict[str, tuple]:
    """Volumes as (xmin, xmax, ymin, ymax, zmin, zmax)."""
    lb, sb = BLADES["long"], BLADES["short"]
    return {
        "unit": (-HALF_W, HALF_W, BODY_Y[0], BODY_Y[1], BODY_Z[0], BODY_Z[1]),
        # nothing at all in the exhaust plume
        "fan_exhaust": (-HALF_W, HALF_W, FAN_FACE_Y - FAN_CLEAR, FAN_FACE_Y,
                        BODY_Z[0], BODY_Z[1]),
        # no metal in front of the terminal face: intake air, live parts, cables
        "terminal_face": (-HALF_W, HALF_W, TERMINAL_FACE_Y, TERMINAL_FACE_Y + INTAKE_CLEAR,
                          BODY_Z[0], BODY_Z[1]),
        # LED sight line / trim-pot screwdriver line, straight out along +Y
        "led_svr_access": (1.0, 7.0, 0.0, 80.0, 4.0, 21.0),
        # lug + bolt hardware + an in-line lug barrel on each blade, cable leaving +Y
        "lug_long": (lb["x"][0] - 4.0, lb["x"][1] + LUG_HARDWARE_OUT,
                     lb["hole_yz"][0] - 14.0, 70.0,
                     lb["hole_yz"][1] - 10.0, lb["hole_yz"][1] + 10.0),
        "lug_short": (sb["x"][0] - 8.0, sb["x"][1] + LUG_HARDWARE_OUT,
                      sb["hole_yz"][0] - 14.0, 62.0,
                      sb["hole_yz"][1] - 10.0, sb["hole_yz"][1] + 10.0),
        # the AC lead leaving the terminal block along +Y
        "ac_cable": (AC_BLOCK["x"][0], AC_BLOCK["x"][1], AC_BLOCK["y"][1], 70.0,
                     AC_BLOCK["z"][0] - 2.0, AC_BLOCK["z"][1] + 3.0),
    }


def keepout_solid(name: str) -> cq.Workplane:
    x0, x1, y0, y1, z0, z1 = keepouts()[name]
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


# ---------------------------------------------------------------------------
# The vendor solid - for fit checks. Never re-measured by hand.
# ---------------------------------------------------------------------------
_UNIT_CACHE: dict = {}


def vendor_step_path() -> Path:
    """Where the vendor STEP is ($NSP1600_STEP wins)."""
    override = os.environ.get("NSP1600_STEP")
    return Path(override) if override else (VENDOR_DIR / VENDOR_STEP_NAME)


def nsp1600_unit() -> cq.Workplane:
    """All 19 vendor solids, placed in the mount frame (translation only)."""
    key = str(vendor_step_path())
    if key not in _UNIT_CACHE:
        wp = cq.importers.importStep(key)
        _UNIT_CACHE[key] = wp.translate(VENDOR_TO_MOUNT)
    return _UNIT_CACHE[key]


# ---------------------------------------------------------------------------
# Screw arithmetic - raises rather than lets a bracket bottom out
# ---------------------------------------------------------------------------
def screw_engagement(screw_length: float, grip: float) -> float:
    """How far a screw enters the unit through `grip` of bracket, washer and spacer."""
    return screw_length - grip


def check_side_screw(screw_length: float, grip: float) -> float:
    """
    Penetration of an M4 into a side wall, in [3.0, 5.0].

    5.0 mm is MEAN WELL's stated maximum. Beyond it the screw runs out of the
    threaded cross-tube's engagement zone and heads for the PCB and the short
    blade's root; the joint still feels tight while it does it.
    """
    e = screw_engagement(screw_length, grip)
    if e > SIDE_M4_MAX_PENETRATION:
        raise ValueError(
            f"M4x{screw_length:g} through {grip:g} mm of stack penetrates {e:.2f} mm - "
            f"the datasheet allows {SIDE_M4_MAX_PENETRATION:g} mm max into the side wall.")
    if e < SIDE_M4_MIN_ENGAGEMENT:
        raise ValueError(
            f"M4x{screw_length:g} through {grip:g} mm of stack engages only {e:.2f} mm - "
            f"fewer than {SIDE_M4_MIN_ENGAGEMENT / 0.7:.1f} threads of M4x0.7. "
            "Lengthen the screw or thin the stack.")
    return e


def check_bottom_screw(screw_length: float, grip: float) -> float:
    """Penetration of an M3 into the bottom face, in [2.0, 4.0]. 4.0 is the datasheet
    max; the PCB underside is 4.5 mm above the outer face."""
    e = screw_engagement(screw_length, grip)
    if e > BOTTOM_M3_MAX_PENETRATION:
        raise ValueError(
            f"M3x{screw_length:g} through {grip:g} mm penetrates {e:.2f} mm - the datasheet "
            f"allows {BOTTOM_M3_MAX_PENETRATION:g} mm; the PCB is at "
            f"{BOTTOM_M3_MEASURED_FREE:g}.")
    if e < 2.0:
        raise ValueError(
            f"M3x{screw_length:g} through {grip:g} mm engages only {e:.2f} mm - the extruded "
            "hole offers about 2 mm of thread and needs all of it.")
    return e
