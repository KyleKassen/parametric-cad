"""Check printable STL topology, record hashes, and package the prototype files."""

from __future__ import annotations

import hashlib
import json
import math
import struct
import zipfile
from collections import Counter
from pathlib import Path

PART_DIR = Path(__file__).absolute().parent


def remove_zero_edge_triangles(path):
    """Normalize binary-float seams on a 0.00001 mm grid and drop collapsed faces.

    The grid is 5,000 times finer than the 0.05 mm export tolerance. OCCT can
    tessellate a shared edge to neighbouring float32 values in separate faces.
    Recompute normals; never fill missing faces or smooth the actual geometry.
    """
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    kept = []
    for i in range(count):
        record = raw[84 + i * 50 : 84 + (i + 1) * 50]
        values = struct.unpack("<12fH", record)
        points = [tuple(round(n, 5) for n in values[j : j + 3]) for j in (3, 6, 9)]
        if len(set(points)) == 3:
            u = [points[1][j] - points[0][j] for j in range(3)]
            v = [points[2][j] - points[0][j] for j in range(3)]
            n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
            length = math.sqrt(sum(x * x for x in n))
            if length > 1e-12:
                kept.append(
                    struct.pack(
                        "<12fH",
                        *(x / length for x in n),
                        *(x for point in points for x in point),
                        0,
                    )
                )
    removed = count - len(kept)
    path.write_bytes(raw[:80] + struct.pack("<I", len(kept)) + b"".join(kept))
    return removed


def check_stl(path):
    raw = path.read_bytes()
    count = struct.unpack_from("<I", raw, 80)[0]
    if len(raw) != 84 + count * 50:
        raise ValueError(f"Unexpected binary STL size: {path}")
    edges = Counter()
    for i in range(count):
        values = struct.unpack_from("<12fH", raw, 84 + i * 50)
        points = [tuple(round(n, 5) for n in values[j : j + 3]) for j in (3, 6, 9)]
        if len(set(points)) != 3:
            raise ValueError(f"Degenerate triangle {i}: {path}")
        for a, b in ((0, 1), (1, 2), (2, 0)):
            edges[tuple(sorted((points[a], points[b])))] += 1
    boundary = sum(n == 1 for n in edges.values())
    nonmanifold = sum(n > 2 for n in edges.values())
    if boundary or nonmanifold:
        raise ValueError(f"Non-watertight STL {path}: {boundary=}, {nonmanifold=}")
    return {"triangles": count, "boundary_edges": boundary, "nonmanifold_edges": nonmanifold}


def main():
    out = PART_DIR / "exports"
    version = json.loads((PART_DIR / "params.json").read_text(encoding="utf-8"))["version"]
    fit = json.loads((PART_DIR / "references/fit_report.json").read_text(encoding="utf-8"))
    evaluation = json.loads((PART_DIR / "references/evaluation.json").read_text(encoding="utf-8"))
    if fit["version"] != version or not fit["all_passed"]:
        raise ValueError("Re-run mechanical fit checks on the current revision before packaging")
    export_check = next(c for c in evaluation["checks"] if c["id"] == "export")
    if f"_{version}.step" not in export_check["message"] or export_check["status"] != "PASS":
        raise ValueError("Re-run evaluation on the current revision before packaging")
    score = evaluation["design"]["score"]
    paths = [PART_DIR / n for n in ("README.md", "DESIGN.md", "CONNECTOR.md")]
    paths += sorted(out.glob(f"*_{version}.step")) + sorted(out.glob(f"*_{version}.stl"))
    paths += sorted((out / "coupons").glob(f"*_{version}.*"))
    paths += [out / "coupons/README.md", out / "coupons/coupon_validation.json"]
    paths += [
        PART_DIR / "references/product/with_reference_connectors_front_io.png",
        PART_DIR / "references/product/exploded_front_io.png",
        PART_DIR / "references/product/open_housing_open.png",
        PART_DIR / "references/product/open_housing_interior_elevation.png",
        PART_DIR / "references/fit_report.json",
        PART_DIR / "references/evaluation.json",
    ]
    records = []
    for path in paths:
        removed = remove_zero_edge_triangles(path) if path.suffix == ".stl" else 0
        record = {
            "file": path.relative_to(PART_DIR).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        if path.suffix == ".stl":
            record["mesh_check"] = check_stl(path)
            record["mesh_check"]["zero_area_export_triangles_removed"] = removed
            record["mesh_check"]["seam_normalization_grid_mm"] = 0.00001
        records.append(record)
    manifest = {
        "part": PART_DIR.name,
        "version": version,
        "units": "mm",
        "status": "prototype candidate; not production accepted",
        "mechanical_checks": (
            f"{len(fit['checks'])}/{len(fit['checks'])} pass; reference hardware, not exact SKUs"
        ),
        "style_gate": f"{score}/100; unchanged target 70; see evaluation report for verdict",
        "files": records,
    }
    manifest_path = out / "package_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    package = out / f"prototype-print-package-{version}.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in paths + [manifest_path]:
            archive.write(path, path.relative_to(PART_DIR).as_posix())
    print(f"Packaged {len(paths)} files; all STL boundary/manifold checks pass: {package}")


if __name__ == "__main__":
    main()
