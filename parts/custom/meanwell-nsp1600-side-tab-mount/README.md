# Mean Well NSP-1600 narrow-side mount with local tabs — N2

**Preliminary side-mount prototype.** This separate design implements the requested narrow-side orientation and replaces the continuous side extensions with four local stud tabs. The completed N1 design remains unchanged.

![Actual N2 CAD assembly](references/product/assembled_hero.png)

| Comparison | N1 bottom mount | N2 side mount |
|---|---:|---:|
| Maximum adapter width | 125 mm | **72 mm** |
| Width between stud stations | 125 mm | **45 mm** |
| Adapter overall length | 300.6 mm | 316.8 mm |
| Plate thickness | 5 mm | 6 mm |
| Unperforated rounded outline area | 37,520 mm² | 16,618 mm² |
| Calculated adapter mass | 0.502 kg | **0.267 kg** |
| PSU plus adapter height, above main panel | 46 mm | **91 mm** |

N2 reduces maximum width by **42.4%** and adapter outline area by **55.7%**. These figures exclude cables, tool clearance and the reference main panel. The taller orientation increases overturning demand; a 6 mm plate and 44 mm long local tabs avoid relying on equal roll-load sharing between the two PSU screws. The plate extends 16.2 mm past the terminal-side chassis plane to maintain material around the front countersink and stud tabs.

## Files

| Purpose | Actual deliverable |
|---|---|
| Editable parametric CAD | [model.py](model.py), [params.json](params.json), [spec.json](spec.json) |
| Manufactured plate | [plate_N2.step](exports/plate_N2.step) |
| Full reference assembly | [assembled_device_mount_N2.step](exports/assembled_device_mount_N2.step): 35 separate solids, including all 19 original PSU components |
| PSU, adapter and two screws | [device_adapter_N2.step](exports/device_adapter_N2.step) |
| Adapter and hardware | [mount_hardware_N2.step](exports/mount_hardware_N2.step) |
| Main-panel interface reference | [FPE_interface_REFERENCE_ONLY.step](exports/FPE_interface_REFERENCE_ONLY.step) |
| CNC geometry | [Profile and drills](exports/profile_drill_N2.dxf), [underside countersinks](exports/countersinks_UNDERSIDE_N2.dxf) |
| FPE placements | [Stud coordinates](exports/FPE_stud_coordinates_N2.csv), [stud-center DXF](exports/FPE_stud_pattern_REFERENCE_N2.dxf) |
| Drawings | `drawings/MeanWell_N2_drawing_package.pdf`: dimensioned A3 sheets and a calibrated 1:1 fit template; editable SVG drawings included |
| Hardware | [BOM.md](BOM.md), [catalog_bom.json](references/research/catalog_bom.json) |
| Engineering | [ENGINEERING_NOTE.md](ENGINEERING_NOTE.md), calculation source and results under `references/engineering/` |
| Assembly and validation | [ASSEMBLY.md](ASSEMBLY.md), [PROTOTYPE_VALIDATION.md](PROTOTYPE_VALIDATION.md) |
| Source evidence | [Measured side findings](references/geometry/MEASURED_SIDE_FINDINGS.md), [orientation and hardware evidence](references/research/orientation_side_mount_evidence.md) |
| Verification | `quality/cad_verification.json`, `quality/manufacturing_verification.json`, `quality/repository_evaluation.json` |

The STL is a preview mesh, not a released printed structural alternative. The DXFs describe a machined flat plate, not a bend-developed sheet-metal part. All machining views retain the same XY coordinates; the shop must transform the underside setup correctly. The main panel is a 92 × 340 × 6 mm **interface reference**, not the customer's finished FPE panel or an order file.

## Interfaces and manufacturing

