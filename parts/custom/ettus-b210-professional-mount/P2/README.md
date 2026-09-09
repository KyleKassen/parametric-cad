# B210 mounting system — thinner P2 revision

Preliminary CNC manufacturing package for a radio inside an equipment box, attached to a rigid metal plate in stationary indoor service. Both flat and upright arrangements are included. The original P1 package and source radio STEP remain unchanged.

| Part | P1 | P2 |
|---|---:|---:|
| Base broad section | 12 mm | 8 mm (33% thinner) |
| Pocket floor | 6 mm | 4 mm |
| Retainer bars | 8 mm | 5 mm (37.5% thinner) |
| Upright web and foot | 8 mm | 6 mm with integral edge ribs and local 10 mm bolt seats |
| Retainer station pitch along Y | 70 mm | 76 mm |
| Retainer screw | M5 × 50 | McMaster M5 × 45 |

Four small integral bosses rise to Z9.20 to preserve useful thread depth in the thinner base. Stock 30 mm spacers and selected shims set a measured 0.20–0.30 mm gap above the radio. The screws seat the bars on metal spacers; they do not squeeze the cover. Upright ribs recover stiffness with 6 mm walls. The footprint remains 160 ×180 flat and 79 ×180 upright. Height above the supporting plate is 50.8508 flat and 176 upright, excluding cable/tool service space. Hardware below the assumed 6 mm plate extends to Z−16 flat and Z−18.8 upright; allow at least 20 mm accessible below the mounting surface.

## Files

- `exports/B210_mount_shop_pack_P2.pdf`: dimensioned drawings, assembly and machining notes.
- `exports/B210_flat_assembly_P2.step`, `B210_upright_assembly_P2.step`: named, distinct device, mount and nominal purchased hardware components.
- `exports/B210_M01_base_P2.step`, `B210_M02_retainer_P2.step`, `adapter_machined.step`: custom machined parts. `B210_M03_spacer_P2.step` and film geometry are procurement/fit reference envelopes.
- `exports/*.dxf`: actual machining sections and plate drilling templates. Layers are depth references, not all through cuts. No sheet-metal flat pattern applies.
- `McMaster_BOM.md` and `McMaster_BOM.csv`: exact McMaster products, quantities, links, pack counts, observed prices and purchasing notes. Custom machined parts and supporting plate are separate.
- `engineering_note.md`, `references/engineering/engineering_checks.md`, `references/fit_tolerance_stack.md`, `prototype_validation_plan.md`: calculations, assumptions and prototype acceptance gates.
- `exports/*verification*.json`, `mass_screen.json`: executed geometry/manufacturing checks and calculated mass. No physical tests have occurred.

## Regenerate

The editable parametric source is `model.py`, `vertical_adapter.py`, `params.json` and `adapter_params.json`, using CadQuery 2.7.0. This is reproducible CAD source, not a native SolidWorks feature tree. Use Python 3.11 and the included `requirements.txt`. On Windows use a short environment/output path; long-path OCP DLL loading failed in the project environment. This revision used `C:/venvs/cadquery/Scripts/python.exe`.

From this folder, after installing requirements:

```powershell
& C:/venvs/cadquery/Scripts/python.exe vertical_adapter.py --out C:/b210work/p2
& C:/venvs/cadquery/Scripts/python.exe model.py --out C:/b210work/p2
& C:/venvs/cadquery/Scripts/python.exe verify.py --out C:/b210work/p2
& C:/venvs/cadquery/Scripts/python.exe verify_hardware.py --out C:/b210work/p2
& C:/venvs/cadquery/Scripts/python.exe verify_additional.py --out C:/b210work/p2
& C:/venvs/cadquery/Scripts/python.exe make_views.py --out C:/b210work/p2
& C:/venvs/cadquery/Scripts/python.exe make_documents.py --out C:/b210work/p2
& C:/venvs/cadquery/Scripts/python.exe build_mcmaster_bom.py
& C:/venvs/cadquery/Scripts/python.exe package_release.py --staging C:/b210work/p2
```

Run `python references/engineering/engineering_calculations.py --write` after any geometry/material/load change. Named parameters are coupled engineering dimensions; arbitrary values do not automatically produce a safe fit. Source hash mismatch deliberately stops regeneration. All dimensions are millimetres. The source model's original bytes are preserved in `references/input_device.step`.

This metal design is not sized for polymer printing. Use certified 6061-T6/T651 stock and the drawing finish/inspection requirements. The spacers are purchased aluminum of unspecified alloy; do not assign the frame material's yield strength to them. Purchased dimensions and locking/preload behavior require receiving inspection and prototype qualification. There has been no fabrication, purchase, physical fit test or application qualification.

Calculated mount mass (device excluded): flat **0.492 kg**, upright **0.900 kg**. Upright mass falls **19.3%** from the P1 CAD estimate1.115 kg. These are volumes with stated density assumptions, not weighed parts.
