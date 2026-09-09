# Mean Well NSP-1600 stud adapter — engineering note

This is a preliminary machined adapter for horizontal, stationary indoor mounting on a rigid metal panel inside the proposed cooled enclosure. The selected **5 mm plate passes the stated analytical plate yield screens**, with a minimum calculated factor of 3.04 against certified material yield. This is not an assembled-system safety factor. The countersunk screw heads, PSU mounting bosses, FPE stud attachment, preload, complete supporting panel and powered enclosure still require the qualifications below. No FEA, fabrication, physical load test or thermal test was performed.

## Evidence, concept and geometry

The user-supplied Mean Well specification dated 2025-08-19 gives a 1.8 kg supply, nominal body 300×85×41 mm and three authorized bottom M3 mounting holes. Its page 6 limits external bottom-screw penetration to 4 mm and recommends 6–8 kgf·cm for those mounting screws. The separately specified side M4 holes and terminal screws have different limits. Current manufacturer documents inspected by the research agent retain the bottom mounting instructions.

The supplied STEP was freshly audited. Its normalized bottom interface is Z=0, terminal end Y=0, body approximately Y=−300.6 to 0 and X±42.5 mm. Bottom axes are X±35/Y−16.1 and X0/Y−280.8 mm. Small differences between source-coordinate measurements and these normalized drawing values are recorded by the geometry audit. The source includes fan-frame geometry reaching the nominal bottom plane. The adapter must therefore avoid loading the plastic frames. The apparent thread-bearing regions are short (about 1.38 mm near the terminals and 1.22 mm at the fan end); this is geometric evidence, not a full-thread or strength specification. No 2 mm engagement requirement from earlier unrelated designs is imposed.

The chosen route is one machined 6061-T6/T651 plate, 125×300.6×5.00±0.05 mm, R8 corners and consistent 0.4 mm outer edge breaks. Four verified-type FPE WGU30 M3 studs lie at X±55/Y−16.1 and −280.8 mm. Two 0.50±0.05 mm top reliefs span X−40..−2.85 and +2.85..+40, Y−299.1..−269.5, with R0.5 corners. These retain a full-height central metal contact strip and outer metal contacts. Preserve the shallow pocket edges and central land dimensions; remove burrs without a large pocket-mouth chamfer. Require at least 0.2 mm actual gap to both plastic fan frames after tightening and under normal service.

A folded tray or side-ear bracket could use the published side M4 holes, but adds parts/bends and occupies lateral service space. A bottom plate uses the three manufacturer-authorized attachment points, keeps the unit removable, and places the fastener heads flush underneath for the panel interface. A 3.5 mm plate was rejected because its narrow rear strip fails the selected factor-3 handling screen. The 5 mm plate gives useful margin without ribs beneath the seating face. The uncut plate mass upper bound is 0.5073 kg. The exported plate volume gives 0.5021 kg at the same assumed stock density; the actual supply mass is taken from its manufacturer, not from CAD density. A 2.4 kg package allowance covers the 1.8 kg supply, this plate and nominal hardware, subject to weighing the built package.

## Load path and load cases

Normal horizontal gravity passes from the metal chassis contacts into the adapter and the supporting panel. Reverse handling and overturning pass through the three M3 screws and their conical plate seats, across the local plate strips, through four M3 stud/nut joints and the FPE bonded/load-stud interfaces into the main panel. In-plane translation is restrained by screw/countersink and stud-hole bearing; no friction, fan-frame or incidental connector support is credited. Clearance at the studs permits small movement before bearing and must be acceptable to the cable installation. The three separated device points and four separated panel points restrain unintended rotation when their joints are intact.