The original +X side of the PSU rests on the aluminum plate. Its two designated M4 axes become X+2.3 mm at Y−5.8 and −257.8 mm. Use two [McMaster 91294A190](https://www.mcmaster.com/91294A190/) M4 × 0.7 × 10 mm overall-length, 90° countersunk screws. Nominal penetration is **4.05 mm**, with a proposed received-assembly window of **3.75–4.35 mm**; the manufacturer maximum is **5 mm from the chassis mounting face**. Finish the seats using the received screws, with heads flush to 0.10 mm below the adapter underside. The ideal CAD screw cone does not prove real DIN7991 head seating or strength.

Four FPE WGU30 M3 studs on a **57 × 252 mm** rectangle pass through the local tabs. Nominal 12 mm stud projection, specified washers and locknuts leave 1.45 mm beyond the nut. Measure the actual projection and confirm full nylon engagement plus at least 1 mm/two complete threads beyond the nut. Reserve a 5.5 AF socket with outside diameter ≤10 mm, internal depth ≥10 mm, 60 mm axial approach and 20 mm removal lift.

Machine certified 6061-T6/T651 from 1/4-inch or thicker stock to 6.00 ±0.05 mm. The 45 mm spine, four tabs, R4 convex/concave corners and 0.4 mm outer edge breaks form one part. No fan reliefs or thermal pad are needed on the nominal metal side interface. Apply clear MIL-DTL-5541 Type II Class 3 conversion; dimensions are after finish. Keep the designated FG earth conductor—plate contact is not proof of a protective-earth bond.

Datums: **A** is the underside at Z0; **B** is the left spine tangent plane at X−22.5; **C** is the fan-end plane at Y−300.6. Tab edges are not datum B. The original STEP is translated into the N1 frame, rotated +90° about Y and translated (−20.5, 0, 42.5), then placed on the adapter. Its source geometry is preserved.

## Required physical checks

**Rear side thread:** the manufacturer drawing specifies M4, but the matching STEP has an open Ø5 hole without a modeled rear threaded boss, nut or insert. Confirm the actual rear M4 feature, complete engagement and both screw-tip clearances before final machining/assembly. Do not create an inferred insert, drill the unit or tighten into a plain hole. The nominal fixed countersinks also cannot guarantee the full manufacturer's ±0.5 mm general pattern tolerance: use the calibrated template and actual coordinate survey.

**Structural joints:** the analytical transverse plate-frame bending/shear factor is approximately **3.33** under the stated conservative load model. This is not a whole-mount rating or proof that all contact stresses meet that factor. Screw-head/seat concentration, preload, short chassis bosses, unilateral metal toe contact, FPE anchorage and final panel support remain separate qualifications. The engineering note reports contact-pressure sensitivities and proposed qualification loads explicitly. Retention depends on the intact two-screw/contact couple as well as the four panel joints.

**Side-orientation cooling:** the user selected this orientation, but Mean Well publishes the ambient curve for horizontal operation and requires current derating for other orientations. The applicable side-mounted output limit is unresolved. Preserve factory terminal-end intake and fan-end exhaust, verify actual cable/lug/guard/tool space, and test the final TEC-cooled enclosure. The provisional 12 V full-load typical-efficiency example is about 185 W PSU conversion loss; it is neither a side-mounted operating permission nor a TEC capacity claim.

No fabrication, physical fit test, joint proof, powered test or purchase was performed. This design has no vehicle, airborne, outdoor or overhead qualification.

## Regenerate and review

Use Python 3.11 with the pinned `requirements.txt`. Short writable paths avoid Windows STEP/PDF export limitations. From this design folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe model.py
.\.venv\Scripts\python.exe verify_and_render.py --work-dir C:/cadwork/nsp1600_side_verify
.\.venv\Scripts\python.exe verify_manufacturing.py
.\.venv\Scripts\python.exe references/engineering/engineering_calculations.py --write
.\.venv\Scripts\python.exe make_documents.py --render
.\.venv\Scripts\python.exe drawings/verify_document.py
```

PDF rasterization additionally requires Poppler's `pdftoppm`; see `drawings/REGENERATE.md`. The portable folder includes its feature builders. The optional full repository gate is `python -m lib.evaluate parts/custom/meanwell-nsp1600-side-tab-mount --no-render` from the repository root.

Edit named parameters to revise the tab length, width, hole coordinates, thickness, stud pattern or panel interface. Every change invalidates the present fit/load/drawing review until regenerated and inspected. The engineering and drawing scripts reject unsupported input changes rather than silently reusing the old conclusions. A new source STEP requires a fresh component and mounting-feature audit. Inspect final CAD views and all PDF pages, record the current PDF hash in the visual review, and then run `package_design.py` to create the checked archive. Digital packaging does not grant fabrication or operating qualification.
