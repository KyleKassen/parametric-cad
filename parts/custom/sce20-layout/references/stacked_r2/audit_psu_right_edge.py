"""Bound rightward N2 PSU translation against the real enclosure, in mm.

The existing side-tab adapter retains its geometry and R180 orientation. This
audit checks only PSU/case interfaces, leaving stacked component design to the
main layout task. A radius-15 socket cylinder is an explicit access allowance.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "enclosure"))
from audit_enclosure import bbox  # noqa: E402
from check_candidate import collisions  # noqa: E402


def main() -> None:
    source = cq.Shape.importBrep(str(HERE.parent / "enclosure/source_enclosure.brep"))
    psu = cq.Shape.importBrep(str(HERE.parent / "enclosure/candidate_meanwell_source.brep"))
    psu = psu.rotate((0, 0, 0), (0, 0, 1), 180).translate((0, 65.6, 0))
    source_obstacles = []
    for i, solid in enumerate(source.Solids()):
        if i in [0, 1, 2, 60]:
            continue
        if i >= 61:
            solid = solid.translate((0, 0, 2.825))
        solid = solid.translate((215.9, 215.9, 106.395))
        source_obstacles.append((f"source_solid_{i}", solid))
    sockets = [
        (f"factory_socket_{x}_{y}", cq.Solid.makeCylinder(15, 60, cq.Vector(x, y, 0)))
        for x in [22.225, 409.575]
        for y in [22.225, 409.575]
    ]
    records = []
    for x in [371.5, 378, 382, 386, 390, 391.8, 393.8, 395.8]:
        installed = psu.translate((x, 0, 0))
        physical = collisions(installed, source_obstacles)
        access = collisions(installed, sockets)
        records.append(
            {
                "center_x_mm": x,
                "translation_y_mm": 65.6,
                "rotation_z_deg": 180,
                "bbox_mm": bbox(installed),
                "case_and_factory_hardware_hits": physical,
                "factory_socket_hits": access,
                "adapter_right_panel_margin_mm": 431.8 - x - 36,
                "native_stud_cavity_edge_web_mm": 431.8 - x - 28.5 - 6.05,
            }
        )
        print(x, "hardware", len(physical), "socket", len(access), flush=True)

    # Translate a test socket in the opposite direction, avoiding repeated
    # tessellation/box work on every PSU solid during the bounded search.
    def socket_hit(x: float) -> bool:
        probe = cq.Solid.makeCylinder(15, 60, cq.Vector(409.575 - x, 22.225, 0))
        return bool(collisions(probe, [("PSU", psu)]))

    lo, hi = 371.5, 395.8
    limiting = socket_hit(hi)
    if limiting:
        for _ in range(22):
            mid = (lo + hi) / 2
            if socket_hit(mid):
                hi = mid
            else:
                lo = mid
    else:
        lo = hi
    mm = {
        "nominal_body_local_half_width": 20.5,
        "adapter_local_half_width": 36,
        "stud_local_half_pitch_x": 28.5,
        "native_cavity_radius": 6.05,
        "native_socket_radius": 5,
        "panel_width": 431.8,
        "panel_height": 431.8,
        "case_inner_x_at_PSU_z": [-36.195, 467.995],
        "case_inner_y_at_PSU_z": [-36.195, 467.995],
        "PSU_and_corridor_y_range": [-34.4, 466.2],
    }
    report = {
        "schema": "sce20-stacked-r2-psu-right-edge/1",
        "units": "mm",
        "assumptions": [
            "Original N2 side mount retained, R180, translationY65.6,Z0.",
            "New backpanel6mm retains rear seat, original studs fixed, nuts shifted2.825mm.",
            (
                "Physical enclosure-wall freedom in this Z band was proved in "
                "final_candidate_fit.json."
            ),
            (
                "No production tolerances, heat rejection, strength or cable harness "
                "validation is inferred."
            ),
        ],
        "dimensions_mm": mm,
        "candidates": records,
        "no_overhang_upper_center_x_mm": 395.8,
        "lower_right_R15_socket_is_limiting": limiting,
        "nominal_max_center_x_mm": lo,
        "nominal_max_center_x_0p1_mm_rounded_down": math.floor(lo * 10) / 10,
        "upper_bound_search_mm": [lo, hi],
        "interpretation": (
            "Choose manufacturing/handling margin below the geometric limit; "
            "do not place exactly at a tangent."
        ),
    }
    (HERE / "psu_right_edge_audit.json").write_text(json.dumps(report, indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
