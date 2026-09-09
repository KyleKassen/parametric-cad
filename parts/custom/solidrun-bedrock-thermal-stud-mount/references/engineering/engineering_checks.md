# Bedrock thermal stud mount T1 — engineering screen

This is a preliminary plate and thermal-interface design. The analytical screens meet the selected plate yield target, but **the assembled mounting and cooling system is not rated**. No device mass, mounting-thread capacity, FPE bond capacity, thermal contact resistance, airflow coefficient or TEC capacity was measured. No FEA or physical test was performed. The existing Bedrock mount notes supplied leads only; their depth, torque, mass, material and thermal claims were not adopted.

## Configuration and datums

The new geometry audit separates the superimposed Tile, 30 W and 60 W bodies in the supplied STEP. T1 represents a Tile body plus a derived single opposite fin bank. That CAD construction does not prove that the physical bank is interchangeable or that its internal thermal joint performs as modeled. The manufacturer/file's “60 W” name is not a rating of this derived configuration, and this calculation gives the fin bank no cooling credit.

The Tile mating face is Z=0, with the computer extending toward +Z. Six measured axes are (−60,−70), (60,−70), (0,−40), (0,30), (−50,70), (50,70) mm. Fresh face area is approximately 20,410.10 mm², bounded by X±64.486/Y±79.5 mm. The adapter is 166×184×5.10 mm, with four FPE stud axes X±76/Y±82 mm. The 200×220×6 mm panel is a reference interface, not a confirmed complete enclosure or heat sink.

Both adapter faces have 126×156 mm, R5 TIM fields recessed 0.05±0.01 mm. Six nominal Ø8 upper islands bear on the Tile near its mounting holes. Six Ø10 lower lands retain the countersink seats and provide hard contact against the panel. The surrounding metal rim also seats. Two 1 mm escape grooves on each face, at the same depth and Y±20, run toward +X outside the field. They avoid a sealed grease cavity and give air/excess material an escape path. No thermal area outside the Tile footprint, including those grooves, is credited.

## Construction and TIM selection

The selected construction is a machined 6061 plate with **metal stops defining the grip and a thin, nonstructural grease film**. This keeps the screw clamp path out of a compressible pad. It does not eliminate the need to qualify bolt preload, actual contact and surface flatness. No structural retention or sustained clamp-force credit is assigned to the grease.

The selected TIM is Dow 340, available as McMaster 10405K83. Dow classifies it as a noncuring, thin-bond-line TIM for gaps below 100 µm. Its English manufacturer TDS gives typical k=0.67 W/(m·K); the McMaster listing gives 0.68. The model uses 0.67. An older regional Dow document gives a lower value equivalent to approximately 0.42, so that value is retained as a sensitivity. These are typical inputs, not lot-certified minimum properties. Confirm the current data sheet for the received product.

A full 130×160 mm pad at only 10 psi would require approximately 1434 N total compression; 40 psi would require 5736 N. Therefore the published grease impedance at 40 psi is **not** used as this assembly's thermal resistance, and neither Shore hardness nor a catalog low-pressure statement defines the needed preload. A thick full-face pad was rejected because its force/deflection and long-term compression would load unverified shallow threads. A fixed-gap gel such as Laird Tgel 600 is an alternative if the surfaces cannot meet the Dow 340 thin-gap requirement, but it requires a deliberate TIM/drawing revision and new thermal qualification.

Machine both faces in balanced setups from suitable stock, control free-state flatness, deburr, clean and inspect unclamped. The 0.4 mm edge break belongs only on exposed outer rim edges. Keep the 0.05 mm TIM steps and island perimeters burr-free while preserving their depth and minimum land diameter; a generic 0.4 mm chamfer there would destroy the functional feature. Mask the active TIM fields and hard seating lands from added thick coatings; do not remove the computer's original finish by default. Existing device/panel finishes add unknown contact resistance. The nominal 0.05 mm relief is not proof of a 0.05 mm bond line: with a 0.06 mm maximum cut, less than 0.04 mm remains for combined mating-face departure before the 0.10 mm limit is exceeded. All intended stops must seat without rocking or forcing a bowed part flat through the device screws. Separate drawing flatness/parallelism limits do not by themselves guarantee the assembled gap against an unmeasured Tile or panel.