Inputs are explicit preliminary assumptions: 3g incidental acceleration added to 1g gravity, 50 N cable force and a 100 mm cable lever. The cable couple is **5 N·m**, not 1 N·m. Device force is 1.8×4×9.81+50=120.632 N, rounded to a 125 N resultant. Package force is 2.4×4×9.81+50=144.176 N, rounded to 145 N. Each is a resultant with arbitrary direction, not simultaneous full loading on all three axes. The free couple has arbitrary direction; adding it independently to the force/height moment is conservative. Cable routing must prevent loads exceeding these assumptions. These cases do not qualify vehicle, airborne, seismic, outdoor or overhead service, or a shock/vibration spectrum.

The unknown force/CG position is allowed anywhere in the 85×300.6 mm body plan. The force height is conservatively bounded by 41 mm above the supply interface and 46 mm above the panel interface. This is a bounding envelope, not a measured center of gravity. A rigid elastic group is solved with B rows [1,x,y] and N=B(BᵀB)⁻¹[Fz,−My,Mx]. The script takes the exact individual tension maximum over the rectangular application-point box and force/couple balls. Shear is bounded by F/n+(C+F·r_application)r_i/Σr². Preload, joint separation and local prying are outside this model.

Maximum front M3 demand is 232.28 N tension and 99.79 N shear; rear M3 demand is 154.63 N tension and 149.72 N shear. Local screens round these to 240/100 N at the front and 160/150 N at the rear. The maximum FPE rigid-group demand is 135.52 N tension/84.93 N shear. A proposed qualification demand of 250 N tension/150 N shear per stud is carried into the plate-hole screen; it is neither an FPE allowable nor proof that prying is bounded by that value.

## Plate checks and thickness selection

Use certified unwelded 6061-T6/T651 stock with minimum yield 240 MPa. E=70 GPa is an approximate supplier guidance value for deflection calculations, not a guaranteed minimum. The screening target is 3 against metal yield because loads, effective strip widths and contact distribution are uncertain. A separately chosen 1.5 bending stress allowance addresses local geometry approximately; it is not a validated notch factor. There is no polymer structural credit.

The rear screw loads a transverse strip between the 110 mm stud spacing. A 35 mm gross strip fits inside the 19.8 mm rear end margin; deduct 7 mm for the hole/seat to use only 28 mm net width. Conservatively reduce this entire net strip to the minimum 4.40 mm pocket-floor thickness even though the central bridge and portions outside the relief retain 4.95 mm. Span is increased to 110.3 mm for location/clearance. Use I=bt³/12, Z=bt²/6, M=PL/4 and δ=PL³/(48EI). This is an effective-strip idealization requiring physical correlation, not an exact two-dimensional plate/contact solution.

The front holes are 20 mm inward from their respective studs. The 16.1 mm front edge distance allows a symmetric 30 mm gross strip; deduct 7 mm for a 23 mm net strip. Use the minimum unrelieved 4.95 mm thickness, a 20.3 mm arm, and the conservative equal pair of 240 N loads. M=P·a. The maximum free beam deflection is P·a(3L²−4a²)/(24EI). Normal stress combines 1.5M/Z with V/(bt), and shear is conservatively 1.5(P+V)/(bt); σ_VM=√(σ²+3τ²). Peak stresses are added despite not necessarily occurring together. These checks do not transfer device loads into an imaginary unsupported plate-center point: device forces enter at the three actual OEM holes near the stud rows. The remaining longitudinal plate carries its own inertia, screened as a uniformly loaded simply supported strip 100 mm wide across 265 mm using the minimum pocket-floor thickness. Its 4g deflection is 0.097 mm. A pinned-strip Euler stability sensitivity gives 6984 N, 48.2 times the 145 N package load; local sheet/contact imperfections still need inspection.

| Nominal plate mm | Front yield factor | Rear yield factor | Rear free deflection mm |
|---|---:|---:|---:|
| 3.5 | 1.48 | 1.41 | 1.123 |
| 4.5 | 2.46 | 2.53 | 0.462 |
| 5.0 | 3.04 | 3.21 | 0.321 |

