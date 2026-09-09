# SolidRun Bedrock thermal stud adapter — T1 bill of materials

**Preliminary fit and thermal prototype.** Quantities below make one adapter installation with six housing screws and four panel studs. Prices were observed on 2026-09-08 in USD. Nothing was purchased.

| Item | Qty installed | Part / specification | Initial purchase | Observed price |
|---|---:|---|---|---:|
| M01 — custom adapter | 1 | 166×184×5.10 mm; machine from nominal 6.35 mm certified 6061-T651 stock; room-temperature yield ≥240 MPa by material certificate. See [DESIGN.md](DESIGN.md), [params.json](params.json) and manufacturing drawings. | 1 finished part; machining/finish quote required | Not quoted |
| P01 — supporting panel | 1 | 200×220×6 mm **reference interface coupon**. Final enclosure panel, supports, material and thermal connection remain to be specified. | Final panel quote required | Not quoted |
| H01 — housing screws | 6 | [McMaster 91294A188](https://www.mcmaster.com/91294A188/): M4×0.7×8 mm overall length, 90° flat head, DIN 7991, black-oxide alloy steel; catalog Class 10.9 / 120,000 psi tensile; Ø8×2.3 mm catalog head, 2.5 mm hex drive | 1 pack of 100 | $6.25 |
| H02 — stud washers | 4 | [McMaster 98688A142](https://www.mcmaster.com/98688A142/): M3 zinc-plated hardened steel, ISO 7089; ID 3.2×OD 7×0.5–0.6 mm | 1 pack of 100 | $9.38 |
| H03 — stud locknuts | 4 | [McMaster 90576A102](https://www.mcmaster.com/90576A102/): M3×0.5, zinc-plated steel, Class 8, nylon insert, DIN 985 / ISO 10511; 5.5 mm AF×4 mm overall height | 1 pack of 100 | $4.88 |
| F01 — factory-installed panel studs | 4 | [Front Panel Express stud process](https://docs.frontpanelexpress.com/elements/studs_standoffs.html): native FPD catalog **WGU30, M3 load stud, 12 mm, reverse side, zero depth offset**. Select in the FPE panel design; this is not a McMaster part. | 4 installed studs with panel; FPE quote required | Not quoted |
| T01 — thermal compound | As required at both interfaces | [McMaster 10405K83](https://www.mcmaster.com/10405K83/): Dow 340 noncuring heat-sink compound, 5 fl oz tube. One tube provides prototype and rework inventory; the complete tube is not an installed quantity. | 1 tube | $69.83 |

**Initial McMaster packs and tube: $90.34.** The six screws, four washers and four nuts consume $0.9454 of those fastener packs; the remaining pieces are inventory. The complete system cost is unknown because custom machining, finish and the FPE panel/studs are unquoted. Prices exclude tax, shipping, fixtures, tools, validation, the computer, cables and the thermoelectric cooling system.

## Fit and installation limits

The adapter's finished thickness is 5.10±0.05 mm. Use the specified clear chemical conversion finish, MIL-DTL-5541 Type II Class 3, through a qualified finisher; critical dimensions and gaps apply after finish. Do not assume this establishes an RF ground bond or remove the computer's finish by default.

The four provisional FPE stud coordinates are **X±76, Y±82 mm**, measured from the adapter center: a 152×164 mm pattern. The catalog's nominal 12 mm protrusion leaves 2.35 mm above a 5.10 mm adapter, 0.55 mm washer and 4.00 mm nut. Verify actual protrusion, complete nut engagement, socket clearance and seating. The catalog base/cavity geometry is a reference; stud anchorage, installation torque, temperature and load capacity remain unqualified for this assembly. Nut prevailing torque must not overload the FPE anchorage.

The nylon locknut's catalog temperature limit is **85°C at the nut**. It is not the system's ambient or operating-temperature rating. Measure the actual heated panel and nut temperatures; revise the hardware if this limit cannot be met.

M4×8 length includes the countersunk head. Nominal screw projection is **8.00+0.05−5.10 = 2.95 mm**. The proposed finished-assembly acceptance is **2.85–3.00 mm actual projection**, **at least 2.00 mm complete thread engagement** after entry and tip losses, and **at least 0.50 mm clearance to the verified full-diameter blind limit**. These are simultaneous project criteria, not SolidRun-approved thread limits. Gauge each actual screw/seat and all six device holes before installation. Never tighten a screw to find the blind end. The ideal conical CAD head does not reproduce the complete catalog 2.3 mm head profile. No head strength, female-thread capacity or tightening torque is inferred from the catalog strength class. No washer fits under these countersunk heads.

## Selected thermal interface

Dow 340 is a **thin nonstructural grease**, applied separately between Tile and adapter and between adapter and supporting panel. The adapter has 126×156 mm fields recessed **0.050±0.010 mm** on both faces; integral hard metal lands close the mechanical clamp paths. Actual assembled gaps must remain **below 0.10 mm**, with demonstrated coverage and safe closing force. Two **1 mm wide, 0.05 mm deep escape grooves per face**, at Y±20 mm, lead to the +X edge. They provide a proposed escape path for air and excess grease; physical filling still requires inspection.

Control the application quantity, protect screw bores/connectors from grease, and inspect and renew each exposed interface after removal. Neither grease nor gel provides structural retention, electrical isolation or an established ground bond. A nominal pocket depth does not prove real flatness, contact pressure, thermal resistance or system cooling capacity. If the device or panel cannot meet the gap limit, revise the interface using a qualified gap filler before assembly.

[Dow's official material guide](https://www.dow.com/documents/11/11-3930-01-silicones-from-dow-for-appliances.pdf?iframe=true) places 340 in its noncuring, below-100 µm bond-line category. The received product's current TDS/SDS must govern application. No pressure-conditioned datasheet result is assigned to this unqualified low-preload joint. The Laird Tgel 600 and McMaster thermal tape comparisons are **not procurement selections**; details and source limitations are in [hardware_tim_candidates.md](references/research/hardware_tim_candidates.md).

Machine-readable quantities, exact product URLs, prices and evidence status are in [catalog_bom.json](references/research/catalog_bom.json). Physical thread fit, grease coverage, allowable preload, thermal behavior and the actual TEC cooling boundary remain open validation items.
