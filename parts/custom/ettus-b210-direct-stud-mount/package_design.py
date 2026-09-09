"""Check the D1 deliverables and create a portable ZIP with SHA256 inventory."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import cadquery as cq
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
ZIP_NAME = "B210_direct_stud_mount_D1_complete.zip"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    checks = []

    def check(name: str, ok: bool, detail=None) -> None:
        checks.append({"check": name, "pass": bool(ok), "detail": detail})

    for name in ("cad_verification.json", "manufacturing_verification.json"):
        data = json.loads((HERE / "references" / name).read_text(encoding="utf-8"))
        check(name, data["status"] == "PASS", len(data["checks"]))
    engineering = json.loads(
        (HERE / "references/engineering/engineering_results.json").read_text(encoding="utf-8")
    )
    check(
        "Plate-only analytical target met",
        engineering["plate_target_met"],
        engineering["minimum_screened_plate_yield_factor"],
    )
    check(
        "Engineering input hash matches",
        engineering["root_parameter_file_sha256"]["params.json"] == sha(HERE / "params.json"),
    )
    params = json.loads((HERE / "params.json").read_text(encoding="utf-8"))
    check(
        "Original input preserved",
        sha(HERE / "references/input_device.step") == params["input_step_sha256"],
    )
    drawing_manifest = json.loads(
        (HERE / "drawings/drawing_source_manifest.json").read_text(encoding="utf-8")
    )
    for record in drawing_manifest["sources"]:
        path = HERE / record["path"]
        check("Drawing source: " + record["path"], path.exists() and sha(path) == record["sha256"])
    pdf = HERE / "drawings/B210_direct_stud_mount_shop_pack_D1.pdf"
    reader = PdfReader(pdf)
    check("PDF five pages", len(reader.pages) == 5)
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    for term in ("91294A126", "98688A142", "90576A102", "93.599", "120.015", "1.80", "5.70"):
        check("PDF includes " + term, term in text)
    check("PDF has no placeholder image text", "placeholder" not in text.lower())
    check("PDF has linked catalog items", sum(len(p.get("/Annots", [])) for p in reader.pages) >= 4)
    # Read-only preservation check against earlier design manifests, when present.
    for suffix in ("", "P2"):
        old = HERE.parent / "ettus-b210-professional-mount" / suffix
        manifest = old / "file_manifest.json"
        if manifest.exists():
            records = json.loads(manifest.read_text(encoding="utf-8"))["files"]
            mismatches = [
                name
                for name, record in records.items()
                if not (old / name).exists() or sha(old / name) != record["sha256"]
            ]
            check(
                "Prior design preserved: " + (suffix or "P1"),
                not mismatches,
                {"files_checked": len(records), "mismatches": mismatches},
            )
    # STEP headers contain timestamps, so compare geometry rather than bytes.
    with tempfile.TemporaryDirectory(prefix="b210_gate_") as temp:
        work = Path(temp)
        names = ("plate_D1.step", "ettus-b210-direct-stud-mount_v1.step")
        for name in names:
            shutil.copyfile(HERE / "exports" / name, work / name)
        a, b = [cq.importers.importStep(str(work / name)).val() for name in names]
        difference = sum(s.Volume() for s in a.cut(b).Solids())
        difference += sum(s.Volume() for s in b.cut(a).Solids())
        check(
            "Identical custom STEP geometry in gate and deliverable", difference < 1e-6, difference
        )
    final = {
        "revision": "D1",
        "status": "PASS" if all(c["pass"] for c in checks) else "FAIL",
        "scope": "Digital deliverables only; preliminary fit prototype, no physical validation",
        "checks": checks,
        "visual_review": (
            "All five PDF pages and final CAD views inspected."
            " Final page2 and corrected orthographic views rechecked after edits."
        ),
    }
    (HERE / "references/final_delivery_checks.json").write_text(
        json.dumps(final, indent=2), encoding="utf-8"
    )
    if final["status"] != "PASS":
        print(json.dumps(final, indent=2))
        raise SystemExit("Resolve delivery failures before packaging.")
    exclude = {"__pycache__", ".ruff_cache", "_layout_preview", "attempts"}
    files = sorted(
        p
        for p in HERE.rglob("*")
        if p.is_file()
        and not any(part in exclude for part in p.relative_to(HERE).parts)
        and p.name not in {ZIP_NAME, "file_manifest.json", "archive_check.json"}
    )
    inventory = {
        "revision": "D1",
        "status": "PRELIMINARY FIT PROTOTYPE",
        "files": {
            p.relative_to(HERE).as_posix(): {"bytes": p.stat().st_size, "sha256": sha(p)}
            for p in files
        },
    }
    manifest_path = HERE / "file_manifest.json"
    manifest_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    files.append(manifest_path)
    archive = HERE / ZIP_NAME
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in files:
            z.write(path, f"{HERE.name}/{path.relative_to(HERE).as_posix()}")
    with zipfile.ZipFile(archive) as z:
        bad = z.testzip()
        assert bad is None, bad
        for name, record in inventory["files"].items():
            assert hashlib.sha256(z.read(f"{HERE.name}/{name}")).hexdigest() == record["sha256"]
    result = {
        "status": "PASS",
        "zip": ZIP_NAME,
        "bytes": archive.stat().st_size,
        "files": len(files),
        "sha256": sha(archive),
        "CRC_and_file_hashes": "PASS",
    }
    (HERE / "archive_check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
