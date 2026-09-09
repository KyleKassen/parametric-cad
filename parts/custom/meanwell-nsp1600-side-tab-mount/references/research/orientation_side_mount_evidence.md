# NSP-1600 narrow-side mounting — N2 evidence

Checked **2026-09-08**. This is a new side-mount concept; the completed N1 design remains unchanged. Exact source copies and their hashes are in [source_manifest.json](source_manifest.json). No supplier contact, order or physical test was performed.

## Manufacturer evidence relevant to the change

The [current NSP-1600 specification](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf), revision **2026-06-15**, Case296A, was reopened. Page 6 identifies **two M4 mounting holes per narrow side** (group 2), with **5.00 mm maximum penetration** and **7–10 kgf·cm recommended mounting torque**. Its drawing defines penetration inward from the chassis mounting face. Pitch, complete engagement and mounting capacity are not specified. Page 8 shows optional side brackets and M4×4 combination screws. These attachment features are distinct from cover/assembly fasteners. The drawing's general tolerance is ±0.5 mm.

Page 3's ambient curve is explicitly **HORIZONTAL**: 100% load through 50°C, 75% at 60°C, 50% at 70°C. The separate input table permits full rated output at 180–264 Vac; its points are 80% at 115 Vac, 70% at 100 Vac and 60% at 90 Vac. These were read from the plotted curve and table, not inferred from the −20…70°C operating-range statement. [Specification pages 3, 6 and 8](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf).

The [official enclosed-type installation manual](https://www.meanwell.com/Upload/PDF/Enclosed_Type_EN.pdf), dated **2025.12.17**, includes NSP. Item 3 states that nonstandard orientation can increase internal temperature and requires output-current derating. It supplies no NSP-1600 side-specific factor. Item 4 requires unobstructed fans/vents and 100–150 mm separation from an adjacent heat source. It also requires mounting-screw insulation clearance, disconnected maintenance and FG protective earth.

## Consequences for this design

**N2 side-orientation allowable output is unresolved.** The horizontal curve cannot be transferred to this arrangement. The final side, inlet temperature, input voltage, output load and duty require manufacturer guidance or a qualified temperature assessment of the actual enclosed assembly. No arbitrary 10%, 20% or other orientation derating is selected. Reaching the TEC enclosure air target does not establish acceptable PSU internal temperatures or heat-rejection capacity.

Calculated conversion of the published side mounting torque is **0.6865–0.9807 N·m**, using 0.0980665 N·m per kgf·cm. This is not proof of a custom countersunk head/seat, friction condition, threadlocking procedure or case-boss load capacity. Confirm received M4 pitch/threads, complete engagement, side seating contacts and internal clearance. The two points on one side do not independently establish resistance to every overturning axis: the plate/contact width and joint prying need explicit engineering review. The manufacturer's optional brackets establish the intended side attachment group, not approval of this custom on-edge arrangement at full output.

Local tabs reduce the amount of panel occupied but introduce bending and prying around their necks and holes. Their thickness, fillets, bearing regions and main-panel support must be sized from the new orientation. Do not inherit N1's plate factor, fan-relief layout or bottom M3 requirements. Keep the factory airflow path, wiring/tool access and protective-earth connection; no TIM or conductive-cooling function is assumed.

## Verified screw options and final preliminary selection

All three exact McMaster product detail pages were read live during N2 and displayed next-day delivery. Prices are observed USD pack prices, excluding tax/shipping; no purchase was made. The final 6.00 mm plate uses two M4×10 screws; the shorter options are retained as comparison evidence only.

| Exact candidate | Overall length | Catalog geometry/material | Pack |
|---|---:|---|---:|
| **Selected [91294A190](https://www.mcmaster.com/91294A190/)** | 10 mm | M4×0.7, fully threaded 6g; DIN7991; 90° head Ø8×2.3 mm; 2.5 mm hex; black-oxide alloy steel; Class10.9 /120000 psi tensile | 100/$6.38 |
| [91294A188](https://www.mcmaster.com/91294A188/) | 8 mm | M4×0.7, fully threaded 6g; DIN7991; 90° head Ø8×2.3 mm; 2.5 mm hex; black-oxide alloy steel; Class10.9 /120000 psi tensile | 100/$6.25 |
| [91294A186](https://www.mcmaster.com/91294A186/) | 6 mm | Same independently read dimensions, head form, thread fit and catalog material/class | 100/$6.12 |

Length includes the head. For a closed hard-contact joint, calculate projection **P=L+r−t**, where r is actual head recess and t is finished grip thickness. At r=0.05 mm, M4×8 through 4 mm gives 4.05 mm nominal projection; through 3 mm it gives 5.05 mm and already exceeds the 5 mm maximum. M4×6 through 3 mm gives 3.05 mm. These are examples, not final fits or complete engagement claims. Gauge actual screw length, head seat, plate thickness and internal clearance. The catalog 2.3 mm head height is not the full geometry of an ideal Ø8→Ø4 cone. No washer belongs under a countersunk head, and ordinary shank strength is not reduced-head loadability. Black oxide is appropriate only to the stated dry indoor environment.

The final selected 6.00±0.05 mm plate with M4×10 and 0.05 mm nominal head recess gives **4.05 mm nominal projection**. The assumed tolerance stack gives **3.75–4.35 mm**, to be physically gauged. Its screw-length tolerance is an assumption, not catalog data. The 5.00 mm manufacturer maximum remains the hard limit. The rear thread is not present in the supplied STEP and must be confirmed on the actual supply before fit release.

## FPE and procurement continuity

The [FPE stud help](https://docs.frontpanelexpress.com/elements/studs_standoffs.html) and retained official 6.5.1 catalog support WGU30 M3 load studs: nominal base Ø11.9×2.2 mm, cavity Ø12.1×2.3 mm, available geometric lengths 6/12/20 mm, minimum panel thickness 3 mm and minimum 0.5 mm cavity-to-edge/opposing material. Installed load, torque, cure and temperature capacity remain unverified. The M4 WGU40 label/thread-size inconsistency is unresolved. N2 selects four M3×12 nominal studs at X±28.5/Y−5.8 and −257.8 mm, conditional on final panel support and anchor qualification.

Same-day verified [98688A142 M3 washers](https://www.mcmaster.com/98688A142/) and [90576A102 M3 nylon locknuts](https://www.mcmaster.com/90576A102/) are selected, four each. Their original exact-page evidence was reused read-only from the completed SolidRun ZIP, not re-quoted. The locknut's 85°C limit applies at the actual nut; prevailing torque must suit the eventual FPE anchor procedure. Nominal tail is 1.45 mm; actual acceptance requires full nylon engagement and ≥1.00 mm complete thread beyond each nut. [catalog_bom.json](catalog_bom.json) records the selected preliminary quantities and excludes the shorter screw alternatives from its totals. It is not a production release or an order.
