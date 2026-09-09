# Regenerate the N1 drawings

From the mount directory, run:

```powershell
& 'C:/venvs/cadquery/Scripts/python.exe' make_documents.py --render
```

The generator requires ReportLab, svglib and Poppler (`pdftoppm`). It reads the final CAD parameters, selected catalog BOM, CAD-derived PNGs and both passing verification records under `quality`. Critical dimension changes stop generation and require reviewing the fixed drawing annotations. `--svg-only` is available while preparing views; it does not establish final CAD verification.

The output is a six-page A3 landscape PDF and two editable dimensioned SVGs. Manufacturing DXFs come from `model.py`; these SVGs are dimensioned illustrations, not machining contours. The PDF's sixth page contains true 1:1 vector geometry rotated 90 degrees to fit A3, with independent horizontal and vertical 100 mm calibration bars.

Verify the final electronic PDF with a Python runtime containing `pypdf`:

```powershell
python drawings/verify_document.py
```

Render and inspect every final PDF page after edits. The generated manifest starts with pending review status; update review records only after that inspection and the root engineering review. Printed scale and fit still require checking the calibration bars and received PSU. This is a preliminary fit prototype, not a production release.
