"""Check N2 digital deliverables and package a portable, hashed ZIP.

This never marks physical fit, load or thermal tests complete. A current visual
review record must be supplied after inspection; regenerated PDFs do not inherit
an earlier review automatically.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ZIP_NAME = "MeanWell_NSP1600_side_tab_mount_N2_complete.zip"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf8"))


def main():
    checks = []

    def ck(name, passed, detail=None):
        checks.append(dict(check=name, passed=bool(passed), detail=detail))

    p = read(HERE / "params.json")
    ck(
        "Original STEP preserved",
        sha(HERE / "references/input_device.step") == p["input_step_sha256"],
    )
    ck(
        "User PDF preserved",
        sha(HERE / "datasheets/NSP-1600-spec_USER.pdf") == p["source_pdf_sha256"],
    )
    for name in ("cad_verification.json", "manufacturing_verification.json"):
        d = read(HERE / "quality" / name)
        ck(name, d["status"] == "PASS", len(d["checks"]))
        ck(name + " current parameters", d["params_sha256"] == sha(HERE / "params.json"))
    engineering = read(HERE / "references/engineering/engineering_results.json")
    ck(
        "Plate frame analytical target met",
        engineering["plate"]["frame_target_met"],
        engineering["plate"]["minimum_frame_yield_factor"],
    )
    ck(
        "Contact limitation retained; no whole-mount pass claimed",
        engineering["plate"]["screen_target_met"] is False
        and engineering["contacts"]["status"] == "HOLD_REQUIRES_JOINT_QUALIFICATION"
        and engineering["contacts"]["seat_pressure_factor3_yield_ratio"] < 3,
        engineering["contacts"]["seat_pressure_factor3_yield_ratio"],
    )
    ck("Engineering self checks", engineering["calculation_self_checks"]["status"] == "passed")
    ck("Engineering parameters current", engineering["params_sha256"] == sha(HERE / "params.json"))
    for name, record in engineering["input_audit"]["files"].items():
        ck("Engineering input: " + name, sha(HERE / name) == record["sha256"])
    review = read(HERE / "quality/repository_evaluation.json")
    ck("Repository gate passed", review["overall"] == "PASS", review["design"]["score"])
    ck("No design metric floors failed", not review["design"]["floor_failures"])
    manifest = read(HERE / "drawings/drawing_source_manifest.json")
    pdf = HERE / "drawings" / manifest["pdf"]
    ck("PDF matches generation manifest", sha(pdf) == manifest["pdf_sha256"])
    for record in manifest["sources"]:
        path = HERE / record["path"].replace("\\", "/")
        ck("Drawing input: " + record["path"], sha(path) == record["sha256"])
    reader = PdfReader(pdf)
    ck(
        "Six A3 PDF pages",
        len(reader.pages) == 6
        and all(
            abs(float(pg.mediabox.width) - 420 * 72 / 25.4) < 0.1
            and abs(float(pg.mediabox.height) - 297 * 72 / 25.4) < 0.1
            for pg in reader.pages
        ),
    )
    text = "\n".join(pg.extract_text() or "" for pg in reader.pages)
    for term in (
        "91294A190",
        "98688A142",
        "90576A102",
        "252",
        "316.8",
        "6.00",
        "3.75",
        "4.35",
        "57",
        "72",
    ):
        ck("PDF contains " + term, term in text)
    ck("PDF catalog links", sum(len(pg.get("/Annots", [])) for pg in reader.pages) >= 3)
    document_check = read(HERE / "drawings/document_verification.json")
    ck(
        "Current PDF document checks",
        document_check["status"] == "PASS" and document_check["pdf_sha256"] == sha(pdf),
        len(document_check["checks"]),
    )
    visual_path = HERE / "quality/visual_review.json"
    visual = read(visual_path) if visual_path.exists() else {}
    ck(
        "Current PDF root visual review",
        visual.get("pdf_sha256") == sha(pdf) and visual.get("all_six_pages_reviewed") is True,
    )
    ck("CAD views reviewed", visual.get("cad_views_reviewed") is True)
    for name, digest in visual.get("views", {}).items():
        ck("Reviewed CAD image current: " + name, sha(HERE / name) == digest)
    independent = read(HERE / "quality/independent_review.json")
    ck("Independent consistency review complete", independent["status"] == "PASS")
    required = [
        "model.py",
        "params.json",
        "spec.json",
        "requirements.txt",
        "README.md",
        "BOM.md",
        "DESIGN.md",
        "ENGINEERING_NOTE.md",
        "ASSEMBLY.md",
        "PROTOTYPE_VALIDATION.md",
        "exports/plate_N2.step",
        "exports/assembled_device_mount_N2.step",
        "exports/device_adapter_N2.step",
        "exports/mount_hardware_N2.step",
        "exports/FPE_interface_REFERENCE_ONLY.step",
        "exports/profile_drill_N2.dxf",
        "exports/countersinks_UNDERSIDE_N2.dxf",
        "exports/FPE_stud_coordinates_N2.csv",
        "exports/FPE_stud_pattern_REFERENCE_N2.dxf",
        "drawings/MW_NSP_M01_plans_N2.svg",
        "drawings/MW_NSP_M01_tabs_section_N2.svg",
        "verify_and_render.py",
        "references/engineering/engineering_calculations.py",
        "make_documents.py",
        "verify_manufacturing.py",
    ]
    ck("All essential deliverables present", all((HERE / name).is_file() for name in required))
    for suffix in (
        "meanwell-nsp1600-stud-mount",
        "ettus-b210-professional-mount",
        "ettus-b210-professional-mount/P2",
        "ettus-b210-direct-stud-mount",
        "solidrun-bedrock-thermal-stud-mount",
    ):
        old = HERE.parent / suffix
        old_manifest = old / "file_manifest.json"
        if old_manifest.exists():
            records = read(old_manifest)["files"]
            changed = [
                n
                for n, v in records.items()
                if not (old / n).exists() or sha(old / n) != v["sha256"]
            ]
            ck(
                "Earlier design preserved: " + suffix,
                not changed,
                dict(files_checked=len(records), mismatches=changed),
            )
    result = dict(
        status="PASS" if all(c["passed"] for c in checks) else "FAIL",
        revision="N2",
        scope="Digital integrity only; PRELIMINARY physical fit and joint qualification",
        checks=checks,
    )
    (HERE / "quality/final_delivery_checks.json").write_text(
        json.dumps(result, indent=2), encoding="utf8"
    )
    if result["status"] != "PASS":
        print(json.dumps([c for c in checks if not c["passed"]], indent=2))
        raise SystemExit("Resolve digital-delivery discrepancies before packaging")
    excludes = {"__pycache__", ".ruff_cache", "attempts", "qa", "_layout_preview", "qa_rasters"}
    files = sorted(
        path
        for path in HERE.rglob("*")
        if path.is_file()
        and not any(x in excludes for x in path.relative_to(HERE).parts)
        and path.name not in {ZIP_NAME, "file_manifest.json", "archive_check.json"}
    )
    inventory = dict(
        revision="N2",
        status="PRELIMINARY FIT PROTOTYPE; NO PHYSICAL QUALIFICATION",
        files={
            path.relative_to(HERE).as_posix(): dict(bytes=path.stat().st_size, sha256=sha(path))
            for path in files
        },
    )
    out = HERE / "file_manifest.json"
    out.write_text(json.dumps(inventory, indent=2), encoding="utf8")
    files.append(out)
    archive = HERE / ZIP_NAME
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in files:
            z.write(path, HERE.name + "/" + path.relative_to(HERE).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name, record in inventory["files"].items():
            assert hashlib.sha256(z.read(HERE.name + "/" + name)).hexdigest() == record["sha256"]
    archive_result = dict(
        status="PASS",
        zip=ZIP_NAME,
        bytes=archive.stat().st_size,
        files=len(files),
        sha256=sha(archive),
        CRC_and_file_hashes="PASS",
    )
    (HERE / "archive_check.json").write_text(json.dumps(archive_result, indent=2), encoding="utf8")
    print(json.dumps(archive_result), flush=True)


if __name__ == "__main__":
    main()
