# AM59 sealed mast-head enclosure, V2

Status: preliminary engineering design basis. The V2 CAD defines packaging,
interfaces, service access, and performance envelopes. It does **not** define
released heat-exchanger, pump, radiator, fan, RF-feedthrough, electrical-
connector, gasket, or mast-interface part numbers. The complete assembly is
an IP66/IP67 design target, not an IP or NEMA-certified product, until a
representative production assembly passes the qualification plan in this
document.

## Executive decision

The AM59 amplifier has no documented ingress-protection rating in the
model-specific data supplied for this project. The entire amplifier, including
its factory fans, heatsink, SMA input, N output, sample ports, and 7W2
power/control connector, shall therefore remain inside one sealed, dry
chamber.

The selected architecture is:

```text
horn / rotator
upper structural plate
four-post load-bypass frame
  white ventilated solar shield
  continuously welded 5052 dry chamber
    AM59 on removable cartridge
    sealed dry-air recirculation duct
    qualified air-to-liquid heat exchanger
    dry-side circulation fans and sensors
    OEM connectors and internal pigtails
  gasketed side service lid
  welded coolant-tube penetrations
  sealed RF, power, and control bulkheads
  IP68/IP69K-rated pressure-equalization vent
  externally floodable and freely drainable wet bay
    redundant coolant pumps
    air-to-liquid radiator
    redundant IP68 fans
    expansion volume, fill/service points, and sensors
lower structural plate
existing mounting plate / castle-cut pipe
BlueSky mast
```

No ambient air enters the dry chamber. The AM59 factory fans and supplemental
dry-side fans circulate the same clean air through the amplifier and the
air-to-liquid coil. Coolant passes through continuously welded tube
penetrations to the external wet bay. External fans reject heat from the
radiator. The wet bay is intentionally not a sealed enclosure: its components
are individually wet-rated, and its geometry must flood and drain without
trapping water.

This is a different enclosure philosophy from the V1 rain shroud. V1 remains
a fair-weather, ambient-air concept. V2 is the baseline for driving rain,
dust, washdown, and temporary immersion.

## Environmental claim boundary

The qualification targets are the relevant tests of IEC 60529:

- IP6X: dust-tight;
- IPX6: resistance to powerful water jets; and
- IPX7: temporary immersion, with the project requirement fixed at 1 m for
  30 minutes.

IPX6 and IPX7 are separate tests. Passing one does not imply passing the
other. The final designation may be written `IP66/IP67` only after both have
been passed on the complete production-equivalent assembly.

The operating modes are deliberately narrower than the survival envelope:

| Exposure | Permitted state |
|---|---|
| Dust, wind-driven rain, normal outdoor splash | Normal RF operation, subject to thermal and wind limits |
| Washdown | RF disabled; +50 V amplifier supply isolated; external wet-bay circuits operated only if their released parts and connectors permit it |
| Temporary immersion, 1 m / 30 min | Entire mast-head assembly unpowered; survival only |
| Submerged operation | Prohibited |
| Pressure/steam cleaning or hot chemical washdown | Prohibited unless a separate IPX9/IP69K and chemical-compatibility requirement is defined and qualified |

The hydrophobic vent, connector caps, cable assemblies, bulkhead seals,
service-lid gasket, welded joints, and every accessory are part of the tested
enclosure. A high-rated empty box does not confer that rating on a modified
assembly. The lowest-rated installed item or interface governs.

NEMA enclosure types are not interchangeable with IEC IP codes. NEMA Type 4X
addresses hose water and corrosion resistance, Type 6 addresses occasional
submersion, and Type 6P adds prolonged submersion and corrosion provisions.
The construction objective is Type 6P-like where compatible with the mast
mass budget, but this project shall not claim a NEMA type without the
applicable evaluation. IEC and NEMA compliance statements remain separate.

Authoritative standards references:

