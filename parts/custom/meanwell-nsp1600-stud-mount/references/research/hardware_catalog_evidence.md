# Selected hardware verification

Checked 2026-09-08. No order, cart addition or purchase was made.

## M3×8 housing screw

The exact [McMaster 91294A128](https://www.mcmaster.com/91294A128/) was found in the live M3×8 countersunk-screw search table, then its **Product Detail** page was opened and read. It was not selected by extrapolating part-number patterns.

| Property | Exact product-page value |
|---|---|
| Thread | M3×0.5, right hand, coarse, metric Class 6g |
| Length | 8 mm; measured from top of countersunk head |
| Head | Standard flat head, 90°, Ø6 mm, catalog height 1.7 mm |
| Drive | 2 mm hex |
| Threading / tip | Fully threaded / flat tip |
| Material | Black-oxide alloy steel |
| Listed strength / hardness | Class 10.9; 120,000 psi tensile; Rockwell C32 |
| Specification | DIN 7991 |
| Pack | 100 screws for $5.82; exact unit allocation $0.0582 |
| Availability display | Delivers tomorrow, observed today; future availability not guaranteed |

The catalog does not state a qualified countersunk-head axial capacity, tightening torque for this PSU joint, actual male-thread lead length or complete-head tolerance envelope. Retain actual hardware gauging and conditional joint checks. The [Mean Well product drawing](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-spec.pdf) gives 6–8 kgf·cm for its bottom M3 mounting features; it does not explicitly address DIN 7991 heads or this custom adapter seat. Do not increase that recommendation or infer head/joint capacity from the catalog class.

## Other selected hardware

[98688A142 M3 washers](https://www.mcmaster.com/98688A142/), [90576A102 M3 nylon locknuts](https://www.mcmaster.com/90576A102/) and the official FPE WGU30 M3×12 nominal catalog geometry were independently verified earlier on the same date in this workspace session. The retained [B210 catalog snapshot](B210_catalog_source_snapshot.json) preserves the source record; [catalog_bom.json](catalog_bom.json) contains the current Mean Well quantities and revised fit notes. No new live availability claim is made for the carried washer/nut records.

M4 WGU40 remains unselected because the readable official catalog names M4 but assigns ThreadSize=3000. The selected WGU30 M3 record is internally consistent; its installed anchorage still has no verified load, torque or temperature rating.