The calculated cavity estimate is about 0.96 mL per interface, approximately 2.01 g using the English TDS density. This is a geometric estimate, **not a prescribed dispense dose**. Establish the dose and pattern on a representative witness assembly, close slowly, allow air/excess to escape and check continuous transfer without persistent dry patches. Do not use bolt torque to force out an excessive charge. Verify actual gaps below 0.10 mm on both interfaces in the installed orientation, under normal cable/gravity load and after warm operation. Renew the grease after separation and inspect for migration or bleed during cycling.

## Mechanical loads and load path

Device mass allowance is 1.5 kg and complete package allowance is 2.1 kg, both unverified. The uncut plate alone is at most 0.4206 kg at 2,700 kg/m³. Weigh the actual configuration; do not derive device mass by assigning aluminum density to the imported assembly.

With g=9.81 m/s², 3g incidental inertia plus 1g gravity and 20 N cable force:

- Device force: 1.5×4×9.81+20=78.86 N, rounded to **80 N resultant**.
- Package force: 2.1×4×9.81+20=102.40 N, rounded to **110 N resultant**.
- Add an independent **1 N·m free couple**, motivated by 20 N at a 50 mm lever.
- Bound the device load height by 51 mm, package height by 60 mm, and the plan position anywhere inside X±65/Y±80 mm. This is deliberately more conservative than assuming a centered CG.

Each force and couple can act in any direction within its resultant bound; these are not per-axis simultaneous amplitudes. The intended application is stationary indoor equipment in a TEC-cooled enclosure. No vehicle, airborne, overhead, vibration or shock-spectrum suitability is claimed.

The compression path is Tile→upper metal islands/rim→adapter→lower metal lands/rim→main panel. Uplift and in-plane loads pass through the six M4 screw joints, plate and four retained FPE stud/nut joints. Friction is not credited for retention. Hole geometry provides positive shear restraint after clearance is taken up. The separated fastener groups restrain all translations and rotations when correctly seated. Neither connectors nor fins are clamped.

## Bolt-group calculation and unrated joints

For the arbitrary six-point pattern, each row of B is [1,x,y]. The elastic normal-force vector is N=B(BᵀB)⁻¹[Fz,−My,Mx]ᵀ. This preserves force and both moment equilibria and accounts for the group's Y-centroid at −1.6667 mm. The source calculates the exact normal extrema over the independent force/couple balls and the stated load-position rectangle. In-plane demand uses direct F/n plus a conservative torsion term (C+F r_CG) r_i/J about the group centroid.

- Maximum M4 elastic demand: **68.74 N tension / 38.13 N shear**. Use a local **75 N tension and 75 N shear** plate/fastener screen.
- Maximum FPE elastic demand: **87.77 N tension / 55.09 N shear**. Request supplier or representative-joint qualification for **200 N tension with 100 N shear per stud**. These values are demands, not FPE allowable loads.
- A 2 N·m cable-couple sensitivity raises M4 tension to 74.56 N, still within the 75 N local screen. Confirm actual plug/cable levers.

These are external-load calculations. Preload, prying, unequal seating, panel flexibility, bond creep and temperature cycling are not resolved by the rigid group. In particular, main-panel contact outside a stud can increase stud tension. No FPE adhesive, stud, nut/washer, device female-thread or enclosure-wall capacity is assigned. Supplier approval or a representative qualified joint test remains necessary. Obtain an installation/locking method consistent with those joint limits; no torque value is invented here.

## Plate screens

