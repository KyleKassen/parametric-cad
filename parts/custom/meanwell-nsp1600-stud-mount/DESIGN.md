# Mean Well NSP-1600 stud adapter — N1

Preliminary mechanical fit prototype. Separate sibling design; no changes to previous mounts.

## Function and concept

Attach the power supply to one metal adapter through its manufacturer-designated bottom mounting holes, with recessed countersunk heads. Place the adapter over four FPE factory load studs on the main metal panel and retain with washers/locknuts. The user provisionally selects NSP-1600-12; 24 V remains possible. This mount uses the common Case296A interface, not electrical-output hardware.

Compared concepts: the OEM side brackets use four side M4 joints but add brackets and fasteners around the unit. A bent tray similarly increases parts/forming and can obstruct service. The selected bottom adapter uses three designated M3 points, one custom part and four exposed stud ears, preserving the original top cover and side screws. It is a machined plate, not sheet metal and not a printed substitute. No thermal pad or grease is selected: the manufacturer's built-in fans and end vents remain the cooling path.

## Ground truth

User PDF revision2025-08-19, Case296A, specifies300×85×41 mm, general tolerance±0.5 mm,1.8 kg, three bottom M3 holes with4 mm maximum penetration and6–8 kgf·cm recommended mounting torque. Side M4 and small cover/assembly holes are separate features. Fresh official2026-06-15 spec agrees on the selected bottom interface; terminal details differ and require actual unit confirmation.

The provided component-library STEP and repo vendor copy match SHA256d421a1e7fb7a3b5fd2e12588484a2e970456301955c0a17f55be6d56324dd8a0. All19 valid source solids are retained. Normalize by translation(-66.7869113,-354.1518617,-1.4999997): X is width centered, Y0 is the terminal chassis plane, Z0 the bottom metal seating plane. Body/guard envelope extendsY-300.6..0; terminals toY+38; Z0..41. The guard-inclusive300.6 dimension differs from nominal300 and is recorded rather than replacing manufacturer dimensions.

The bottom M3 pattern is(-35,-16.1),(35,-16.1),(0,-280.8) mm. Source bottom minor cylinders only represent thin flanged bosses, not full thread helices or a2 mm engagement specification. At the front two axes the PCB is4.5 mm above the bottom; the manufacturer's4 mm maximum governs all three. Actual thread/seat and PCB clearance remain inspection items.

The fan bottoms include exposed plastic frames coplanar with the metal bottom. Two local0.50 mm reliefs prevent mounting pressure on those frames while preserving the metal central spineX±2.75 and outside metal strips. These are clearance pockets, not thermal-compound fields or a fan-flow rating.

## Datums and construction

Adapter125×300.6×5.00±0.05 mm, centeredY-150.3; R8 corners,0.4 mm external rim breaks. DatumA=lower panel seating planeZ0; B=leftX-62.5; C=fan endY-300.6. Power supply bottom atZ5.00. ThreeØ3.4 housing bores have underside90° seats,Ø6.1 REF; actual M3×8 heads must finish flush to0.10 mm belowA.

Fan reliefs: X[-40,-2.85] and[2.85,40],Y[-299.1,-269.5],R0.5,0.50±0.05 mm deep. Keep the5.7 mm center land and outer bracket lands intact; pocket-location control and actual minimum0.20 mm fan-frame gap are required. Thin pocket boundaries stay burr-free without applying the0.4 mm outside chamfer to them.

Four M3 FPEWGU30 load studs, nominal12 mm projection, atX±55,Y-16.1 and-280.8. The same verified M3 stud/washer/nut family as prior mounts avoids relying on an inconsistent M4 catalog entry. Stud anchorage capacity/torque/temperature remain unqualified. Reference panel145×340×6 mm, centeredY-150.3, is not the user's final FPE panel. No pad or stud standoff gap separates its seating surface from the adapter.

Machine certified6061-T6/T651 from nominal6 mm/1⁄4-inch stock, Sy≥240 MPa, supported two-sided setups. Clear conversion MIL-DTL-5541TypeIIClass3; dimensions after finish. No bends, inaccessible tools or decorative ribs.5 mm is selected after3.5/4.5 mm failed the conservative rear/front strip strength screen once fan reliefs and countersink deductions were included. The plate is structural; large cosmetic cutouts would weaken the load path.

## Loads, cooling and service

