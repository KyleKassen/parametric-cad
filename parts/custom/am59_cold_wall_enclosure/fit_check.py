"""Geometry, thermal, and mass/CG gate check for the AM59 cold-wall enclosure."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PART_DIR = Path(__file__).parent
PROJECT_ROOT = PART_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lib.housing import clearance, interference  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "am59_cold_wall_enclosure_model",
    PART_DIR / "model.py",
)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def _bbox_text(workplane) -> str:
    bb = workplane.val().BoundingBox()
    return (
        f"{bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm; "
        f"min=({bb.xmin:.2f}, {bb.ymin:.2f}, {bb.zmin:.2f}), "
        f"max=({bb.xmax:.2f}, {bb.ymax:.2f}, {bb.zmax:.2f})"
    )


def main() -> int:
    params = model.load_params()
    tub = model.create_enclosure_tub(params)
    lid = model.create_lid(params)
    gasket = model.create_lid_gasket_reference(params)
    chassis = model.create_amplifier_chassis_reference(params)
    heatsink = model.create_relocated_heatsink_reference(params)
    clamps = model.create_flange_clamp_bars(params)
    cradle = model.create_heatsink_cradle(params)
    duct = model.create_heatsink_duct_sheet(params)
    hood = model.create_air_tunnel_hood(params)
    mesh = model.create_mesh_screens_reference(params)
    din = model.create_din_provision(params)
    keepout = model.create_din_keepout_reference(params)
    tim = model.create_tim_references(params)
    shield = model.create_solar_shield(params)

    print(f"tub:      {_bbox_text(tub)}")
    print(f"chassis:  {_bbox_text(chassis)}")
    print(f"heatsink: {_bbox_text(heatsink)}")
    print(f"hood:     {_bbox_text(hood)}")

    failures: list[str] = []

    counts = model.amp_solid_counts()
    if counts["total"] != params["amplifier"]["native_solid_count_total"]:
        failures.append(f"Vendor solid partition lost solids ({counts['total']} != 80)")
    if counts["chassis"] < 25 or counts["heatsink"] < 45:
        failures.append(
            f"Chassis/heatsink split does not match the expected vendor grouping (got {counts})"
        )

    # --- Dry-boundary and mechanical interference gates ------------------
    no_overlap_pairs = [
        ("chassis vs tub", chassis, tub),
        ("chassis vs clamp bars", chassis, clamps),
        ("chassis vs DIN provision", chassis, din),
        ("chassis vs DIN keep-out", chassis, keepout),
        ("chassis vs TIM pads", chassis, tim),
        ("heatsink vs tub", heatsink, tub),
        ("heatsink vs cradle", heatsink, cradle),
        ("heatsink vs duct sheet", heatsink, duct),
        ("heatsink vs hood", heatsink, hood),
        ("heatsink vs mesh screens", heatsink, mesh),
        ("heatsink vs TIM pads", heatsink, tim),
        ("TIM pads vs tub", tim, tub),
        ("cradle vs tub", cradle, tub),
        ("clamp bars vs tub", clamps, tub),
        ("lid vs tub", lid, tub),
        ("lid gasket vs tub", gasket, tub),
        ("lid gasket vs lid", gasket, lid),
        ("hood vs tub", hood, tub),
        ("solar shield vs lid", shield, lid),
    ]
    for name, a, b in no_overlap_pairs:
        overlap = interference(a, b)
        if overlap > 0.5:
            failures.append(f"{name}: interference {overlap:.2f} mm3")

    # --- Contact gates (load paths and seal stack) -----------------------
    contact_pairs = [
        ("chassis on upper TIM", chassis, tim, 0.05),
        ("heatsink on lower TIM", heatsink, tim, 0.05),
        ("TIM on cold floor/pad", tim, tub, 0.05),
        ("lid on rim", lid, tub, 0.05),
        ("gasket in groove", gasket, tub, 0.05),
        ("gasket under lid", gasket, lid, 0.05),
        ("cradle pillars on floor bosses", cradle, tub, 0.05),
        ("clamp bars on flange", clamps, chassis, 0.1),
        ("cradle rails on baseplate ledge", cradle, heatsink, 0.1),
        ("duct sheet on fin tips", duct, heatsink, 0.1),
        ("shield standoffs on lid", shield, lid, 0.05),
    ]
    for name, a, b, limit in contact_pairs:
        gap = clearance(a, b)
        if gap > limit:
            failures.append(f"{name}: not in contact (gap {gap:.3f} mm)")

    # --- Clearance gates -------------------------------------------------
    clearance_pairs = [
        ("chassis to tub (TIM gap)", chassis, tub, 0.9),
        ("heatsink to tub (TIM gap)", heatsink, tub, 0.9),
        ("heatsink to hood", heatsink, hood, 20.0),
        ("heatsink to mesh screens", heatsink, mesh, 20.0),
        ("chassis to DIN keep-out", chassis, keepout, 15.0),
        ("chassis to DIN provision", chassis, din, 10.0),
        ("DIN keep-out to tub", keepout, tub, 2.5),
        ("DIN keep-out to lid", keepout, lid, 5.0),
    ]
    for name, a, b, minimum in clearance_pairs:
        gap = clearance(a, b)
        if gap < minimum:
            failures.append(f"{name}: clearance {gap:.2f} < {minimum} mm")

    # --- Thermal gates ---------------------------------------------------
    thermal = model.thermal_assessment(params)
    for mode, result in thermal["modes"].items():
        state = "PASS" if result["passes"] else "FAIL"
        detail = result.get("case_c", result.get("cabin_air_c", 0.0))
        print(f"thermal {mode}: {detail:.1f} C vs {result['limit_c']:.0f} C -> {state}")
        if not result["passes"]:
            failures.append(f"Thermal mode fails: {mode}")
    if thermal["case_temperatures_c"]["matched_45c"] > 64.0:
        failures.append("Matched full power exceeds the derate threshold at 45 C")
    if thermal["cabin_air_max_gate_45c"] > 65.0:
        failures.append("Cabin air exceeds 65 C at the max internal budget")

    # --- Mass / CG gates -------------------------------------------------
    mass = model.mass_cg_assessment(params)
    print(
        f"mass {mass['total_mass_kg']:.2f} kg, CG height "
        f"{mass['cg_height_above_skirt_base_mm']:.1f} mm, moment "
        f"{mass['cg_moment_about_base_kg_m']:.2f} kg m"
    )
    if mass["total_mass_kg"] > 18.0:
        failures.append("Total estimated mass exceeds 18 kg")
    if mass["cg_height_above_skirt_base_mm"] > 135.0:
        failures.append("CG height exceeds 135 mm above the skirt base")
    if mass["cg_moment_about_base_kg_m"] > 2.5:
        failures.append("CG moment about the base exceeds 2.5 kg m")

    # --- DIN provision sanity -------------------------------------------
    d = params["din_provision"]
    rail_length = d["rail_x"][1] - d["rail_x"][0]
    keepout_volume_l = (
        (d["keepout_x"][1] - d["keepout_x"][0])
        * (d["keepout_y"][1] - d["keepout_y"][0])
        * (d["keepout_z"][1] - d["keepout_z"][0])
        / 1e6
    )
    print(f"DIN rail {rail_length:.0f} mm, keep-out {keepout_volume_l:.2f} L")
    if rail_length < 300.0:
        failures.append("DIN rail provision is under 300 mm")
    if keepout_volume_l < 2.4:
        failures.append("DIN component keep-out is under 2.4 L")

    if failures:
        print("\nFAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
