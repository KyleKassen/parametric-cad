"""Independent fixed enclosure and factory service-clearance check, in mm.

Use --fpe-adapters to substitute the exported B210 4 mm and Bedrock 6 mm revisions.
The original candidate's top-left factory nut overlap is primarily in XY and
therefore persists for a stock-thickness increase. Socket diameter is a declared
planning allowance, not an inferred catalog requirement.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cadquery as cq
from audit_enclosure import bbox

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
PANEL_FACE = -106.395
BOX_CACHE = {}
SOLID_CACHE = {}
PLACEMENTS = {
    "meanwell": {"translation": [378, 65.6, 0], "rotation": 180},
    "bedrock": {"translation": [90, 315, 0], "rotation": 0},
    "b210": {"translation": [259, 285, 0], "rotation": 180},
    "peplink": {"translation": [90, 100, 6], "rotation": 0},
    "oz": {"translation": [259, 70, 0], "rotation": 0},
}


def placed(shape: cq.Shape, placement: dict) -> cq.Shape:
    x, y, z = placement["translation"]
    return shape.rotate((0, 0, 0), (0, 0, 1), placement["rotation"]).translate(
        (x - 215.9, y - 215.9, z + PANEL_FACE)
    )


def overlap(a: cq.Shape, b: cq.Shape) -> bool:
    for shape in [a, b]:
        if id(shape) not in BOX_CACHE:
            BOX_CACHE[id(shape)] = (shape, shape.BoundingBox())
    aa, bb = BOX_CACHE[id(a)][1], BOX_CACHE[id(b)][1]
    return all(
        getattr(aa, axis + "min") < getattr(bb, axis + "max") - 1e-6
        and getattr(bb, axis + "min") < getattr(aa, axis + "max") - 1e-6
        for axis in "xyz"
    )


def collisions(a: cq.Shape, other_solids: list[tuple[str, cq.Shape]]) -> list[dict]:
    results = []
    if id(a) not in SOLID_CACHE:
        SOLID_CACHE[id(a)] = (a, a.Solids())
    for name, solid in other_solids:
        if not overlap(a, solid):
            continue
        if id(solid) not in SOLID_CACHE:
            SOLID_CACHE[id(solid)] = (solid, solid.Solids())
        for index, a_solid in enumerate(SOLID_CACHE[id(a)][1]):
            if not overlap(a_solid, solid):
                continue
            for other_index, b_solid in enumerate(SOLID_CACHE[id(solid)][1]):
                if not overlap(a_solid, b_solid):
                    continue
                hit = a_solid.intersect(b_solid)
                if hit.Volume() > 1e-5:
                    results.append(
                        {
                            "other": name,
                            "probe_solid_index": index,
                            "other_solid_index": other_index,
                            "volume_mm3": hit.Volume(),
                            "bbox_mm": bbox(hit),
                        }
                    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--placements-json", type=Path)
    parser.add_argument("--out-json", type=Path, default=HERE / "candidate_fit.json")
    parser.add_argument("--fpe-adapters", action="store_true")
    args = parser.parse_args()
    if args.placements_json:
        raw = json.loads(args.placements_json.read_text())
        raw = raw.get("placements", raw)
        PLACEMENTS.update(
            {
                name: {
                    "translation": record.get("translation", record.get("translation_mm")),
                    "rotation": record.get("rotation", record.get("rotation_z_deg")),
                }
                for name, record in raw.items()
            }
        )
    interfaces = json.loads((HERE.parent / "interfaces/mount_interfaces.json").read_text())
    source = cq.Shape.importBrep(str(HERE / "source_enclosure.brep"))
    source_solids = source.Solids()
    # Prove a simple slab once instead of intersecting many complex component
    # solids with the broad bounding box of the enclosure's folded rear shell.
    free_slab = (
        cq.Workplane("XY").box(504.188, 504.188, 100).translate((0, 0, PANEL_FACE + 50)).val()
    )
    wall_proof = collisions(free_slab, [(f"source_solid_{i}", source_solids[i]) for i in [0, 1, 2]])
    assert not wall_proof
    obstacles = [
        (f"enclosure_source_solid_{i}", solid.translate((0, 0, 2.825)) if i >= 61 else solid)
        for i, solid in enumerate(source_solids)
        if i not in {0, 1, 2, 60}
    ]
    models = {}
    model_inputs = {}
    for name, placement in PLACEMENTS.items():
        if args.fpe_adapters and name in {"bedrock", "b210"}:
            prefix = "Bedrock" if name == "bedrock" else "B210"
            path = HERE.parents[1] / "exports" / f"{prefix}_FPE_R1_device_adapter.step"
        elif name in interfaces["components"]:
            path = ROOT / interfaces["components"][name]["integration_step"]
        else:
            path = HERE.parent / "router_oz" / f"{name}_normalized.step"
        cache_name = (
            f"candidate_{name}_fpe_source.brep"
            if args.fpe_adapters
            else (f"candidate_{name}_source.brep")
        )
        cache = HERE / cache_name
        if cache.exists():
            shape = cq.Shape.importBrep(str(cache))
        else:
            shape = cq.importers.importStep(str(path)).val()
            shape.exportBrep(str(cache))
        models[name] = placed(shape, placement)
        model_inputs[name] = str(path)
        bounds = models[name].BoundingBox()
        assert bounds.xmin > -252.094 and bounds.xmax < 252.094
        assert bounds.ymin > -252.094 and bounds.ymax < 252.094
        assert bounds.zmin >= PANEL_FACE - 1e-5 and bounds.zmax < PANEL_FACE + 100
    component_results = {}
    for name, model in models.items():
        print(f"Checking fixed obstacles: {name}", flush=True)
        component_results[name] = {
            "source_bbox_mm": bbox(model),
            "fixed_collisions": collisions(model, obstacles),
        }
    tools = []
    for x in [-193.675, 193.675]:
        for y in [-193.675, 193.675]:
            tool = cq.Solid.makeCylinder(15, 60, cq.Vector(x, y, PANEL_FACE))
            hits = collisions(tool, list(models.items()))
            tools.append(
                {
                    "center_lowerleft_xy_mm": [x + 215.9, y + 215.9],
                    "planning_radius_mm": 15,
                    "planning_height_mm": 60,
                    "component_intersections": hits,
                }
            )
    air = []
    for reservation in interfaces["components"]["meanwell"]["reservations"]:
        b = reservation["bbox_mm"]
        prism = (
            cq.Workplane("XY")
            .box(b["x"][1] - b["x"][0], b["y"][1] - b["y"][0], b["z"][1] - b["z"][0])
            .translate(tuple((b[a][1] + b[a][0]) / 2 for a in "xyz"))
            .val()
        )
        prism = placed(prism, PLACEMENTS["meanwell"])
        air.append(
            {
                "name": reservation["name"],
                "source_bbox_mm": bbox(prism),
                "enclosure_and_factory_hardware_collisions": collisions(prism, obstacles),
                "other_component_collisions": collisions(
                    prism, [(k, v) for k, v in models.items() if k != "meanwell"]
                ),
                "nearest_inner_y_wall_gap_mm": min(
                    prism.BoundingBox().ymin + 252.095, 252.095 - prism.BoundingBox().ymax
                ),
            }
        )
    # At the PSU's Z band both sidewalls are flat, without a front flange.
    wall_band = {
        "source_z_mm": [PANEL_FACE + 6, PANEL_FACE + 91],
        "source_x_mm": [-252.095, 252.095],
        "source_y_mm": [-252.095, 252.095],
        "lowerleft_panel_xy_mm": [-36.195, 467.995],
        "evidence": "solid0 faces45/67; solid1 face4; solid2 face10 in panel_geometry.json",
    }
    report = {
        "schema": "enclosure-candidate-fit/1",
        "units": "mm",
        "placements": PLACEMENTS,
        "integration_model_inputs": model_inputs,
        "FPE_standard_stock_adapters": args.fpe_adapters,
        "panel_thickness_mm": 6,
        "source_component_face_z_mm": PANEL_FACE,
        "original_nut_translation_z_mm": 2.825,
        "fixed_studs_translated": False,
        "components": component_results,
        "factory_socket_service_probes": tools,
        "PSU_planning_corridors": air,
        "PSU_wall_band": wall_band,
        "wall_slab_boolean_proof": {"bbox_mm": bbox(free_slab), "hits": wall_proof},
        "notes": [
            (
                "The 100 mm corridors are planning envelopes from the source adapter design, "
                "not measured air paths or CFD results."
            ),
            "All clearance values are nominal CAD, without production tolerance allowance.",
            (
                "The best centered straight 500.6 mm combined PSU + air-corridor span "
                "has only 1.795 mm nominal gap to each 504.19 mm-separated inner wall. "
                "Translation cannot increase the smaller gap."
            ),
            (
                "Closed steel walls at corridor ends do not certify external airflow "
                "or enclosure heat rejection."
            ),
        ],
    }
    args.out_json.write_text(json.dumps(report, indent=2), encoding="utf8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
