"""Cross-check exported hole axes and manufacturing DXF against fresh STEP.

This checks geometry and drafting consistency, not physical tolerances.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import cadquery as cq
import ezdxf
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

HERE = Path(__file__).resolve().parent


def main() -> None:
    checks = []

    def check(name: str, condition: bool, measured=None) -> None:
        checks.append({"check": name, "pass": bool(condition), "measured": measured})

    with tempfile.TemporaryDirectory(prefix="b210_dxf_") as temp:
        work = Path(temp)
        for name in ("plate_D1.step", "plate_profile_mm.dxf"):
            shutil.copyfile(HERE / "exports" / name, work / name)
        plate = cq.importers.importStep(str(work / "plate_D1.step")).val()
        holes = []
        for face in plate.Faces():
            surface = BRepAdaptor_Surface(face.wrapped)
            if surface.GetType() == GeomAbs_Cylinder:
                cylinder = surface.Cylinder()
                point = cylinder.Axis().Location()
                b = face.BoundingBox()
                holes.append(
                    {
                        "x": point.X(),
                        "y": point.Y(),
                        "diameter": 2 * cylinder.Radius(),
                        "zmin": b.zmin,
                        "zmax": b.zmax,
                    }
                )
        source = json.loads(
            (HERE / "references/geometry/under_feet_audit.json").read_text(encoding="utf-8")
        )
        # Fresh audit's original-foot stations independently establish the radio axes.
        stations = source["stations"]
        for i, station in enumerate(stations, 1):
            x, y = station["axis_xy_mm"]
            matches = [
                h
                for h in holes
                if abs(h["diameter"] - 3.4) < 1e-6
                and abs(h["x"] - x) < 1e-6
                and abs(h["y"] - y) < 1e-6
            ]
            check(
                f"Exported housing bore {i} matches fresh vendor axis", len(matches) == 1, matches
            )
            if matches:
                h = matches[0]
                check(
                    f"Exported housing bore {i} straight throat",
                    abs(h["zmin"] - 1.35) < 1e-6 and abs(h["zmax"] - 3.4) < 1e-6,
                    h["zmax"] - h["zmin"],
                )
        expected_studs = [(x, y) for x in (-68.0, 68.0) for y in (-60.0075, 60.0075)]
        for x, y in expected_studs:
            match = [
                h
                for h in holes
                if abs(h["diameter"] - 3.8) < 1e-6
                and abs(h["x"] - x) < 1e-6
                and abs(h["y"] - y) < 1e-6
            ]
            check(f"Exported stud bore {x},{y}", len(match) == 1, match)
        dxf = cq.importers.importDXF(str(work / "plate_profile_mm.dxf"), include=["PROFILE"])
        dxf_solid = dxf.extrude(3.5).val()
        # Drill layers describe separate subtractive operations. Do not silently
        # accept only the first object returned by a multi-layer DXF import.
        drill_doc = ezdxf.readfile(work / "plate_profile_mm.dxf")
        drill_circles = list(drill_doc.modelspace().query("CIRCLE"))
        check("DXF has eight drill operations", len(drill_circles) == 8)
        for drill in drill_circles:
            c = drill.dxf.center
            tool = cq.Solid.makeCylinder(drill.dxf.radius, 3.5, cq.Vector(c.x, c.y, 0))
            dxf_solid = dxf_solid.cut(tool)
        check(
            "Profile DXF forms one valid manufacturable blank",
            dxf_solid.isValid() and len(dxf_solid.Solids()) == 1,
        )
        slab = cq.Workplane("XY").box(200, 200, 0.02).translate((0, 0, 2)).val()
        a, b = plate.intersect(slab), dxf_solid.intersect(slab)
        difference = sum(s.Volume() for s in a.cut(b).Solids())
        difference += sum(s.Volume() for s in b.cut(a).Solids())
        check(
            "DXF outline and eight bores equal STEP at straight midsection",
            difference < 0.00001,
            difference,
        )
        for name, layer, radius in [
            ("plate_underside_machining_mm.dxf", "CSK_REF", 3.05),
            ("FPE_stud_pattern_mm.dxf", "PANEL_STUD_CENTERS", 1.5),
        ]:
            doc = ezdxf.readfile(HERE / "exports" / name)
            circles = [e for e in doc.modelspace().query("CIRCLE") if e.dxf.layer == layer]
            xy = [(round(e.dxf.center.x, 4), round(e.dxf.center.y, 4)) for e in circles]
            expected = (
                [(round(s["axis_xy_mm"][0], 4), round(s["axis_xy_mm"][1], 4)) for s in stations]
                if layer == "CSK_REF"
                else expected_studs
            )
            check(
                name + " reference markers",
                len(circles) == 4
                and sorted(xy) == sorted(expected)
                and all(abs(e.dxf.radius - radius) < 1e-8 for e in circles),
                xy,
            )
    report = {
        "status": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "checks": checks,
        "count": len(checks),
    }
    (HERE / "references/manufacturing_verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report))
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
