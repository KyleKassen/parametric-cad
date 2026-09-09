# Mean Well NSP-1600 stud adapter — N1

**Preliminary fit prototype for stationary indoor, horizontal service.** This separate design attaches the PSU to a machined aluminum adapter using its three manufacturer-designated bottom M3 mounts. Four FPE load studs then attach the adapter to the main panel. The original PSU model is preserved. The 12 V variant is the working selection; the actual voltage, load, air temperature and final panel installation remain unconfirmed.

![Actual CAD assembly](references/product/assembled_hero.png)

The finished adapter is **125 × 300.6 × 5.00 mm**, approximately **0.502 kg** in aluminum. It has R8 corners, consistent 0.4 mm external edge breaks, three underside countersinks and two shallow relief pockets beneath the plastic fan frames. The nominal metal mounting surfaces contact the adapter. The reference main panel is 145 × 340 × 6 mm; it is an interface coupon, not the final enclosure panel or a complete FPE order file.

The five-millimeter thickness follows the plate bending screen, including the narrow rear load path, hole net section and fan-relief depth. A thinner flat plate did not meet the chosen plate-only factor of three with these conservative handling/cable loads. This is not a whole-mount load rating: the PSU mounting bosses, FPE anchors and supporting panel still require qualification.

## Open these files

| Purpose | Deliverable |
|---|---|
| Editable CAD | [model.py](model.py), [params.json](params.json); named feature stages via `build_stages()` |
| Custom part STEP | [plate_N1.step](exports/plate_N1.step) |
| Complete reference assembly | [assembled_device_mount_N1.step](exports/assembled_device_mount_N1.step): 36 separate solids, including all 19 original PSU parts |
| PSU plus adapter and screws | [device_adapter_N1.step](exports/device_adapter_N1.step) |
| Adapter and fastener reference geometry | [mount_hardware_N1.step](exports/mount_hardware_N1.step) |
| Main panel / four studs reference | [FPE_interface_REFERENCE_ONLY.step](exports/FPE_interface_REFERENCE_ONLY.step) |
| CNC planar operations | [Profile and drills](exports/profile_drill_N1.dxf), [top fan reliefs](exports/fan_reliefs_TOP_N1.dxf), [underside countersinks](exports/countersinks_UNDERSIDE_N1.dxf) |
| Panel interface | [Stud coordinates](exports/FPE_stud_coordinates_N1.csv), [stud-center DXF](exports/FPE_stud_pattern_REFERENCE_N1.dxf); placement only |
| Drawings and 1:1 fit template | `drawings/MeanWell_N1_drawing_package.pdf` and editable SVG sheets |
| Hardware | [BOM.md](BOM.md), [catalog_bom.json](references/research/catalog_bom.json) |
| Installation and tests | [ASSEMBLY.md](ASSEMBLY.md), [PROTOTYPE_VALIDATION.md](PROTOTYPE_VALIDATION.md) |
| Engineering | [ENGINEERING_NOTE.md](ENGINEERING_NOTE.md), [detailed calculations](references/engineering/engineering_checks.md), [design intent](DESIGN.md) |
| Evidence | [Fresh geometry findings](references/geometry/MEASURED_FINDINGS.md), [official source register](references/research/meanwell_requirements.md) |
| Digital checks | [CAD verification](quality/cad_verification.json), [manufacturing verification](quality/manufacturing_verification.json), [quality review](quality/DESIGN_REVIEW.md) |

The STL is a geometry preview only. This structural part is specified as machined 6061-T6/T651; no printed structural version or sheet-metal bend pattern is being released. DXF coordinates retain the global XY datum even for the underside operation; the fabricator must set the correct face and fixture transform. Do not treat the Ø6.1 countersink reference circles as a final depth acceptance criterion. The physical screw head must be flush to 0.10 mm below datum A.

## Hardware and physical release checks

