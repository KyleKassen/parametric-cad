"""Audit the supplied enclosure STEP in source coordinates, in millimetres.

Original vendor geometry is imported read-only; every measurement retains the
zero-based import solid and face indices so the evidence is reproducible.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Plane

HERE = Path(__file__).resolve().parent
SOURCE = Path(
    "C:/Users/KyleKassen/OneDrive - Ataero/Shared Documents - Ataero San Antonio/"
    "06 R&D Products/NEW R&D/04 Shared Engineering/02 Component Library/"
    "Enclosures & Transport/Saginaw SCE-20H2010LP CAD Package/SCE-20H2010LP.stp"
)


def bbox(shape: cq.Shape) -> dict:
    b = shape.BoundingBox()
    return {a: [round(getattr(b, a + "min"), 7), round(getattr(b, a + "max"), 7)] for a in "xyz"}


def face_record(face: cq.Face, index: int) -> dict:
    surface = BRepAdaptor_Surface(face.wrapped)
    result = {
        "face_index_zero_based": index,
        "type": str(surface.GetType()),
        "area_mm2": face.Area(),
        "bbox_mm": bbox(face),
    }
    if surface.GetType() == GeomAbs_Plane:
        result["normal"] = list(face.normalAt().toTuple())
        result["wires"] = []
        for wire in face.Wires():
            edges = []
            for edge in wire.Edges():
                curve = BRepAdaptor_Curve(edge.wrapped)
                record = {
                    "type": str(curve.GetType()),
                    "length_mm": edge.Length(),
                    "bbox_mm": bbox(edge),
                    "vertices_mm": [list(v.toTuple()) for v in edge.Vertices()],
                }
                if curve.GetType() == GeomAbs_Circle:
                    circle = curve.Circle()
                    loc = circle.Location()
                    record.update(radius_mm=circle.Radius(), center_mm=[loc.X(), loc.Y(), loc.Z()])
                edges.append(record)
            result["wires"].append({"bbox_mm": bbox(wire), "edges": edges})
    elif surface.GetType() == GeomAbs_Cylinder:
        cylinder = surface.Cylinder()
        loc = cylinder.Axis().Location()
        axis = cylinder.Axis().Direction()
        result.update(
            radius_mm=cylinder.Radius(),
            axis_location_mm=[loc.X(), loc.Y(), loc.Z()],
            axis_direction=[axis.X(), axis.Y(), axis.Z()],
        )
    return result


def main() -> None:
    shape = cq.importers.importStep(str(SOURCE)).val()
    solids = shape.Solids()
    summary = []
    for i, solid in enumerate(solids):
        record = {
            "solid_index_zero_based": i,
            "bbox_mm": bbox(solid),
            "volume_mm3": solid.Volume(),
            "face_count": len(solid.Faces()),
            "valid": solid.isValid(),
        }
        summary.append(record)
    report = {
        "source": str(SOURCE),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "units": "mm (OCCT imports declared STEP units)",
        "bbox_mm": bbox(shape),
        "solids": summary,
    }
    (HERE / "solid_inventory.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(json.dumps(report, indent=2), flush=True)
    candidates = []
    for i, solid in enumerate(solids):
        b = solid.BoundingBox()
        sizes = sorted([b.xlen, b.ylen, b.zlen])
        if sizes[0] < 6 and sizes[1] > 400:
            rec = {**summary[i], "faces": [face_record(f, j) for j, f in enumerate(solid.Faces())]}
            candidates.append(rec)
            cq.exporters.export(solid, str(HERE / f"candidate_solid_{i}.step"))
    (HERE / "panel_candidates.json").write_text(json.dumps(candidates, indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