| Check | Equivalent stress MPa | Yield factor |
|---|---:|---:|
| front strip | 79.07 | 3.04 |
| rear relief strip | 74.76 | 3.21 |
| longitudinal self load | 3.07 | 78.30 |
| countersink external punching | 12.15 | 19.75 |
| countersink external bearing factor3 | 45.29 | 5.30 |
| stud hole bearing factor2 | 25.25 | 9.50 |
| stud hole edge tearout | 5.80 | 41.40 |
| stud external plate punching | 7.53 | 31.89 |
| housing hole shear bearing factor2 | 28.41 | 8.45 |

Selected free bending predictions are 0.435 mm at the front and 0.321 mm at the rear. Full-panel compression support makes the normal seated case stiffer, but is not credited for reverse handling. At 1.5 times the local external loads, predicted free elastic deflections are 0.652/0.482 mm. These are analytical predictions. Do not infer screw preload, case deformation, actual frame gap or system stiffness from them.

## Countersinks, screw fit and unqualified joints

Select McMaster 91294A128, M3×0.5×8 DIN 7991 countersunk screws with nominal 90°/Ø6 head and 2 mm hex drive, through the 5 mm adapter. Gauge the manufactured seat with received screws: the head must fully seat without rocking and be flush to 0.10 mm recessed. Reference machining dimensions do not alone guarantee flushness. The seat screen uses mouth≤6.2 mm, throat≥3.3 mm, angle≥89°, an upper bore deburr≤0.10 mm, and an effective conical head-seat diameter≥5.7 mm. Maximum cone depth is 1.4755 mm. Minimum material above the cone is 3.4745 mm; after the upper deburr, the straight cylindrical ligament is 3.3745 mm. Require a measured minimum 3.30 mm straight ligament. External pull-through uses A=πd·3.30 and shear yield Sy/√3. Average conical-seat bearing uses projected annular area 15.896 mm² with a factor 3 on external average pressure. These are external-load plate screens, not a countersunk screw-head rating.

Nominal projection is 3.05 mm at 0.05 mm head recess. An explicitly assumed screw length tolerance ±0.20 mm, plate ±0.05 and head recess 0–0.10 gives 2.75–3.35 mm, leaving 0.65 mm below Mean Well's published 4.00 mm maximum. The screw-length tolerance is not a verified catalog tolerance. Measure all three installed projections; **4.00 mm is the hard maximum**, and confirm the received screw engages the actual short boss correctly and reaches clamp-up without internal obstruction. Do not use the approximate CAD thread region to invent a female alloy, a minimum complete engagement or pullout strength. Do not drill, retap or replace case features by default.

Mean Well's bottom-mount torque range converts to 0.5884–0.7845 N·m. It is published installation guidance, **not a tensile/pullout capacity or a tested rating for this specific DIN 7991 head, finish and aluminum seat**. Obtain confirmation that the selected head/seat and any locking treatment are suitable, or qualify a representative joint before production tightening. Do not invent a different torque or assume a threadlocker is neutral to friction.

For scale only, the uncalibrated relation T=KFd with d=3 mm gives:

| Assumed K | Illustrative clamp force N | Average projected cone pressure MPa |
|---|---:|---:|
| 0.1 | 1961–2615 | 123.4–164.5 |
| 0.2 | 981–1308 | 61.7–82.3 |
| 0.3 | 654–872 | 41.1–54.8 |

These wide ranges are sensitivity calculations, not preload predictions, torque settings or accepted loads. The clamp path closes locally from cone through the plate into the chassis contact/boss. Preload cannot simply be equated to the external free-strip load, yet local contact pressure, countersink wedging, chassis bearing and screw-head strength still require qualification. The short extruded/threaded boss, case material, head reduced loadability and mounting-joint strength remain unverified. No thread stripping factor is assigned. M3 tensile area 5.03 mm² gives nominal external shank stresses recorded in the JSON; those values do not certify the head or female thread.

