# N2 fresh side-interface audit

The unchanged component-library STEP was imported again for this audit. It has **19 valid solids in millimetres**, SHA256 `d421a1e7fb7a3b5fd2e12588484a2e970456301955c0a17f55be6d56324dd8a0`. All numeric solid identities here are zero-based in original import order. The N1 design and its reference files were not modified. No physical measurement, assembly or test was performed.

## Selected side and datums

The first normalization translates the source by `(-66.7869113,-354.1518617,-1.4999997)` mm. This gives original-width X=±42.5, terminal-chassis Y=0, and original bottom Z=0. The original complete assembly is 85 ×338.6 ×41 mm, including terminal blades; its fan guard reaches Y=-300.6 and its longest blade reaches Y=+38.

Use the **original +X side** as the preliminary side-contact face. After the first translation, rotate +90 degrees around Y and translate `(-20.5,0,42.5)`:

`Xnew = Zold -20.5; Ynew = Yold; Znew =42.5 -Xold`.

The resulting original reference envelope is X=-20.5..20.5, Y=-300.6..38, Z=0..85 mm. The face seats at new Z=0. Both designated M4 axes become **X=+2.3**, at **Y=-5.8 and -257.8**, a **252.0 mm pitch**. Z is inward into the PSU. The opposite -X side would instead use -90 degrees around Y and the corresponding mirrored X axis; its mounting line would be X=-2.3.

The +X side has 11,542.20648 mm² of nominal coplanar metal, versus 11,485.65781 mm² on -X. It also gives greater modeled terminal-end screw clearance. These modest geometric advantages do not establish a thermal or structural advantage.

## Side mounting features: manufacturer versus actual source

The manufacturer's Case296A drawing, mounting group 2, specifies **two M4 mounting holes per side**, maximum penetration **5 mm** measured inward from the casing, and recommended mounting torque **7–10 kgf·cm** (0.6865–0.9807 N·m). See the retained manufacturer evidence in the project research folder and the [official NSP-1600 specification](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf), mechanical drawing page 6. Neither screw pitch, thread capacity nor accepted custom countersunk-seat capacity is established by the model. The manufacturer limit governs even where the STEP is empty.

| Feature | Fresh STEP evidence, both sides | Consequence |
|---|---|---|
| Terminal-end station | Original Y=-5.80000098, Z=22.79999999. Rounded geometric entry extends inward 0..0.72 mm. Ø3.1 cylindrical surface extends 0.72..2.10 mm, length1.38 mm. | A short local side-wall extrusion, not a cross-body tube. No modeled helical thread or complete engagement specification. |
| Fan-end station | Original Y=-257.80000098, Z=22.79999999. Ø5.0 opening through the casing from inward depth0..1.20 mm. | **No female thread, insert, nut or rear mounting screw is modeled behind the hole.** Confirm the received rear M4 feature before final screw selection or loading. |
| Nearby small holes | Original Z=16.8, Y=-5.8/-257.8; nominal Ø2.8. | Separate source assembly features, not substitutes for the manufacturer's M4 stations. |

At the terminal-end +X M4 axis, a complete Ø4 cylindrical probe first reaches another component at **7.500003 mm inward**, the negative output blade (source solid13). The thin axial probe gives the same first location. At the -X terminal-end axis, the Ø4 probe first reaches the AC terminal block (solid1) at **5.798055 mm**; a centerline-only probe misses this nearer off-axis obstruction. This is why the finite-diameter probe matters. At both rear stations, the Ø4 probe finds **no material anywhere through the full85 mm width**. Empty CAD space is not permission for a longer screw, nor evidence of electrical safety.

The new exported side-reference STEP was reopened:19 valid solids, unchanged envelope, aggregate volume integration difference18.12 ppm. This small numerical difference is recorded; source mass is not inferred from its modeled volume. All original source bytes remain unchanged.

## Contact faces, seams and local bearing evidence

