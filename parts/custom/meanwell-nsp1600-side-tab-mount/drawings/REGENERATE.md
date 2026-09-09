# Regenerate N2 drawings

From the N2 mount directory:

```powershell
& 'C:/venvs/cadquery/Scripts/python.exe' make_documents.py --render
```

Dependencies are ReportLab, svglib and Poppler (`pdftoppm`). Final generation requires the current CAD parameters, selected catalog BOM, passing CAD/manufacturing records under `quality`, final engineering note/results, and CAD-derived product/section PNGs. Critical dimensions are guarded: changes stop generation until the fixed annotations are reviewed. `--svg-only` can prepare vector pages while other final artifacts are being completed.

Outputs are a six-page A3 landscape PDF and two editable dimensioned SVGs. Page6 is a true 1:1 template rotated90 degrees to fit A3, with separate100 mm calibration bars in both paper directions. The contour's R4 quarter circles use standard cubic Beziers with less than0.002 mm geometric approximation error. These are drawing/template curves; the exact manufacturing contours come from `model.py` STEP and DXF exports.

Use a Python runtime containing `pypdf` to verify the electronic PDF:

```powershell
python drawings/verify_document.py
```

That verifier reads the finished PDF's actual path coordinates to check its paper size, template outline, all six bore positions/diameters and two calibration bars. It also checks critical annotations and catalog links. It does not certify a printer's scaling or the received PSU's fit.

Render and visually inspect every final page after edits. The generated source manifest starts pending review; final approval applies to drawing clarity and consistency for a preliminary mechanical fit prototype only. Rear M4 thread confirmation, side-orientation derating, casing/head/contact/preload/FPE capacities, real wiring, and physical load/thermal checks remain separate release requirements.
