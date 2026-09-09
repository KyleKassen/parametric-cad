"""Verify N2 manufacturing exports independently of model.py.

Requires generated STEP, two operation DXFs and a four-stud coordinate CSV.
Missing files produce NOT_READY; mismatches or exceptions cannot leave stale PASS.
No physical machining, screw fit, preload or installed capacity is certified.
"""

from __future__ import annotations

import argparse
import csv
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
LINEAR_TOL = 2e-5
VOLUME_TOL = 3e-5
FILES = (
    "plate_N2.step",
    "profile_drill_N2.dxf",
    "countersinks_UNDERSIDE_N2.dxf",
    "FPE_stud_pattern_REFERENCE_N2.dxf",
    "FPE_stud_coordinates_N2.csv",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def volume(shape: cq.Shape) -> float:
    return sum(abs(solid.Volume()) for solid in shape.Solids())


def difference(a: cq.Shape, b: cq.Shape) -> float:
    return volume(a.cut(b)) + volume(b.cut(a))


def combine(workplane: cq.Workplane) -> cq.Shape:
    solids = workplane.solids().vals()
    if len(solids) == 1:
        return solids[0]
    return cq.Compound.makeCompound(solids)


def cylinder(radius: float, height: float, x: float, y: float, z: float) -> cq.Shape:
    return cq.Solid.makeCylinder(radius, height, cq.Vector(x, y, z))


def nominal_tab_blank(p: dict) -> cq.Shape:
    """Independent stock construction: central spine plus two rectangular tabs.

    The external vertical edges are rounded after the Boolean union. This does
    not use or import the root model's profile vertex/arc construction.
    """
    result = (
        cq.Workplane("XY")
        .box(
            p["spine_width"],
            p["plate_length"],
            p["plate_thickness"],
            centered=(True, True, False),
        )
        .translate((0, p["plate_center_y"], 0))
    )
    for y in p["tab_stations_y"]:
        tab = (
            cq.Workplane("XY")
            .box(
                p["plate_width"],
                p["tab_length"],
                p["plate_thickness"],
                centered=(True, True, False),
            )
            .translate((0, y, 0))
        )
        result = result.union(tab)
    return result.edges("|Z").fillet(p["corner_radius"]).val()


def points_match(a: list, b: list, tolerance: float = LINEAR_TOL) -> bool:
    if len(a) != len(b):
        return False
    return all(math.dist(aa, bb) < tolerance for aa, bb in zip(sorted(a), sorted(b), strict=True))


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


def bounds(shape: cq.Shape) -> list[float]:
    box = shape.BoundingBox()
    return [box.xmin, box.xmax, box.ymin, box.ymax, box.zmin, box.zmax]


def near(a: list, b: list) -> bool:
    return all(abs(x - y) < LINEAR_TOL for x, y in zip(a, b, strict=True))


def surfaces(plate: cq.Shape) -> tuple[list, list, list]:
    cylinders, cones, planes = [], [], []
    for face in plate.Faces():
        surface = BRepAdaptor_Surface(face.wrapped)
        row = {"bounds_mm": bounds(face), "area_mm2": face.Area()}
        if surface.GetType() == GeomAbs_Plane:
            if abs(surface.Plane().Axis().Direction().Z()) > 1 - 1e-8:
                planes.append(row)
        elif surface.GetType() in (GeomAbs_Cylinder, GeomAbs_Cone):
            item = surface.Cylinder() if surface.GetType() == GeomAbs_Cylinder else surface.Cone()
            if abs(item.Axis().Direction().Z()) < 1 - 1e-8:
                continue
            point = item.Axis().Location()
            row["xy_mm"] = [point.X(), point.Y()]
            if surface.GetType() == GeomAbs_Cylinder:
                row["diameter_mm"] = item.Radius() * 2
                cylinders.append(row)
            else:
                row["included_angle_deg"] = abs(math.degrees(item.SemiAngle())) * 2
                cones.append(row)
    return cylinders, cones, planes


def run_checks(p: dict, local: Path, check, evidence: dict) -> None:
    thickness = p["plate_thickness"]
    housing, studs = p["housing_points"], stud_points(p)
    check("Parameters declare millimeters", p["units"] == "mm")
    check("Two side housing stations and four stud stations", len(housing) == 2 and len(studs) == 4)
    source_path = HERE / "references/geometry/side_reference_and_contacts.json"
    source = json.loads(source_path.read_text(encoding="utf-8-sig"))
    evidence["fresh_interface_audit_sha256"] = digest(source_path)
    check(
        "Fresh source audit identifies the preserved STEP",
        source["source_sha256"] == p["input_step_sha256"],
    )
    check(
        "Housing pattern matches fresh nominal vendor axes",
        points_match(housing, source["nominal_mount_axes_xy_mm"]),
        housing,
    )
    check(
        "Original plus-X side and missing rear thread explicitly recorded",
        p["device_face_source"] == "+X" and p["rear_thread_not_modeled"] is True,
    )
    evidence["device_thread_limitation"] = (
        "Manufacturer identifies two side M4 mount points, but the rear STEP "
        "contains an unthreaded opening without its mating thread. Actual rear "
        "thread confirmation is a physical release requirement; adapter CAD "
        "verification does not resolve it."
    )

    step_path = local / "plate_N2.step"
    check(
        "STEP explicitly declares millimeter length units",
        bool(
            re.search(
                r"SI_UNIT\s*\(\s*\.MILLI\.\s*,\s*\.METRE\.\s*\)",
                step_path.read_text(encoding="ascii", errors="replace"),
            )
        ),
    )
    plate = cq.importers.importStep(str(step_path)).val()
    check("Reopened plate is one valid solid", plate.isValid() and len(plate.Solids()) == 1)
    nominal_bounds = [
        -p["plate_width"] / 2,
        p["plate_width"] / 2,
        p["plate_center_y"] - p["plate_length"] / 2,
        p["plate_center_y"] + p["plate_length"] / 2,
        0,
        thickness,
    ]
    check("STEP scale and datum bounds", near(bounds(plate), nominal_bounds), bounds(plate))
    evidence["reopened_plate_volume_mm3"] = volume(plate)
    cq.exporters.export(plate, str(local / "independent_roundtrip.step"))
    reopened = cq.importers.importStep(str(local / "independent_roundtrip.step")).val()
    error = difference(plate, reopened)
    check(
        "Second STEP roundtrip is valid and geometrically equal",
        reopened.isValid() and len(reopened.Solids()) == 1 and error < VOLUME_TOL,
        error,
    )

    cylinders, cones, planes = surfaces(plate)
    csk_depth = (
        (p["countersink_diameter_reference"] - p["housing_clearance_diameter"])
        / 2
        / math.tan(math.radians(p["countersink_angle_deg"] / 2))
    )
    for name, axes, diameter, start in (
        ("Housing", housing, p["housing_clearance_diameter"], csk_depth),
        ("Stud", studs, p["stud_clearance_diameter"], p["bore_deburr"]),
    ):
        selected = [f for f in cylinders if abs(f["diameter_mm"] - diameter) < LINEAR_TOL]
        check(name + " cylindrical bore count", len(selected) == len(axes), len(selected))
        for index, xy in enumerate(axes, 1):
            matches = [f for f in selected if math.dist(f["xy_mm"], xy) < LINEAR_TOL]
            check(f"{name} bore {index} axis", len(matches) == 1, matches)
            if matches:
                expected_z = [start, thickness - p["bore_deburr"]]
                actual_z = matches[0]["bounds_mm"][4:]
                check(
                    f"{name} bore {index} straight throat",
                    near(actual_z, expected_z),
                    {"actual_z_mm": actual_z, "expected_z_mm": expected_z},
                )
    for index, xy in enumerate(housing, 1):
        matches = [
            f
            for f in cones
            if math.dist(f["xy_mm"], xy) < LINEAR_TOL and abs(f["bounds_mm"][4]) < LINEAR_TOL
        ]
        expected_xy = [
            xy[0] - p["countersink_diameter_reference"] / 2,
            xy[0] + p["countersink_diameter_reference"] / 2,
            xy[1] - p["countersink_diameter_reference"] / 2,
            xy[1] + p["countersink_diameter_reference"] / 2,
        ]
        check(
            f"Countersink {index} opening, angle and depth",
            len(matches) == 1
            and near(matches[0]["bounds_mm"], expected_xy + [0, csk_depth])
            and abs(matches[0]["included_angle_deg"] - p["countersink_angle_deg"]) < LINEAR_TOL,
            matches,
        )

    check(
        "Only two horizontal planar contact levels; no borrowed fan pockets",
        all(
            abs(f["bounds_mm"][4]) < LINEAR_TOL or abs(f["bounds_mm"][4] - thickness) < LINEAR_TOL
            for f in planes
        ),
        sorted({round(f["bounds_mm"][4], 8) for f in planes}),
    )
    for label, z in (("Lower panel datum", 0), ("Upper metal contact datum", thickness)):
        area = sum(f["area_mm2"] for f in planes if abs(f["bounds_mm"][4] - z) < LINEAR_TOL)
        check(label + " retained as planar metal face", area > 100, area)

    docs = {name: ezdxf.readfile(local / name) for name in FILES if name.endswith(".dxf")}
    evidence["dxf_layers"] = {}
    for name, doc in docs.items():
        layers = sorted({e.dxf.layer for e in doc.modelspace()})
        evidence["dxf_layers"][name] = layers
        check(
            name + " declares millimeters",
            doc.header.get("$INSUNITS") == 4,
            doc.header.get("$INSUNITS"),
        )

    profile_doc = docs["profile_drill_N2.dxf"]
    drills = list(profile_doc.modelspace().query("CIRCLE"))
    check("Profile DXF has exactly six drill operations", len(drills) == 6, len(drills))
    for name, layer, axes, diameter in (
        ("Housing", "HOUSING_DRILL", housing, p["housing_clearance_diameter"]),
        ("Stud", "STUD_DRILL", studs, p["stud_clearance_diameter"]),
    ):
        selected = [e for e in drills if e.dxf.layer == layer]
        xy = [(e.dxf.center.x, e.dxf.center.y) for e in selected]
        check(
            name + " DXF drill coordinates and diameters",
            points_match(xy, axes)
            and all(abs(e.dxf.radius * 2 - diameter) < LINEAR_TOL for e in selected),
            xy,
        )

    blank = combine(
        cq.importers.importDXF(str(local / "profile_drill_N2.dxf"), include=["PROFILE"]).extrude(
            thickness
        )
    )
    check("Profile DXF extrudes one valid blank", blank.isValid() and len(blank.Solids()) == 1)
    expected_blank = nominal_tab_blank(p)
    error = difference(blank, expected_blank)
    check(
        "DXF curved tab outline equals independent named-parameter blank",
        expected_blank.isValid() and error < VOLUME_TOL,
        error,
    )
    check(
        "Named spine, tab stations and end bounds are internally consistent",
        abs(p["plate_fan_end_y"] - nominal_bounds[2]) < LINEAR_TOL
        and abs(p["plate_terminal_end_y"] - nominal_bounds[3]) < LINEAR_TOL
        and len(p["tab_stations_y"]) == 2
        and points_match(
            [(0, y) for y in p["tab_stations_y"]],
            [(0, xy[1]) for xy in housing],
        ),
    )
    profile_entities = [e for e in profile_doc.modelspace() if e.dxf.layer == "PROFILE"]
    check(
        "Profile contains machinable line/arc contour entities",
        len(profile_entities) > 0
        and all(e.dxftype() in {"LINE", "ARC", "LWPOLYLINE", "POLYLINE"} for e in profile_entities),
        {
            kind: sum(e.dxftype() == kind for e in profile_entities)
            for kind in sorted({e.dxftype() for e in profile_entities})
        },
    )
    for filename in ("profile_drill_N2.dxf", "countersinks_UNDERSIDE_N2.dxf"):
        doc = docs[filename]
        duplicate_blank = combine(
            cq.importers.importDXF(str(local / filename), include=["PROFILE"]).extrude(thickness)
        )
        error = difference(duplicate_blank, expected_blank)
        check(filename + " outline agrees with independent blank", error < VOLUME_TOL, error)
        circles = list(doc.modelspace().query("CIRCLE"))
        for label, layer, axes, diameter in (
            ("housing", "HOUSING_DRILL", housing, p["housing_clearance_diameter"]),
            ("stud", "STUD_DRILL", studs, p["stud_clearance_diameter"]),
        ):
            subset = [e for e in circles if e.dxf.layer == layer]
            centers = [(e.dxf.center.x, e.dxf.center.y) for e in subset]
            check(
                filename + " duplicate " + label + " operation coordinates",
                points_match(centers, axes)
                and all(abs(e.dxf.radius * 2 - diameter) < LINEAR_TOL for e in subset),
                centers,
            )
    reference = docs["FPE_stud_pattern_REFERENCE_N2.dxf"]
    reference_points = [
        (e.dxf.location.x, e.dxf.location.y)
        for e in reference.modelspace().query("POINT")
        if e.dxf.layer == "PANEL_STUD_CENTERS"
    ]
    check(
        "FPE reference DXF has four exact factory-stud center points",
        points_match(reference_points, studs),
        reference_points,
    )
    reconstructed = cq.Workplane(obj=blank).faces(">Z or <Z").edges().chamfer(p["edge_break"]).val()
    for drill in drills:
        center = drill.dxf.center
        tool = cylinder(drill.dxf.radius, thickness + 2, center.x, center.y, -1)
        reconstructed = reconstructed.cut(tool)
        deburr = p["bore_deburr"]
        top = cq.Solid.makeCone(
            drill.dxf.radius,
            drill.dxf.radius + deburr,
            deburr,
            cq.Vector(center.x, center.y, thickness - deburr),
        )
        reconstructed = reconstructed.cut(top)
        if drill.dxf.layer == "STUD_DRILL":
            lower = cq.Solid.makeCone(
                drill.dxf.radius + deburr,
                drill.dxf.radius,
                deburr,
                cq.Vector(center.x, center.y, 0),
            )
            reconstructed = reconstructed.cut(lower)

    csk_entities = [
        e
        for e in docs["countersinks_UNDERSIDE_N2.dxf"].modelspace().query("CIRCLE")
        if e.dxf.layer == "CSK_REF"
    ]
    csk_xy = [(e.dxf.center.x, e.dxf.center.y) for e in csk_entities]
    check(
        "Countersink DXF has two exact side-housing reference openings",
        points_match(csk_xy, housing)
        and all(
            abs(e.dxf.radius * 2 - p["countersink_diameter_reference"]) < LINEAR_TOL
            for e in csk_entities
        ),
        csk_xy,
    )
    for csk in csk_entities:
        center = csk.dxf.center
        tool = cq.Solid.makeCone(
            csk.dxf.radius,
            p["housing_clearance_diameter"] / 2,
            csk_depth,
            cq.Vector(center.x, center.y, 0),
        )
        reconstructed = reconstructed.cut(tool)
    error = difference(reconstructed, plate)
    check(
        "Complete DXF-driven machining reconstruction equals reopened STEP",
        reconstructed.isValid() and error < VOLUME_TOL,
        error,
    )
    evidence["reconstruction_volume_mm3"] = volume(reconstructed)

    with (local / "FPE_stud_coordinates_N2.csv").open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        headers = reader.fieldnames or []
    evidence["stud_csv_headers"] = headers
    alternatives = (
        ("x_mm", "y_mm"),
        ("X_mm", "Y_mm"),
        ("x_from_adapter_center_mm", "y_from_adapter_center_mm"),
    )
    columns = next(((x, y) for x, y in alternatives if x in headers and y in headers), None)
    check("FPE CSV declares X/Y coordinates in millimeters", columns is not None, columns)
    if columns:
        xy = [(float(row[columns[0]]), float(row[columns[1]])) for row in rows]
        check(
            "FPE CSV four centers equal parameters and STEP stud axes",
            len(rows) == 4 and points_match(xy, studs),
            xy,
        )
    evidence["machining_interpretation"] = (
        "PROFILE is an external blank; HOUSING_DRILL/STUD_DRILL are through operations; "
        "No pockets are selected; CSK_REF records opening diameter, "
        "with nominal 90-degree angle and depth controlled by STEP/drawing. "
        "No DXF contour is a sheet-metal flat pattern or thermal pad."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exports", type=Path, default=HERE / "exports")
    parser.add_argument(
        "--report", type=Path, default=HERE / "quality/manufacturing_verification.json"
    )
    args = parser.parse_args()
    pfile = HERE / "params.json"
    report = {
        "status": "NOT_READY",
        "units": "mm",
        "checks": [],
        "evidence": {},
        "limitations": (
            "Nominal manufacturing geometry only; no physical or installed qualification. "
            "Actual rear M4 thread, contact lands, countersunk-head fit, side-orientation "
            "derating and FPE anchor capacities remain unresolved."
        ),
    }

    def check(name: str, passed: bool, measured=None) -> None:
        report["checks"].append({"check": name, "pass": bool(passed), "measured": measured})

    try:
        p = json.loads(pfile.read_text(encoding="utf-8-sig"))
        report["params_sha256"] = digest(pfile)
        missing = [name for name in FILES if not (args.exports / name).is_file()]
        report["missing_files"] = missing
        if not missing:
            with tempfile.TemporaryDirectory(prefix="nsp_side_manufacturing_") as temporary:
                work = Path(temporary)
                hashes = {}
                for name in FILES:
                    shutil.copyfile(args.exports / name, work / name)
                    hashes[name] = digest(work / name)
                report["evidence"]["input_sha256"] = hashes
                run_checks(p, work, check, report["evidence"])
                check(
                    "Exports unchanged during verification",
                    all(digest(args.exports / name) == sha for name, sha in hashes.items()),
                )
                check(
                    "Parameters unchanged during verification",
                    digest(pfile) == report["params_sha256"],
                )
            report["status"] = "PASS" if all(c["pass"] for c in report["checks"]) else "FAIL"
    except Exception as error:
        report["status"] = "ERROR"
        check("Verifier completed without exception", False, repr(error))
    report["count"] = len(report["checks"])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {"status": report["status"], "count": report["count"], "report": str(args.report)}
        )
    )
    for failure in (c for c in report["checks"] if not c["pass"]):
        print(json.dumps(failure))
    raise SystemExit(
        0 if report["status"] == "PASS" else 2 if report["status"] == "NOT_READY" else 1
    )


if __name__ == "__main__":
    main()
