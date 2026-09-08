"""
The Bedrock V3000 mounting interface, as measured — shared by every mount variant.

Every number here was taken off the vendor B-rep with `lib/analyze_step.py` and
point/ring probes (see `parts/vendor/solidrun-bedrock-v3000/README.md`), not from a
datasheet and not from a previous part's notes. The variants' geometry, the keep-out
volumes and the screw-penetration limits live here so that no mount script retypes
them and no two variants can disagree about them.

Frame: the vendor's own. X across the unit (fin direction), Y fore/aft with -Y the
I/O panel and +Y the bare back wall, Z up the long axis with Z=0 the bottom end cap.

Units: mm.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
VENDOR_DIR = PROJECT_ROOT / "parts" / "vendor" / "solidrun-bedrock-v3000"


# Sibling modules are loaded by explicit path under a namespaced key, never by
# putting this part's directory on sys.path. Every part in this repo has a
# `model.py` and pytest runs them all in one process, so a stray sys.path entry
# here silently hands OUR model.py to another part's tests.
def _sibling(name: str):
    key = f"bedrock_v3000_mount.{name}"
    mod = sys.modules.get(key)
    if mod is None:
        spec = importlib.util.spec_from_file_location(key, PART_DIR / f"{name}.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return mod


def sibling(name: str):
    """Load another module from this part directory, sys.path untouched."""
    return _sibling(name)

# ---------------------------------------------------------------------------
# The three chassis variants (all share Y, Z and the fixing set)
# ---------------------------------------------------------------------------
#   key -> X half-width, exact shell volume, and the mass we design to.
# Shell volumes are exact kernel measurements. Design masses are the aluminium
# shell plus an allowance for board, spreader and internal hardware.
VARIANTS = {
    "60w": {"half_x": 36.5, "x_min": -36.5, "x_max": 36.5,
            "shell_mm3": 470740.8, "design_mass_kg": 1.60, "fin_sides": ("+X", "-X")},
    "30w": {"half_x": 22.5, "x_min": -22.5, "x_max": 22.5,
            "shell_mm3": 267462.8, "design_mass_kg": 1.05, "fin_sides": ("+X", "-X")},
    "tile": {"half_x": 14.5, "x_min": -14.5, "x_max": 14.5,
             "shell_mm3": 206452.5, "design_mass_kg": 0.85, "fin_sides": ()},
    # Tile core + ONE 60 W fin bank. Not a body SolidRun ships, but the file's own
    # architecture: the 60 W separates into exactly this at |X| = 14.5, and the
    # Tile carries a six-point M4 pattern tapped from both side walls precisely so
    # a bank can go on one side and a mount on the other.
    "hybrid_posx": {"half_x": 36.5, "x_min": -14.5, "x_max": 36.5,
                    "shell_mm3": 338375.7, "design_mass_kg": 1.30,
                    "fin_sides": ("+X",), "flat_x": -14.5},
    "hybrid_negx": {"half_x": 36.5, "x_min": -36.5, "x_max": 14.5,
                    "shell_mm3": 338375.5, "design_mass_kg": 1.30,
                    "fin_sides": ("-X",), "flat_x": 14.5},
}
DEFAULT_VARIANT = "60w"

# The plane the 60 W separates at, measured three ways (volume, point sweep,
# feature positions). See parts/vendor/solidrun-bedrock-v3000/split_variants.py.
FIN_SPLIT_X = 14.5
FIN_BANK_VOLUME = 131921.4

CHASSIS_Z_MIN = 0.0        # bottom end cap plane
CHASSIS_Z_MAX = 160.0      # top end cap plane
CHASSIS_Y_MIN = -65.762    # rearmost chassis material on the I/O end
CHASSIS_Y_MAX = 65.0       # back wall plane
IO_FACE_Y = -65.0          # nominal I/O panel plane
IO_PROUD_Y = -67.957       # the one module that stands 2.957 mm proud of it
SMA_TOP_Z = 170.0          # top of the four SMA bulkhead barrels

# ---------------------------------------------------------------------------
# Fixings — the entire external set on the 30 W and 60 W chassis
# ---------------------------------------------------------------------------
# +Y back wall: 2x M3x0.5 blind tapped, COLLINEAR on X=0, 60.000 mm apart.
# Probed hole runs Y = 65.000 -> 62.000. 1.0 mm of wall behind it, then cavity.
BACKWALL_Y = 65.0
BACKWALL_M3_Z = (50.0, 110.0)
BACKWALL_M3_X = 0.0
BACKWALL_M3_THREAD = "M3x0.5"
BACKWALL_M3_MAX_PENETRATION = 3.0    # HARD. Beyond this the screw bottoms out and
                                     # jacks the bracket off the bearing land.
BACKWALL_M3_TARGET_ENGAGEMENT = 2.5  # what we design to (0.5 mm of reserve)

# The continuous flat land on the back wall. Outboard of |X| = 10 the surface rolls
# away into two blend ridges only 0.1 mm low at Y = 64.9 — a wider flat pad rocks on
# those two ridges instead of bearing, so anything wider must be relieved.
BACKWALL_LAND_X = 10.0
BACKWALL_LAND_Z = (1.0, 159.0)
BACKWALL_LAND_AREA = 3140.8
BACKWALL_RELIEF_MIN = 0.6            # minimum step-back outboard of the land

# -Z bottom end cap: 1x M4x0.7 blind tapped, usable. Probe: void Z 0..8.95, thread
# faces 0..8.09. Its twin at X = -6.0 is occupied by a fitted vendor screw.
BOTTOM_M4_XY = (6.0, 0.0)
BOTTOM_M4_OCCUPIED_XY = (-6.0, 0.0)
BOTTOM_M4_THREAD = "M4x0.7"
BOTTOM_M4_MAX_PENETRATION = 8.0
BOTTOM_M4_TARGET_ENGAGEMENT = 6.0
# Caveat carried from the measurement pass: this is very likely a vendor bottom-cover
# assembly screw (its mirror twin already has one fitted). Every variant here treats
# it as OPTIONAL — each mount must stand up with it omitted.

# -Z bottom end cap flat: the largest single flat on the part, but NOT a solid plate.
# The fin channels are open at the bottom outboard of |X| ~ 14.5, so a plate laid
# across the whole footprint blanks the convection inlets.
BOTTOM_CAP_Z = 0.0
BOTTOM_CAP_X = 29.5
BOTTOM_CAP_Y = 64.0
BOTTOM_CAP_AREA = 4617.2
BOTTOM_CORE_X = 14.5                 # bear only inside this — outboard is fin inlet

# Tile core: 6x M4x0.7 on the X axis, tapped from BOTH ends (thread |X|
# 11.000..13.916 each side, 22 mm of open cavity between). This pattern belongs to
# the Tile core, so it exists on the Tile AND on the hybrid's flat side; it does
# NOT exist on the 30 W or 60 W, whose extrusions are solid at |X| 10.5..14.5.
#
# Both ends are usable at once: a screw retaining a fin bank on one side and a
# screw mounting the unit on the other never meet.
TILE_FACE_X = 14.5
TILE_M4_YZ = ((-60.0, 10.0), (60.0, 10.0), (0.0, 40.0),
              (0.0, 110.0), (-50.0, 150.0), (50.0, 150.0))
TILE_M4_MAX_PENETRATION = 3.5
TILE_SIDE_FLAT_AREA = 20410.1
# Extent of that flat, measured: anything a plate puts inside it is unreachable
# once the unit is bolted on.
TILE_SIDE_FLAT_Y = 64.49
TILE_SIDE_FLAT_Z = (0.5, 159.5)


def flat_side_x(variant: str) -> float:
    """
    The X plane of the bolt-on flat face, for variants that have one.

    The Tile has two (either side); a hybrid has exactly one, opposite its fin
    bank; the 30 W and 60 W have none — both their sides are fin tips.
    """
    v = VARIANTS[variant]
    if "flat_x" in v:
        return v["flat_x"]
    if variant == "tile":
        return -TILE_FACE_X
    raise ValueError(
        f"the {variant} chassis has no flat side — both of its |X| faces are fin "
        "tips, 407.3 mm2 of bearing in seven 0.395 mm strips. Use the +Y back wall "
        "and the -Z end cap instead.")

# ---------------------------------------------------------------------------
# Fin bank (60 W / 30 W) — thermally critical, structurally useless
# ---------------------------------------------------------------------------
# Fins are thin plates in the X-Z plane stacked along Y. The channels between them
# run along Z and are open at BOTH ends, so the unit is a vertical chimney: +Z up is
# the only orientation in which natural convection works as designed.
FIN = {
    "60w": {"tip_x": 36.5, "tip_z": (7.0, 153.0), "tip_width": 0.395,
            "pitch_y": 10.15, "tip_flat_area": 407.3,
            "tip_y": (0.0, 10.15, 20.3, 30.516)},
    "30w": {"tip_x": 22.5, "tip_z": (4.0, 156.0), "tip_width": 0.200,
            "pitch_y": 10.65, "tip_flat_area": 152.0,
            "tip_y": (0.014, 10.65, 21.3)},
}
# The bottom of the fin bank ramps in. Measured half-width against Z at Y = 0:
# |X| <= 29.5 @ Z=0.2, 30.0 @ 0.5, 31.5 @ 2.0, 34.5 @ 5.0, 36.5 @ 8.0 — about 45 deg.
BASE_FLARE = ((0.2, 29.5), (0.5, 30.0), (2.0, 31.5), (5.0, 34.5), (8.0, 36.5))
BASE_FLARE_TOP_Z = 8.0

# ---------------------------------------------------------------------------
# Keep-outs — service envelopes, not just solid geometry
# ---------------------------------------------------------------------------
IO_CABLE_CLEARANCE = 55.0   # RJ45 plug body + Cat6 minimum bend radius
SMA_CABLE_CLEARANCE = 45.0  # SMA plug body + RG316 minimum bend radius


def keepouts(variant: str = DEFAULT_VARIANT) -> dict[str, tuple]:
    """
    Volumes a mount may not enter, as (xmin, xmax, ymin, ymax, zmin, zmax).

    `io_cables` and `sma_cables` are service envelopes: the connectors themselves are
    smaller, but a bracket that clears the connector and not the plug is not a mount.
    """
    v = VARIANTS[variant]
    ko = {
        "unit": (v["x_min"], v["x_max"], IO_PROUD_Y, CHASSIS_Y_MAX,
                 CHASSIS_Z_MIN, SMA_TOP_Z),
        "io_cables": (-12.0, 12.0, IO_PROUD_Y - IO_CABLE_CLEARANCE, IO_PROUD_Y,
                      4.4, 153.4),
        "sma_cables": (-10.0, 8.0, -52.0, 54.0, SMA_TOP_Z,
                       SMA_TOP_Z + SMA_CABLE_CLEARANCE),
    }
    # The fin volume proper: root to tip, over the Z band the tips actually span,
    # and only on the sides that HAVE a bank. Bounding it by the tip band rather
    # than the full chassis height is what makes this a real check — a full-height
    # prism flags a shock stop standing beside the base flare, where there is no
    # fin to shadow. Listing only the real sides is what lets a hybrid mount bolt
    # flat to the side that has no bank.
    fin = FIN.get("60w" if variant.startswith("hybrid") else variant)
    if fin:
        z0, z1 = fin["tip_z"]
        for side in v["fin_sides"]:
            if side == "-X":
                ko["fin_bank_neg_x"] = (-fin["tip_x"], -BOTTOM_CORE_X,
                                        CHASSIS_Y_MIN, CHASSIS_Y_MAX, z0, z1)
            else:
                ko["fin_bank_pos_x"] = (BOTTOM_CORE_X, fin["tip_x"],
                                        CHASSIS_Y_MIN, CHASSIS_Y_MAX, z0, z1)
    return ko


def keepout_solid(name: str, variant: str = DEFAULT_VARIANT) -> cq.Workplane:
    """One named keep-out as a box, for interference checks."""
    x0, x1, y0, y1, z0, z1 = keepouts(variant)[name]
    return (cq.Workplane("XY")
            .box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


# ---------------------------------------------------------------------------
# Vendor solids — for fit checks. Never re-measured by hand.
# ---------------------------------------------------------------------------
def _vendor_module():
    """
    The vendor part's splitter, so variant selection lives in one place.

    Loaded by path under a namespaced key rather than by putting the vendor
    directory on sys.path — see _sibling().
    """
    key = "bedrock_v3000_mount.split_variants"
    mod = sys.modules.get(key)
    if mod is None:
        spec = importlib.util.spec_from_file_location(
            key, VENDOR_DIR / "split_variants.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return mod


def vendor_step_path() -> Path:
    """Where the vendor STEP actually is ($BEDROCK_V3000_STEP wins)."""
    override = os.environ.get("BEDROCK_V3000_STEP")
    return Path(override) if override else (VENDOR_DIR / "Bedrock V3000 Basic 3D model.step")


_HYBRID_SIDE = {"hybrid_posx": "+X", "hybrid_negx": "-X"}


def bedrock_unit(variant: str = DEFAULT_VARIANT) -> cq.Workplane:
    """One chassis variant plus the shared connector solids, in the vendor frame."""
    sv = _vendor_module()
    if variant in _HYBRID_SIDE:
        return cq.Workplane(obj=sv.hybrid_unit(_HYBRID_SIDE[variant]))
    return cq.Workplane(obj=sv.unit(variant))


def bedrock_chassis(variant: str = DEFAULT_VARIANT) -> cq.Workplane:
    """The bare chassis shell of one variant, in the vendor frame."""
    sv = _vendor_module()
    if variant in _HYBRID_SIDE:
        return cq.Workplane(obj=sv.hybrid(_HYBRID_SIDE[variant]))
    return cq.Workplane(obj=sv.chassis(variant))


def bedrock_fin_bank(side: str = "+X") -> cq.Workplane:
    """One 60 W fin bank on its own, in the vendor frame."""
    return cq.Workplane(obj=_vendor_module().fin_bank(side))


def bedrock_60w() -> cq.Workplane:
    """Fit-check builder: the 60 W unit (the design target)."""
    return bedrock_unit("60w")


def bedrock_30w() -> cq.Workplane:
    """Fit-check builder: the 30 W unit."""
    return bedrock_unit("30w")


def bedrock_tile() -> cq.Workplane:
    """Fit-check builder: the Tile unit."""
    return bedrock_unit("tile")


def bedrock_hybrid(fin_side: str = "+X") -> cq.Workplane:
    """Fit-check builder: the hybrid unit — flat one side, 60 W fin bank the other."""
    return bedrock_unit("hybrid_posx" if fin_side == "+X" else "hybrid_negx")


# ---------------------------------------------------------------------------
# Screw arithmetic — the check that actually stops a bracket bottoming out
# ---------------------------------------------------------------------------
def screw_engagement(screw_length: float, grip: float) -> float:
    """How far a screw of `screw_length` enters the tapped hole through `grip` of bracket."""
    return screw_length - grip


def check_backwall_screw(screw_length: float, grip: float) -> float:
    """
    Engagement of an M3 in the back wall, raising if it would bottom out.

    The hole is 3.000 mm deep with 1.0 mm of wall behind it. A screw that reaches the
    bottom does not simply stop — it jacks the bracket off the bearing land, which is
    the one failure mode that still looks like a tight joint.
    """
    e = screw_engagement(screw_length, grip)
    if e > BACKWALL_M3_MAX_PENETRATION:
        raise ValueError(
            f"M3x{screw_length:g} through {grip:g} mm of bracket penetrates {e:.2f} mm — "
            f"the back-wall hole is only {BACKWALL_M3_MAX_PENETRATION:g} mm deep. "
            "It will bottom out and jack the bracket off the face."
        )
    if e < 1.5:
        raise ValueError(
            f"M3x{screw_length:g} through {grip:g} mm of bracket engages only {e:.2f} mm — "
            "fewer than three full threads of M3x0.5. Reduce the grip or lengthen the screw."
        )
    return e


def check_bottom_screw(screw_length: float, grip: float) -> float:
    """Engagement of the M4 in the bottom end cap, raising if it would bottom out."""
    e = screw_engagement(screw_length, grip)
    if e > BOTTOM_M4_MAX_PENETRATION:
        raise ValueError(
            f"M4x{screw_length:g} through {grip:g} mm of bracket penetrates {e:.2f} mm — "
            f"the bottom-cap hole gives {BOTTOM_M4_MAX_PENETRATION:g} mm of usable thread."
        )
    if e < 3.0:
        raise ValueError(
            f"M4x{screw_length:g} through {grip:g} mm of bracket engages only {e:.2f} mm."
        )
    return e
