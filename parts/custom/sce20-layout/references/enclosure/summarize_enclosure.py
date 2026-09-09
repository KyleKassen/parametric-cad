"""Reduce measured STEP faces into the replaceable panel mounting contract.

Coordinates and dimensions are millimetres. The cavity proof is a conservative
rectangular volume, excluding the four factory panel retainers whose individual
bounding boxes are retained as local keepouts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cadquery as cq
from audit_enclosure import SOURCE, bbox
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane

HERE = Path(__file__).resolve().parent


def main() -> None:
    inventory = json.loads((HERE / "solid_inventory.json").read_text())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == inventory["source_sha256"]
    panel = json.loads((HERE / "panel_candidates.json").read_text())[0]
    face = panel["faces"][0]
    assert panel["solid_index_zero_based"] == 60
    corners = sorted(
        {round(e["radius_mm"], 7) for e in face["wires"][0]["edges"] if "radius_mm" in e}
    )
    holes = []
    for wire in face["wires"][1:]:
        edge = wire["edges"][0]
        assert all(e["type"].endswith("Circle") for e in wire["edges"])
        center = [round(v, 7) for v in edge["center_mm"][:2]]
        holes.append(
            {
                "center_xy_mm": center,
                "diameter_mm": round(edge["radius_mm"] * 2, 7),
                "type": "round through hole",
            }
        )
    shape = cq.importers.importStep(str(SOURCE)).val()
    shape.exportBrep(str(HERE / "source_enclosure.brep"))
    solids = shape.Solids()
    big_planes = []
    for i in [0, 1, 2, 3, 9]:
        for j, f in enumerate(solids[i].Faces()):
            surface = BRepAdaptor_Surface(f.wrapped)
            if surface.GetType() == GeomAbs_Plane and f.Area() > 10000:
                big_planes.append(
                    {
                        "solid_index_zero_based": i,
                        "face_index_zero_based": j,
                        "normal": list(f.normalAt().toTuple()),
                        "bbox_mm": bbox(f),
                        "area_mm2": f.Area(),
                    }
                )
    local_keepouts = [inventory["solids"][i] for i in list(range(44, 48)) + list(range(61, 65))]
    z_low = -109.22 + 0.0001
    z_high = 131.1402 - 0.0001
    probe = (
        cq.Workplane("XY")
        .box(431.8, 431.8, z_high - z_low)
        .translate((0, 0, (z_low + z_high) / 2))
        .val()
    )
    skip = {44, 45, 46, 47, 60, 61, 62, 63, 64}
    hits = []
    for i, solid in enumerate(solids):
        if i in skip:
            continue
        b = solid.BoundingBox()
        if (
            b.xmax < -215.9
            or b.xmin > 215.9
            or b.ymax < -215.9
            or b.ymin > 215.9
            or b.zmin > z_high
            or b.zmax < z_low
        ):
            continue
        hit = solid.intersect(probe)
        if hit.Volume() > 1e-5:
            hits.append(
                {
                    "solid_index_zero_based": i,
                    "intersection_volume_mm3": hit.Volume(),
                    "bbox_mm": bbox(hit),
                }
            )
    factory_stud_cylinders = []
    for i in [44, 61]:
        for j, f in enumerate(solids[i].Faces()):
            surface = BRepAdaptor_Surface(f.wrapped)
            if surface.GetType() == GeomAbs_Cylinder:
                c = surface.Cylinder()
                factory_stud_cylinders.append(
                    {
                        "solid_index_zero_based": i,
                        "face_index_zero_based": j,
                        "diameter_mm": c.Radius() * 2,
                        "bbox_mm": bbox(f),
                    }
                )
    report = {
        "source": inventory["source"],
        "source_sha256": inventory["source_sha256"],
        "units": "mm",
        "identity_evidence": {
            "step_product_name": "SUBPANEL",
            "step_product_entity": "#108856",
            "solid_index_zero_based": 60,
            "face_index_zero_based": 0,
            "panel_valid": panel["valid"],
        },
        "panel": {
            "width_mm": 431.8,
            "height_mm": 431.8,
            "source_thickness_mm": 3.175,
            "corner_radius_mm": corners[0],
            "center_xy_mm": [0, 0],
            "source_rear_face_z_mm": -112.395,
            "source_component_face_z_mm": -109.22,
            "holes": holes,
        },
        "transforms": {
            "panel_center_component_face_origin_to_source_translation_mm": [0, 0, -109.22],
            "panel_lower_left_component_face_origin_to_source_translation_mm": [
                -215.9,
                -215.9,
                -109.22,
            ],
            "rotation_degrees": [0, 0, 0],
            "normal_toward_door_source": [0, 0, 1],
            "source_x_positive": "right as viewed through open door",
            "source_y_positive": "up as viewed through open door",
            "if_new_thickness_rear_face_retained": (
                "new_component_face_z_mm = -112.395 + new_thickness_mm"
            ),
        },
        "keepouts": {
            "factory_subpanel_stud_and_nut_solids": local_keepouts,
            "factory_panel_stud_top_source_z_mm": -96.52,
            "factory_nut_top_source_z_mm": -100.6856,
            "factory_nut_bounding_radius_mm": 9.4615,
            "source_document_pocket_solid_index_zero_based": 9,
            "source_document_pocket_bbox_mm": inventory["solids"][9]["bbox_mm"],
            "nearest_door_assembly_z_over_panel_mm": 131.1402,
            "clearance_above_source_panel_to_document_pocket_mm": 240.3602,
        },
        "conservative_cavity_probe": {
            "source_bbox_mm": bbox(probe),
            "excluded_solids_zero_based": sorted(skip),
            "remaining_intersections": hits,
            "passed": not hits,
            "meaning": (
                "No enclosure material intersects this rectangular volume except excluded "
                "original subpanel and four factory subpanel stud/nut assemblies. "
                "Keep their local boxes clear. Actual free shape varies beyond this proven volume."
            ),
        },
        "source_large_planar_faces": big_planes,
        "factory_stud_and_nut_cylinders": factory_stud_cylinders,
        "sales_drawing": {
            "file": str(SOURCE.with_name("SCE-20H2010LP Sales Drawing.pdf")),
            "visually_reviewed": True,
            "mounting_pitch_in": 15.25,
            "nominal_usable_depth_in": 10.29,
            "note": (
                "Sales drawing nominal usable depth does not account for the door document "
                "pocket over its local XY footprint. STEP local clearance governs layout."
            ),
        },
        "limitations": [
            (
                "STEP establishes geometry only, not material strength, allowable panel load, "
                "vibration duty or fastener torque."
            ),
            (
                "No screenshot was available in the visible user request. The named SUBPANEL "
                "product and unique 431.8 mm square flat solid were identified directly from "
                "the supplied STEP."
            ),
            (
                "Increasing panel thickness while retaining the rear mounting face reduces "
                "component clearance and available original enclosure stud projection by "
                "exactly the thickness increase."
            ),
        ],
    }
    (HERE / "panel_geometry.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(
        json.dumps(
            {"panel": report["panel"], "probe_passed": not hits, "large_planes": big_planes},
            indent=2,
        )
    )
    assert not hits


if __name__ == "__main__":
    main()
