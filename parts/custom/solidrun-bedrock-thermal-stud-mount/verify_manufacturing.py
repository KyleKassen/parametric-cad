"""Independently inspect exported T1 STEP and manufacturing DXF geometry.

Run after model.py. No model functions are imported. Missing exports produce a
NOT_READY report; geometric mismatches produce FAIL and a nonzero exit status.
This is a nominal CAD/drafting check, not a manufacturing or thermal test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import tempfile
from pathlib import Path

import cadquery as cq
import ezdxf
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane

HERE = Path(__file__).resolve().parent
TOL = 2e-5
VOLUME_TOL = 2e-5


def volume(shape: cq.Shape) -> float:
    return sum(abs(solid.Volume()) for solid in shape.Solids())


def difference(a: cq.Shape, b: cq.Shape) -> float:
    return volume(a.cut(b)) + volume(b.cut(a))


def cylinder(radius: float, height: float, x: float, y: float, z: float) -> cq.Shape:
    return cq.Solid.makeCylinder(radius, height, cq.Vector(x, y, z))


def round_rectangle(width: float, length: float, radius: float, height: float) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .sketch()
        .rect(width, length)
        .vertices()
        .fillet(radius)
        .finalize()
        .extrude(height)
        .val()
    )


def points_match(a: list, b: list) -> bool:
    aa = sorted((round(x, 5), round(y, 5)) for x, y in a)
    bb = sorted((round(x, 5), round(y, 5)) for x, y in b)
    return aa == bb


def stud_points(p: dict) -> list[tuple[float, float]]:
    angle = math.radians(p["stud_pattern_rotation_deg"])
    return [
        (
            x * math.cos(angle) - y * math.sin(angle) + p["stud_pattern_center_x"],
            x * math.sin(angle) + y * math.cos(angle) + p["stud_pattern_center_y"],
        )
        for x in (-p["stud_pitch_x"] / 2, p["stud_pitch_x"] / 2)
        for y in (-p["stud_pitch_y"] / 2, p["stud_pitch_y"] / 2)
    ]


def analytic_faces(plate: cq.Shape) -> tuple[list, list, list]:
    cylinders, cones, planes = [], [], []
    for face in plate.Faces():
        surf = BRepAdaptor_Surface(face.wrapped)
        bounds = face.BoundingBox()
        row = {"zmin": bounds.zmin, "zmax": bounds.zmax, "area": face.Area()}
        if surf.GetType() in (GeomAbs_Cylinder, GeomAbs_Cone):
            primitive = surf.Cylinder() if surf.GetType() == GeomAbs_Cylinder else surf.Cone()
            axis = primitive.Axis()
            if abs(axis.Direction().Z()) < 1 - 1e-8:
                continue
            row.update(x=axis.Location().X(), y=axis.Location().Y())
            if surf.GetType() == GeomAbs_Cylinder:
                row["diameter"] = 2 * primitive.Radius()
                cylinders.append(row)
            else:
                row["half_angle_deg"] = abs(math.degrees(primitive.SemiAngle()))
                row["bbox_diameter"] = max(bounds.xlen, bounds.ylen)
                cones.append(row)
        elif surf.GetType() == GeomAbs_Plane:
            if abs(surf.Plane().Axis().Direction().Z()) > 1 - 1e-8:
                row["z"] = (bounds.zmin + bounds.zmax) / 2
                planes.append(row)
    return cylinders, cones, planes


def find_one(folder: Path, patterns: tuple[str, ...]) -> Path | None:
    for pattern in patterns:
        found = sorted(folder.glob(pattern))
        if len(found) == 1:
            return found[0]
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, default=HERE / "exports")
    args = parser.parse_args()
    export_dir = args.exports.resolve()
    export_dir.mkdir(parents=True, exist_ok=True)
    pfile = HERE / "params.json"
    p = json.loads(pfile.read_text(encoding="utf-8-sig"))
    checks: list[dict] = []
    evidence: dict = {}

    def check(name: str, condition: bool, measured=None) -> None:
        checks.append({"check": name, "pass": bool(condition), "measured": measured})

    def write_report(status: str, missing: list[str] | None = None) -> None:
        report = {
            "status": status,
            "scope": "Independent nominal STEP/DXF manufacturing geometry inspection",
            "limitations": (
                "Does not certify actual machining, screw compatibility, preload, "
                "thread/stud capacity, thermal performance or physical flatness."
            ),
            "params_sha256": hashlib.sha256(pfile.read_bytes()).hexdigest(),
            "checks": checks,
            "count": len(checks),
            "evidence": evidence,
            "missing": missing or [],
        }
        path = export_dir / "manufacturing_verification.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"status": status, "count": len(checks), "report": str(path)}))
        for failure in (item for item in checks if not item["pass"]):
            print(json.dumps(failure))

    paths = {
        "plate STEP": find_one(export_dir, ("plate_T1.step", "plate.step", "plate*.step")),
        "profile DXF": find_one(export_dir, ("plate_profile_mm.dxf", "*profile*.dxf")),
        "underside DXF": find_one(
            export_dir, ("plate_underside_machining_mm.dxf", "*underside*.dxf")
        ),
        "top pocket DXF": find_one(export_dir, ("thermal_top_pocket_contour_mm.dxf",)),
        "bottom pocket DXF": find_one(export_dir, ("thermal_bottom_pocket_contour_mm.dxf",)),
        "FPE pattern DXF": find_one(export_dir, ("FPE_stud_pattern_mm.dxf", "*stud*pattern*.dxf")),
    }
    missing = [label for label, path in paths.items() if path is None]
    if missing:
        write_report("NOT_READY", missing)
        raise SystemExit(2)

    evidence["inputs"] = {
        label: {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        for label, path in paths.items()
    }
    with tempfile.TemporaryDirectory(prefix="bedrock_manufacturing_") as temp:
        work = Path(temp)
        local = {}
        for label, path in paths.items():
            local[label] = work / path.name
            shutil.copyfile(path, local[label])
        plate_path = local["plate STEP"]
        plate = cq.importers.importStep(str(plate_path)).val()
        check("STEP is one valid solid", plate.isValid() and len(plate.Solids()) == 1)
        check(
            "STEP declares millimeter length units",
            bool(
                re.search(
                    r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)",
                    plate_path.read_text(encoding="ascii", errors="replace"),
                )
            ),
        )
        bounds = plate.BoundingBox()
        measured_bounds = [
            bounds.xmin,
            bounds.xmax,
            bounds.ymin,
            bounds.ymax,
            bounds.zmin,
            bounds.zmax,
        ]
        expected_bounds = [
            -p["plate_width"] / 2,
            p["plate_width"] / 2,
            -p["plate_length"] / 2,
            p["plate_length"] / 2,
            0,
            p["plate_thickness"],
        ]
        check(
            "STEP scale and datum bounds",
            all(abs(a - b) < TOL for a, b in zip(measured_bounds, expected_bounds, strict=True)),
            measured_bounds,
        )
        evidence["plate_volume_mm3"] = volume(plate)

        # Re-export the imported part and reopen it. Neither operation imports model.py.
        roundtrip_path = work / "independent_roundtrip.step"
        cq.exporters.export(plate, str(roundtrip_path))
        roundtrip = cq.importers.importStep(str(roundtrip_path)).val()
        check(
            "Second STEP roundtrip validity", roundtrip.isValid() and len(roundtrip.Solids()) == 1
        )
        check(
            "Second STEP roundtrip solid equality",
            difference(plate, roundtrip) < VOLUME_TOL,
            difference(plate, roundtrip),
        )

        source = json.loads(
            (HERE / "references/geometry/critical_dimensions.json").read_text(encoding="utf-8-sig")
        )
        housing = source["hole_axes_xy_mm"]
        studs = stud_points(p)
        check(
            "Six housing parameters match fresh vendor axes",
            len(housing) == 6 and points_match(housing, p["housing_points"]),
            housing,
        )
        check(
            "Fresh vendor audit has the intended source hash",
            source["source_sha256"] == p["input_step_sha256"],
        )
        cylinders, cones, planes = analytic_faces(plate)
        csk_depth = (
            (p["countersink_diameter_reference"] - p["housing_clearance_diameter"])
            / 2
            / math.tan(math.radians(p["countersink_angle_deg"] / 2))
        )
        thickness = p["plate_thickness"]
        for family, points, diameter, zmin, zmax in (
            (
                "Housing",
                housing,
                p["housing_clearance_diameter"],
                csk_depth,
                thickness - p["bore_deburr"],
            ),
            (
                "Stud",
                studs,
                p["stud_clearance_diameter"],
                p["bore_deburr"],
                thickness - p["bore_deburr"],
            ),
        ):
            matches = [f for f in cylinders if abs(f["diameter"] - diameter) < TOL]
            check(f"{family} bore count", len(matches) == len(points), len(matches))
            for index, (x, y) in enumerate(points, 1):
                at_axis = [f for f in matches if abs(f["x"] - x) < TOL and abs(f["y"] - y) < TOL]
                check(f"{family} bore {index} axis", len(at_axis) == 1, at_axis)
                if at_axis:
                    face = at_axis[0]
                    check(
                        f"{family} bore {index} straight throat",
                        abs(face["zmin"] - zmin) < TOL and abs(face["zmax"] - zmax) < TOL,
                        {"measured": [face["zmin"], face["zmax"]], "expected": [zmin, zmax]},
                    )
        for index, (x, y) in enumerate(housing, 1):
            at_axis = [
                f
                for f in cones
                if abs(f["x"] - x) < TOL and abs(f["y"] - y) < TOL and abs(f["zmin"]) < TOL
            ]
            check(
                f"Countersink {index} angle, opening and depth",
                len(at_axis) == 1
                and abs(at_axis[0]["zmax"] - csk_depth) < TOL
                and abs(at_axis[0]["bbox_diameter"] - p["countersink_diameter_reference"]) < TOL
                and abs(at_axis[0]["half_angle_deg"] * 2 - p["countersink_angle_deg"]) < TOL,
                at_axis,
            )

        depth = p["thermal_pocket_depth"]
        for label, z in (
            ("Lower seating datum", 0),
            ("Lower pocket floor", depth),
            ("Upper pocket floor", thickness - depth),
            ("Upper contact datum", thickness),
        ):
            face_area = sum(f["area"] for f in planes if abs(f["z"] - z) < TOL)
            check(label + " is a planar face", face_area > 1, {"z_mm": z, "area_mm2": face_area})

        # Verify both pocket outlines and full-height contact islands independently.
        sample_h = depth / 3
        field = round_rectangle(
            p["thermal_field_width"],
            p["thermal_field_length"],
            p["thermal_field_corner_radius"],
            sample_h,
        )
        vent_y = p.get("thermal_vent_y_positions", [])
        for y in vent_y:
            x0, x1 = p["thermal_vent_start_x"], p["thermal_vent_end_x"]
            vent = round_rectangle(x1 - x0, p["thermal_vent_width"], 0.25, sample_h)
            field = field.fuse(vent.translate(((x0 + x1) / 2, y, 0)))
        check("Two escape grooves per thermal face", len(vent_y) == 2, vent_y)
        nominal_stock = round_rectangle(
            p["plate_width"], p["plate_length"], p["corner_radius"], thickness
        )
        nominal_stock = (
            cq.Workplane(obj=nominal_stock).faces(">Z or <Z").edges().chamfer(p["edge_break"]).val()
        )
        for label, land_diameter, z in (
            ("Lower", p["underside_countersink_land_diameter"], depth / 3),
            ("Upper", p["tile_contact_land_diameter"], thickness - 2 * depth / 3),
        ):
            tool = field.translate((0, 0, z)).intersect(nominal_stock)
            expected = tool
            for x, y in housing:
                expected = expected.cut(cylinder(land_diameter / 2, sample_h, x, y, z))
            # Expected is the removed pocket region; no material may remain there.
            check(
                label + " recessed field is fully removed",
                volume(plate.intersect(expected)) < VOLUME_TOL,
                volume(plate.intersect(expected)),
            )
            lands = tool.cut(expected)
            for x, y in housing:
                if label == "Lower":
                    r0 = p["countersink_diameter_reference"] / 2 - z
                    drill = cq.Solid.makeCone(r0, r0 - sample_h, sample_h, cq.Vector(x, y, z))
                else:
                    # Top deburr has its own exact cone; include its varying radius.
                    radius = p["housing_clearance_diameter"] / 2
                    r0 = radius + max(0, z - (thickness - p["bore_deburr"]))
                    r1 = radius + max(0, z + sample_h - (thickness - p["bore_deburr"]))
                    drill = cq.Solid.makeCone(r0, r1, sample_h, cq.Vector(x, y, z))
                lands = lands.cut(drill)
            measured = plate.intersect(tool)
            error = difference(measured, lands)
            check(
                label + " contact land pattern equals nominal CAD section",
                error < VOLUME_TOL,
                error,
            )

        docs = {
            label: ezdxf.readfile(path) for label, path in local.items() if path.suffix == ".dxf"
        }
        evidence["dxf_layers"] = {}
        for label, doc in docs.items():
            check(
                label + " declares millimeters",
                doc.header.get("$INSUNITS") == 4,
                doc.header.get("$INSUNITS"),
            )
            evidence["dxf_layers"][label] = sorted({e.dxf.layer for e in doc.modelspace()})
        profile_doc = docs["profile DXF"]
        profile_layers = [
            name for name in evidence["dxf_layers"]["profile DXF"] if name.upper() == "PROFILE"
        ]
        check("Profile DXF has explicit PROFILE layer", len(profile_layers) == 1, profile_layers)
        if profile_layers:
            blank = cq.importers.importDXF(str(local["profile DXF"]), include=profile_layers)
            blank = blank.extrude(thickness).val()
            circles = list(profile_doc.modelspace().query("CIRCLE"))
            drills = [
                e
                for e in circles
                if abs(e.dxf.radius * 2 - p["housing_clearance_diameter"]) < TOL
                or abs(e.dxf.radius * 2 - p["stud_clearance_diameter"]) < TOL
            ]
            check(
                "Profile DXF has ten through-drill circles only", len(circles) == len(drills) == 10
            )
            for family, points, diameter in (
                ("Housing", housing, p["housing_clearance_diameter"]),
                ("Stud", studs, p["stud_clearance_diameter"]),
            ):
                selected = [e for e in drills if abs(e.dxf.radius * 2 - diameter) < TOL]
                xy = [(e.dxf.center.x, e.dxf.center.y) for e in selected]
                check(f"Profile DXF {family.lower()} drill axes", points_match(xy, points), xy)
            for drill in drills:
                point = drill.dxf.center
                blank = blank.cut(cylinder(drill.dxf.radius, thickness, point.x, point.y, 0))
            slab = cq.Solid.makeBox(
                p["plate_width"] + 4,
                p["plate_length"] + 4,
                0.02,
                cq.Vector(
                    -p["plate_width"] / 2 - 2, -p["plate_length"] / 2 - 2, thickness / 2 - 0.01
                ),
            )
            error = difference(blank.intersect(slab), plate.intersect(slab))
            check(
                "Profile DXF outline and all ten holes equal STEP midsection",
                error < VOLUME_TOL,
                error,
            )

        # Layer names are explicit to prevent treating reference circles as drills.
        for doc_label, layer, expected_points, radius in (
            ("underside DXF", "CSK_REF", housing, p["countersink_diameter_reference"] / 2),
            ("FPE pattern DXF", "PANEL_STUD_CENTERS", studs, p["stud_diameter"] / 2),
        ):
            entities = [
                e for e in docs[doc_label].modelspace().query("CIRCLE") if e.dxf.layer == layer
            ]
            xy = [(e.dxf.center.x, e.dxf.center.y) for e in entities]
            check(
                doc_label + " " + layer + " markers",
                points_match(xy, expected_points)
                and all(abs(e.dxf.radius - radius) < TOL for e in entities),
                xy,
            )
        # Pocket files contain the actual closed cut-region wires, including the
        # land exclusions. Import every wire rather than only an outside boundary.
        for label, land_diameter in (
            ("top pocket DXF", p["tile_contact_land_diameter"]),
            ("bottom pocket DXF", p["underside_countersink_land_diameter"]),
        ):
            # DXF represents the largest pocket-floor planar footprint. The
            # escape grooves terminate on the sloped outer rim, so the floor
            # outline is not a constant-depth 3D prism at the last 0.05 mm.
            offset = max(0, p["edge_break"] - depth)
            floor_outline = round_rectangle(
                p["plate_width"] - 2 * offset,
                p["plate_length"] - 2 * offset,
                p["corner_radius"] - offset,
                sample_h,
            )
            expected = field.intersect(floor_outline)
            for x, y in housing:
                expected = expected.cut(cylinder(land_diameter / 2, sample_h, x, y, 0))
            imported = cq.importers.importDXF(str(local[label])).extrude(sample_h).val()
            check(
                label + " imports one valid closed cut region",
                imported.isValid() and len(imported.Solids()) == 1,
            )
            error = difference(imported, expected)
            check(
                label + " complete contour equals STEP-verified nominal pocket",
                error < VOLUME_TOL,
                error,
            )

        evidence["escape_groove_interpretation"] = (
            "Pocket DXFs describe the maximum planar floor contour, including two "
            "escape grooves at each face. STEP controls groove intersection with "
            "the outer 0.4 mm chamfer; that final wedge is not an extruded DXF prism."
        )

    write_report("PASS" if all(item["pass"] for item in checks) else "FAIL")
    if not all(item["pass"] for item in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