Use certified, unwelded 6061-T6/T651 stock matching the supplier's >3–6 mm thickness range, with minimum yield 240 MPa. E=70 GPa is approximate room-temperature guidance. The target is factor 3 against plate yield for the stated service screen. This does not cover unknown joints, thermal stress or elevated-temperature strength reduction.

The minimum hard-land thickness is 5.05 mm; deducting both maximum recesses leaves a minimum core of 4.93 mm. Two beam idealizations are used to avoid crediting a perfectly supported or rigid plate:

1. A deliberately narrow 28 mm net strip spans the diagonal support distance L=223.907 mm and carries the local 75 N force at midspan. I=bt³/12=279.587 mm⁴; M=PL/4. Apply a selected 1.5 bending factor, add P/(bt) axial stress, and add two 1.5V/A shear screens before the von Mises combination.
2. A 100 mm net strip screens whole-plate loading and simultaneous moment transfer. M_bound=F L/4+C+F sqrt(rx²+ry²+h²)=14678.5 Nmm, with the same selected bending factor. This deliberately adds overlapping force/moment bounds; it is an engineering screen, not a solved 2-D plate/contact stress distribution.

The chosen effective strip widths and stress factors require prototype correlation. They are not empirical notch factors or proof of exact load sharing. Local bearing/tear-out screens use maximum holes, minimum thickness and adverse edge-position allowance; no washer load-spreading benefit is needed for those average-stress screens.

| Plate screen | Yield factor |
|---|---:|
| local plate strip | 4.28 |
| whole plate strip | 4.41 |
| countersink punching | 76.61 |
| countersink average bearing factor3 | 30.66 |
| plate stud bearing factor2 | 14.54 |
| plate stud tearout | 68.58 |

Minimum screened plate factor is **4.28**; target 3 is met within these mechanical assumptions. This is **not an assembly safety factor**. The narrow unsupported strip predicts 0.896 mm displacement at 75 N and 1.344 mm at a 1.5× local proof load. Those loose free-bending estimates omit the seated main panel and the rigid computer. They do not establish the operating thermal gap. Strength acceptance and hot, loaded thermal-contact acceptance are separate checks; loss of contact requires a stiffer/support-revised design or qualified preload, not an optimistic thermal resistance assumption.

## Countersink and shallow blind threads

Selected candidate screws are McMaster 91294A188, M4×0.7×8 DIN 7991, nominal Ø8 head and 90° cone. The source cone envelope uses mouth≤8.2 mm, throat≥4.4 mm and angle≥89°. Maximum depth is (D−d)/(2 tan[α/2])=1.9335 mm. After a 0.10 mm upper deburr, the minimum calculated straight throat is 3.0165 mm. Require **at least 3.00 mm actual straight throat** after all machining; the punching screen uses that acceptance minimum. The nominal straight cylinder is 5.10−1.80−0.10=3.20 mm. Use the received screw as a gauge to hold its underside head flush to 0.10 mm recessed, never proud.

The bearing calculation requires actual effective cone-seat diameter≥7.6 mm and throat≤4.6 mm. A minimum Ø7.9 hard island around the maximum top-deburr opening has 30.921 mm² net contact area, or 3.234 MPa average bearing per 100 N total screw force. The surrounding Tile material/finish capacity remains unknown. Local preload must be assessed in addition to the external loads; the grease cannot carry or preserve it.

Fresh STEP evidence at every Tile hole shows the entry cone from Z=0 to 0.584 mm; the modeled helical region extends to 3.500 mm, followed by a drill cone to 4.501034 mm and a thin blind end wall. The hole is **blind**, not a clear passage through the complete Tile. None of these model coordinates is a manufacturer screw-penetration allowance. The user's approximately 4 mm depth is useful context, not a precision stop gauge.

