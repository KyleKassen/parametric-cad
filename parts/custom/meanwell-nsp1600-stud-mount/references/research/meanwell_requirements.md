# Mean Well NSP-1600 mounting evidence

Checked 2026-09-08. This register distinguishes manufacturer statements, geometric interpretation and unresolved installation requirements. No supplier contact, purchase, electrical work or physical test was performed. The source STEP and vendor PDFs remain unchanged.

## Sources and revision match

The [official NSP-1600 specification](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf), retrieved today, is eight pages, revision **2026-06-15**, case **296A**. The [official enclosed-type installation manual](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf), linked from [Mean Well's manual page](https://www.meanwell.com/productManual.aspx), is nine pages, dated **2025.12.17**, and explicitly includes the NSP family.

The downloaded PDFs and the existing local vendor copies have **identical normalized extracted text**, although file hashes differ. This confirms the text/revision match; it does not assert byte-identical files. Relevant specification pages 2, 3, 6 and 8 and manual pages 1 and 5 were visually inspected. The exact downloaded originals, extracted text, rendered pages and hashes are retained in this folder. See [source_manifest.json](source_manifest.json) and the reproducible [inspect_sources.py](inspect_sources.py).

## Authorized attachment features

Specification page 6 explicitly labels **three bottom M3 holes**, mounting-hole group 1. The diagram defines penetration L from the power-supply chassis mounting surface inward; it is not the total purchased screw length. Two side M4 holes per side form group 2. Page 8 illustrates the optional side brackets and M4×4 combination screws. [NSP-1600 specification, pages 6–8](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf).

| Manufacturer item | Bottom group 1 | Side group 2 |
|---|---:|---:|
| Count | 3 total | 2 per side, 4 total |
| Screw nominal size | M3 | M4 |
| Maximum external penetration L | **4 mm** | **5 mm** |
| Recommended mounting torque | **6–8 kgf·cm** | **7–10 kgf·cm** |
| Calculated SI torque conversion | **0.5884–0.7845 N·m** | **0.6865–0.9807 N·m** |
| Explicit thread pitch / guaranteed complete engagement | Not specified | Not specified |
| Permitted axial/shear mount load | Not specified | Not specified |

Conversion uses 1 kgf·cm = 0.0980665 N·m. The product-specific mounting table takes precedence over generic material torque tables. The catalog mounting torque is a manufacturer recommendation for its attachment feature; it does not independently qualify a countersunk screw head, custom adapter seat, coating, threadlocker or FPE anchor. Do not add torque for locking chemistry without a qualified procedure.

The bottom drawing has a 70 mm transverse pair, centered within the 85 mm width; the pair is 16.1 mm from the terminal-side case end. The third hole is centered across the width and is 264.7 mm beyond that pair toward the fans. Expressed as drawing coordinates with origin at a terminal-side body corner: **(7.5,16.1), (77.5,16.1), (42.5,280.8) mm**. These transcribed dimensions are subject to the drawing's **±0.5 mm general tolerance**. Use the fresh STEP audit and actual unit to establish the design datum and measured pattern. Do not regard nominal CAD coincidence as tolerance-qualified fit.

The nearby Ø2.8 side features and cover fasteners are not identified as group 1 or group 2 mounting holes. Leave the cover and its screws intact. The [installation manual](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf) requires clearance from internal components and refers the installer to the case drawing for screw limits. M3×0.5 and M4×0.7 are plausible standard coarse-thread interpretations, but pitch, thread condition, engagement and screw-tip clearance require a physical check. Do not use tightening to find a blind end.

## Configuration, mass and operating envelope

The current specification covers **NSP-1600-12, -24, -36 and -48**, sharing a nominal **300×85×41 mm** body; its mechanical drawing gives ±0.5 mm general tolerance. These body dimensions exclude the full installed lug, cable and service envelopes. The packing table states **1.8 kg per unit**, not a 3 kg unit mass. Confirm the actual model and accessories and add adapter/hardware/cable allowances separately. [Specification pages 1–2 and 6](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf).

The permitted working ambient is **−20 to +70°C subject to derating**, 20–90% RH noncondensing. Page 3's curve is labeled **HORIZONTAL**: 100% load to 50°C, 75% at 60°C and 50% at 70°C. It also derates at low input voltage; rated operation is not determined by ambient alone. The generic manual says other orientations require output-current derating, but no alternate-orientation curve is provided for this unit. Therefore horizontal stationary indoor installation is the supported preliminary basis; another orientation requires additional manufacturer information or qualified thermal evaluation. [Specification pages 2–3](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf), [manual item 3](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf).

The vibration entry is 10–500 Hz, 2 G, 10 minutes per cycle, 60 minutes per axis. This is a product specification; it is not a rating for the proposed adapter, FPE studs, cable assembly or supporting structure. No mount shock or fatigue capacity is published. The case material, alloy, thread-insert capacity and permitted local clamp deformation were not established by these sources.

## Airflow and service envelope

The mechanical drawing's airflow arrow runs **from the terminal end toward the two fan outlets**. Keep the terminal-side intake louvres and fan exhaust free. The manual requires unobstructed fans/vents and **100–150 mm clearance when an adjacent device is a heat source**. It does not provide a universal 60 mm fan clearance in the inspected current documents; any such CAD reserve must be labeled a design assumption and validated. Do not enclose the exhaust in an adapter wall or allow it to recirculate into the intake. [Specification page 6](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf), [manual item 4](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf).

The drawing shows output blades projecting **38 mm and 28 mm**, Ø6.5 mm lug holes, AC/FG terminal access, CN1/CN2 connector space, LED and voltage-adjustment access. These dimensions are not complete plug or cable-bend envelopes. Actual lugs, insulation boots, wire gauges, strain relief and vendor bend radii must determine installation clearance and cable loads. Reserve tool approach and hand access while keeping cables away from both ventilation paths.

The unit-specific page 7 gives the AC input terminal screw as **M3.5, maximum 8 kgf·cm = 0.7845 N·m**. The general manual table says 8–10 kgf·cm for several M3.5 terminal families; do not apply its higher value over the specific product maximum. This terminal value is separate from the M3 chassis-mounting torque. No output-lug tightening torque was found in the inspected product drawing.

## Grounding and integration boundaries

Preserve access to the designated **FG terminal** and its protective-earth conductor. The manual explicitly requires FG to earth and isolation from utility power before installation/maintenance. A metal adapter, paint-free contact or FPE stud does not replace that conductor or prove a protective-earth bond. Qualified electrical integration must provide the final wiring, guarding, insulation distance, strain relief and system verification. Mechanical removal is a disconnected-power service operation. [Installation manual, installation items 1 and 8 and warnings](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf).

The specification's EMC tests used a 720×360×1 mm metal plate; that is test context, not a required mounting-plate size or evidence that any new plate is electrically qualified. The final equipment still needs its applicable EMC/safety assessment. No thermally conductive pad is required by these mounting sources; the unit uses forced air. Do not carry the Bedrock grease fields into this design without a separate thermal requirement.

## FPE load studs: M3 verified, M4 unresolved

The [current FPE help](https://docs.frontpanelexpress.com/elements/studs_standoffs.html) supports load studs for heavier equipment, minimum 3 mm panel thickness, 2.3 mm cavities and minimum 0.5 mm material between cavity edges and panel edges/cutouts and behind opposing cavities. It gives no numeric tension, shear, torque, fatigue or temperature rating. The [6.5.1 download](https://www.frontpanelexpress.com/front-panel-designer/download) remains current on the inspected page.

The official distributed `Bolt.d/10-Base.ini` contains **WGU40 / Name=M4**, but its **ThreadSize=3000** conflicts with that label. The shared WGLSU drawing path uses TD directly. The inspected `Bolzen.fpjs` only converts older cavities to standard GU30/GO30; it contains no WGU40 or thread-size override. A catalogue label therefore supports an intended M4 option, but not a verified Ø4 shank envelope. The [FPE product summary](https://www.frontpanelexpress.com/products) omits M4 from its listed stud sizes. No readable overriding configuration or toleranced production drawing was found.

For WGU40, nominal catalog cavity Ø12.1×2.3 mm, base drawing Ø11.9×2.2 mm and geometric lengths 6/12/20 mm are recorded, **with shaft thread and production availability unresolved**. WGO40 is an internally consistent M4 *female load standoff*, a different interface. The consistent **WGU30 M3 load stud** remains the verified fallback, with the same nominal base/cavity dimensions. Neither option has a demonstrated installed capacity. Select actual stud count, spacing and length from the engineering demand and qualify the FPE anchorage including nut installation/prevailing torque.

The retained FPE manufacturer-package SHA-256 is `a9969415df52668fd9b0d85ff47d838c34b109c0b650978006e9e482d184bb1a`; it was read without installation or execution. Relevant original catalog files are copied into this folder. No FPE contact or order was made.
