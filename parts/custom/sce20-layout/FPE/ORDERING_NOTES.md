# Ordering and assembly notes

## What Front Panel Express makes

This quote/prototype package contains one each of `Backpanel_R1.fpd`, `B210_R2.fpd`, `MeanWell_R2.fpd` and `Bedrock_R3.fpd`, with verified native geometry. Obtain supplier acceptance of the following requirements before ordering. All four designs use bare aluminum. Request **6061-T6/T651 or an expressly accepted equivalent**, and **finished thickness ±0.05 mm**. Do not infer alloy, temper, thickness tolerance or surface flatness from the generic aluminum selection in FPD.

FPE's published raw stock is EN AW-5005 at 1–4 mm and EN AW-5754 at 5–10 mm. The requested 6061 material and finished tolerances therefore require a specific quote; substituting standard stock needs engineering acceptance of the screw, thermal and strength interfaces. [FPE aluminum data](https://www.frontpanelexpress.com/downloads/FPE/Aluminum-Datasheet.pdf?v2=).

Backpanel hardware is native FPD hardware on the **front/component side**, depth offset zero:

| Quantity | Catalog code | Selected hardware | Assignment |
|---:|---|---|---|
| 16 | WGU30 | M3 male load stud, 12 mm | Four each for B210, Mean Well, Bedrock and OZ |
| 4 | WGO40 | M4 female load standoff, 6 mm | Peplink router |

Keep hardware bases and adhesive flush with or below the component seating face. Native hardware features define their own machining; the adapters contain ordinary clearance holes. No studs are fitted to the three adapters.

## Bedrock quote acceptance

The thermal interface depends on **0.050 ±0.010 mm deep pockets on both faces**, nominal 126 × 156 mm fields with R5 corners, retained screw lands and escape grooves. Preserve **Ø8 mm front lands** and **Ø12 mm rear lands**, with **Ra ≤1.6 µm** in the contact fields. The final native design/contours define their boundaries.

Request confirmation that FPE can hold these shallow depths and the ±0.05 mm finished stock thickness. Keep the thermal contact faces flat and conductive; an anodized insulating layer is not part of this design. Apply a thin thermal-compound film on both interfaces and verify an assembled gap **≤0.10 mm**. The pocket geometry and compound provision do not establish a thermal rating for the computer, panel or closed cabinet.

**Precision-milling exception:** the Bedrock pocket construction requests a **0.6 mm cutter**, below FPE's published **1 mm minimum milling cutter**. FPE also publishes typical production tolerances of 0.05–0.10 mm, wider than the requested pocket depth tolerance. Obtain written acceptance of the pocket process, tool and depth, or revise and reverify the thermal interface before ordering this plate. A saved FPD object is not evidence of standard-process manufacturability. [FPE technical FAQ](https://www.frontpanelexpress.com/faq).

## Device screws and seating

The device side is FPD front. Device screw heads enter from the reverse side of each adapter. Assemble each device to its adapter before placing the adapter on the backpanel.

| Adapter | Device screws | Reverse countersink, 90° | Nominal head recess | Nominal projection into device |
|---|---|---|---:|---:|
| B210 | 4 × M3×6 flat head | Ø7.1 mouth, 1.85 deep; Ø3.4 bore | 0.55 | 2.55 |
| Mean Well | 2 × M4×10 flat head | Ø8.1 mouth, 1.80 deep; Ø4.5 bore | 0.05 | 4.05 |
| Bedrock | 6 × M4×8 flat head | Ø9.9 mouth, 2.70 deep; Ø4.5 bore | 0.95 | 2.95 |

Dimensions are millimetres. These deliberately recessed seats preserve the original screw projection after changing the B210 plate to 4 mm stock and Bedrock plate to 6 mm stock. Check actual screws and finished plates: B210 projection **2.4–2.9 mm**; Bedrock **2.85–3.00 mm**, at least **2 mm complete thread engagement** and **0.5 mm tip clearance**; Mean Well projection **≤5 mm**. Deburr the opposite bore entrances by no more than 0.1 mm.

The final native STEP audits measured nominal screw projections of **2.549 mm B210**, **4.049 mm Mean Well** and **2.949 mm Bedrock**, consistent with those limits. These are geometry checks using the specified screw heads; verify the manufactured stack with actual hardware.

Backpanel patterns are B210 **136 ×120.015 mm**, Mean Well **57 ×252 mm**, Bedrock **152 ×164 mm**, Peplink **161.8 ×82.7 mm** and OZ **106.2 ×96 mm**. `MOUNTING_COORDINATES.csv` gives every individual location. Preserve the B210 fractional pitch at the native file's 0.001 mm coordinate resolution.

Fit the three aluminum adapters with 7 mm OD ×3.2 mm ID ×0.55 mm washers and M3 locknuts. Fit OZ with **9 ×3.2 ×0.8 mm washers centered in its 4.5 ×9 mm slots**, plus M3 locknuts. The BOM uses 4 mm high, 5.5 mm across-flats nuts; nominal stud projection beyond a 6 mm adapter/washer/nut stack is **1.45 mm**. Check actual locking engagement and avoid excessive clamp load on the printed OZ ears.

Peplink uses M4×8 pan/button-head screws and **9 ×4.3 ×1 mm washers** into the 6 mm female standoffs. Its 2.5 mm ears leave **4.5 mm nominal thread engagement**. Keep screw-head/washer OD ≤9 mm. External antenna cables are assumed; directly attached rigid antennas are outside the reserved envelope.

## Reusing the enclosure mounting hardware

The new plate preserves the original rear seating plane. Increasing the original 3.175 mm subpanel to 6 mm moves its front face and seated factory nuts outward by **2.825 mm**; the original enclosure studs remain fixed. The CAD stack leaves approximately **1.34 mm of original stud beyond the nut**. Verify full engagement on the actual enclosure before loading the assembly. Retain the original four factory nuts and original mounting/bonding provisions; do not substitute an inferred thread size from the STEP geometry.

## Installation and service space

Keep the PSU's complete 100 mm intake and exhaust reservations open. At this placement they end only **1.795 mm from the inner walls**. The intake distance is measured from the terminal face; its existing terminal protrusions are already included. Open internal space does not demonstrate adequate heat removal from a closed enclosure: total heat load and cooling must be checked at intended operation.

Mean Well specifies **100–150 mm clearance when an adjacent device is a heat source**, unobstructed ventilation, and output-current derating for nonstandard mounting orientations/high ambient conditions. The 100 mm axial reservations are layout allowances; they do not establish this adjacent-heat-source separation. Nearby electronics and the PSU's side orientation leave **thermal separation and orientation derating unresolved**. Confirm the intended loads, operating temperatures and mounting orientation with the NSP-1600 specification/manufacturer before operation. [Mean Well enclosed-supply installation manual, installation items 3–4](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf).

The final layout has passed exact enclosure, factory-hardware and Ø30×60 mm tool-envelope checks. Cable fields are planning allowances; check the selected plug boots, coax/fiber bend radii and harness routing. OZ needs **47 mm additional outward cover-opening space plus hand access** and remains a PA12 prototype requiring physical latch/fit testing. System strength, thermal performance and vibration retention have not been qualified.
