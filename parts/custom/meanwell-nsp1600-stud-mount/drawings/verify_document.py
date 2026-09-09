"""Verify PDF paper size, actual template geometry, and document content with pypdf.

Run using a Python runtime with pypdf after regenerating the drawing PDF.
This verifies the electronic PDF; it cannot certify a printer's scale.
"""
from pathlib import Path
import hashlib
import json
import math
from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
PDF = HERE / "MeanWell_N1_drawing_package.pdf"
reader = PdfReader(PDF)
checks = []


def check(name, passed, measured=None):
    checks.append({"check": name, "passed": bool(passed), "measured": measured})
    if not passed:
        raise AssertionError(name)


check("Six pages", len(reader.pages) == 6, len(reader.pages))
for i, page in enumerate(reader.pages, 1):
    dims = [float(page.mediabox.width) * 25.4 / 72,
            float(page.mediabox.height) * 25.4 / 72]
    check(f"Page {i} A3 landscape", abs(dims[0]-420) < .001 and abs(dims[1]-297) < .001, dims)
    check(f"Page {i} preliminary status", "NOT A PRODUCTION RELEASE" in page.extract_text())

page = reader.pages[-1]
ops = page.get_contents().operations
segments = []
paths = []
current = []
start = None
for vals, op in ops:
    if op == b"n":
        current = []
    elif op == b"m":
        start = tuple(float(v) for v in vals)
        current.append(start)
    elif op == b"l":
        end = tuple(float(v) for v in vals)
        segments.append((start, end))
        current.append(end)
        start = end
    elif op == b"c":
        current += [tuple(float(v) for v in vals[i:i+2]) for i in (0, 2, 4)]
        start = current[-1]
    elif op == b"S" and current:
        paths.append(current)

mm = 72 / 25.4
near = lambda a, b: abs(a-b) < .002
for name, a, b in [
    ("Horizontal 100 mm calibration", (65*mm, 60*mm), (165*mm, 60*mm)),
    ("Vertical 100 mm calibration", (375*mm, 96*mm), (375*mm, 196*mm)),
]:
    match = [(c, d) for c, d in segments if all(near(u, v) for u, v in zip(c+d, a+b))]
    check(name, len(match) == 1, math.dist(*match[0])/mm if match else None)

rounded_outline = next(p for p in paths if len(p) == 17)
xs, ys = list(zip(*rounded_outline))
outline = [(max(xs)-min(xs))/mm, (max(ys)-min(ys))/mm]
check("Rotated template outline 300.6 x125 mm", near(outline[0], 300.6) and near(outline[1], 125), outline)

circle_paths = [p for p in paths if len(p) == 13]
check("Seven template drill circles", len(circle_paths) == 7, len(circle_paths))
expected = [(-35, -16.1, 3.4), (35, -16.1, 3.4), (0, -280.8, 3.4),
            (-55, -280.8, 3.8), (-55, -16.1, 3.8), (55, -280.8, 3.8), (55, -16.1, 3.8)]
for i, (path, (x, y, dia)) in enumerate(zip(circle_paths, expected), 1):
    xs, ys = list(zip(*path))
    center = [(max(xs)+min(xs))/2/mm, (max(ys)+min(ys))/2/mm]
    measured_dia = [(max(xs)-min(xs))/mm, (max(ys)-min(ys))/mm]
    check(f"Template hole {i} actual position and bore", near(center[0], 56-y) and near(center[1], 148.5+x)
          and all(near(v, dia) for v in measured_dia), {"paper_center_mm": center, "bore_mm": measured_dia})

fulltext = "\n".join(p.extract_text() for p in reader.pages)
for phrase in ["91294A128", "3.30", "5.70", "2.75-3.35", "81 nominal CAD", "48 manufacturing geometry"]:
    check(f"Critical annotation {phrase}", phrase in fulltext)
links = sum(len(p.get("/Annots", [])) for p in reader.pages)
check("Catalog hyperlinks", links == 4, links)
result = {"status": "PASS", "scope": "Electronic PDF only; printer and physical fit not verified",
          "pdf_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(), "checks": checks}
(HERE / "document_verification.json").write_text(json.dumps(result, indent=2), encoding="utf8")
print(f"PASS: {len(checks)} PDF checks")
