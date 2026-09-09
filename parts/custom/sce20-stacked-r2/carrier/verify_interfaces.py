"""Inspect the exported frame and its nominal purchased/native interfaces.

This verifies reference geometry and fit; FPD must own and verify final native
anchor machining. Connector validity limitations stay inherited and explicit.
"""

from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

import cadquery as cq
import model
from OCP.BRepAdaptor import BRepAdaptor_Surface

HERE = Path(__file__).absolute().parent


def volume_common(a: cq.Shape, b: cq.Shape) -> float:
    return sum(s.Volume() for s in a.copy().intersect(b.copy()).Solids())


def main() -> None:
    p = model.load_params()
    path = HERE / "exports" / (p["name"] + "_frame.step")
    frame = cq.importers.importStep(str(path)).val()
    checks: list[dict] = []

    def ck(name: str, passed: bool, measured=None, criterion=None) -> None:
        checks.append(
            {"check": name, "passed": bool(passed), "measured": measured, "criterion": criterion}
        )

    ck(
        "reopened single valid frame",
        frame.isValid() and len(frame.Solids()) == 1,
        len(frame.Solids()),
        1,
    )
    bbox = frame.BoundingBox()
    ck(
        "reopened expected size",
        all(abs(a - b) < 1e-6 for a, b in zip([bbox.xlen, bbox.ylen, bbox.zlen], [180, 210, 4])),
        [bbox.xlen, bbox.ylen, bbox.zlen],
        [180, 210, 4],
    )
    ck(
        "four support holes",
        sum(
            1
            for f in frame.Faces()
            if f.geomType() == "CYLINDER"
            and abs(BRepAdaptor_Surface(f.wrapped).Cylinder().Radius() - 1.9) < 1e-7
        )
        == 4,
    )
    for i, (x, y) in enumerate(p["support_points"], 1):
        shaft = cq.Solid.makeCylinder(1.5, 6, cq.Vector(x, y, -1))
        ck(
            "M3 shaft through support " + str(i),
            volume_common(shaft, frame) < 1e-7,
            volume_common(shaft, frame),
            0,
        )
        ck("support hole center " + str(i), not frame.isInside(cq.Vector(x, y, 2), 1e-7))
    window = (
        model.rounded_box(146, 160, 3.2, 5, top_break=0, bottom_break=0)
        .val()
        .translate((0, 0, 0.4))
    )
    ck(
        "complete minimum window throat",
        volume_common(window, frame) < 1e-7,
        volume_common(window, frame),
        0,
    )
    for side, z in [("underside", 0.001), ("upper", 3.999)]:
        ck(
            side + " 0.4mm window bevel reaches required X mouth",
            not frame.isInside(cq.Vector(73.398, 0, z), 1e-7),
        )
        ck(
            side + " window bevel retains rail outside mouth",
            frame.isInside(cq.Vector(73.401, 0, z), 1e-7),
        )
    for i, (x, y) in enumerate(p["router_mount_points"], 1):
        cavity = cq.Solid.makeCylinder(6.05, 2.3, cq.Vector(x, y, 1.7))
        contained = volume_common(cavity, frame)
        ck(
            "native anchor machining land " + str(i),
            abs(contained - cavity.Volume()) < 1e-6,
            contained,
            cavity.Volume(),
        )
        ck(
            "nominal1.7mm backing under native anchor " + str(i),
            frame.isInside(cq.Vector(x, y, 0.85), 1e-7),
        )
    ck(
        "surface web from native base to window",
        80.9 - 6.05 - 73.4 >= 1.4,
        80.9 - 6.05 - 73.4,
        ">=1.4mm nominal",
    )
    ck(
        "surface web from native base to outer rim",
        89.6 - 80.9 - 6.05 >= 2.6,
        89.6 - 80.9 - 6.05,
        ">=2.6mm nominal",
    )
    screw = p["support_screw"]
    inserted = screw["underhead_length"] - p["thickness"] - screw["washer_thickness"]
    ck("support screw nominal insertion", abs(inserted - 5.45) < 1e-9, inserted, 5.45)
    ck(
        "extension female end clearance",
        p["extension"]["female_length"] - inserted >= 1,
        p["extension"]["female_length"] - inserted,
        ">=1mm nominal",
    )
    ck(
        "lower extension male end clearance",
        p["support_native_hardware"]["usable_thread"] - p["extension"]["male_length"] >= 1,
        4,
        ">=1mm nominal",
    )
    ck(
        "overall shoulder height",
        p["support_native_hardware"]["length"] + p["extension"]["body_length"] == 70,
        70,
    )
    bedrock_path = (
        model.ROOT / "parts/custom/sce20-layout/exports/Bedrock_FPE_R1_device_adapter.step"
    )
    bedrock = cq.importers.importStep(str(bedrock_path)).val().translate((0, 0, -70))
    ck(
        "frame vs lower Bedrock",
        volume_common(frame, bedrock) < 1e-7,
        volume_common(frame, bedrock),
        0,
    )
    for i, (x, y) in enumerate(p["support_points"], 1):
        column = cq.Solid.makeCylinder(3.5, 70, cq.Vector(x, y, -70))
        ck(
            "D7 support clearance to lower Bedrock " + str(i),
            volume_common(column, bedrock) < 1e-7,
            volume_common(column, bedrock),
            0,
        )
        ck(
            "D7 support minimum gap " + str(i),
            column.distance(bedrock) >= 1.49,
            column.distance(bedrock),
            ">=1.49mm nominal",
        )
    assembly = cq.Assembly(name=p["name"] + "_catalog_envelopes")
    assembly.add(
        frame, name="frame_reference_native_machining_excluded", color=cq.Color(0.72, 0.75, 0.78)
    )
    for i, (x, y) in enumerate(p["router_mount_points"], 1):
        body = cq.Solid.makeCylinder(2.5, 6, cq.Vector(x, y, 4)).cut(
            cq.Solid.makeCylinder(2, 6, cq.Vector(x, y, 4))
        )
        assembly.add(
            body, name="WGO40_L6_body_envelope_" + str(i), color=cq.Color(0.56, 0.58, 0.60)
        )
    assembly_path = HERE / "exports" / (p["name"] + "_catalog_envelopes.step")
    assembly.save(str(assembly_path))
    reopened = cq.importers.importStep(str(assembly_path)).val()
    ck(
        "catalog envelope export valid",
        reopened.isValid() and len(reopened.Solids()) == 5,
        len(reopened.Solids()),
        5,
    )
    report = {
        "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
        "checks": checks,
        "frame_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "fpd_input_sha256": hashlib.sha256((HERE / "fpd_input.json").read_bytes()).hexdigest(),
        "frame_volume_mm3": frame.Volume(),
        "frame_mass_kg_at_2700": frame.Volume() * 2.7e-6,
        "minimum_window_throat_area_mm2": 146 * 160 - (4 - math.pi) * 5**2,
        "scope": (
            "Nominal reopened CAD/frame-interface checks only; "
            "catalog anchors are envelope surrogates, final native FPD machining "
            "and physical load/temperature acceptance remain separate."
        ),
    }
    (HERE / "references").mkdir(exist_ok=True)
    (HERE / "references/interface_verification.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    shutil.copyfile("C:/tmp/Peplink_Carrier_R2_eval.json", HERE / "references/evaluation.json")
    print(report["status"], len(checks), "checks, frame kg", report["frame_mass_kg_at_2700"])
    for c in checks:
        if not c["passed"]:
            print(c)
    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
