# SCE-20H2010LP mounting-panel set

**Quote/prototype package — 8 September 2026.** One aluminum backpanel and three aluminum adapters support all five devices. The layout assumes the cabinet is upright, with cable entry at the bottom. Obtain supplier acceptance of the machining/material requirements before ordering; system thermal and load qualification remains open.

## Front Panel Express order

The intended order contains **one of each** native design:

| Native design | Size, mm | Included features |
|---|---|---|
| `Backpanel_R1.fpd` | 431.8 × 431.8 × 6 | Original outline and six enclosure holes; 16 M3 load studs and four M4 female load standoffs |
| `B210_R2.fpd` | 150 × 148 × 4 | Four backpanel clearance holes; four recessed device-screw holes |
| `MeanWell_R2.fpd` | 72 × 316.8 × 6 maximum outline | Original narrow center and side tabs; four clearance holes and two device-screw holes |
| `Bedrock_R3.fpd` | 166 × 184 × 6 | Four clearance holes, six device-screw holes and shallow thermal pockets on both faces |

Read `ORDERING_NOTES.md` with the quote. The Bedrock pockets, finished thickness, aluminum alloy and thermal contact faces need explicit supplier acceptance. The native designs use bare aluminum; they do not certify a particular alloy or heat treatment.

**All four native files are verified and present.** The three adapter STEP exports passed **110 checks**: B210 31, Mean Well 19, Bedrock 43 general plus 17 thermal-field checks. Native STEP exports and their audit reports are in `verification/`; they are separate from the source CAD references. These checks establish the modeled features, not production-process or operating qualification.

The Peplink router and OZ housing already have integral mounting ears. They mount directly to the new backpanel. **No extra aluminum plate is needed for either.** The OZ base and snap cover remain separate PA12 printed parts, listed in the hardware BOM.

## Assembly information

- `LAYOUT.png` / `LAYOUT.svg`: component placement, mounting points and cable/air reservations.
- `Installed_R1_top.png` / `Installed_R1_iso.png`: renders of the final CAD assembly.
- `Backpanel_R1.step`, `B210_R2.step`, `MeanWell_R2.step`, `Bedrock_R3.step`: individual source CAD references, named to match their native designs. `Installed_R1.step` and `Enclosure_Installed_R1.step` show the mounting assembly and the assembly in the supplied enclosure. Original source paths and copy hashes are retained in the transfer manifest.
- `HARDWARE_BOM.csv`: panel hardware, loose fasteners, thermal compound and printed housing parts. Hardware already included in the native backpanel order is identified separately.
- `MOUNTING_COORDINATES.csv`: nominal hole/hardware input schedule for the four plates. All coordinates are millimetres from each plate's lower-left drawing origin; front is the device side. Native FPD coordinates resolve to 0.001 mm.
- Native `.fpd` files are the orderable designs. `.fpjs`, JSON and DXF files retain the editable generation inputs and contours.
- `NATIVE_FPD_VERIFICATION.md` records application readback, inspections and the independent exported-solid results. `SHA256SUMS.txt` covers every packaged file except itself.

The BOM covers these mounting interfaces. Electronics, connectors, cables and the OZ housing's internal module/connector fasteners follow their existing component instructions.

## Regenerating native files

The final source pairs are `SCE20_BACKPANEL_R1.fpjs` / its `_inputs.json` and `SCE20_ADAPTERS_FINAL_R3.fpjs` / its `_inputs.json`. The first makes the backpanel; the second makes B210 R2, Mean Well R2 and Bedrock R3. Their JSON files provide the dimensions and features. The source scripts retain the original short save paths; the helper stages copies for a different computer or folder.

With Python 3 installed, open PowerShell in this delivery folder and run:

```powershell
python .\regenerate_fpd.py --output-dir C:\FPE_SCE20_R3
```

Choose a new short output folder. The helper rewrites the save paths in staged copies, places the Mean Well outline DXF beside them, and refuses to overwrite existing scripts, inputs or native targets. It does **not** create native FPD files or launch the application.

In Front Panel Designer, use **Edit > Scripts > Add** to add the two staged `.fpjs` files, then execute them individually. The adapter script creates three panels. Require `PASS SAVED+RELOADED` for all four panels in the script output. Inspect the panel properties, hardware, error list and both 2D/3D views, and export/verify STEP before accepting regenerated files. A changed input requires new native verification. Preserve the original delivery and copy only the newly verified native files into a new revision folder.

## Verification and remaining limits

The final CAD integration passed **49 of 49 checks**. The assembly reaches **91.000 mm** above the new panel, leaving **146.535 mm** to the nearest modeled door obstruction. It clears the enclosure, original mounting hardware, all four Ø30 mm factory-nut tool envelopes and the two complete 100 mm PSU end reservations. The selected arrangement retains at least **3.375 mm** additional clearance in the bounded layout search. It is a local max-min layout for the chosen orientations and cable allowances; a global optimum is not established.

The repository's separate **mechanical evaluation passed**. Its **full evaluation failed** the refinement gate: **48.8 / grade D**, below the required 70. This gate has not been waived or presented as passed. Reports and source-copy checksums are in `verification/`.

Bedrock precision milling needs supplier acceptance. The layout does not establish the PSU manufacturer's 100–150 mm clearance from adjacent heat sources or the required derating for its side orientation. Thermal performance, vibration loads and adhesive-stud capacity remain unqualified; see `ORDERING_NOTES.md`.
