# R2 ordering and assembly notes

## Supplier requirements

This is a quote/prototype package for the five plates listed in `README.md`. All plates use bare aluminum. Request **6061-T6/T651 or an expressly accepted equivalent** and **finished thickness ±0.05 mm**. FPD's generic aluminum selection does not certify alloy, temper, thickness or flatness. FPE publishes EN AW-5005 for 1–4 mm raw stock and EN AW-5754 for 5–10 mm; any substitution needs acceptance of the thermal, screw and strength interfaces. [FPE aluminum data](https://www.frontpanelexpress.com/downloads/FPE/Aluminum-Datasheet.pdf?v2=).

The backpanel preserves the original 431.8 mm square outline, R6.35 corners and six enclosure holes. Its rear seating plane stays fixed. All native hardware faces the components, with **depth offset zero and bases/adhesive flush with or below the seating face**. FPD hardware objects define their own machining; do not add separate ordinary mounting cavities.

| Location | Quantity | Selected native FPE hardware |
|---|---:|---|
| Backpanel: Mean Well, Bedrock and OZ | 12 | WGU30 M3 male LOAD studs, 12 mm |
| Backpanel: raised B210 and router carrier | 8 | WGO30 M3 female LOAD standoffs, 20 mm |
| Peplink carrier | 4 | WGO40 M4 female LOAD standoffs, 6 mm |

## Bedrock thermal interface

Keep the Bedrock adapter directly against the main panel. Preserve **0.050 ±0.010 mm pockets on both faces**, the 126 ×156 mm R5 contact fields, **Ø8 front and Ø12 rear lands**, and the 1 mm escape grooves. Contact fields require **Ra ≤1.6 µm**, conductive surfaces and sufficient flatness to maintain assembled gaps **≤0.10 mm** with a thin thermal-compound film. The native file uses separate single-loop regions that form each field.

The selected **0.6 mm cutter** and ±0.010 mm pocket-depth requirement need a supplier exception: FPE publishes a 1 mm minimum milling cutter and typical production tolerances of 0.05–0.10 mm. Obtain written process/material acceptance, or revise and reverify the interface before ordering. Native application acceptance does not establish supplier capability. [FPE technical FAQ](https://www.frontpanelexpress.com/faq).

The windowed carrier leaves 13 mm between the Bedrock top and carrier underside, but Peplink above it changes airflow. Retaining direct panel contact and a window does not qualify temperatures or heat rejection. Keep the vertical fin channels and their ends open, and check both devices at intended loads and ambient temperature.

## Raised-support hardware

Use four **Würth 971500321**, 50 mm long, under the Peplink carrier and four **971300321**, 30 mm long, under B210. Each extension has 5.5 mm hex flats, M3×0.5 male/female threads, 6 mm male length and 7 mm female depth; the specified material is gloss-zinc-plated steel. They are separately purchased extensions, not 50/70 mm native FPE studs. [50 mm drawing](https://www.we-online.com/components/products/datasheet/971500321.pdf), [30 mm drawing](https://www.we-online.com/components/products/datasheet/971300321.pdf).

The native 20 mm standoffs plus those extensions establish **70 mm carrier** and **50 mm B210** underside heights. The 6 mm extension threads enter the native 10 mm usable female thread with 4 mm nominal tip margin. Secure each upper plate with four **M3×10 socket-cap screws**, 5.5 mm head diameter and 3 mm head height, plus **7 ×3.2 ×0.55 mm washers**. A 4 mm plate leaves 5.45 mm nominal insertion into the 7 mm female extension, with 1.55 mm tip margin. Check actual hardware and finished thickness; torque, locking method and anchor/column load capacity are not qualified.

For the carrier screws, use a **2.5 mm hex key or bit whose outside envelope is ≤8 mm for the first 40 mm above the washers**. Keep a larger holder above this zone. The lower screws have approximately 1 mm nominal clearance to the router for that envelope. A 10 mm tool touches the router end wall.

## Device and direct-mount screws

Device screw heads enter from the reverse side of the three existing adapters. Fit each device to its adapter before final installation.

| Adapter | Device screw | Reverse 90° seat: mouth / bore / conical depth, mm | Native-geometry screw projection |
|---|---|---|---:|
| B210 | 4 × M3×6 flat head, OD6 head | 7.1 / 3.4 / 1.85 | 2.549 mm |
| Mean Well | 2 × M4×10 flat head, OD8 head | 8.1 / 4.5 / 1.80 | 4.049 mm |
| Bedrock | 6 × M4×8 flat head, OD8 head | 9.9 / 4.5 / 2.70 | 2.949 mm |

Accept B210 projection **2.4–2.9 mm**; Bedrock **2.85–3.00 mm**, with ≥2 mm complete engagement and ≥0.5 mm tip clearance; Mean Well **≤5 mm**. Opposite bore deburr is ≤0.1 mm. These are specified-screw geometry checks; verify received screws and machined plates.

Mean Well and Bedrock direct studs use 7 ×3.2 ×0.55 mm washers and M3 locknuts. OZ uses **9 ×3.2 ×0.8 mm washers**, centered in its 4.5 ×9 mm slots, and M3 locknuts. The BOM assumes 4 mm high locknuts. A 6 mm plate/0.55 mm washer/nut stack leaves 1.45 mm of a 12 mm stud; verify full locking engagement. Avoid excessive clamping of printed OZ ears.

Peplink uses **M4×8 pan/button-head screws** with **9 ×4.3 ×1 mm washers** through 2.5 mm ears into the carrier's 6 mm female standoffs: 4.5 mm nominal insertion. Keep heads/washers ≤9 mm OD. Use external antenna cables; rigid antennas attached directly to the router are outside the model.

## Installation and service

1. Install and bond the main panel using the enclosure's original provisions. Changing 3.175 mm stock to 6 mm shifts the seated factory nuts outward 2.825 mm; the original studs remain fixed. CAD leaves approximately **1.34 mm beyond the nut**. Verify full engagement on the actual enclosure; do not infer its thread from STEP.
2. Fit the PSU, Bedrock with both thermal interfaces, and the closed OZ housing. Fit the purchased extension columns. Dress Bedrock's left-side cables after panel installation; its conservative cable field overlaps the lower-left factory socket approach and must move for nut service.
3. Fit Peplink to its carrier, then fasten the carrier to its four columns. Fit the B210/adapter assembly to its columns. Route cables with service loops that allow those assemblies to be removed.
4. To service OZ, disconnect or release the necessary B210 cables and remove the complete B210/adapter assembly first. The OZ cover needs about **47 mm additional outward space plus hand access**, which the 17.28 mm closed gap cannot provide. To service Bedrock, remove Peplink and the carrier together; the lower thermal joint may stay intact until Bedrock itself is removed.

Keep both complete 100 mm PSU end reservations open; they stop 1.795 mm short of the inner walls. These planning volumes do not establish Mean Well's **100–150 mm clearance from an adjacent heat source**, or the required derating for a nonstandard mounting orientation/high ambient. Adjacent-device heat, PSU orientation derating and closed-cabinet cooling remain unresolved operating conditions. [Mean Well installation manual, items 3–4](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf).

Cable fields are planning allowances. Check actual plugs, boots, coax/fiber bend radii and routing. Tall columns and adhesive anchors need load/vibration qualification; electrical bonding and complete-system thermal performance are not established by nominal CAD fit.