Projection of an overall-length countersunk screw is L−plate grip+head recess. With assumed length 8.0±0.2 mm, plate 5.10±0.05 and recess 0–0.10, the unscreened range is **2.65–3.25 mm**, nominal **2.95 mm**. The narrower **measured receiving window 2.85–3.00 mm** requires selection/gauging and may reject ordinary stock screws.

At that receiving window, subtracting the 0.584 mm geometric entry leaves only 2.266–2.416 mm before additional female-entry phase and screw-tip incomplete threads. To retain the proposed **≥2.00 mm complete engagement**, their combined additional loss must be no more than **0.266–0.416 mm**. That compatibility has not been verified for the stock DIN screw; a modeled helical start is not a gauge of full female-thread engagement. Do not count lead/chamfer as full engagement, relax the criterion to make the arithmetic fit, or adopt a deeper screw without measured bore/tip-envelope clearance and SolidRun approval. The provisional screen maintains ≥0.50 mm to the modeled full-diameter limit, whereas the axial drill-tip difference is 1.501 mm; these are different quantities.

For context only, a reduced thread-shear surrogate A_s=0.25π×3.3×2.0=5.184 mm² would require female yield≥75.2 MPa at factor 3 under 75 N and zero preload; every additional 100 N preload adds 100.2 MPa to that demand. This does not establish actual thread strength. No Tile alloy or allowable mounting-face temperature was found in inspected manufacturer documentation. M4 nominal tensile area 8.78 mm² gives 17.08 MPa shank equivalent stress for 75 N tension+75 N shear, but the catalog class/tensile listing does not prove the reduced flat-head capacity.

## Thermal calculations: separate the conduction path from heat rejection

Analyze **10, 30 and 60 W through the entire Tile→TIM→adapter→TIM→main-panel path** as independent numerical cases. These are not measured computer heat loads or approved CPU TDPs. The remaining fin bank receives no credit, and no fraction of heat flow is assumed from its name or partial CAD contact.

For each layer, R=t/(k A), with t in metres and A in m². Use 19,000 mm² effective area in the broad-area case, below the two unvented CAD fields; no area outside the Tile is counted. The simple stack includes two grease layers, the full 5.10 mm adapter and the 6 mm reference panel. Aluminum k=150 W/(m·K) is a selected conservative typical screening value, not a certified bound or an assumption that the unknown panel is necessarily 6061. Revise it for the actual panel material.

The following values are **bulk-only, idealized estimates**. They exclude both real contact interfaces of each grease joint, voids, coatings, spreading and panel-to-air resistance. Reduced-area rows model localized heat flow and do **not** authorize poor grease coverage.

| Effective area mm² | Gap each mm | TIM k W/(m·K) | Bulk R K/W | ΔT at 10 W, K | ΔT at 30 W, K | ΔT at 60 W, K |
|---:|---:|---:|---:|---:|---:|---:|
| 19000 | 0.05 | 0.67 | 0.0118 | 0.12 | 0.35 | 0.71 |
| 19000 | 0.10 | 0.67 | 0.0196 | 0.20 | 0.59 | 1.18 |
| 4750 | 0.10 | 0.67 | 0.0784 | 0.78 | 2.35 | 4.71 |
| 950 | 0.10 | 0.67 | 0.3921 | 3.92 | 11.76 | 23.53 |
| 19000 | 0.10 | 0.42 | 0.0290 | 0.29 | 0.87 | 1.74 |

The unknown additions are material: R_total=R_TIM1_bulk+R_contacts1+R_adapter+R_spreading+R_TIM2_bulk+R_contacts2+R_panel+R_panel_to_air. The English TDS's 0.16°C·cm²/W at 40 psi is not substituted for these contacts. At the specified 0.05 mm grease gap, t/k alone is approximately 0.746°C·cm²/W per joint; this already exceeds that high-pressure test result, showing why its bond line/pressure cannot be carried over.

