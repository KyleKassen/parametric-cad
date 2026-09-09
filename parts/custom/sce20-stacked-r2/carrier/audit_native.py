"""Audit actual native carrier STEP against frame CAD and native catalog inputs.

An actual FPD export is mandatory. Never substitutes the in-memory builder.
The largest solid must be the panel; four separate standoff solids must match
the stored native mount pattern and the catalog shoulder/body dimensions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
import model
from OCP.BRepAdaptor import BRepAdaptor_Surface

HERE = Path(__file__).absolute().parent


def bounds(s: cq.Shape) -> dict:
    b = s.BoundingBox()
    return {a: [getattr(b, a + "min"), getattr(b, a + "max")] for a in "xyz"}


def cylindrical_faces(s: cq.Shape) -> list[dict]:
    result = []
    for face in s.Faces():
        if face.geomType() != "CYLINDER":
            continue
        cylinder = BRepAdaptor_Surface(face.wrapped).Cylinder()
        axis = cylinder.Axis()
        if abs(axis.Direction().Z()) < 0.99999:
            continue
        result.append(
            {
                "xy": [axis.Location().X(), axis.Location().Y()],
                "radius": cylinder.Radius(),
                "bbox": bounds(face),
            }
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--native",
        type=Path,
        default=Path("C:/Users/KyleKassen/Desktop/Peplink_Carrier_R2.stp"),
    )
    args = parser.parse_args()
    if not args.native.is_file():
        raise SystemExit("Actual native export is not present: " + str(args.native))
    source = cq.importers.importStep(str(args.native)).val()
    solids = sorted(source.Solids(), key=lambda s: s.Volume(), reverse=True)
    raw_plate = solids[0]
    rb = raw_plate.BoundingBox()
    translation = (-(rb.xmin + rb.xmax) / 2, -(rb.ymin + rb.ymax) / 2, -rb.zmin)
    plate = raw_plate.translate(translation)
    hardware = [s.translate(translation) for s in solids[1:]]
    reference_path = HERE.parent / "exports/Peplink_Carrier_R2.step"
    expected = cq.importers.importStep(str(reference_path)).val()
    p = model.load_params()
    fpd = json.loads((HERE / "fpd_input.json").read_text())
    checks: list[dict] = []

    def ck(name: str, passed: bool, measured=None, criterion=None) -> None:
        checks.append(
            {"check": name, "passed": bool(passed), "measured": measured, "criterion": criterion}
        )

    ck("all native solids valid", all(s.isValid() for s in solids))
    ck("one panel and four native hardware solids", len(solids) == 5, len(solids), 5)
    pb = plate.BoundingBox()
    ck(
        "native panel exact dimensions",
        all(abs(a - b) < 0.0021 for a, b in zip([pb.xlen, pb.ylen, pb.zlen], [180, 210, 4])),
        bounds(plate),
        {"x": [-90, 90], "y": [-105, 105], "z": [0, 4]},
    )
    nv, ev = plate.Volume(), expected.Volume()
    common = plate.copy().intersect(expected.copy())
    overlap = sum(s.Volume() for s in common.Solids())
    retry = None
    error_bound = 0.0
    if overlap == 0:
        retry = [0.00001, 0, 0]
        common = plate.copy().translate(tuple(retry)).intersect(expected.copy())
        overlap = sum(s.Volume() for s in common.Solids())
        error_bound = plate.Area() * retry[0]
    diff = {
        "native_extra_metal_mm3": max(0, nv - overlap),
        "native_missing_metal_mm3": max(0, ev - overlap),
        "boolean_retry_translation_mm": retry,
        "conservative_translation_error_bound_mm3": error_bound,
    }
    upper_bound = max(0, nv - overlap) + max(0, ev - overlap) + error_bound
    ck(
        "complete plate geometry and both rim bevels",
        upper_bound < 5,
        {**diff, "nominal_symmetric_difference_upper_bound_mm3": upper_bound},
        "<5 mm3 permits 0.001 mm native machining quantization, not a missed bevel or hole",
    )
    cylinders = cylindrical_faces(plate)
    for x in [-68, 68]:
        for y in [-75, 75]:
            corners = [
                c
                for c in cylinders
                if math.dist(c["xy"], [x, y]) < 0.0021 and abs(c["radius"] - 5) < 0.0021
            ]
            ck("window throat R5 corner " + str((x, y)), bool(corners), corners)
    for i, (x, y) in enumerate(p["support_points"], 1):
        found = [
            c
            for c in cylinders
            if math.dist(c["xy"], [x, y]) < 0.0021 and abs(c["radius"] - 1.9) < 0.0021
        ]
        ck("support through bore " + str(i), len(found) == 1, found)
    for i, (x, y) in enumerate(p["router_mount_points"], 1):
        found = [
            c
            for c in cylinders
            if math.dist(c["xy"], [x, y]) < 0.0021 and abs(c["radius"] - 6.05) < 0.0021
        ]
        ck("native anchor cavity " + str(i), len(found) >= 1, found)
        if found:
            zrange = found[0]["bbox"]["z"]
            ck(
                "native anchor depth/backing " + str(i),
                abs(zrange[0] - 1.7) < 0.0031 and abs(zrange[1] - 4) < 0.0031,
                zrange,
                [1.7, 4],
            )
    for x, y in [(72.99, 0), (-72.99, 0), (0, 79.99), (0, -79.99), (0, 0)]:
        ck("window through at " + str((x, y)), not plate.isInside(cq.Vector(x, y, 2), 1e-7))
    for x, y in [(73.01, 0), (-73.01, 0), (0, 80.01), (0, -80.01)]:
        ck(
            "window throat retains frame at " + str((x, y)),
            plate.isInside(cq.Vector(x, y, 2), 1e-7),
        )
    all_hardware = []
    for s in hardware:
        b = s.BoundingBox()
        all_hardware.append(
            {
                "xy": [(b.xmin + b.xmax) / 2, (b.ymin + b.ymax) / 2],
                "bbox": bounds(s),
                "volume_mm3": s.Volume(),
                "cylinders": cylindrical_faces(s),
            }
        )
    for a in [e for e in fpd["elements"] if e["kind"] == "bolt"]:
        xy = [a["x"] - 90, a["y"] - 105]
        hs = [h for h in all_hardware if math.dist(h["xy"], xy) < 0.0031]
        ck(a["id"] + " actual hardware axis", len(hs) == 1, hs)
        if not hs:
            continue
        h = hs[0]
        ck(
            a["id"] + " native shoulder height6",
            abs(h["bbox"]["z"][1] - 10) < 0.0021,
            h["bbox"]["z"],
            "top Z10 above panel underside; shoulder6 above panelfrontZ4",
        )
        bodies = [c for c in h["cylinders"] if abs(c["radius"] - 2.5) < 0.0021]
        ck(a["id"] + " catalog outer bodyD5", bool(bodies), bodies)
        # Native STEP renders the verified WGO40 female thread as D3.7, not
        # the thread's nominal D4. Do not turn a display cylinder into a thread
        # specification. Check the internal opening and available axial span;
        # native FPD code WGO40 independently controls actual M4 semantics.
        female = [
            c
            for c in h["cylinders"]
            if 0 < c["radius"] < 2.49
            and abs(c["bbox"]["z"][0] - 4) < 0.0021
            and abs(c["bbox"]["z"][1] - 10) < 0.0021
        ]
        ck(a["id"] + " internal female opening spans6mm", len(female) == 1, female)
    report = {
        "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
        "native": str(args.native),
        "native_sha256": hashlib.sha256(args.native.read_bytes()).hexdigest(),
        "reference": str(reference_path),
        "reference_sha256": hashlib.sha256(reference_path.read_bytes()).hexdigest(),
        "fpd_input_sha256": hashlib.sha256((HERE / "fpd_input.json").read_bytes()).hexdigest(),
        "normalization_translation": translation,
        "checks": checks,
        "native_hardware_inventory": all_hardware,
        "scope": (
            "Actual exported native geometry only. Native FPD reload independently verifies WGO40 "
            "thread semantics, usable thread, side and depth offset. STEP cylinder diameter "
            "does not independently certify thread pitch or hardware strength."
        ),
    }
    out = HERE / "references/native_carrier_geometry_audit.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report["status"], len(checks), "checks", diff)
    for c in checks:
        if not c["passed"]:
            print(c)
    print(out)
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
