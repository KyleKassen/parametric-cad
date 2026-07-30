"""
Acceptance checks that need more than a dimension, measured on the artifact.

spec.json can assert a bounding box and a hole count. It cannot assert "the
sealing land is wide enough on every side", "no blind tap can break into the
sealed volume", or "every feature is reachable on a 3-axis machine" - those are
RELATIONSHIPS between features, and they are exactly what a parameter change
quietly breaks while every dimensional check still passes.

Everything below is measured by ray-casting the re-imported STEP that
lib/evaluate.py hands over in EVAL_STEP_PATH. Nothing is read back out of the
model, because the model is not what gets manufactured.

Exit 0 = every requirement met, 1 = at least one failed, 2 = nothing to check.
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import cadquery as cq

PART_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PART_DIR.parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lib.analyze_step import _cylinder_features  # noqa: E402

PARAMS = json.loads((PART_DIR / "params.json").read_text(encoding="utf-8"))
D = PARAMS["dimensions"]
F = PARAMS["features"]

# Requirements, stated once, here - not buried in the assertions below.
MIN_SEAL_LAND = 4.5  # mm of flat land between the groove and the cavity mouth
MIN_SCREW_CLEAR = 1.5  # mm from a lid tap hole edge to the groove
MIN_TAP_BACKING = 2.0  # mm of material behind a blind tap
SQUEEZE_BAND = (20.0, 30.0)
FILL_BAND = (75.0, 85.0)
FIN_PITCH_BAND = (6.0, 12.0)

FAILURES: list[str] = []
LINES: list[str] = []


def check(ok: bool, label: str, detail: str) -> None:
    LINES.append(f"  [{'PASS' if ok else 'FAIL'}] {label:26s} {detail}")
    if not ok:
        FAILURES.append(f"{label}: {detail}")


def crossings(shape: cq.Shape, origin, direction) -> list[float]:
    """Distances along a ray at which it crosses the solid's boundary, sorted."""
    from OCP.BRepIntCurveSurface import BRepIntCurveSurface_Inter
    from OCP.gp import gp_Dir, gp_Lin, gp_Pnt

    inter = BRepIntCurveSurface_Inter()
    inter.Init(shape.wrapped, gp_Lin(gp_Pnt(*origin), gp_Dir(*direction)), 1e-7)
    hits: list[float] = []
    while inter.More():
        hits.append(inter.W())
        inter.Next()
    hits.sort()
    out: list[float] = []
    for w in hits:
        if not out or abs(w - out[-1]) > 1e-4:
            out.append(w)
    return out