Use three [McMaster 91294A128](https://www.mcmaster.com/91294A128/) M3 × 0.5 × 8 mm, 90° flat-head hex screws. Nominal protrusion into the PSU is 3.05 mm; gauge each actual assembly to 2.75–3.35 mm, always below the manufacturer's **4 mm maximum from the chassis face**. Verify the actual M3 pitch, complete engagement through each mounting boss and tip clearance. The model's smooth screw shank and ideal cone are reference proxies; they do not establish thread fit or the real DIN7991 head envelope.

Four M3 FPE WGU30 studs, nominal 12 mm projection, lie on a **110 × 264.7 mm** rectangle. Four 98688A142 washers and four 90576A102 nylon locknuts complete that interface. See the BOM for full specifications, verified catalog links and observed pack prices. FPE must accept the actual panel material/thickness, stud installation, position tolerance and load/temperature/installation-torque demands before the panel is ordered.

The manufacturer's general ±0.5 mm dimensions do not guarantee simultaneous fit through three self-centering countersinks. Print the 1:1 template at 100%, check its calibration bars, survey the actual unit and verify the pattern before final drilling/countersinking. Do not pull misaligned holes into position with the screws. Gauge at least 0.20 mm clearance under both plastic fan frames and contact on the intended metal lands. Changes to those narrow lands require renewed geometry and strength checks.

There is **no thermal pad in this design**. Preserve the factory terminal-end intake and twin-fan exhaust. The 100 mm end corridors are planning reservations; actual cables, lugs, guards and adjacent heat sources determine the final layout. The 12 V unit's full-load typical-efficiency example gives about **185 W PSU heat loss**. The TEC cooling capacity, recirculation, condensation and total enclosure heat budget remain unverified. Preserve the designated FG protective-earth conductor.

## Regenerate

Tested with Python 3.11 and the pinned packages in `requirements.txt`. Work from a short writable path when possible; the generators stage STEP/PDF kernel operations in temporary folders to avoid Windows long-path failures.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe model.py
.\.venv\Scripts\python.exe verify_and_render.py --work-dir C:/cadwork/nsp1600_verify
.\.venv\Scripts\python.exe verify_manufacturing.py
.\.venv\Scripts\python.exe references/engineering/engineering_calculations.py --write
.\.venv\Scripts\python.exe make_documents.py
```

Optional: within the original repository, run `python -m lib.evaluate parts/custom/meanwell-nsp1600-stud-mount --no-render`. The portable folder includes the feature builders but not the entire repository evaluation suite.

Edit `params.json` to revise the fit, stock thickness, hole positions, stud pitch/rotation/offset and panel size. The source datum is X across the 85 mm PSU width, Y0 at the terminal-side chassis plane, Z0 on the adapter underside. Source STEP normalization is translation only; unit mounting face is placed at the plate top. A new STEP hash requires repeating the component audit before using stored solid indices.

Changing dimensions invalidates the current drawings, strength calculations and physical release criteria until regenerated and reviewed. The engineering and drawing scripts deliberately reject unsupported changes instead of silently claiming the old checks still apply. Inspect every regenerated PDF page and CAD view, rerun the applicable checks, then run `package_design.py` to rebuild the ZIP and hash inventory. Packaging verifies digital integrity; it cannot perform or approve physical testing.

## Completed and pending

Nominal CAD: **81 checks pass**, including exported STEP validity/scale/count, adapter fit, fan clearance, mounting screw tip clearance, tool approach and sampled straight removal. The custom part passes the project gate at **79.1/100, band B, role plate**. Independent manufacturing verification reconstructs the part from DXF operations and compares it to the reopened STEP. Analytical checks and their assumptions are provided separately; no FEA or physical test was performed.

Before fabrication release, complete the fit survey and receive the actual hardware. Before operating installation, qualify the PSU threaded mounts, FPE anchors, main panel/supports and final cables; then perform the thermal and retention tests in the prototype plan. Vehicle, airborne, outdoor and overhead use are outside this preliminary design basis.