- [IEC 60529 publication page](https://webstore.iec.ch/en/publication/2447)
- [ANSI/IEC 60529 scope and contents](https://www.nema.org/docs/default-source/about-us-document-library/ansi-iec_60529-2020-contents-and-scopef0908377-f8db-4395-8aaa-97331d276fef.pdf)
- [NEMA enclosure-type definitions](https://www.nema.org/docs/default-source/products-document-library/nema-enclosure-types.pdf)
- [NEMA enclosure FAQ](https://www.nema.org/docs/default-source/standards-document-library/faq-enclosures.pdf)
- [NEMA bulletin on enclosure-system ratings](https://www.nema.org/docs/default-source/technical-document-library/eng-buletin-no.-123-nema-and-ip-ratings-liquidtight-flexible-metal-conduit_final.pdf)

A controlled copy of the applicable standard, not this summary, shall govern
the released test procedure.

## Governing equipment data

The user-supplied
[AM59-005D model-specific data](../../vendor/microwave-amps/datasheets/AM59-005D.pdf)
and vendor STEP are the governing amplifier sources.

| Item | Design input |
|---|---:|
| Nominal amplifier body | 320 x 180 x 102 mm, excluding mounting flange |
| STEP packaging envelope | approximately 364.12 x 200 x 102 mm, including fans, flange, and connectors |
| Amplifier mass | 2.5 kg |
| Frequency | 2998 MHz +/-20 MHz |
| Typical peak output | +64 dBm, approximately 2.51 kW |
| Maximum duty | 3% |
| Nominal pulse condition | 30 us at 1000 Hz |
| Positive input | +48 to +50 V, 4 A average at nominal pulse operation |
| Negative input | -8 V, 80 mA average |
| Permitted operating case temperature | -10 to +70 C |
| OEM overtemperature behavior | off at 75 C, reset at 55 C |
| Factory connectors | SMA input, N output, 7W2 power/control |
| Factory cooling | three ebm-papst 612 NGLE fans |

The standard 612 NGLE fan shall not be assumed ingress-rated. The
manufacturer's data lists moisture-protected variants as options rather than
attributes of every fan. Keeping all three fans in the dry chamber avoids
depending on an undocumented fan variant.

The amplifier's published electrical input is about 200.6 W average at the
nominal pulse condition. The average RF output at +64 dBm and 3% duty is
about 75.4 W, giving a first-order matched-load heat estimate near 125 W.
The internal circulator/termination may convert reflected power to additional
internal heat. Until Microwave Amps supplies a bounded worst-case thermal
profile, the enclosure shall be designed and tested at **300 W total internal
heat at 45 C ambient**. This 300 W basis includes amplifier uncertainty,
dry-side fan/control dissipation, manufacturing tolerance, fouling, and
residual solar leakage; it is not a statement that the AM59 continuously
dissipates 300 W.

Mast inputs remain preliminary:

- [BlueSky BSM2-M-M202-AL2-000 product page](https://blueskymast.com/product/bsm2-m-m202-al2-000/)
- [BlueSky 2 m AL2 datasheet](https://blueskymast.com/wp-content/uploads/2014/07/BSM2-M-M202-AL2-000.pdf)
- [BlueSky Standard Series manual](https://blueskymast.com/wp-content/uploads/2014/04/User-Manual-AL2-Standard-200-Series.pdf)

The published 45.4 kg deployable-load and 70 mph mast values are not approval
of this payload. Pod mass, horn and rotator mass, center of gravity, projected
area, cable loads, gust response, guying, foundation/soil, and deployment
height must be assessed as one system.

## Mechanical architecture

### Structural load path

The antenna and rotator load path is independent of the environmental
enclosure:

1. The user's existing castle-cut pipe and mounting plate attach to a blank,
   surveyed lower interface plate.
2. Four structural posts connect the lower plate to the upper rotator plate.
3. Local cross-members support the enclosure cradle without interrupting the
   primary post-to-plate load path.
4. The AM59 cartridge, dry chamber, solar shield, radiator, and wet bay carry
   no horn or rotator load.

The lower and upper plates remain blank in preliminary CAD because controlled
drawings for the actual `BSM2-P-M201-AL2-00P` pipe/plate and rotator were not
provided. Hole patterns, pilots, dowels, edge distances, joint preload, and
fastener grades shall be added only from surveyed or manufacturer-controlled
interfaces. The proprietary BlueSky castle geometry shall not be copied or
re-created.

The pod should be centered about the mast axis to minimize eccentric gravity
and wind moment. Its cradle shall include:

- positive fore/aft and lateral location;
- preloaded primary retention;
- captive service hardware;
- a rated secondary retention lanyard;
- hard stops that remain effective after elastomer aging, if isolators are
  used; and
- accessible inspection and torque-witness features.

The enclosure walls and service lid are not structural frame members. No
rotator load may cross the gasket joint.

The complete assembly requires static, fastener, weld, fatigue, modal, and
wind analysis. A proof load of the released assembly does not replace those
analyses. Welding of any 6061-T6 structural member must account for reduced
heat-affected-zone strength; a bolted and doweled structure may be preferable
where repeatable alignment and field replacement are important.

The V2 packaging coordinates are fixed in `params.json` as the current design
baseline:

- upper and lower interfaces: 250 x 250 x 8 mm central blank plates with
  connected 50 x 50 mm post landing pads;
- four 30 x 30 x 3 mm load-bypass posts;
- upper-plate top: Z = 340 mm;
- welded dry chamber: 600 x 270 x 260 mm, spanning
  X = -380 to +220 mm, Y = -135 to +135 mm, and Z = 20 to 280 mm;
- external wet cooling bay: X = +220 to +345 mm;
- solar shield: 620 x 300 mm with its lower surface at Z = 300 mm; and
- exact AM59 STEP envelope in the installed pose:
  X = -345.4 to +18.72 mm, Y = -100 to +100 mm, and Z = 52 to 154 mm.

The 605 mm asymmetric longitudinal cradle rails make the structural-frame
envelope longer than the mast-interface plates and extend beneath the wet
cooling bay so its weight is not cantilevered from the pressure wall.
Including the service lid and external wet bay, the preliminary pod spans
approximately 735 mm along X. The open plate geometry reduces mast-head mass
while retaining an unresolved 250 x 250 mm blank interface region for the
existing plate and rotator. These dimensions are packaging decisions, not a
structural release.

### Preliminary mass and wind sanity check

The current CAD material volumes, evaluated at 2700 kg/m3 for aluminum, give:

| Modeled item | Preliminary mass |
|---|---:|
| Structural bridge and extended cradle rails | 5.69 kg |
| Welded dry pressure body | 6.27 kg |
| Stiffened service lid | 1.20 kg |
| AM59 cartridge | 0.30 kg |
| Solar shield | 0.75 kg |
| AM59 vendor unit | 2.50 kg |
| Subtotal before cooling hardware, harnesses, fasteners, and coolant | 16.71 kg |

The coil, radiator, redundant pumps and fans, coolant, accumulator, plumbing,
feedthroughs, controls, harnesses, fasteners, isolation hardware, and
retention are provisionally another 8-11 kg. The resulting planning estimate
is therefore **25-28 kg for the amplifier pod**, before rotator, horn, moving
RF jumper, and their mounting hardware. Reference-envelope solid volumes are
not used as component masses.

The broadside pressure-body/wet-bay outline is approximately
0.735 x 0.260 m, or 0.191 m2 before adding detailed brackets. At 70 mph
(31.3 m/s), sea-level dynamic pressure is about 600 Pa. Using a preliminary
bluff-body drag coefficient of 1.2 gives roughly 140 N (31 lbf) broadside
wind force on the pod alone. This is only a sizing warning: gust factor,
shield gaps, frame members, cable loads, horn area, aerodynamic interaction,
deployment altitude, mast dynamics, guying, and soil/foundation behavior are
not included.

The BlueSky system's published 45.4 kg deployable-load value would leave only
about 17-20 kg for the rotator, horn, cables, and hardware at the planning
mass. Weight compliance alone would still not establish acceptable bending
moment or wind stability. A combined mass/CG/projected-area load case is a
mandatory release gate; if it fails, the correct fallback is a smaller
OEM-qualified cold-wall amplifier or a sealed mid-mast/ground installation,
not a weaker enclosure.

### Dry chamber

The chamber is a continuously welded 5052-H32 aluminum weldment. Preliminary
wall, roof, and floor thicknesses in CAD are packaging values and shall be
confirmed by plate-deflection, weld-distortion, handling, vibration, and
hydrostatic-load analyses. There are no open drains, louvers, fan apertures,
or weep holes in the dry volume.

The chamber must withstand approximately 9.8 kPa differential pressure at
1 m water depth. This creates a distributed load of almost 1 kN on each
0.1 m2 of exposed panel area. Large flat panels require beads, cross-breaks,
ribs, or bonded/welded hat sections so that deflection cannot unload the
gasket, contact internal equipment, or permanently distort a flange.

The enclosure is mounted with its service lid vertical or near vertical,
never as an upward-facing tray. External features shed water downward.
Horizontal ledges receive a drainage slope. The roof has a separate solar
shield and does not rely on the gasket seam as a drip edge.

### Service lid and face seal

The chamber has one removable side/end service lid. All other dry-boundary
joints are continuously welded or use qualified bulkhead components. The lid
uses:

- a machined-after-welding, continuous flat flange;
- one continuous, replaceable O-ring in a captured gland;
- a gasket material chosen from the actual water, detergent, fuel, oil, UV,
  ozone, and temperature exposure;
- captive stainless fasteners outside the seal line;
- close fastener spacing established by flange-deflection analysis;
- positive metal compression stops;
- locating dowels that do not penetrate the dry boundary;
- a captive safety lanyard; and
- a documented tightening sequence and torque.

For water and mild-detergent exposure, peroxide-cured EPDM is the preliminary
seal-material candidate. It is not released until the cleaning chemicals and
all incidental fluids are known. Fluorosilicone or another compound may be
needed for fuel/oil exposure, but substitution requires a new compression,
temperature, and immersion review.

Gland dimensions shall be calculated from the selected O-ring supplier's
design handbook, including squeeze, stretch, fill, tolerance stack, thermal
expansion, compression set, surface finish, and corner radius. The CAD gasket
is only a swept volume. Room-temperature fit is not evidence of sealing.
Neither RTV nor a liquid gasket is an acceptable primary field-service seal.

Lid fasteners shall not pass through to the dry volume. Blind holes in the
external flange or welded external studs are preferred. Compression remains
adequate with one adjacent fastener at its minimum preload. Repeated lid
cycling is part of qualification.

### Removable amplifier cartridge

The AM59 mounts to a removable metal cartridge using all twelve factory
M4 locations, subject to OEM confirmation of screw standard, engagement,
torque, and permitted mounting orientation. The cartridge:

- supports both mounting-flange rails continuously or at validated hard
  points;
- uses flush fasteners where required for extraction;
- includes keyed locating features and captive primary retention;
- provides a separate secondary retention feature;
- cannot be inserted in the wrong orientation;
- removes through the service opening without disturbing the structural
  bridge; and
- leaves adequate hand/tool access for every dry-side connector.

The heatsink body is not clamped, drilled, sealed through a wall, or used as a
mounting datum. The entire factory assembly stays dry and serviceable.

### Solar shield

A white or very light gray, UV-stable outer shield covers the roof and
sun-facing sides. It is spaced from the pressure boundary by non-absorptive
standoffs, is open at its lower edges, and supports natural ventilation of
the gap. Its fasteners attach to external bosses and do not penetrate the dry
volume. The shield must tolerate wind suction and must not obstruct lid
removal, wet-bay drainage, pressure venting, radiator airflow, or inspection.

Solar qualification uses the released color, coating, shield spacing, wind
condition, and orientation. A generic ambient-temperature chamber test does
not include solar loading unless equivalent absorbed power is applied.

## Thermal-management system

### Governing performance requirement

At 300 W internal dissipation and 45 C ambient:

- the AM59 case shall remain at or below 65 C in steady normal operation;
- no local component shall exceed its manufacturer rating;
- the system shall maintain at least 5 C margin below the AM59's documented
  70 C operating-case limit; and
- control shall remove RF before the OEM 75 C trip point is approached.

The resulting maximum allowed case-to-ambient thermal resistance is:

`(65 - 45) C / 300 W = 0.0667 K/W`

The design target is no more than **0.050 K/W installed case-to-ambient
resistance** from representative AM59 case measurement points to ambient,
equivalent to at least 20 W/K. Within that budget, the dry-air-to-ambient
thermal train targets no more than **0.033 K/W**, or at least 30 W/K. This
allows about 10 C dry-air rise at 300 W and reserves the remaining
case-to-air margin for the amplifier, sensor tolerance, fouling, flow
variation, manufacturing variation, and short transients. It is a
full-system test requirement, not a value that can be satisfied by quoting a
radiator catalog rating in isolation.

The modeled coil, radiator, pumps, and fans are rectangular or cylindrical
**performance envelopes only**. They are not approved parts and shall not
appear on a released procurement BOM until measured curves demonstrate the
required conductance, airflow, coolant flow, pressure margin, electrical
rating, environmental rating, and life.

A commercial closed-loop air-to-air enclosure heat exchanger provides a
useful size/weight sanity check, not a selectable component: the
[Rittal SK 3126.100](https://www.rittal.com/us-en_US/products/PG20231215KLI101/PG20231215KLI102/PG20240718KLI002/PRO0282?variantId=3126100)
is rated 17.5 W/K and weighs 8.9 kg. Its published external IP rating is
insufficient for this project. The reference shows that a genuinely
qualified 20 W/K passive heat-transfer path is not a token sheet-metal fin.

### Closed dry-air loop

The dry loop is:

```text
coil outlet / cool plenum
  -> AM59 fan inlet
  -> AM59 heatsink channels
  -> sealed hot plenum
  -> low-loss air-to-liquid coil
  -> coil outlet / cool plenum
```

Every return path is gasketed or sealed so hot discharge cannot bypass the
coil and recirculate directly to the amplifier inlet. Internal duct panels
are removable without disturbing the enclosure pressure boundary.

The three AM59 fans provide only about 63 m3/h total nominal free-air flow,
and their approximately 20 Pa pressure capability leaves little margin for a
coil and duct. Supplemental dry-side circulation fans are therefore required
unless a full-scale system test proves the OEM fans sufficient.

Preliminary dry-loop requirements are:

- at least 120 m3/h measured airflow through the amplifier and coil at the
  released system resistance and worst density;
- no more than 8 C dry-air temperature rise through the 300 W heat source at
  the actual qualified flow;
- a coil and duct pressure drop compatible with both OEM and supplemental fan
  curves;
- no reverse flow through an idle fan;
- tachometer or equivalent proof of circulation; and
- access for cleaning without exposing the amplifier to wet-side debris.

The 120 m3/h value is a starting performance requirement, not a fan part
number. Flow, pressure, acoustics, bearing life, vibration, and interaction
with the factory fans must be measured. Microwave Amps must confirm that the
proposed recirculation temperature, backpressure, fan interaction, and
mounting orientation are acceptable.

Dry-side air is initially clean and dry. Assembly shall occur in a controlled
environment, with a dry-air or nitrogen purge if required. A replaceable
desiccant cartridge may manage residual moisture during storage, but it is not
the primary barrier and may not obstruct circulation. Internal relative
humidity and dew-point margin are monitored.

### Air-to-liquid coil and dry-boundary penetrations

The dry-side coil shall be a fully brazed or welded, pressure-rated assembly.
No hose barb, threaded fitting, compression fitting, quick disconnect, or
serviceable coolant joint is permitted inside the dry chamber. The supply and
return tubes continue through welded sleeves or are themselves continuously
welded into qualified bulkhead bosses. All detachable fluid joints are on the
wet side of the pressure boundary and are positioned over a free drain path.

The coil and penetrations require:

- material compatibility with the coolant, radiator, pump, and tubing;
- proof and leak test above maximum pump shutoff pressure, thermal expansion
  pressure, and service-fill pressure with an engineering safety margin;
- braze/weld process qualification and traceability;
- no trapped crevice that can retain wash chemicals;
- strain relief so pump vibration and hose loads do not reach wall welds;
- allowance for differential thermal expansion;
- a dry-side drip tray that cannot conceal leakage; and
- a liquid sensor below the coil and both penetrations.

Coolant shall never be treated as electrically harmless. Even initially
deionized fluid becomes conductive in service. A detected internal leak
causes immediate RF disable and source isolation.

### Coolant circuit

At 300 W, limiting coolant temperature rise to 3 C requires approximately:

`300 W / (3.7 kJ/kg-K x 3 K) = 0.027 kg/s`, or roughly `1.6 L/min`

The preliminary minimum measured flow is 2.0 L/min at worst viscosity and the
released circuit pressure drop. Each of two pumps shall be capable of the
minimum flow by itself at that head. Check valves or a validated hydraulic
arrangement prevent an operating pump from back-driving the failed branch.

The circuit includes:

- two individually fused, speed/tach monitored pumps;
- a full-flow radiator sized from measured heat-rejection curves;
- supply and return temperature sensors;
- an independent flow switch or flow meter;
- an expansion accumulator sized for the complete fluid-volume and
  temperature range;
- a pressure relief provision routed safely into the wet bay;
- a pressure sensor;
- a low-point drain and high-point fill/bleed arrangement;
- a serviceable particulate screen only if pump/radiator requirements demand
  one; and
- keyed, lockable service caps with secondary seals.

The coolant mixture and freeze point shall be selected from the actual minimum
storage and operating temperatures. A corrosion-inhibited propylene-glycol/
water mixture is a preliminary candidate. The final selection must be
approved for the pump, radiator, coil, seals, tubing, reservoir/accumulator,
and every wetted metal. Do not combine copper/brass and aluminum wetted
components without a documented galvanic/coolant-life strategy. Coolant
replacement interval, concentration check, contamination limit, and disposal
procedure are maintenance requirements.

A single pump failure results in RF shutdown in the baseline logic; the
remaining pump provides controlled cooldown. Continued reduced-power operation
on one pump may be enabled only after fault testing proves adequate flow and
thermal margin. Redundancy is not permission to ignore a fault.

### External wet bay

The wet bay is physically below or beside the dry enclosure and is open at
its lowest surfaces. It has:

- multiple drainage paths that remain effective in every deployed
  orientation;
- no upward-facing cup, closed-cell pocket, or capillary crevice;
- finger/debris guards that preserve calculated free area;
- separated radiator intake and exhaust paths;
- sufficient stand-off to prevent hot-air recirculation;
- accessible pumps, radiator, sensors, and connectors;
- protected hoses with abrasion and bend-radius control; and
- a geometry that can be rinsed, inspected, and dried after immersion.

Pumps, fan motors, wet-side connectors, splices, and sensors must each carry a
documented immersion rating for their installed configuration. Potting alone
is not accepted without process controls and environmental qualification.

Two 120 mm wet-side fans provide airflow through the radiator. An
[ebm-papst AxiForce 120 family](https://www.ebmpapst.com/content/dam/ebm-papst/loc/americas/us/local-literature/Experience%20the%20future%20of%20fan%20technology%20with%20AxiForce.pdf)
member is an illustrative starting family: published variants operate from
36-60 V, approach 345 m3/h free-air flow, and offer tach/PWM and optional
IP68 protection. No generic family member is released; the exact moisture-
protected suffix and its immersion test evidence are mandatory. Selection
must use the radiator system curve, operating point, salt/chemical exposure,
connector sealing, acoustic/vibration limits, altitude, life, and derating.
Free-air flow cannot be used as installed radiator flow.

Loss of one external fan causes RF shutdown in the baseline logic while the
surviving fan and pumps complete cooldown. Any later allowance for degraded
operation requires a tested heat-load limit. Fans do not operate submerged.

### Pressure equalization

The dry chamber uses a replaceable, screw-in hydrophobic and oleophobic
pressure-equalization vent rated for IP68 immersion and IP69K wash exposure
in its selected installation. The vent reduces cyclic pressure loads from
temperature, altitude, solar heating, and weather while blocking bulk liquid
and particulates.

Applicable manufacturer guidance:

- [GORE screw-in protective vents](https://www.gore.com/products/screw-protective-vents-outdoor-electronics-enclosures)
- [GORE protective-vent FAQ](https://www.gore.com/resources/faq-gore-protective-vents)

The released vent must be sized from enclosure free volume, maximum thermal
ramp, altitude transport, allowable differential pressure, and membrane
contamination. It mounts on a sheltered vertical or downward-facing surface,
away from radiator exhaust and direct jet impingement. Its mounting boss,
O-ring, torque, wall finish, and replacement interval are part of the
qualified design. The vent is not a drain. Its behavior when wetted or
temporarily submerged must be included in pressure and recovery tests.

## Electrical, control, and fault protection

### Power architecture

The +48 to +50 V amplifier supply is switched and protected at the source.
Loss of communications, controller watchdog, interlock power, or any critical
sensor drives the RF-enable line to the safe state and opens the source
contactor. The AM59's internal overtemperature protection remains active but
is the last layer, not normal regulation.

The source and harness must be checked for:

- average and pulse current;
- transient voltage drop and cable inductance;
- connector contact derating at maximum ambient;
- short-circuit energy and selective protection;
- creepage/clearance under condensation and contamination;
- protective bonding; and
- safe discharge after isolation.

No local capacitor bank, precharge circuit, or change to the OEM power wiring
is permitted without Microwave Amps approval.

Wet-bay pumps and fans use an independently fused low-voltage feed so they can
complete cooldown after RF and +50 V are removed. An upstream master isolation
device removes all mast-head power for washdown, service, or flood threat.

### Instrumentation

Minimum monitored points are:

- AM59 case temperature at an OEM-approved location;
- amplifier inlet and outlet dry-air temperature;
- coil air inlet and outlet temperature;
- coolant supply and return temperature;
- coolant flow and pressure;
- both pump tach/speed or independent current/rotation evidence;
- every dry-side and wet-side fan tach;
- wet-bay ambient temperature;
- dry-chamber relative humidity and dew point;
- dry-chamber liquid leak sensor;
- service-lid closed/interlock state;
- controller supply and watchdog; and
- AM59 overtemperature and reflected-power/fault outputs available from the
  OEM interface.

Temperature sensors used for protection require calibration, error budgets,
plausibility checks, open/short detection, and an independent hardware
shutdown path where a single software fault could otherwise exceed a safe
temperature.

### Preliminary interlock behavior

Exact thresholds shall be finalized from thermal qualification. The initial
safe-state logic is:

| Condition | Required response |
|---|---|
| AM59 case reaches 60 C | Warning and telemetry alarm |
| Case reaches 63 C or thermal rise exceeds validated model | Inhibit new RF pulses / controlled RF shutdown |
| Case reaches 65 C | Immediate RF disable and source isolation |
| Case cools below 55 C after ordinary thermal trip | Manual or supervised reset only |
| Dry-side liquid detected | Immediate RF disable, isolate amplifier supply, keep safe cooldown only if electrically permissible, require inspection |
| Coolant flow below qualified minimum | Immediate RF disable; run redundant pump/fans for cooldown |
| One pump or radiator fan fails | RF disable in baseline configuration; maintain cooldown with remaining devices |
| Both pumps fail or coolant pressure is unsafe | RF and wet-bay power isolation as dictated by the hazard analysis |
| Dry-air circulation fan fault | RF disable |
| Relative humidity/dew-point margin approaches condensation | Warning, then RF inhibit before condensation is credible |
| Lid open or lid interlock invalid | RF and amplifier supply inhibited |
| Controller watchdog, sensor plausibility, or communications fault | Fail-safe RF disable |
| Rising-water/immersion condition | Source isolation of all mast-head circuits |

The OEM trip at 75 C must never be the first intended response. Reset after a
leak, immersion, overpressure, or repeated unexplained thermal event requires
physical inspection; automatic restart is prohibited.

## Connector and cable boundary

All factory AM59 connectors remain inside the dry chamber. Short internal
pigtails terminate at purpose-selected enclosure bulkheads. Internal cables
are supported independently so no external cable load reaches the OEM
connectors.

### RF output

At +64 dBm the output path carries approximately 2.51 kW peak. In a 50 ohm
matched system this corresponds to about 354 V RMS and 501 V peak before
allowance for mismatch. A high VSWR can produce substantially higher local
voltage and current.

The output bulkhead/feedthrough and moving jumper therefore require:

- operation at 2998 MHz +/-20 MHz;
- documented peak-pulse and average-power capability at the maximum allowed
  duty and worst permitted VSWR;
- an environmental seal rated in both mated and capped states;
- a hermetic or otherwise independently qualified dry-boundary construction;
- low measured insertion loss and VSWR;
- temperature rise and arc testing at maximum conditions;
- no unsupported right-angle convenience adapter;
- weatherproof external mating interface and tethered rated cap;
- straight connector departure, minimum bend radius, and structural strain
  relief; and
- repeated-flex qualification over every rotator position.

A generic N bulkhead is not approved merely because the AM59 has an N output.
The selected feedthrough must be evaluated as an RF component and as an
enclosure penetration. The CAD feedthrough is an envelope and keep-out only.
A
[SPINNER 7/16 female bulkhead adapter](https://products.spinner-group.com/7-16-female-bulkhead-mounting-to-7-16-female-adapter-bn920400)
is an illustrative environmental architecture because its published range
extends beyond 3 GHz and its mated interface is identified as IP68. That still
does **not** prove +64 dBm pulse capability, worst-VSWR voltage margin,
altitude performance, insertion loss, or compatibility with an N-interface
horn. Written manufacturer approval and RF testing remain release gates.

The output jumper is made as short as service loop, bend radius, and rotator
travel allow. Its delivered-power benefit shall be calculated from measured
2998 MHz insertion loss of the complete old and new assemblies, including all
connectors and bend states.

### RF input and monitor ports

The low-power RF input uses a sealed SMA-class bulkhead or qualified hermetic
feedthrough, keyed/routed so it cannot be confused with a monitor connection.
External cable boots provide strain relief and secondary weather protection;
they are not the primary IP seal.

A
[TE IP68 SMA panel connector](https://www.te.com/en/product-2502465-1.html)
is an illustrative input/monitor construction. The exact part, mating cable,
frequency response, panel seal, cap, rear sealing, and installed-state report
must be checked before it becomes a released item.

Forward and reverse monitor ports remain inside the dry volume unless a
specific external-monitor requirement is approved. They receive OEM-approved
50 ohm terminations with adequate pulse power. A nominal -30 dBc sample can
still approach +34 dBm, approximately 2.5 W peak, at full output.

### Power and control

The exterior shall not expose the factory 7W2 connector. Internal OEM-approved
7W2 pigtails transition to separate ruggedized power and control bulkheads.
Separating power from low-level control improves contact sizing, keying, EMC,
and service error prevention.

Jam-nut circular connectors with an integral panel O-ring minimize the number
of sealing interfaces. MIL-DTL-38999 Series III or a demonstrably equivalent
family is a candidate architecture, not an automatic selection:

- [TE MIL-DTL-38999 Series III](https://www.te.com/en/products/connectors/circular-connectors/intersection/mil-dtl-38999-series-iii-connectors.html)
- [TE jam-nut connector design](https://www.te.com/en/products/connectors/circular-connectors/intersection/military-grade-jam-nut-connectors.html)
- [TE hermetic MIL-DTL-38999 connectors](https://www.te.com/en/products/connectors/circular-connectors/intersection/hermetic-mil-dtl-38999-standard-connectors.html)
- [TE high-current bulkhead feedthrough example](https://www.te.com/en/about-te/news-center/adm-deutsch-lightweight-bulkhead-feedthroughs.html)

The
[Amphenol PanelMate AT](https://www.amphenol-sine.com/panelmate-at)
is another illustrative mixed power/signal architecture with published
IP67/IP68/IP69K options and 25 A/13 A contact classes. Its exact insert,
contact count, flange seal, rear wire seals, cavity plugs, backshell, cap,
inrush performance, and bundled-wire temperature derating would still need
to be released as one connector/harness system.

The released connector set must provide:

- adequate continuous, pulse, and fault current per contact with temperature
  derating;
- sufficient voltage, creepage, and clearance;
- environmentally sealed mated condition;
- equally rated tethered caps for unmated transport/service;
- jam-nut or welded/hermetic panel sealing;
- backshell strain relief and 360-degree shield termination where required;
- unique keying and labels;
- touch-safe power contacts or a verified dead-before-unmate procedure; and
- field-replaceable external cable assemblies without opening the dry chamber.

No connector hole is machined from a catalog shell size until the exact suffix,
panel thickness, seal, torque, mate, cap, and backshell stack are released.

All exterior connectors face horizontally or downward and receive drip loops.
No cable gland may be substituted without equal system-level IP, immersion,
strain-relief, temperature, chemical, and cable-diameter qualification.

## Bonding, EMC, lightning, and safety

- Bond the AM59 chassis to its cartridge, cartridge to enclosure, enclosure to
  structural bridge, bridge to existing mast plate, and rotator/antenna to the
  site grounding system.
- Use short, wide tinned-copper braids across removable or bearing interfaces.
- Provide masked, machined conductive pads. Coating is removed only at
  intentional bonds, and the completed joint perimeter is environmentally
  sealed.
- Keep protective bonding distinct from +50 V, -8 V, and signal returns and
  follow the OEM grounding scheme.
- Use 360-degree cable-shield termination at enclosure entry where required by
  EMC design.
- Coordinate surge protection at the mast/base boundary. Do not place an
  arbitrary low-power suppressor in the 2.5 kW peak RF output path.
- Bond the liquid loop and radiator where analysis requires it, without
  creating galvanic current paths.
- Include emergency-off, storm shutdown, RF-exclusion-zone, mast-lowering, and
  stored-energy procedures.

The enclosure is not a lightning protection system. Site grounding, bonding,
surge protection, separation distance, and personnel protection require a
system-level design.

## Materials, finishes, and corrosion control

Baseline materials and practices are:

- 5052-H32 sheet and flange stock for the welded pressure boundary;
- aluminum coil, radiator, tubing, and wetted fittings where practical to
  avoid mixed-metal coolant corrosion;
- 6061-T6 or another analyzed alloy for separate machined structural members;
- 316 stainless exterior fasteners, electrically isolated from broad wet
  aluminum contact except at intentional bonds;
- no zinc-plated carbon-steel exterior hardware;
- conversion coating or approved pretreatment, epoxy primer where applicable,
  and UV-stable light-color polyester powder/topcoat;
- masked sealing lands, connector lands, vent boss, weld-inspection zones, and
  electrical bond pads; and
- sealed edges and drainage that prevent persistent electrolyte crevices.

All welding uses a qualified procedure and operators. Pressure-boundary welds
receive visual inspection and liquid-penetrant examination before coating.
The gasket flange is machined after welding or otherwise processed to meet
flatness and surface-finish requirements. Weld repair is documented and
re-inspected.

Stainless fasteners use isolating washers/sleeves or a compatible barrier
compound where electrical bonding is not intended. Anti-seize, threadlocker,
and barrier products must be compatible with aluminum, gasket materials,
coolant, and wash chemicals. Intentional bond points use a documented
conductive joint treatment and corrosion reseal.

If salt, fertilizer, deicing chemical, disinfectant, solvent, fuel, or
high-alkaline wash exposure is credible, the exact concentration, temperature,
dwell, and rinse must be added to the requirements. "Washdown" alone is not a
chemical-compatibility specification.

## Preliminary BOM by function

No entry marked `performance envelope` is released for purchase.

| Qty | Functional item | Release status / requirement |
|---:|---|---|
| 1 | Existing BlueSky castle-cut pipe and plate | Retain; inspect and survey |
| 1 | Lower structural interface plate | Blank in preliminary CAD |
| 1 | Upper rotator interface plate | Blank in preliminary CAD |
| 1 set | Four-post load-bypass structure, cross-members, gussets, dowels, fasteners | Analyze complete load case |
| 1 | Continuously welded 5052 dry chamber | Pressure-boundary drawing and weld procedure required |
| 1 | Machined removable service lid | Hydrostatic/deflection analysis required |
| 1 | Continuous lid O-ring | Compound and gland unresolved |
| 1 | AM59 removable cartridge and retention set | OEM mounting approval required |
| 1 | AM59-3S-64-64 | User/vendor equipment |
| 1 set | Sealed internal dry-air duct/plenums | Airflow test required |
| 2 | Supplemental dry-side circulation blowers | Redundant, tach-monitored performance envelopes |
| 1 | Air-to-liquid dry-side coil | Performance envelope; fully welded/brazed |
| 2 | Coolant pumps | Performance envelope; each sized for full minimum flow |
| 1 | Air-to-liquid radiator | Performance envelope |
| 2 | Wet-side IP68 fans | Redundant, tach-monitored performance envelopes |
| 1 set | Coolant tubing, check valves, accumulator, relief, fill/bleed, drain, service caps | Fluid/pressure compatibility unresolved |
| 1 fill | Inhibited coolant | Mixture and maintenance interval unresolved |
| 1 | IP68/IP69K screw-in pressure vent | Flow/installation sizing unresolved |
| 1 set | Case, air, coolant, ambient, humidity, leak, flow, pressure, and lid sensors | Safety error budget required |
| 1 | Fail-safe controller / interlock module | Hardware shutdown path required |
| 1 | High-power RF output feedthrough | Performance envelope; RF and ingress proof required |
| 1 | Qualified high-power moving RF jumper | Rotator travel and horn interface unresolved |
| 1 | Sealed/hermetic RF input feedthrough | Exact part unresolved |
| 1 | Rugged power bulkhead pair and capped cable assembly | Exact contacts/shell unresolved |
| 1 | Rugged control bulkhead pair and capped cable assembly | Exact contacts/shell unresolved |
| 1 | OEM 7W2 internal pigtail | OEM part/pinout required |
| 1 set | Internal RF, DC, control, and sensor harnesses | Routing, EMC, and strain relief required |
| 1 set | Tethered environmental caps and parking points | Same required rating as mated interfaces |
| 1 set | White ventilated solar shields and external standoffs | Wind and solar test required |
| 1 set | Wet-bay guards, drains, hose supports, and debris screens | Must preserve hydraulic/airflow performance |
| 1 set | Ground studs, bond straps, isolators, labels, and torque marks | Bond and corrosion test required |
| 1 | Secondary enclosure/cartridge retention lanyard | Rated and captive |

## Qualification and release plan

Tests use production materials, welds, finishes, seals, connectors, caps,
vents, cable diameters, torque values, and assembly processes. A bare
prototype box is not representative.

### 1. Requirements and design controls

1. Freeze the environmental profile: temperature, altitude, solar irradiance,
   rain rate, jet/wash pressure, cleaning chemicals, salt, dust type,
   immersion water, storage, transport, vibration, shock, and service life.
2. Obtain controlled drawings and load data for the mast plate, rotator, horn,
   and cables.
3. Obtain Microwave Amps approval for orientation, M4 mounting, recirculated
   airflow, backpressure, fan interaction, connector mating parts, heat load,
   reflected-power behavior, and shutdown timing.
4. Complete system hazard analysis and DFMEA, including water ingress, coolant
   leak, blocked radiator, pump/fan failure, sensor failure, uncontrolled RF,
   cable arc, lightning, galvanic corrosion, and mast overload.
5. Allocate verifiable requirements to every sealing and thermal component.

### 2. Material, weld, and component qualification

1. Qualify weld procedures and inspect representative corner, boss, coolant-
   tube, and flange coupons.
2. Verify coating adhesion, UV exposure, scribe corrosion, and salt/chemical
   resistance for the actual finish system.
3. Immerse aged gasket, potting, hose, coolant, coating, labels, vent, and
   connector specimens in every specified fluid and temperature.
4. Obtain component IP reports for wet-side motors, connectors, vent, and
   sensors; confirm the reports cover the exact suffix and installed state.
5. Pressure-cycle the coolant coil and circuit from minimum temperature to
   maximum pump/relief condition and verify leak integrity.
6. Life-test pump and fan candidates at temperature and system resistance.

### 3. Pressure-boundary manufacturing verification

1. Visual and dye-penetrant inspect all pressure-boundary welds before finish.
2. Measure service-flange flatness and surface finish after welding/coating.
3. Leak-test each dry chamber before equipment installation using a calibrated
   pressure-decay, tracer-gas, or equivalent method correlated to the ingress
   requirement.
4. Proof the chamber and lid for the required external hydrostatic
   differential with structural margin; inspect permanent set and gasket
   contact.
5. Leak-test the complete coolant coil and welded penetrations independently
   from the dry chamber.
6. Record serial number, gasket batch, vent batch, connector suffixes,
   fastener torque, and test results.

### 4. Thermal and fluid qualification

1. Build a thermal mule with the released chamber, duct, coil, pumps,
   radiator, fans, solar shield, coolant, screens/guards, and cable loading.
2. Map actual dry-air flow and pressure at all amplifier fan inlets. Verify no
   coil bypass or hot-air short circuit.
3. Measure coolant flow, pump operating points, radiator airflow, pressure,
   and component temperature at minimum/maximum supply voltage and fluid
   viscosity.
4. Apply a calibrated 300 W distributed heat load at 45 C ambient until
   equilibrium. Demonstrate AM59-equivalent case points at or below 65 C and
   total installed thermal resistance at or below 0.050 K/W.
5. Repeat with solar simulation, no-wind and adverse-wind orientations,
   realistic dust/fouling allowance, voltage tolerance, and maximum permitted
   altitude.
6. Repeat with the real AM59 at maximum permitted duty into a qualified load,
   monitoring every case, air, coolant, connector, and electronics
   temperature.
7. Test one-pump, one-wet-fan, dry-fan, low-flow, blocked-radiator, sensor,
   overpressure, controller, and power-loss faults. Verify safe shutdown and
   cooldown with no reliance on operator timing.
8. Freeze/thaw and thermal-cycle the filled system; inspect fluid separation,
   expansion, seal damage, leaks, and restart behavior.

### 5. Ingress qualification

The sequence is performed on fully assembled, production-equivalent units,
with representative external cables. Both mated and capped connector
configurations are tested where either can occur in service.

1. Baseline insulation resistance, dielectric withstand as applicable,
   grounding/bond resistance, leak rate, mass, humidity, RF loss/VSWR, and
   functional test.
2. Temperature/pressure cycling to exercise the vent and lid seal.
3. IP6X dust test in accordance with IEC 60529, including enclosure
   depressurization if the controlled standard requires it.
4. IPX6 water-jet test from every accessible direction, including seams,
   coolant penetrations, connectors, vent, and lid corners.
5. Drain and externally dry without opening. Repeat electrical, RF, humidity,
   leak, and functional measurements; inspect the wet bay.
6. IPX7 temporary immersion at the project's declared 1 m / 30 min condition,
   unpowered.
7. Drain and externally dry without opening. Repeat electrical, RF, humidity,
   leak, and functional measurements before internal inspection.
8. Open the chamber in a controlled dry environment and inspect witness media,
   low points, connector backs, coil, and gasket for any ingress.
9. Repeat critical ingress tests after gasket service-life cycling, thermal
   cycling, vibration, corrosion exposure, and cable flex.

Acceptance is no harmful dust or water ingress under the controlled standard,
no unsafe electrical degradation, no hidden coolant leak, and full specified
function. A pressure-decay result alone does not replace dust and water tests.

### 6. RF, electrical, EMC, and cable qualification

1. Measure complete input/output insertion loss, return loss, shielding, and
   feedthrough heating at 2998 MHz.
2. Pulse-power proof the output feedthrough, cable, service loop, mating
   connectors, and horn transition or qualified load at maximum peak power,
   duty, and worst permitted VSWR.
3. Monitor arcs, partial discharge indicators if applicable, connector
   temperature, reflected power, and interlock response.
4. Flex the complete moving jumper through all rotator positions for the
   specified life, then repeat RF and ingress tests.
5. Validate +50 V pulse droop, contact temperature, fault interruption,
   emergency stop, stored-energy discharge, and dead-before-unmate behavior.
6. Conduct applicable emissions, susceptibility, ESD, surge, and bonding
   tests with pumps, fans, controller, and transmitter operating.

### 7. Structural and deployment qualification

1. Update mass, center of gravity, inertia, and projected area from the
   production model and measured hardware.
2. Analyze combined gravity, horn/rotator, cable, operational wind, survival
   wind, gust, transport, deployment, and handling cases with appropriate
   factors.
3. Review the exact configuration with BlueSky or a qualified structural
   engineer against mast height, guying, soil/base, and operating procedures.
4. Analyze panel and lid response at immersion differential pressure and wind
   suction.
5. Conduct sine/random vibration or a justified transport/deployment
   equivalent, modal survey, proof load, and fastener slip/witness inspection.
6. Re-run leak, ingress, bond, and alignment checks after structural testing.

### 8. Immersion recovery procedure

After any actual immersion:

1. Keep all mast-head power isolated at the source.
2. Lower or otherwise make the assembly safe before access.
3. Drain the wet bay completely and rinse with approved fresh water if the
   immersion fluid was dirty, saline, or chemically contaminated.
4. Inspect radiator, fans, pumps, hoses, caps, vent, connectors, seals, and
   coatings; replace contaminated filters/screens and any suspect vent.
5. Perform coolant-loop pressure/leak test, dry-chamber leak test, insulation
   resistance, bond resistance, and connector/RF inspection.
6. Confirm internal humidity and leak sensor state before applying auxiliary
   power.
7. Run pumps and fans under supervision, verify flow and temperatures, then
   restore amplifier power and RF only through the controlled commissioning
   sequence.

There is no automatic return to service after immersion.

## Maintenance basis

The released manual shall define:

- pre-deployment visual inspection;
- lid-fastener torque and witness-mark inspection;
- gasket cleaning, lubrication if allowed, cycle count, and replacement;
- pressure-vent inspection and replacement;
- radiator cleaning method that cannot damage fins or seals;
- wet-bay drain and debris inspection;
- coolant concentration, pH/conductivity if applicable, level, contamination,
  and replacement interval;
- pump/fan tach trend and service-life replacement;
- connector cleaning, cap use, mate-cycle limit, and torque;
- RF jumper bend, abrasion, insertion-loss, and life inspection;
- corrosion repair and bond-resistance measurement;
- annual or deployment-count-based enclosure leak checks; and
- mandatory post-washdown, post-immersion, lightning, drop, or overtemperature
  inspections.

Opening the service lid breaks the qualified seal and requires a documented
reseal inspection and leak check before field exposure.

## Release gates

The design shall not be released for fabrication or field RF operation until
all of the following are closed:

1. Exact lower BlueSky plate and upper rotator geometry, materials, fasteners,
   datums, and loads are controlled.
2. Horn/rotator mass, CG, inertia, projected area, travel, output-connector
   location, cable routing, and VSWR are known.
3. Microwave Amps approves orientation, all mounting details, dry-loop
   backpressure/flow, thermal basis, fan interaction, wiring, connector parts,
   reflected-power behavior, and protection logic.
4. The complete payload/wind configuration is approved against the exact mast
   deployment.
5. The air-to-liquid coil, pumps, radiator, wet/dry fans, coolant, accumulator,
   and tubing are selected from measured system curves and released drawings.
6. A production-equivalent thermal assembly passes 300 W at 45 C with the
   required margin and every defined fault response.
7. The high-power RF feedthrough and moving jumper pass peak-power,
   worst-VSWR, loss, heating, motion-life, and environmental tests.
8. Exact power/control connectors, contacts, caps, backshells, seals, and
   internal OEM pigtails are selected and pin-controlled.
9. Cleaning fluids, salt/chemical exposure, storage temperature, altitude,
   solar, vibration, and service life are quantitatively defined.
10. Lid, flange, O-ring, pressure vent, coolant penetrations, and weld process
    are fully toleranced and manufacturing-qualified.
11. The complete assembled system passes IP6X, IPX6, and IPX7 tests after
    thermal, structural, corrosion, and service-cycle preconditioning.
12. Safety, EMC, grounding, lightning/surge, RF exposure, emergency shutdown,
    maintenance, and immersion-recovery reviews are approved.

Until those gates close, every CAD radiator, coil, pump, fan, connector, vent,
and interface feature is a spatial reservation or performance envelope. The
CAD is appropriate for packaging and design review, not procurement,
certification, or an environmental claim.
