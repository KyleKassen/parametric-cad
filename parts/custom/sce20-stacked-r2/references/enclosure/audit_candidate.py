"""Independent stacked-R2 enclosure audit with exact component B-reps, in mm.

Factory enclosure hardware is measured source geometry. The new carrier and
extension posts are conservative envelopes until their final export is supplied.
No original STEP or R1 model is modified by this audit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
R2 = HERE.parents[1]
R1 = R2.parent / "sce20-layout"
sys.path.insert(0, str(R1 / "references/enclosure"))
from audit_enclosure import bbox  # noqa: E402
from check_candidate import collisions  # noqa: E402

PLACEMENTS = {
    "bedrock": {"translation_mm": [122, 107, 0], "rotation_z_deg": 0},
    "peplink": {"translation_mm": [122, 90, 80], "rotation_z_deg": 0},
    "b210": {"translation_mm": [282, 107, 50], "rotation_z_deg": 180},
    "oz": {"translation_mm": [282, 107, 0], "rotation_z_deg": 0},
    "meanwell": {"translation_mm": [391, 65.6, 0], "rotation_z_deg": 180},
}


def placed(shape: cq.Shape, transform: dict) -> cq.Shape:
    return shape.rotate((0, 0, 0), (0, 0, 1), transform["rotation_z_deg"]).translate(
        transform["translation_mm"]
    )


def main() -> None:
    source = cq.Shape.importBrep(str(R1 / "references/enclosure/source_enclosure.brep"))
    source_solids = source.Solids()
    # Original source rear seat remains fixed for the 6 mm main plate.
    shift = (215.9, 215.9, 106.395)
    enclosure = []
    for i, solid in enumerate(source_solids):
        if i == 60:
            continue
        if i >= 61:
            solid = solid.translate((0, 0, 2.825))
        enclosure.append((f"source_solid_{i}", solid.translate(shift)))
    wall_slab = cq.Workplane("XY").box(504.188, 504.188, 120).translate((215.9, 215.9, 60)).val()
    wall_hits = collisions(wall_slab, enclosure[:3])
    assert not wall_hits
    hardware = enclosure[3:]
    components = {}
    source_paths = {}
    for name, pl in PLACEMENTS.items():
        # These caches were imported from the final R1 manufacturing revisions.
        cache = R1 / "references/enclosure" / f"candidate_{name}_fpe_source.brep"
        source_paths[name] = str(cache)
        components[name] = placed(cq.Shape.importBrep(str(cache)), pl)
    conservative = {
        "peplink_carrier_outer_envelope": cq.Workplane("XY")
        .box(180, 210, 4)
        .translate((122, 107, 72))
        .val(),
    }
    for x in [52, 192]:
        for y in [10, 204]:
            name = f"Peplink_carrier_post_D8_{x}_{y}"
            conservative[name] = cq.Solid.makeCylinder(4, 70, cq.Vector(x, y, 0))
    for x in [214, 350]:
        for y in [46.992, 167.007]:
            name = f"B210_post_D8_{x}_{y}"
            conservative[name] = cq.Solid.makeCylinder(4, 50, cq.Vector(x, y, 0))
    models = {**components, **conservative}
    component_results = {}
    for name, shape in models.items():
        b = shape.BoundingBox()
        assert b.xmin > -36.194 and b.xmax < 467.994
        assert b.ymin > -36.194 and b.ymax < 467.994
        assert b.zmin >= -1e-5 and b.zmax < 120
        hits = collisions(shape, hardware)
        component_results[name] = {
            "bbox_mm": bbox(shape),
            "factory_and_case_hardware_hits": hits,
            "conservative_envelope": name in conservative,
        }
        print(name, len(hits), flush=True)
    sockets = []
    for x in [22.225, 409.575]:
        for y in [22.225, 409.575]:
            tool = cq.Solid.makeCylinder(15, 60, cq.Vector(x, y, 0))
            sockets.append(
                {
                    "center_xy_mm": [x, y],
                    "radius_mm": 15,
                    "height_mm": 60,
                    "hits": collisions(tool, list(models.items())),
                }
            )
    corridors = []
    for name, low, high in [
        ("PSU_terminal_intake_100mm", -34.4, 65.6),
        ("PSU_fan_exhaust_100mm", 366.2, 466.2),
    ]:
        prism = (
            cq.Workplane("XY")
            .box(41, high - low, 85)
            .translate((391, (high + low) / 2, 48.5))
            .val()
        )
        corridors.append(
            {
                "name": name,
                "bbox_mm": bbox(prism),
                "factory_and_case_hardware_hits": collisions(prism, hardware),
                "other_equipment_hits": collisions(
                    prism, [(n, s) for n, s in models.items() if n != "meanwell"]
                ),
                "Y_inner_wall_margin_mm": min(low + 36.195, 467.995 - high),
            }
        )
    report = {
        "schema": "sce20-stacked-r2-enclosure-fit/1",
        "units": "mm",
        "placements": PLACEMENTS,
        "inputs": source_paths,
        "main_panel_thickness_mm": 6,
        "component_face_source_z_mm": -106.395,
        "original_nut_translation_z_mm": 2.825,
        "expanded_wall_slab": {"bbox_mm": bbox(wall_slab), "wall_hits": wall_hits},
        "components_and_supports": component_results,
        "factory_socket_probes": sockets,
        "PSU_corridors": corridors,
        "max_modeled_component_height_mm": max(s.BoundingBox().zmax for s in models.values()),
        "nearest_door_pocket_above_main_panel_mm": 237.5352,
        "nominal_door_margin_mm": 237.5352 - max(s.BoundingBox().zmax for s in models.values()),
        "limitations": [
            "New carrier checked as solid outer envelope; its window reduces occupancy.",
            (
                "New extension posts conservatively represented by diameter 8 mm cylinders "
                "to full height."
            ),
            (
                "This report checks enclosure/factory hardware/socket and PSU corridors, "
                "not every inter-component or mounting interface."
            ),
            (
                "With B210 underside Z50, upper B210 must be removed before the documented "
                "OZ outward cover motion to 79.72 mm."
            ),
            (
                "PSU corridors establish nominal geometry only, not closed-case heat "
                "rejection or side-orientation output rating."
            ),
        ],
    }
    passed = (
        not wall_hits
        and all(not r["factory_and_case_hardware_hits"] for r in component_results.values())
        and all(not s["hits"] for s in sockets)
        and all(
            not c["factory_and_case_hardware_hits"] and not c["other_equipment_hits"]
            for c in corridors
        )
    )
    report["status"] = "PASS" if passed else "FAIL"
    (HERE / "candidate_fit.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(report["status"], "door margin", report["nominal_door_margin_mm"], flush=True)
    assert passed


if __name__ == "__main__":
    main()
