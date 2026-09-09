"""Independently inspect the actual FPD-exported R2 backpanel and hardware STEP.

Catalog/thread identity is established by the separate native SAVE/RELOAD audit.
This script measures exported geometry and never infers threads from bore size.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

HERE = Path(__file__).resolve().parent
R2 = HERE.parents[1]


def bounds(shape):
    b = shape.BoundingBox()
    return {a: [getattr(b, a + "min"), getattr(b, a + "max")] for a in "xyz"}


def cylinders(shape):
    out = []
    for face in shape.Faces():
        if face.geomType() != "CYLINDER":
            continue
        surf = BRepAdaptor_Surface(face.wrapped).Cylinder()
        axis = surf.Axis()
        if abs(axis.Direction().Z()) < 0.999999:
            continue
        loc = axis.Location()
        out.append(
            {
                "axis_xy_mm": [loc.X(), loc.Y()],
                "radius_mm": surf.Radius(),
                "bbox_mm": bounds(face),
            }
        )
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", required=True, type=Path)
    args = parser.parse_args()
    p = json.loads((R2 / "params.json").read_text())
    raw = cq.importers.importStep(str(args.native)).val()
    solids = raw.Solids()
    plate_index = max(range(len(solids)), key=lambda i: solids[i].Volume())
    raw_plate = solids[plate_index]
    b = raw_plate.BoundingBox()
    # FPD STEP front is +Z; front Z0 and lower-left XY are expected. This
    # measured translation only removes exporter roundoff/coordinate origins.
    shift = (-b.xmin, -b.ymin, -b.zmax)
    plate = raw_plate.translate(shift)
    hardware = [s.translate(shift) for i, s in enumerate(solids) if i != plate_index]
    checks = []

    def check(name, ok, measured=None, criterion=None):
        checks.append(
            {"check": name, "pass": bool(ok), "measured": measured, "criterion": criterion}
        )

    check("native plate valid", plate.isValid())
    check("all native hardware valid", all(h.isValid() for h in hardware))
    check("one plate plus twenty hardware solids", len(solids) == 21, len(solids), 21)
    check(
        "native panel dimensions",
        all(abs(getattr(b, a + "len") - n) < 0.0021 for a, n in zip("xyz", [431.8, 431.8, 6])),
        bounds(plate),
        "431.8 x431.8 x6",
    )
    plate_cylinders = cylinders(plate)
    for x in [6.35, 425.45]:
        for y in [6.35, 425.45]:
            corners = [
                c
                for c in plate_cylinders
                if math.dist(c["axis_xy_mm"], [x, y]) < 0.0021
                and abs(c["radius_mm"] - 6.35) < 0.0011
            ]
            check(
                f"native R6.35 corner at {x},{y}",
                len(corners) == 1,
                corners,
                "one radius6.35 cylindrical outside wall",
            )
    feature_evidence = []
    for feature in p["mounting_holes"] + p["hardware"]:
        is_anchor = "catalog_code" in feature
        radius = 6.05 if is_anchor else feature["diameter"] / 2
        zspan = [-2.3, 0] if is_anchor else [-6, 0]
        matches = [
            c
            for c in plate_cylinders
            if math.dist(c["axis_xy_mm"], [feature["x"], feature["y"]]) < 0.0021
            and abs(c["radius_mm"] - radius) < 0.0011
        ]
        valid = [
            c for c in matches if all(abs(a - z) < 0.0021 for a, z in zip(c["bbox_mm"]["z"], zspan))
        ]
        check(
            feature["id"] + (" native anchor cavity" if is_anchor else " factory bore"),
            len(valid) == 1,
            valid,
            {"radius_mm": radius, "Z_span_mm": zspan},
        )
        feature_evidence.append(
            {
                "id": feature["id"],
                "kind": "anchor" if is_anchor else "factory",
                "matches": valid,
                "axis_error_mm": math.dist(valid[0]["axis_xy_mm"], [feature["x"], feature["y"]])
                if valid
                else None,
                "radius_error_mm": abs(valid[0]["radius_mm"] - radius) if valid else None,
            }
        )
    matched_solids = set()
    hardware_evidence = []
    for h in p["hardware"]:
        matches = []
        for i, solid in enumerate(hardware):
            sb = solid.BoundingBox()
            center = [(sb.xmin + sb.xmax) / 2, (sb.ymin + sb.ymax) / 2]
            if math.dist(center, [h["x"], h["y"]]) < 0.0021:
                matches.append((i, solid, center))
        check(
            h["id"] + " unique native hardware axis",
            len(matches) == 1,
            [m[2] for m in matches],
            [h["x"], h["y"]],
        )
        if len(matches) != 1:
            continue
        i, solid, center = matches[0]
        matched_solids.add(i)
        sb = solid.BoundingBox()
        check(
            h["id"] + " native front height/recess",
            abs(sb.zmin + 2.3) < 0.0021 and abs(sb.zmax - h["length"]) < 0.0021,
            [sb.zmin, sb.zmax],
            [-2.3, h["length"]],
        )
        check(
            h["id"] + " native recessed flange diameter",
            abs(sb.xlen - 12.1) < 0.0021 and abs(sb.ylen - 12.1) < 0.0021,
            [sb.xlen, sb.ylen],
            [12.1, 12.1],
        )
        probe = cq.Solid.makeCylinder(0.15, 0.9, cq.Vector(center[0], center[1], h["length"] - 1))
        probe_overlap = sum(s.Volume() for s in solid.intersect(probe).Solids())
        female = h["catalog_code"] == "WGO30"
        check(
            h["id"] + " exported open female/solid male end",
            probe_overlap < 1e-7 if female else probe_overlap > 0.01,
            probe_overlap,
            "open axial bore" if female else "solid axial stud",
        )
        hardware_evidence.append(
            {
                "id": h["id"],
                "native_solid_index_excluding_plate": i,
                "expected_catalog_from_params_not_inferred_from_STEP": h["catalog_code"],
                "bbox_mm": bounds(solid),
                "axis_xy_mm": center,
                "vertical_cylinder_surfaces": cylinders(solid),
            }
        )
    check(
        "every exported hardware solid matched once",
        len(matched_solids) == 20,
        len(matched_solids),
        20,
    )
    reference_path = R2 / "exports/Backpanel_R2.step"
    reference = cq.importers.importStep(str(reference_path)).val()
    common = plate.intersect(reference)
    common_volume = sum(s.Volume() for s in common.Solids())
    assert common_volume > 1_000_000, "Unexpected empty OCCT common; investigate, do not accept."
    native_extra = max(0, plate.Volume() - common_volume)
    native_missing = max(0, reference.Volume() - common_volume)
    difference = native_extra + native_missing
    check(
        "whole native plate/reference geometry",
        difference < 3,
        difference,
        "<3 mm3 permits FPD0.001 mm coordinate quantization; "
        "feature coordinates/depths independently checked",
    )
    report = {
        "schema": "sce20-stacked-r2-native-backpanel-audit/1",
        "status": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "units": "mm",
        "native_step": str(args.native.resolve()),
        "native_sha256": hashlib.sha256(args.native.read_bytes()).hexdigest(),
        "reference_step": str(reference_path),
        "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "raw_native_bbox_mm": bounds(raw),
        "raw_plate_bbox_mm": bounds(raw_plate),
        "raw_plate_solid_index": plate_index,
        "native_to_component_datum_translation_mm": shift,
        "native_plate_volume_mm3": plate.Volume(),
        "reference_plate_volume_mm3": reference.Volume(),
        "native_extra_metal_mm3": native_extra,
        "native_missing_metal_mm3": native_missing,
        "plate_symmetric_difference_mm3": difference,
        "maximum_feature_axis_error_mm": max(f["axis_error_mm"] or 0 for f in feature_evidence),
        "maximum_feature_radius_error_mm": max(f["radius_error_mm"] or 0 for f in feature_evidence),
        "checks": checks,
        "plate_features": feature_evidence,
        "hardware_geometry": hardware_evidence,
        "hardware_catalog_counts_from_matched_params": {
            code: sum(
                h["expected_catalog_from_params_not_inferred_from_STEP"] == code
                for h in hardware_evidence
            )
            for code in ["WGU30", "WGO30"]
        },
        "limitations": [
            "Native SAVE/RELOAD metadata, catalog and dialogs establish thread/catalog identity; "
            "this STEP only corroborates geometry.",
            "Female cylindrical bore diameters are simplified exported geometry and are not "
            "a thread gauge or usable engagement depth.",
            "The M3 catalog hardware exports diameter2.7 mm simplified male shafts and female "
            "bores. These measured diameters do not redefine the catalog thread.",
            "Hardware flange export fills the diameter12.1 x2.3 cavity; "
            "the integration catalog body uses diameter11.9 x2.2.",
            "Nominal geometric verification does not establish supplier tolerances, "
            "received thread fit, bond strength or load qualification.",
        ],
    }
    output = HERE / "Backpanel_R2_native_geometry_audit.json"
    output.write_text(json.dumps(report, indent=2))
    print(report["status"], len(checks), "checks; symmetric difference mm3", difference)
    print(output)
    if report["status"] != "PASS":
        print(json.dumps([c for c in checks if not c["pass"]], indent=2))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