The actual +X main casing face (solid17, not the removable cover16) spans old Y=-264.4..0 and old Z=1.3..41. In the new side frame it is X=-19.2..20.5: **39.7 mm of available width**, with circular openings/recesses, not a continuous41 mm rectangle. Its planar area is10,165.53011 mm². The fan bracket (solid0) continues the side face from Y=-298.2..-264.4 across the full41 mm width, with area1,376.67637 mm². Their seam is Y=-264.4. The rear fan guard extends another2.4 mm to Y=-300.6; do not confuse that envelope with contact-face length.

No source solid projects beyond either X=±42.5 plane. The source has circular casing features and omits separate proud cover-screw heads. Physical screw heads, labels, feet, coating, burrs and panel coplanarity must be checked before assuming flush side seating. The source does not establish the function of every circular recess; do not describe them all as vents or all as structural anchors.

Actual planar-face intersections with proposed rectangular station footprints give:

| New-frame footprint | Nominal coplanar metal area |
|---|---:|
| X=±20.5, Y=-21.8..0 |729.80223 mm², all main casing |
| X=±20.5, Y=-273.8..-241.8 |1,162.82721 mm², main casing plus fan bracket |

Smaller explicit patches were checked for the roll-load calculation. All are on the **main casing**, not its removable cover. They demonstrate material presence only, not bearing strength or adequate preload:

| New-frame patch | Actual metal / rectangular area | Minimum X lever from M4 lineX=2.3 |
|---|---:|---:|
| X=-13.7..-12.7, Y=station±4, either station |8.000/8.000 mm² |15.0 mm |
| X=17.3..18.3, frontY=-9.8..-1.8 |7.47147/8.000 mm² |15.0 mm |
| X=17.3..18.3, rearY=-261.8..-253.8 |3.92785/8.000 mm² |15.0 mm |
| X=19.1..20.0, Y=station±4, either station |7.200/7.200 mm² |16.8 mm; near the upper casing edge |
| X=17.3..18.3, frontY=-11.8..-9.8 or rearY=-254.8..-252.8 |2.000/2.000 mm² |15.0 mm |

The requested right-hand15 mm-lever patches are **not fully supported rectangles**; circular casing features remove part of their area. Engineering must use the actual contact geometry or a physically qualified alternative. Additional larger interior patches are retained in `side_reference_and_contacts.json`.

## Cooling, connectors and service orientation

With +X down, the fans stack vertically across the new85 mm height and exhaust toward -Y. The terminal/AC/DC/control end remains +Y, with the manufacturer's flow direction running from the terminal end toward the fans. The old cover becomes the new +X vertical wall; the original bottom becomes the new -X vertical wall. A narrow side adapter therefore need not cover the original fan undersides.

The longest DC blade still projects38 mm beyond Y=0, the other27.95 mm, and the source AC terminal block approximately7.96 mm. These are component envelopes, not complete lug, boot, cable-bend, finger-protection or socket clearances. Real wiring, independent strain relief, FG protective-earth access, fan intake/exhaust corridors and lift/removal space need installation checks.

The published NSP-1600 load/ambient curve is for horizontal installation; the side-standing orientation needs manufacturer guidance or thermal qualification. Do not carry the N1 horizontal full-power assumption into this orientation. No thermal interface pad or grease requirement is inferred.

## Reproduce and inspect

Run `audit_side_mount.py`, then `side_sections_and_contact.py` using `C:/venvs/cadquery/Scripts/python.exe`. Both read the unchanged original STEP and write only this N2 geometry-reference folder and short temporary staging. `side_geometry_audit.json` preserves all analytic source-face records and probe hits. `side_reference_and_contacts.json` contains the transform, STEP reopen result and actual contact-patch areas. The side-reference STEP contains all19 original solids; it contains no invented rear threads.

Four true mounting-axis sections are provided as editable SVG and PNG in `sections`. Seven source context views, including both full side profiles, are in `views`. View renders are centered solely for camera framing; the exported reference retains the stated datums. The files record nominal CAD observations and outstanding physical holds, not a fabricated or qualified mount.
