# SolidRun Bedrock thermal stud mount — T1

**Preliminary fit/thermal prototype. Not released for production or rated service.**

One machined aluminum adapter attaches to the Tile face with six recessed M4 screws, then drops onto four FPE M3 studs. Two thin thermal-compound interfaces carry heat toward the supporting panel. The opposite fin bank remains exposed. The user's enclosure has a thermoelectric cooler; no direct cold-side connection or total cooling capacity is established.

The adapter is **166 × 184 × 5.10 mm**, approximately **0.412 kg**. One part serves a flat panel or a vertical panel; keep the fins vertical for the manufacturer's natural-convection orientation. A 200 × 220 × 6 mm main-panel coupon appears only to show the stud/interface relationship. It does not define the customer's complete FPE panel.

## Start here

- `drawings/SolidRun_T1_drawing_package.pdf`: dimensioned manufacturing and installation drawings.
- `BOM.md`: exact McMaster links, quantities, conditional screw selection and FPE stud details.
- `ASSEMBLY.md`: surface preparation, screw-depth gauge, compound application and service.
- `ENGINEERING_NOTE.md`, `references/engineering/`: assumptions, equations, loads and limitations.
- `PROTOTYPE_VALIDATION.md`: required fit, retention and thermal tests.
- `exports/plate_T1.step`: custom machined part.
- `exports/assembled_device_mount_T1.step`: 43 distinct components, including reference panel, TIM and simplified hardware.
- `exports/device_adapter_T1.step`: computer/adapter subassembly.
- `exports/vertical_fin_installation_REFERENCE.step`: same assembly rigidly rotated for vertical fin channels.
- `exports/plate_profile_mm.dxf`, `plate_underside_machining_mm.dxf`, `thermal_*_pocket_contour_mm.dxf`: planar machining vectors. STEP and drawing control pocket depth and outer-rim transitions. No bends are required.
- `exports/FPE_stud_pattern_mm.dxf`, `FPE_stud_coordinates_mm.csv`: panel stud centers, **not panel drill/countersink instructions**.
- `exports/plate_T1_preview.stl`: viewing/fit mockup only, not a printable structural alternative.
- `references/product/`: images rendered from the actual CAD.

## Source configuration and release limits

The input STEP contains 22 solids, including three superimposed enclosure variants. It is preserved byte for byte in `references/input_device.step`. The assembly uses the actual Tile body, 19 shared auxiliary bodies and one fin bank clipped from the actual 60 W alternative. This **derived spatial reference** matches the requested arrangement visually; it is not a separately supplied hybrid CAD model, a verified detachable fin assembly, or evidence that one bank dissipates 60 W. Confirm the actual physical computer configuration before fabrication.

The fresh audit measured six blind threaded features at the requested face. Full-diameter geometry ends at 3.5 mm, followed by a drill cone to 4.501 mm; that drill point is not usable M4 screw depth. The user's M4/~4 mm observations and these surfaces do not establish allowable preload, torque or thread capacity.

Selected McMaster M4 × 8 screws must pass the physical acceptance gauge in ASSEMBLY.md. Actual screw-tip geometry may make a stock screw unsuitable despite its correct nominal size. Stop and revise if the minimum complete engagement and maximum projection cannot both be met. Do not shorten screws or deepen holes casually.

This design assumes stationary indoor installation on a rigid metal panel. Handling/cable load calculations are preliminary screening loads, not a vehicle, airborne, shock, vibration, outdoor or overhead rating. The actual FPE anchor capacity, computer threads and total thermal path need qualification.

## Reproduce and edit

Use Python 3.11 with the pinned packages in `requirements.txt`; the original environment was CadQuery 2.7.0 / OCCT and VTK 9.3.1. Install in an isolated environment:

```powershell
python -m pip install -r requirements.txt
python model.py
python verify_and_render.py
python verify_manufacturing.py
python references/engineering/engineering_calculations.py --write
python make_documents.py
```

Run from this folder. Optional drawing QA rendering uses `python make_documents.py --render` and requires Poppler `pdftoppm` on PATH; ordinary PDF generation does not. Native CAD tools can have Windows long-path limits; `model.py` stages exports in a temporary short directory. `--work-dir C:/cadwork/solidrun` is also supported. The verification tool's work directory can be overridden similarly. The geometry audit can be repeated with an explicit source:

```powershell
python references/geometry/audit_tile_hybrid.py --source references/input_device.step
```

`model.py:create_part(params=None)` is the editable, reproducible part definition. `build_stages()` exposes the base, thermal pockets and individual bores. `params.json` exposes plate size, thickness, six housing coordinates, stud spacing/rotation, thermal recess/lands/vents, countersinks, hardware and reference panel. A parameter change requires new screw, load, tolerance and fit checks; it is not automatic qualification.

`lib/features.py` and `render_support.py` are packaged for standalone regeneration. The repository's optional `python -m lib.evaluate parts/custom/solidrun-bedrock-thermal-stud-mount --no-render` requires the parent repository evaluation tools. Its retained appearance report flags the functional 0.05 mm pocket boundaries and manufacturer-fixed hole layout; it did not clear the initially raised cosmetic threshold. These were not altered merely to improve that score. Actual geometry/manufacturing results are separate in `exports/cad_verification.json` and `exports/manufacturing_verification.json`.

No part has been fabricated, installed, purchased or physically tested by this work. Confirm the reference panel geometry with FPE and measured hardware before placing a manufacturing order.