Working basis: stationary indoor, horizontal bottom-down mounting in the TEC-cooled enclosure. Manufacturer published derating curve is horizontal; other orientations need revised output derating and thermal validation. Screen gravity plus3g incidental handling,125 N device resultant,145 N package resultant,50 N cable force included, and an independent5 N·m couple from50 N at100 mm. The manufacturer1.8 kg supply mass plus a0.5073 kg uncut-plate upper bound and hardware are covered by a provisional2.4 kg package allowance. Local device-joint screens use240 N tension/100 N shear at each front point and160 N tension/150 N shear at the rear. Detailed calculations bound CG locations and do not turn OEM vibration data into a mount qualification.

Metal contact carries compression. Three M3 screws, plate and four stud joints provide positive restraint; no friction-only or connector support. Thread, sheet boss, screw-head, preload, FPE anchor and final panel capacities remain separate from the plate yield screen. Manufacturer torque6–8 kgf·cm converts to0.5884–0.7845 N·m, but received countersunk-head/finish/locking compatibility needs verification; no arbitrary torque or structural thread rating is inferred.

Reserve100 mm unobstructed intake/terminal and fan-exhaust corridors as a preliminary layout choice, not a published universal fan-clearance minimum. Manufacturer requires free vents and100–150 mm separation when an adjacent device is a heat source. Cables, lugs, terminal barriers, FG earth conductor, screwdriver access and bend radii must be verified with actual installed electrical hardware. Preserve factory covers; do not drill the supply or use the plate as the only protective-earth path.

The12 V model is1500 W output at125 A, not1500 W waste heat. At89% typical efficiency its nominal full-load loss is about185 W; actual input/load/ambient and TEC heat budget remain unknown. No heat rejection through the adapter is credited. Disconnect power and cables, remove four stud nuts/washers and lift at least20 mm. Three countersunk screws are accessible on the bench after lifting. Removal frequency is unspecified; prototype10 service cycles are proposed.

## Tolerance and release limits

Nominal M3×8 projection is8+0.05-5.00=3.05 mm; assumed length±0.20, plate±0.05 and recess0..0.10 give2.75..3.35 mm, below the4 mm maximum. Gauge every installed projection and ensure the received screw's complete threads traverse the actual flanged boss; do not inherit a fictitious2 mm female-engagement minimum from another unit.

The datasheet's general±0.5 mm cannot be guaranteed by three self-centering countersinks. Use the supplied1:1 fit template and measure the actual three-hole pattern before final drilling/countersinking. If needed revise the named coordinates and regenerate; do not force screws, enlarge finished cone seats or use slotted cones with unverified contact. Stud-hole clearance and positional allowances are checked separately.

Unresolved: actual voltage/load/ambient, production case variant and pattern, screw dimensions/head compatibility/locking procedure, fan relief fit, actual cable/lug access, FPE anchoring and final panel supports, TEC capacity and enclosure ventilation, thermal derating and application-specific vibration. No fabrication, purchase or physical test is implied.

## Completed digital review

The exported/reopened N1 plate passes the repository gate at **79.1/100, band B, role plate**. The original hard threshold70 and edge-break metric threshold60 are unchanged. All built-in floors pass: edge body term81.0≥10, sharp-edge score89.0≥25. Measured coverage100%, no probe errors. `config_delta` is+12.7 from the legitimate plate role (default enclosure66.4→plate79.1), with zero waiver contribution. This is an interface plate, not an enclosure body.

Unfixed aesthetic findings are the broad underside, the manufacturer-imposed three-hole family and four shallow pocket-edge runs. Flat seating, the existing OEM pattern and narrow metal contact lands control these features; decorative recesses, moved holes or0.4mm pocket-mouth breaks would harm fit/load paths. All exposed outer rims retain the consistent0.4mm break. The full report, floor/configuration record and rationale are in [quality/DESIGN_REVIEW.md](quality/DESIGN_REVIEW.md).

Nominal CAD verification passes81checks, including36valid separate components, source preservation, STEP scale/count, zero unintended adapter interference,0.50mm fan-frame gap,1.45mm front screw-tip/PCB gap, socket access and removal. Independent manufacturing verification passes48checks including DXF-operation reconstruction against the STEP. Plate-only analytical yield factor is3.04 minimum. These are digital and analytical results, not physical fit, joint-strength or thermal validation.
