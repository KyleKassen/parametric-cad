# Mean Well NSP-1600 side-tab mount — N2 BOM

**Preliminary fit prototype; no purchase or production release.** This independent side-mounted design uses two manufacturer-designated side M4 points. Confirm the actual rear thread before installation: the supplied STEP shows an opening there without a modeled thread, nut or insert. The 12 V model is provisional and side-orientation allowable output remains unresolved.

| Item | Qty | Complete specification / product | Initial purchase | Observed USD |
|---|---:|---|---|---:|
| M01 — adapter | 1 | CNC 6061-T6/T651, certified minimum yield 240 MPa; 6.00±0.05 mm finished thickness, 45 mm spine, 72 mm maximum width at two 44 mm tab stations, 316.8 mm overall length; R4 contour and 0.4 mm external edge breaks per drawing. Clear MIL-DTL-5541 Type II Class 3 conversion after machining. | 1 finished part | Quote |
| P01 — main panel | 1 | 92×340×6 mm interface reference with factory-installed studs. Final panel material, support and complete layout require confirmation. | Final panel | Quote |
| H01 — case screws | 2 | [McMaster 91294A190](https://www.mcmaster.com/91294A190/): M4×0.7×10 mm **overall** length, fully threaded 6g; DIN 7991, 90° flat head, Ø8×2.3 mm catalog head, 2.5 mm hex; black-oxide alloy steel, catalog Class 10.9 /120,000 psi tensile | 100 screws | $6.38 |
| H02 — stud washers | 4 | [McMaster 98688A142](https://www.mcmaster.com/98688A142/): M3 zinc-plated hardened steel, ISO 7089; ID 3.2×OD 7×0.5–0.6 mm, Rockwell C30 | 100 washers | $9.38 |
| H03 — stud nuts | 4 | [McMaster 90576A102](https://www.mcmaster.com/90576A102/): M3×0.5 zinc-plated steel nylon-insert locknut, Class 8; DIN 985 /ISO 10511, 6H; 5.5 mm AF×4 mm overall height | 100 nuts | $4.88 |
| F01 — panel studs | 4 | [FPE WGU30 load stud](https://docs.frontpanelexpress.com/elements/studs_standoffs.html), **M3, 12 mm geometric length, reverse side, zero depth offset**, factory installed. WGU30 is an FPD catalog identifier, not a McMaster SKU. | 4 installed studs | Quote |

**Initial McMaster packs total $20.64; allocated installed hardware $0.6980.** Remaining pieces are inventory. Prices were observed **2026-09-08**. The M4×10 exact product page was read live during N2 and displayed next-day delivery. Washer/nut data and prices were verified earlier the same day and reused read-only from the completed prior evidence. Tax, shipping, machining/finish, FPE panel/studs, PSU, wiring/guards/strain relief, fixtures and validation are excluded. Complete installed cost is unavailable. See [catalog_bom.json](references/research/catalog_bom.json) for quantities and provenance; shorter screws retained there are unselected alternatives.

## Fit and installation limits

The selected side mounting points are X+2.3 mm at Y−5.8 and −257.8 mm in the N2 drawing frame. The [Mean Well specification](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf), page 6, permits **5.00 mm maximum penetration from the side chassis mounting face** and recommends **7–10 kgf·cm =0.6865–0.9807 N·m**. This guidance does not independently qualify the custom countersunk head/seat, finish, threadlocking treatment or actual case attachment strength. Do not use cover screws or add an insert to resolve the rear STEP discrepancy by default.

With a 6.00 mm plate and 0.05 mm nominal head recess, M4×10 gives **4.05 mm nominal projection**. The assumed dimensional stack is **3.75–4.35 mm**, leaving 0.65 mm below the manufacturer maximum at its assumed upper extreme. Actual received screw length and seat must be gauged; the assumed length tolerance is not a verified McMaster tolerance. Heads must fully seat flush to 0.10 mm below datum A. Confirm actual engagement and internal clearance at both threads. The ideal conical hardware proxy is not a complete 2.3 mm catalog head or a reduced-head capacity rating. No washer is used under either countersunk screw.

Four FPE axes at **X±28.5, Y−5.8/−257.8 mm** form a 57×252 mm rectangle. Nominal stud tail is **12−6−0.55−4=1.45 mm**. Require actual full nylon engagement and **at least 1.00 mm of complete thread beyond each nut**; received stud projection and hardware dimensions govern. Check a 5.5 mm AF socket with OD≤10 mm and internal depth≥10 mm, 60 mm axial approach and ≥20 mm removal lift. Factory base/cavity geometry is nominal; anchoring load, cure, torque and temperature limits and final panel support remain unqualified. Nut installation and prevailing torque must be compatible with the accepted anchor procedure.

The locknut limit is **85°C at the actual nut**, not system ambient. Use sufficient machining stock to finish the 6 mm plate, with certified temper/strength and drawing flatness. Preserve the side metal contact regions and local tab sections; no sheet-metal or printed substitute is released. Chemical conversion and metal contact do not replace FG protective earth.

## Cooling and service

**No TIM is selected.** Keep the factory terminal-end intake and opposite fan exhaust clear. The [Mean Well manual](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf) requires output-current derating for nonstandard orientation; no NSP-1600 side-specific factor was found. Do not transfer the horizontal full-load curve to N2. Actual side-mounted load, inlet temperature, input voltage and enclosure cooling require qualification. The 100 mm end corridors are layout reserves, while 100–150 mm separation from an adjacent heat source is manufacturer guidance.

Confirm real cable/lug/terminal-cover, FG, strain-relief and tool envelopes. Mechanical service is disconnected: remove four nuts/washers and lift the complete supply/adapter before accessing the underside case screws. See [ASSEMBLY.md](ASSEMBLY.md) and [PROTOTYPE_VALIDATION.md](PROTOTYPE_VALIDATION.md).
