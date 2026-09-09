# T1 drawing regeneration

Run the part's `model.py`, `verify_and_render.py` and `verify_manufacturing.py` workflows first, as described by the part README. Then run:

```powershell
& 'C:/venvs/cadquery/Scripts/python.exe' 'parts/custom/solidrun-bedrock-thermal-stud-mount/make_documents.py' --render
```

The document generator uses `params.json`, the verified catalog JSON, passed CAD/manufacturing verification records and the final CAD-derived images. It stops if guarded critical dimensions, selected hardware, verification counts or the manufacturing parameter hash change; review the drawing annotations before deliberately updating guards.

`SolidRun_T1_drawing_package.pdf` is the six-page A3 package. `SR_TS_M01_dimensioned_plan_T1.svg` and `SR_TS_M01_sections_T1.svg` are editable vector views. Manufacturing DXFs come from `model.py`; this drawing generator does not overwrite fabrication geometry. `qa/page-1.png` through `page-6.png` are rendered page-review evidence, and the source manifest records input hashes.

The short staging directory `C:/b210work/solidrun/documents` avoids Windows path-length limitations. The finished PDF is copied into this folder. Reopen and visually inspect every changed page before updating the review record. All T1 documents remain preliminary fit and thermal prototype information, not a production release.