As a spreading sensitivity, an equivalent circular thin plate carrying all heat radially from 5% to 100% of the area gives R_radial=ln(r₂/r₁)/(2πkt)≈0.322 K/W, or approximately 19.3 K at 60 W. This intentionally simplified alternative path is not an exact rectangular spreading solution and must not be added as a verified system resistance. It demonstrates that a nearly isothermal full face is not assured by high bulk conductivity alone. Actual internal Tile heat-flux distribution is unknown.

## TEC-cooled air remains the unknown boundary

The user confirms TEC enclosure cooling, but no direct mechanical/thermal connection to a TEC cold face is modeled. The panel therefore transfers heat to cooled air with unknown coefficient h and unknown operating air temperature. For one fully exposed reference-panel face A=0.044 m², R_air=1/(hA). The following h values are **assumed sensitivity inputs**, not measurements or a claim about the enclosure fan:

| Assumed h W/(m²·K) | R_air K/W | ΔT panel−air at 10 W, K | at 30 W, K | at 60 W, K |
|---:|---:|---:|---:|---:|
| 5 | 4.545 | 45.5 | 136.4 | 272.7 |
| 10 | 2.273 | 22.7 | 68.2 | 136.4 |
| 25 | 0.909 | 9.1 | 27.3 | 54.5 |
| 50 | 0.455 | 4.5 | 13.6 | 27.3 |

Large tabulated rises are linear-model warnings of insufficient assumed air-side conductance, not predictions that the real computer will reach those temperatures; radiation, convection and power limiting change with temperature. Additional faces or conduction to the enclosure may help but are not credited without a known geometry/path. For an illustrative 20 K panel-to-air budget, 10/30/60 W would require h≈11.36/34.09/68.18 W/(m²·K) over that one face. The 20 K budget is a design comparison, **not a SolidRun temperature limit**.

Consequently a low calculated TIM/plate resistance does not establish 60 W rejection to the cooled air. Measure airflow/thermal performance in the actual box. The TEC setpoint alone is not the panel temperature, and TEC capacity must cover all enclosure loads at actual hot-side conditions. Its hot side rejects the pumped heat plus electrical input. No TEC cooling capacity, airflow or total enclosure heat load has been provided here.

## Creep, expansion and electrical/finish considerations

Metal stops prevent pad compression/creep from defining the mechanical grip. Grease can still migrate, bleed or redistribute and lose thermal coverage; closed pockets, excessive charge and forced assembly must be avoided. Repeat thermal and removal-cycle checks. A hypothetical CTE mismatch of 10 µm/(m·K), 50 K temperature change and 160 mm span gives 0.08 mm free differential movement. The actual Tile alloy and temperature field are unknown, so similar expansion cannot be claimed. Fully restraining that mismatch would create additional thermal stress not included in the room-temperature plate factors.

The metal stops make this an electrically conductive mechanical interface; neither thin grease nor ordinary anodized contact is a qualified electrical-isolation barrier or protective grounding bond. Confirm the intended grounding scheme separately. Preserve the device finish, control added coatings on the adapter, and inspect exposed contact lands for corrosion consistent with indoor service. Record humidity and minimum surface temperatures in the TEC enclosure to identify condensation during its actual operating cycle.

## Prototype validation and acceptance gates

