# B210 flat and upright mounting system - P1

Preliminary prototype manufacturing package for a metal plate inside an equipment box. Flat and upright layouts share a machined aluminum cradle, two removable bars and four spacers. The upright option adds two identical machined angle supports. Nothing is drilled, peeled off or threaded into the radio.

This is reproducible parametric CAD, not a native SolidWorks feature tree. Edit `params.json` and `adapter_params.json`; the Python feature builders are the source of truth. STEP parts are editable imported solids in conventional CAD. Preserve the original device file.

## Start here

- `exports/B210_mount_shop_pack_P1.pdf`: six-page dimensioned manufacturing and installation pack.
- `exports/B210_flat_assembly_P1.step` and `B210_upright_assembly_P1.step`: device, mount and nominal hardware as distinct named assembly components.
- `exports/B210_M01_base_P1.step`, `B210_M02_retainer_P1.step`, `B210_M03_spacer_P1.step`, `adapter_machined.step`: production part geometry.
- `exports/B210_M01_machining_sections_P1.dxf`: actual part sections at named Z depths on separate layers. These are toolpath reference contours, **not a one-operation laser blank**; do not machine all layers as through cuts.
- `exports/B210_M02_profile_P1.dxf`, `B210_M04_film_profile_P1.dxf`, `adapter_side_profile.dxf`: applicable planar manufacturing profiles. No sheet-metal flat pattern applies to the selected machined construction.
- `drawings/B210_M05_adapter_P1.svg`: detailed dimensioned adapter drawing, supplemental to the PDF.
- `exports/B210_BOM_P1.csv`: quantities for each orientation and hardware specifications.
- `engineering_note.md`, `prototype_validation_plan.md`, `references/engineering/engineering_checks.md`: engineering basis, calculations, unresolved release conditions and proposed tests.
- `references/fit_tolerance_stack.md`: numerical worst-case fit stacks and required spacer/under-head shim selection.
- `exports/B210_flat_plate_drill_template_P1.dxf` and `B210_upright_plate_drill_template_P1.dxf`: four-hole support drilling templates in installed coordinates; supporting plate remains an integration item.
- `exports/verification_report.json`, `hardware_verification.json`, `adapter_verification.json`: executed CAD checks. Physical tests have not occurred.

All dimensions are millimetres. The flat hardware envelope above the supporting surface is 160 x180 x56; upright is79 x180 x176. Supporting-foot footprint alone is73 x180 upright. Allow the stated cable, tool, withdrawal and below-plate nut spaces. The supporting plate itself is not supplied geometry; thickness6 is an explicit hardware-stack assumption.

## Regenerate

Use a **short path** for the Python environment on Windows. The project `.venv` fails loading OpenCASCADE because of Windows path-length limits; the working environment used here was `C:/venvs/cadquery/Scripts/python.exe`, Python3.11.4, CadQuery2.7.0, VTK9.3.1. No original source was overwritten. The included `render_support.py` is a copy of the project's headless VTK helper.

Example portable setup from this folder (Python3.11):

```powershell
uv venv --python 3.11 C:/venvs/b210-p1
uv pip install --python C:/venvs/b210-p1/Scripts/python.exe -r requirements.txt
& C:/venvs/b210-p1/Scripts/python.exe vertical_adapter.py
& C:/venvs/b210-p1/Scripts/python.exe model.py --out C:/b210work/p1 --render
& C:/venvs/b210-p1/Scripts/python.exe verify.py --out C:/b210work/p1
& C:/venvs/b210-p1/Scripts/python.exe verify_hardware.py --out C:/b210work/p1
& C:/venvs/b210-p1/Scripts/python.exe make_documents.py --out C:/b210work/p1
& C:/venvs/b210-p1/Scripts/python.exe references/engineering/engineering_calculations.py --write-note
```

`vertical_adapter.py` exports its part to this folder's `exports`; copy those adapter files into a separate `--out` directory when collecting regenerated deliverables. `model.py` uses that builder directly for the upright assembly. Copy a reviewed short-path output back to `exports` after all checks pass. To avoid Windows limitations after extracting the ZIP, a folder such as `C:/b210-p1` is recommended. On Linux/macOS use the environment's normal `python` executable.

The included `references/input_device.step` is a byte-preserved copy of the supplied file, SHA256 `c59b649ccc6a4c128885fd9e64acfd74d756b23bbcff7f119e21a4acb426c912`. A changed device hash deliberately stops regeneration; remeasure the new configuration and update the design. You may supply its original path with `--source`. Named parameters expose fit, base dimensions, attachment spacing, bars, spacers, hardware and orientation. Parameters are coupled engineering dimensions: rerun geometry and structural checks after any change; not every arbitrary parameter combination is valid.

## Manufacture and release

Use certified6061-T6/T651, CNC-milled parts with the drawing finish and critical tolerances. The adapter is an L profile machined from thick plate; it is not a bent bracket. Sawn/waterjet roughing may reduce milling time, but finish the critical surfaces and holes. Stock waste is the tradeoff for few unique parts, stiffness and no bending-tool assumptions in small quantities. No price or lead time has been quoted.

Do **not** print these metal-sized solids as working polymer parts. A printed mount would require different sections, layer orientation, creep/heat data and validation. STL is intentionally not a manufacturing deliverable for the selected process.

The drawings support prototype manufacture, not a released installation rating. Actual enclosure contact strength, configured mass/CG, supplied screws, final gaps, plate stiffness, cable assemblies, thermal operation in the box and vibration requirements remain physical/integration checks. No torque is invented; qualify the metal-seat tightening and locking procedure against the documented tapped-thread capacity. All source-model limitations, including duplicate front overlays and unverified device attachment capacity, are recorded in the engineering note.