FPE WGU30 M3 load studs use the known catalog geometry, but axial/shear, bond cure, temperature and torque capacities were not found. Their supplier qualification and the actual main-panel design are required. A 6 mm main-panel thickness is reference geometry only. The plate hole-bearing screen uses a conservative 2.4 mm screw-root bearing diameter and factor 2; edge tearout uses the reduced edge thickness after both outer breaks. Washers/nuts and full thread engagement must match the verified BOM, and enough stud tail must remain for the selected nut. Define locking and tightening from the qualified hardware/FPE process; no unsupported torque is assigned. A flat plate cannot compensate for a warped, contaminated or insufficiently stiff panel.

The additional stud plate-punching screen uses the 250 N external tensile demand around a 3.7 mm hole perimeter through the 4.95 mm minimum plate. It assumes the intact specified nut/washer physically bridges the hole; it does not assign a washer bending capacity or a stud-head/bond rating. Inspect received nut/washer dimensions, seating and permanent deformation in the joint qualification. Housing-hole in-plane bearing is additionally screened at 150 N, using the conservative 4.40 mm relief floor and 2.4 mm root-bearing diameter.

## Manufacturing, fit and electrical/service requirements

Machine from traceable 6061 stock, with both seating planes finished to the drawing. Use conventional face milling, drilling and 90° countersinking, then shallow relief milling. R0.5 pocket corners require a suitably small cutter or a shop-agreed larger radius that still clears the measured fan outline and preserves the contact spine; cutter access is open from the top. Protect the thin full-height central contact land during clamping and deburring. Finish dimensions are after any coating. Do not count paint, oxide or an anodized interface as a reliable protective-earth connection or as thermally helpful contact. Specify surface treatment/grounding with the enclosure design and retain the PSU's designated earth connection.

The specification's general ±0.5 mm tolerance is larger than fixed countersinks can absorb by self-centering. The 1:1 fit template and actual measurement of all three hole positions are therefore release requirements. Revise the named CAD coordinates to the received supply if necessary; do not force-fit screws or substitute elongated countersinks with line contact. Check the actual fan contour against the 0.1 mm nominal lateral pocket margins and confirm the full metal contact land remains. Pocket depth is chosen for ≥0.2 mm physical fan-frame clearance, not as a cooling improvement.

Mount the supply to its adapter before placing the adapter over the four panel studs. All three screw heads must remain below the adapter underside and must not hold the plate off the panel. Install the verified washers/nuts using the specified compact socket envelope and lock method. Remove the complete supply/adapter from the studs for service; the device screws become accessible once lifted. The panel stud pattern is parametric. Provide independent cable strain relief and verify actual lug, terminal-cover, bend, insulation and tool envelopes. Maintain the manufacturer's fan intake/exhaust and installation clearances. No mount surface may obstruct the airflow path, touch a fan or become an electrical shorting path.

## Enclosure heat budget

No TIM or conductive cooling function is specified for this supply. It has factory forced-air cooling; no panel cooling credit is used. The user is considering the 12 V variant, with 24 V also possible. At rated output, the published typical efficiencies imply the following conversion losses, using P_loss=P_out(1/η−1):

| Variant | Rated output W | Typical efficiency | Calculated typical supply loss W |
|---|---:|---:|---:|
| NSP-1600-12 | 1500 | 89.0% | 185.4 |
| NSP-1600-24 | 1608 | 91.0% | 159.0 |
| NSP-1600-36 | 1602 | 91.5% | 148.8 |
| NSP-1600-48 | 1608 | 92.5% | 130.4 |

These are not worst-case heat-loss specifications. Input voltage, load, setpoint, inlet temperature and fan behavior change loss and derating. Heat from loads located inside the same enclosure, wiring, other supplies and the TEC electrical input/hot side must be included separately. A TEC air-temperature target does not establish heat removal capacity. The 12 V case alone is approximately 185 W of supply conversion heat at rated output, before any other in-box losses. Confirm the actual variant and operating load, applicable derating and airflow, then size and test the complete enclosure. Do not block the fan path or claim a safe full-power temperature from this mount calculation.

