# Direct-stud D1 drawing package

The drawing package is a preliminary fit-prototype document. It does not authorize a production installation or establish the capacity of the radio's housing inserts, FPE studs or support panel.

Run from the repository root after the final CAD export and image generation:

```powershell
& 'C:/venvs/cadquery/Scripts/python.exe' 'parts/custom/ettus-b210-direct-stud-mount/make_documents.py' --render
```

Required inputs are `params.json`, `references/research/catalog_bom.json`, the three CAD-derived images `references/product/assembled_hero.png`, `plate_bottom_hero.png`, `exploded_iso.png`, and `references/views/section_fastener.png`. The generator refuses changed critical geometry until its drawing annotations are reviewed. It requires ReportLab, svglib and Poppler; it does not edit the source STEP, CAD model, catalog or manufacturing DXFs.

Outputs are `B210_direct_stud_mount_shop_pack_D1.pdf`, `B210_DS_M01_dimensioned_D1.svg`, `drawing_source_manifest.json`, and rasterized page checks under `qa/`. The SVG is a dimensioned part drawing with a nominal enlarged section. The CAD model/export script separately produces the manufacturing STEP and DXF contours.

All dimensions apply after finish. Datum A is the adapter underside, B its left edge and C its lower edge. Physical screw-seat gauging, actual projection, internal screw-tip separation, effective engagement and the straight bore length are acceptance requirements; nominal countersink mouth diameter does not override them.

The final PDF is generated only after all actual CAD images exist. Any regenerated document requires visual review before delivery; the stored approval concerns this preliminary prototype and does not establish a production release.