1. **Fit and receiving:** inspect the original unit, thread identity, actual blind-hole/entry profile and every received screw. Confirm 2.85–3.00 mm projection, ≥2.00 mm complete engagement and the physical no-bottoming clearance. If stock tips cannot satisfy both, hold installation and resolve the joint with SolidRun. Check head flushness/recess, ≥3.00 mm straight countersink throat, metal-stop seating, panel stud flushness, FPE nut/tool engagement and connector/cable clearance. Do not force mismatched six-hole patterns or bowed faces into place.
2. **Mechanical qualification:** weigh the exact computer/configuration and package. Obtain approved joint preload/locking and device/FPE limits. Use a rigid representative six-point surrogate for plate/panel proof work, rather than proof-loading unverified device threads. Apply the 80 N device/110 N package wrenches and 1 N·m couple in adverse orientations; check slip, lift, loosening and local damage. A separate surrogate local proof may apply 112.5 N at each housing point in turn. Proposed screening acceptance: no cracks/loosening, no more than 1.5 mm elastic displacement in that deliberately severe local proof, and ≤0.10 mm residual. Any actual service gap requirement is stricter than this general structural criterion.
3. **Gap and coverage:** qualify dispensing on representative surfaces. Require all intended hard stops to seat, actual TIM gaps <0.10 mm on both faces, continuous transfer with no persistent dry patches and no protruding screws or trapped debris. Repeat under normal gravity/cable force in the installed orientation and warm steady operation. Changes in hot gap, rocking or loss of contact require redesign/rework, not credit from the bulk-only table.
4. **Thermal path test:** first use an instrumented, insulated heater surrogate to impose known 10/30/60 W through the mount path. Insulate/measure parasitic losses and record temperatures near both interfaces, adapter, panel and local cooled air after a defined steady-state criterion. This avoids mistaking the real fin bank's parallel cooling for heat carried by the plate. Demonstrate the allocated temperature rise and gap stability using the actual panel/TEC airflow. Then test the real computer at its expected workload, ambient, enclosure heat load and orientations; compare component temperatures, throttling and operation with an appropriate baseline and obtain the manufacturer's limits. Electrical input power alone does not measure heat through the adapter.
5. **Durability/service:** cycle between actual operating temperatures, inspect grease transfer/migration, preload/locking, screw threads and FPE attachment, and repeat the thermal test after removal/reassembly. Reapply TIM after separation. Application-specific vibration or environmental qualification requires additional requirements; none has occurred.

## Evidence and regeneration

- [Fresh geometry audit](../geometry/solidrun_geometry_audit.json): source coordinates, blind entry and drill geometry; no material/allowable depth inferred.
- [thyssenkrupp 6061 data](https://ucpcdn.thyssenkrupp.com/_legacy/UCPthyssenkruppBAMXUK/assets.files/material-data-sheets/aluminium/aluminium-6061.pdf): certified-stock yield screening and typical stiffness/thermal context.
- [Dow appliance guide, p29](https://www.dow.com/documents/11/11-3930-01-silicones-from-dow-for-appliances.pdf?iframe=true): Dow 340 classified for thin bond lines below 100 µm.
- [Dow-authored English 340 TDS, distributor-hosted](https://www.ulbrich-group.com/chemical-technical-products/TDS_DOWSIL_340_eng.pdf): typical k=0.67, density and the separately identified 40 psi test. [Older regional Dow TDS](https://www.dow.com/documents/01/01-1641-11-dowsil-340-heat-sink-compound.pdf?iframe=true): lower conductivity sensitivity; confirm the received product's current data.
- [Laird Tgel 600](https://www.laird.com/sites/default/files/2025-11/THR-DS-Tgel%20600%20Data%20Sheet.pdf): documented fixed-gap alternative, not the selected T1 material.
- [Bossard fastener material reference](https://www.bossard.com/global-en/-/media/bossard-group/website/documents/technical-resources/en/f-004-en.pdf): M4 tensile area. [Countersunk-head limitation](https://www.bossard.com/us-en/eshop/screws-and-bolts-with-internal-drive/hex-socket-flat-countersunk-head-screws-fully-threaded/p/2103/): reduced head loadability can apply.
- Project procurement evidence identifies McMaster 10405K83, 91294A188 and the selected FPE WGU30 interface. These product identities do not establish a completed-joint allowable.

Run `python references/engineering/engineering_calculations.py --write` from the project directory. The adjacent JSON records named inputs, individual group reactions, all result tables, arithmetic checks and the audited CAD parameter hash. A changed critical dimension causes the parameter audit to fail rather than silently retain an obsolete calculation. No unresolved acceptance item is waived by a passing script.
