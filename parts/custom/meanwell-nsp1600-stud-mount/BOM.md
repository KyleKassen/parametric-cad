# Mean Well NSP-1600 bottom stud adapter — N1 BOM

**Preliminary mechanical integration.** One installation uses three PSU mounting screws and four FPE panel studs. The 12 V PSU is the provisional electrical selection; 24 V remains possible. Operating load, ambient, final wiring and supporting enclosure remain unconfirmed. No purchase was made.

| Item | Qty installed | Complete specification / exact product | Initial purchase | Observed USD price |
|---|---:|---|---|---:|
| M01 — custom adapter | 1 | 125×300.6×5.00±0.05 mm CNC plate; certified 6061-T6/T651, minimum room-temperature yield 240 MPa; clear MIL-DTL-5541 Type II Class 3 conversion after machining. Two 0.50±0.05 mm fan-frame relief pockets per final CAD/drawings. | 1 finished part | Quote required |
| P01 — main panel | 1 | 145×340×6 mm **reference interface coupon**, centered Y−150.3 mm. Final panel material, supports and FPE installation require confirmation. | Final panel with installed studs | Quote required |
| H01 — PSU screws | 3 | [McMaster 91294A128](https://www.mcmaster.com/91294A128/): M3×0.5×8 mm overall length; DIN 7991, 90° flat head, 2 mm hex drive; fully threaded 6g, black-oxide alloy steel; catalog Class 10.9 / 120,000 psi tensile; catalog head Ø6×1.7 mm | 1 pack of 100 | $5.82 |
| H02 — stud washers | 4 | [McMaster 98688A142](https://www.mcmaster.com/98688A142/): M3 zinc-plated hardened steel flat washer, ISO 7089; ID 3.2×OD 7×0.5–0.6 mm; Rockwell C30 | 1 pack of 100 | $9.38 |
| H03 — stud locknuts | 4 | [McMaster 90576A102](https://www.mcmaster.com/90576A102/): M3×0.5 zinc-plated steel, Class 8, nylon insert, DIN 985 / ISO 10511, 6H; 5.5 mm AF×4 mm overall height | 1 pack of 100 | $4.88 |
| F01 — panel load studs | 4 | [Front Panel Express native load stud](https://docs.frontpanelexpress.com/elements/studs_standoffs.html): **WGU30, M3, 12 mm geometric length, reverse side, zero depth offset**, factory installed. It is an FPD catalog identifier, not a McMaster SKU. | 4 installed with the main panel | Quote required |

**Initial McMaster packs: $20.08.** The three screws, four washers and four nuts consume **$0.7450** of those packs; unused pieces remain inventory. The M3×8 screw's exact product page was verified live on **2026-09-08** during this Mean Well task and displayed next-day delivery. Washer/nut specifications and observed prices were verified earlier that day during the same workspace session's B210 procurement research and carried into this BOM. No purchase or supplier quote was made. Tax, shipping, fabrication/finish, FPE panel/studs, PSU, wiring/lugs/guards, strain relief, fixtures and validation are excluded. A complete installed cost is therefore unavailable.

## Mounting and hardware fit

The [current Mean Well specification](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf), revision 2026-06-15, explicitly authorizes **three bottom M3 mounting holes**. It permits **4 mm maximum penetration from the PSU chassis mounting face** and recommends **6–8 kgf·cm (0.5884–0.7845 N·m)** mounting torque. Its side M4 holes are a separate mounting option. Do not repurpose cover screws or nearby assembly features.

The M3×8 overall screw length minus the nominal 5.00 mm adapter plus 0.05 mm nominal head recession gives **3.05 mm penetration**. The assumed tolerance range is **2.75–3.35 mm**, below the manufacturer's 4 mm hard maximum; confirm actual finished screw/seat dimensions, thread engagement and internal clearance at all three holes. Nominal dimensions alone do not prove fit. The catalog's 1.7 mm head height is not the complete geometry of an ideal 90° conical proxy. The manufacturer's chassis torque does not independently establish reduced countersunk-head capacity, adapter-seat capacity, or a suitable threadlocking procedure. No washer belongs under the countersunk screws, and the finished heads must remain inside the adapter envelope.

The four provisional FPE axes are **X±55 mm**, at **Y−16.1 and −280.8 mm**: 110 mm across, 264.7 mm along. The nominal stack of 5.00 mm plate +0.55 mm washer +4.0 mm nut leaves **2.45 mm** beyond the nut on a 12 mm stud. Confirm installed projection, complete nylon engagement, protruding full threads and access using a **5.5 AF socket with OD≤10 mm and internal depth≥10 mm**. Check the actual socket before committing the panel layout.

The two upper fan-frame relief pockets occupy X−40 to −2.85 mm and X+2.85 to +40 mm, Y−299.1 to −269.5 mm, with R0.5 corners and 0.50±0.05 mm depth. Their purpose is to avoid loading the plastic fan frames. The retained metal strip at the rear mounting station remains structural; follow the final STEP/drawing rather than altering the pocket layout during fabrication.

WGU30 is the internally consistent M3 load-stud entry in the official catalog. The M4 WGU40 entry has conflicting diameter data and is not selected. FPE base/cavity geometry is nominal: Ø11.9×2.2 mm base within a Ø12.1×2.3 mm cavity. Final flushness, panel thickness, adhesive/anchor process and installed axial, shear, torque and temperature capacity remain qualification items. Do not infer anchor capacity from the nut's strength class.

The nylon locknut's catalog limit is **85°C at the actual nut**. It is not an ambient or assembly-temperature rating. Prevailing and installation torque must remain compatible with the FPE anchor. Inspect after prototype removal cycles and replace nuts for the final qualified installation as required by the assembly procedure.

## Cooling, grounding and service

**No thermal pad, grease or tape is selected.** This PSU uses forced air: intake at the terminal end, exhaust through the twin fans. Keep its ventilation paths unobstructed and preserve access to the terminals, FG, CN1/CN2, indicator and adjustment control. The preliminary operating basis is horizontal; the published curve supports full rated load through 50°C, with derating above that and at low input voltage. Other orientations need separate evaluation. The [Mean Well installation manual](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf) calls for 100–150 mm separation from an adjacent heat source.

For enclosure planning, the provisional 12 V variant is rated 1500 W output at 89% typical efficiency; **1500×(1/0.89−1) ≈185 W** of calculated PSU loss at that point. This is not a measured heat load or a claim that the enclosure can reject it. The 24 V variant has different efficiency/output data; revise the thermal evaluation when the electrical choice and workload are known.

Preserve the designated **FG protective-earth connection**. Neither metal adapter contact nor chemical conversion coating proves an earth bond. Final wiring, guards and strain relief need qualified electrical integration; actual lugs/cables set bend and tool-clearance envelopes. Disconnect and secure against reconnection before mechanical installation or removal. Preserve the PSU cover and original internal hardware.

Evidence and source limitations are recorded in [meanwell_requirements.md](references/research/meanwell_requirements.md). Exact machine-readable quantities, prices and provenance are in [catalog_bom.json](references/research/catalog_bom.json).