## Prototype and release plan

1. Inspect the actual supply, model/variant, mounting pattern, fan outline, case contact regions and threads. Gauge every screw projection and seat. Confirm no internal interference and obtain head/seat/torque suitability for the manufacturer's short M3 mounting bosses. Weigh the package against the 2.4 kg allowance.
2. Inspect machined thicknesses, relief positions, straight countersink ligaments, finish, flatness and burrs. Assemble with received hardware, verify ≥0.2 mm fan-frame gap, no head proudness, full metal seating and no plastic contact. Check actual terminal covers, lugs, cable bend radii, compact socket access and removal path.
3. Use representative supported metal surrogates for initial plate/joint checks. Apply the 240/100 N front and 160/150 N rear local demands, with tension/shear combinations appropriate to the load path; correlate displacement to the strip assumptions. A separate 1.5× plate proof may use 360 N front/240 N rear with matched shear increments on surrogate attachments. Do not apply that proof to unqualified PSU bosses or FPE studs. Proposed acceptance: no fracture/loosening or permanent set above 0.10 mm; free-strip elastic movement below 0.70 mm at the 1.5× local proof, with fixture compliance removed. If longitudinal plate self-load is applied concurrently, use 0.85 mm combined elastic movement. These displacement criteria are separate from the actual ≥0.2 mm normal-service fan gap; check no fan-frame contact through the qualified handling cases as well.
4. Qualify the FPE bonded stud/panel interface at the specified temperature, cure and tightening conditions, including the 250 N tension/150 N shear proposed per-stud demand and any measured prying. Qualify the final case, screw and countersink joint at the approved mounting torque. Record witness marks, seating and post-cycle loosening; no capacity is assumed from appearance or the CAD.
5. Perform a complete assembly handling/strain-relief check using the stated force/couple envelope after joints are qualified. Verify repeated removal, reinstallation and witness-mark stability. Reassess if acceleration, cable forces, orientation or support changes.
6. Operate the actual 12/24 V configuration at intended input/output and worst expected enclosure ambient. Measure supply inlet/exhaust and enclosure temperatures, output load, electrical input and hot-side TEC conditions; verify manufacturer derating and no recirculation/blocked airflow. Include noncondensing humidity requirements and enclosure condensation behavior. Record results without equating fan noise or air setpoint with adequate cooling.

## Reproduction and sources

Run `python -B references/engineering/engineering_calculations.py --write` from this design folder. The script regenerates this note and `engineering_results.json`, checks its arithmetic/equilibrium and records source hashes. It is separate from CAD generation. Critical CAD parameters must match; changes to geometry, material, load basis or interfaces require rerunning and reviewing the calculations. All numerical records remain preliminary until correlated with the physical assembly.

- User-supplied manufacturer PDF: `datasheets/NSP-1600-spec_USER.pdf`, 2025-08-19, pp.2 and6. Current primary specification: [Mean Well NSP-1600 specification](https://www.meanwell.com/Upload/PDF/NSP-1600/NSP-1600-SPEC.PDF). The research archive records the inspected current revision and installation instructions.
- [thyssenkrupp 6061 material data](https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf): certified T6/T651 plate strength selection is 240 MPa; elastic modulus is approximate guidance. The research archive contains the working manufacturer-document URL if this legacy link moves.
- [Bossard metric tensile stress areas](https://www.bossard.com/global-en/-/media/bossard-group/website/documents/technical-resources/en/f-004-en.pdf): M3 area5.03 mm². [Bossard countersunk-head guidance](https://www.bossard.com/us-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-flat-countersunk-head-screws-fully-threaded/p/2103/) notes reduced head loadability; ordinary shank properties are not a head rating.
- Exact screw, washer, nut and FPE catalog evidence is retained by the procurement/research agent in this design's references. No alloy/strength or adhesive-capacity claim is inferred from their rendered geometry.