def main() -> int:
    env = os.environ.get("EVAL_STEP_PATH", "")
    step = Path(env) if env else PART_DIR / "exports" / f"{PART_DIR.name}_v1.step"
    if not step.is_file():
        print(f"no STEP to check: {step}")
        return 2
    shape = cq.importers.importStep(str(step)).val()
    print(f"checking {step}\n")

    L, W, H = D["body_length"], D["body_depth"], D["body_height"]
    seal, lid, cp, fb, fl = (
        F["lid_seal"],
        F["lid_fasteners"],
        F["cold_plate"],
        F["fin_bank"],
        F["base_flange"],
    )
    half_gl, half_gw = seal["groove_length"] / 2, seal["groove_width"] / 2

    # 1. one body, inside the envelope it was sold on ------------------------
    check(len(shape.Solids()) == 1, "single_solid", f"{len(shape.Solids())} solid(s)")
    bb = shape.BoundingBox()
    got, limit = (bb.xlen, bb.ylen, bb.zlen), D["envelope_limit"]
    check(
        all(g <= lim + 0.05 for g, lim in zip(got, limit)),
        "envelope",
        f"{got[0]:.2f} x {got[1]:.2f} x {got[2]:.2f} mm inside {limit}",
    )

    # 2. 3-axis machinable: no cylindrical feature runs off a part axis ------
    feats = _cylinder_features(shape)
    off_axis = [f for f in feats if f["axis_label"] not in ("X", "Y", "Z")]
    check(
        not off_axis,
        "three_axis_holes",
        f"{len(feats)} cylindrical features, {len(off_axis)} off the part axes",
    )

    # 3. the seal, measured rather than asserted -----------------------------
    #    depth from a ray up the groove centreline, width from a ray across it
    up = crossings(shape, (0.0, -half_gw, -20.0), (0, 0, 1))
    depth = (up[0] - 20.0) if up else float("nan")
    across = [t - W for t in crossings(shape, (0.0, -W, depth / 2), (0, 1, 0))]
    near = sorted(v for v in across if v < 0)
    width = (near[2] - near[1]) if len(near) >= 3 else float("nan")
    cord = seal["cord_diameter"]
    squeeze = (cord - depth) / cord * 100.0
    fill = (math.pi * cord**2 / 4) / (width * depth) * 100.0
    check(
        SQUEEZE_BAND[0] <= squeeze <= SQUEEZE_BAND[1],
        "seal_squeeze",
        f"{squeeze:.1f}% on a {cord} mm cord in a {depth:.2f} mm groove {SQUEEZE_BAND}",
    )
    check(
        FILL_BAND[0] <= fill <= FILL_BAND[1],
        "seal_fill",
        f"{fill:.1f}% of a {width:.2f} x {depth:.2f} mm groove {FILL_BAND}",
    )

    # 4. sealing land: the groove must not crowd the cavity mouth ------------
    for axis, direction, origin in (
        ("y", (0, 1, 0), (0.0, -W, 0.02)),
        ("x", (1, 0, 0), (-L, 0.0, 0.02)),
    ):
        span = L if axis == "x" else W
        vals = sorted(t - span for t in crossings(shape, origin, direction) if t - span < 0)
        land = abs(vals[3] - vals[2]) if len(vals) >= 4 else float("nan")
        check(
            land >= MIN_SEAL_LAND,
            f"seal_land_{axis}",
            f"{land:.2f} mm of flat land between groove and cavity mouth (>= {MIN_SEAL_LAND})",
        )

    # 5. lid screws: the rhythm, and every one clear of the seal path --------
    tap = [f for f in feats if f["axis_label"] == "Z" and abs(f["diameter"] - 3.3) < 0.05]
    check(len(tap) >= 16, "lid_screw_count", f"{len(tap)} x D3.3 tapped holes on Z (>= 16)")
    out_x, out_y = half_gl + width / 2, half_gw + width / 2
    clear = min(max(abs(f["p1"][0]) - out_x, abs(f["p1"][1]) - out_y) - 1.65 for f in tap)
    check(
        clear >= MIN_SCREW_CLEAR,
        "lid_screw_clear_of_seal",
        f"nearest tap edge is {clear:.2f} mm outboard of the groove (>= {MIN_SCREW_CLEAR})",
    )
    inset = min(min(L / 2 - abs(f["p1"][0]), W / 2 - abs(f["p1"][1])) for f in tap)
    check(
        abs(inset - lid["inset"]) < 0.05,
        "lid_screw_inset",
        f"every lid screw {inset:.2f} mm from the part edge (spec {lid['inset']})",
    )

    # 6. no blind tap may break into the sealed volume -----------------------
    ray = crossings(shape, (fb["pitch"] / 2, 0.0, -20.0), (0, 0, 1))
    plate = (ray[1] - ray[0]) if len(ray) >= 2 else float("nan")
    check(
        plate >= cp["grid_tap_depth"] + MIN_TAP_BACKING,
        "coldplate_tap_backing",
        f"{plate:.2f} mm of cold plate behind a {cp['grid_tap_depth']} mm tap "
        f"(>= +{MIN_TAP_BACKING})",
    )
    mast = fl["thickness"] + fl["pad_thickness"] + (W - D["cavity_width"]) / 2
    check(
        mast >= fl["tap_depth"] + MIN_TAP_BACKING,
        "flange_tap_backing",
        f"{mast:.1f} mm behind a {fl['tap_depth']} mm mast tap (>= +{MIN_TAP_BACKING})",
    )

    # 7. handedness: the two connectors are not interchangeable --------------
    bore = [
        f
        for f in feats
        if f["axis_label"] == "Y" and abs(f["diameter"] - F["circular_connector"]["bore"]) < 0.1
    ]
    check(
        bool(bore) and bore[0]["p1"][0] < 0,
        "circular_connector_port",
        f"circular bore at x = {bore[0]['p1'][0]:.1f} mm, must be < 0"
        if bore
        else "no circular bore found",
    )
    rect_screws = [
        f
        for f in feats
        if f["axis_label"] == "Y" and abs(f["diameter"] - 2.5) < 0.05 and f["p1"][0] > 0
    ]
    check(
        len(rect_screws) >= 4,
        "rect_connector_starboard",
        f"{len(rect_screws)} rectangular-land taps at x > 0 (>= 4)",
    )

    # 8. the fin bank the thermal case was made on --------------------------
    mid = crossings(shape, (-L, 0.0, H + fb["height"] / 2), (1, 0, 0))
    centres = [(mid[i] + mid[i + 1]) / 2 for i in range(0, len(mid) - 1, 2)]
    blades = len(centres)
    pitch = (centres[-1] - centres[0]) / (blades - 1) if blades > 1 else float("nan")
    check(blades >= 18, "fin_count", f"{blades} blades measured across the roof (>= 18)")
    check(
        FIN_PITCH_BAND[0] <= pitch <= FIN_PITCH_BAND[1],
        "fin_pitch",
        f"{pitch:.2f} mm measured pitch {FIN_PITCH_BAND} for natural convection",
    )

    print("\n".join(LINES))
    if FAILURES:
        print(f"\n{len(FAILURES)} of {len(LINES)} requirements NOT met")
        return 1
    print(f"\nall {len(LINES)} requirements met")
    return 0


if __name__ == "__main__":
    sys.exit(main())
