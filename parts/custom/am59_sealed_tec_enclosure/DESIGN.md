# AM59 sealed thermoelectric enclosure

## Engineering disposition

The Seifert 3050303 is a good way to eliminate the custom liquid loop and the
uncertain heat-transfer path through an ordinary enclosure wall. It is not,
however, a one-for-one replacement for the earlier cooler:

- one 3050303 cannot remove the AM59's estimated 125 W normal heat load with
  useful temperature margin;
- four units are the minimum practical bank for the existing 300 W enclosure
  design basis;
- the complete cooler is rated IP66 / Type 4X, not IP67; and
- four opposed recessed units require a wider enclosure than the AM59 alone.

This design therefore uses **four recessed 3050303 units**, two symmetrically
on each long wall. The normal operating configuration targets IP6X/IPX6 after
complete-assembly testing. Two removable secondary covers, one around each
cooler bank, establish the proposed pressure boundary for **unpowered,
planned 1 m / 30 min immersion**. Those covers block airflow and are
interlocked so the amplifier and coolers cannot run while either cover is
installed.

The result is a self-contained enclosure design. BlueSky mast, rotator,
adapter, load path, and mounting details are deliberately outside this scope.

## Source hierarchy and dimensional control

The design uses the following sources:

1. the exact supplied
   `parts/vendor/microwave-amps/AM59-3S-64-64.STEP`;
2. the exact supplied
   `parts/vendor/seifert/Seifert - 3050303.STEP`;
3. the supplied
   `parts/vendor/seifert/Seifert - 3050303 Drawing.pdf`;
4. the supplied
   `parts/vendor/seifert/seifertcooling Datasheet.pdf`; and
5. Seifert's current official
   [3050303 data](https://production.seifertsystems.com/us/user-manual/manual-output/?datasheet=1&pid=1967)
   and
   [installation manual](https://production.seifertsystems.com/en/user-manual/manual-output/?pdf=.pdf&pid=1967).

The supplied Seifert STEP measures 153.5 x 134.93 x 206.0 mm. The supplied
drawing reports 153.5 x 134.9 x 206.0 mm and a 71.0/63.9 mm split about the
mounting plane, but does not unambiguously label the two sides. Current
Seifert data reports 154 x 138 x 200 mm, split approximately 65 + 73 mm.
Projection side assignment, maximum current, and maximum input power must be
reconciled on the purchased, serial-number-controlled unit.

The CAD therefore:

- places the exact supplied STEP;
- uses the current, more conservative 2.8 A / 66 W electrical maxima;
- preserves at least 3 mm of final growth allowance around the purchased
  unit; and
- treats serial-number-controlled Seifert drawings and a first-article
  measurement as fabrication release gates.

The supplied installation data is represented as a 170 x 120 mm cutout,
105 x 185 mm mounting pattern, four 8 mm holes, and 4.5 N m mounting-nut
torque. A released cutting file shall come from the purchased cooler's current
template, not from a screenshot or this concept model.

## Thermal sizing

### Heat basis

The prior AM59 engineering basis is retained:

| Condition | Enclosure heat |
|---|---:|
| Normal matched operation estimate | 125 W |
| Severe reflection / degraded condition | 200 W |
| Full enclosure design basis | 300 W |

The 300 W value is the maximum **net sensible heat entering the dry
enclosure** during qualified operation:

- 200 W AM59 severe-condition basis; plus
- one combined 100 W allocation for internal auxiliaries, wiring/feedthrough
  loss, residual absorbed solar heat after the production shields, and
  heat-estimation uncertainty.

Those allocations total 300 W; they are not cumulative additions to a
separate 300 W amplifier load. Seifert's 15 percent selection factor is not
embedded in the 300 W and is applied once, afterward. A qualification heater
must be adjusted so equipment heat plus measured residual solar ingress totals
300 W; a 300 W heater must not be combined with an additional unquantified
solar load.

Seifert's nominal 170 BTU/h rating is 50 W at 35 C cabinet air and 35 C
ambient. It must not be multiplied by four and treated as a universal 200 W
rating. Thermoelectric capacity depends strongly on the cabinet-to-ambient
temperature difference.

Conservative readings from the supplied 3050-family performance curve at
45 C ambient are:

| Cabinet air | Approximate capacity per 3050303 |
|---:|---:|
| 50 C | 74 W |
| 55 C | 91 W |
| 60 C | 107 W |
| 65 C | 124 W |

These are graph readings, not certified test points. They require confirmation
on the purchased units.

### Selected four-unit operating point

At 45 C ambient and 55 C cabinet air:

`4 x 91 W = 364 W`

Applying Seifert's 15 percent minimum sizing margin to the 300 W design heat:

`300 W x 1.15 = 345 W`

The bank therefore has approximately 19 W above the margin-adjusted
requirement, or 21.3 percent above the un-margined 300 W basis. This is enough
to proceed to prototype, but it is not a large margin.

At 50 C cabinet air the same bank provides only about 296 W, which does not
meet 300 W plus 15 percent. The design cannot promise 50 C cabinet air at the
worst thermal point.

The 55 C cabinet-air point is a sizing boundary, not a desired continuous
operating point. It leaves only 10 C to the absolute 65 C case qualification
limit. Full-power release instead requires AM59 inlet air no greater than
52 C and corrected hottest-case temperature below 60 C at steady state. If
the prototype cannot meet that condition at the 300 W basis, four 3050303
units are not enough; the answer is a larger cooler family or additional
coolers, not a software adjustment.

### Degraded modes

At the 55 C cabinet-air design point:

| Healthy coolers | Capacity | Allowed estimated heat | Margin-adjusted requirement | Required action |
|---:|---:|---:|---:|---|
| 4 | 364 W | 300 W | 345 W | Qualified full mode |
| 3 | 273 W | 200 W | 230 W | Automatic RF/duty limiting |
| 2 | 182 W | 125 W | 143.8 W | Matched-load reduced mode only |
| 1 | 91 W | 0 W RF | 143.8 W for 125 W | RF inhibit; remove +50 V |
| 0 | 0 W | 0 W RF | — | RF inhibit; remove +50 V |

Four units are consequently N+1 for the 200 W degraded condition, not for
uninterrupted 300 W operation.

The provisional system envelope uses the hottest measured air entering either
cooler bank, after solar heating and recirculation:

| Healthy coolers | 300 W permitted through | 200 W permitted through | 125 W permitted through |
|---:|---:|---:|---:|
| 4 | 45 C bank inlet | 55 C bank inlet | 60 C bank inlet |
| 3 | Not permitted | 45 C bank inlet | 60 C bank inlet |
| 2 | Not permitted | Not permitted | 50 C bank inlet |
| 1 or 0 | RF inhibited | RF inhibited | RF inhibited |

Above 60 C at either bank inlet, RF is inhibited regardless of cooler count.
These preliminary boundaries use interpolated graph data and the 15 percent
selection factor; purchased-unit calorimetry controls release. The cooler's
-20 to 65 C UL component range is not a complete-system operating claim.

### Electrical and ambient-side rejection

Per current Seifert data, each unit is:

- 24 VDC;
- 2.4 A nominal;
- 2.8 A maximum;
- 3.7 A starting;
- 58 W nominal / 66 W maximum input; and
- protected by a 4 A time-delay fuse.

For four units:

- maximum running current is 11.2 A;
- simultaneous starting current is 14.8 A;
- maximum cooler input is 264 W;
- installed cabinet-side airflow is approximately 92 m3/h; and
- installed ambient-side airflow is approximately 256 m3/h.

At a 300 W net dry-boundary load and 66 W maximum input per cooler, the
external side rejects approximately 564 W. At the 364 W curve-capacity point
it could reject approximately 628 W. The latter is a cooler-bank capability
point, not an additional simultaneous enclosure load. Both cooler banks must
have unobstructed ambient inlet and outlet paths for that duty.

Use a 24 V, 20 A minimum supply in the ground/support equipment. Do not put the
48-to-24 V converter inside this enclosure: its conversion loss would add
heat exactly where heat is most expensive. Size the feeder and connector for
voltage drop, 14.8 A start, fault current, temperature, bundling, and contact
derating.

## Packaging

### Main dry body

The nominal welded shell is:

| Dimension | Value |
|---|---:|
| X length | 495 mm |
| Y width, shell | 410 mm |
| Z height | 320 mm |
| Wall | 3 mm starting point |
| Cooler-coaming envelope, Y | 426 mm |
| Localized service collar/lid, Y x Z | 430 x 340 mm |

The exact AM59 placement is:

- X: -345.40 to +18.72 mm;
- Y: -100.00 to +100.00 mm; and
- Z: +52.00 to +154.00 mm.

The four coolers are centered at X = -245 and -40 mm on both Y walls, all at
Z = 180 mm. Their combined exact STEP envelope is:

- X: -321.75 to +36.75 mm;
- Y: -268.00 to +268.00 mm; and
- Z: +77.00 to +283.00 mm.

The CAD-kernel fit check finds 43.07 mm minimum solid-to-solid clearance
between the AM59 and the exact cooler models. The 410 mm shell width is not
arbitrary: a 300 mm box would leave the opposed cabinet-side cooler sections
too close together for the approximately 200 mm-wide AM59.

The CAD-derived known mass is approximately 31.4 kg in operating
configuration and 37.1 kg with both immersion caps, excluding the AM59,
gaskets, fasteners, connectors, wiring, controller hardware, and lifting
hardware. Each modeled aluminum cap is approximately 2.88 kg. Complete mass,
center of gravity, lift points, service support, and handling limits remain
release items because the AM59 mass/CG and exact hardware are not yet known.

### Cooler interface panels

Each cooler penetrates a long wall through its supplier-defined opening. Each
interface includes:

- a continuously welded internal aluminum doubler ring;
- a flat, continuous, defect-free sealing land whose actual finish stack is
  qualified with the factory-attached Seifert seal;
- the Seifert-supplied mounting material and factory-attached seal;
- four M6 nuts and nylon washers tightened to 4.5 N m in Seifert's specified
  sequence;
- hard dimensional control of cutout, flatness, coating mask, and surface
  finish; and
- an intentional corrosion/bonding scheme.

The concept starts with 4 mm internal doubler frames, 160 x 215 mm outside and
126 x 176 mm inside. That is a packaging and stiffness starting point. Final
thickness, weld sequence, local stress, vibration, and gasket-land distortion
require analysis and a welded first article.

Do not ask the thin wall and four cooler studs to absorb cable loads. All
external cabling receives independent strain relief.

### Service end

The only ordinary service opening is the -X end. It uses:

- an 8 mm starting-thickness lid;
- a continuous molded or spliced-and-vulcanized environmental seal;
- 32 captive M5 fasteners outside the seal;
- 50 mm maximum fastener pitch;
- hard compression stops;
- four vertical external stiffening ribs; and
- blind/replaceable inserts that do not create through leakage paths;
- dual-channel lid-open sensing that inhibits RF, removes +50 V, and requires
  verified stored-energy discharge before access.

At 1 m water depth the lid sees approximately 1.43 kN of resultant pressure
load before local factors. The final plate, ribs, flange, insert pullout, seal
compression, and fastener preload require calculation or FEA. The current
5.33 mm seal, 4.5 mm gland depth, and 15.6 percent squeeze are only starting
values pending the chosen seal supplier's data.

The 350 x 274 mm service opening is wholly inside the 374 x 284 mm gasket
inside boundary. It provides at least 12 mm Y and 5 mm Z of solid flange
support per edge. The 390 x 300 mm seal proxy and the localized 430 x 340 mm
welded collar/lid provide approximately 7.25 mm of material between every
M5-hole edge and both the seal OD and collar edge. The 32-fastener pattern and
5.33 mm seal section remain starting geometry pending the selected seal.

The AM59 sits on a removable 6 mm cartridge using all twelve represented OEM
mounting positions. The tray bears on two welded floor rails, seats against
two fixed +X stops, and is captured by two removable -X retainers. A dedicated
flexible bond strap bridges the removable cartridge to a prepared enclosure
bond point. The cold-drop baffle is captive to the service module and leaves
with the lid; the retainers are removed before extraction. Use a rated external
service cradle before the tray leaves the internal rails. Final screw type,
rail/stop/clamp loads, anti-lift retention, engagement, torque, isolation,
shock/vibration, and orientation require analysis and Microwave Amps approval.

## Closed cabinet-air path

The Seifert units keep ambient air and cabinet air separate, but their four
cabinet fans and four ambient fans do not automatically produce useful AM59
airflow. Without baffles, cold discharge can short-circuit directly back to a
nearby cooler inlet while the AM59 hot zone stagnates.

The CAD reserves:

- two side supply channels;
- a roof hot-return divider;
- a +X hot-discharge riser; and
- a -X cold-inlet drop.

The intent is:

1. the AM59 factory fans draw conditioned air at -X;
2. the amplifier discharges toward +X;
3. the hot discharge rises into the roof return;
4. the return distributes to all four cooler cabinet-side inlets; and
5. cooler discharge feeds the two side supply channels and returns to -X.

The baffles are sheet-metal envelopes, not released duct geometry. Cooler
inlet/outlet orientation must be mapped from the purchased unit and its
instruction manual. The AM59's approximately 63 m3/h is the sum of three
free-air fan ratings; the Seifert bank's 92 m3/h is four times Seifert's
installed/system-flow value in its own test configuration. They are not
directly comparable and neither establishes delivered flow here.

Obtain available fan curves, measure final system resistance and every branch
operating point, and correlate pressure/flow to passing thermal results.
Qualification must show no stall, reversal, unstable fan interaction, or
short-circuit recirculation at nominal and minimum qualified voltage, with
production shields, adverse wind, and the released cleanliness condition.
Only the resulting configuration-controlled pressure/flow limit becomes the
production acceptance criterion.

Seifert requires each cabinet-side fan to run continuously while the system is
energized. Only the ambient fan and Peltier elements for a unit switch
together. Lead/lag rotation applies to those switched pairs and must never
remove power from a cabinet fan. Each branch is independently monitored.

The white solar shields are open, ventilated radiation barriers. They are not
rain covers and do not contribute to the IP boundary. The side shields must
not reduce the four coolers' combined approximately 256 m3/h installed
ambient flow.

## Condensation

Thermoelectric cooling can put a cold heat sink below local dew point. A drain
would defeat the immersion boundary, and a trap or check valve is not a
credible IP67 barrier.

The design uses three layers:

1. calculate dew point from a redundant cabinet humidity/temperature
   measurement;
2. keep the coldest commanded surface at least 3 C above dew point, derating
   RF if thermal capacity is insufficient under that constraint; and
3. place a sealed, monitored catch pan below each cooler for fault
   condensation.

Each modeled pan has at least 100 mL design capacity. A leak strip or point
sensor is required in every pan. Any detected liquid inhibits RF, records the
event, and requires inspection, dry-out, and manual reset. The pans are fault
containment, not routine condensate reservoirs.

Do not route the standard open condensate drain through the enclosure. If
Seifert's condensate kit is used as a collection tray, its tube remains wholly
inside the dry boundary and terminates in sealed monitored containment.

Use a controlled service procedure, dry assembly air, and replaceable
desiccant during storage. The desiccant is supplementary and is not the
thermal control strategy.

## Environmental boundary

### Normal operating configuration

With the two immersion caps removed:

- the four Seifert coolers are part of the environmental boundary;
- the cooler component rating is IP66 / Type 4X;
- the complete enclosure targets IP6X and IPX6;
- connectors must be mated or fitted with equal-rated tethered caps; and
- the pressure-equalization vent must have a supplier-supported IP68/IP69K
  rating in the installed orientation.

This is a design target, not a certification. Component ratings do not confer
an enclosure rating.

IPX6 supports powerful water jets. It does not authorize an arbitrary
pressure washer, nozzle distance, temperature, detergent, or IPX9K procedure.
The maintenance wash process must match the tested process.

Seifert's current instructions call for removing the cooler from the cabinet
for wet cleaning of the ambient heat sink. Any in-place wet wash is therefore
a project-qualified deviation even though the cooler is IP66. Install each
unit vertically on a side wall with its electrical connection above the
cabinet fan. Do not release roof or rotated installation without written
Seifert approval. Seifert lists approximately 40,000 h average fan life under
normal conditions and transport/storage of -40 to 70 C, maximum 95 percent RH
at 25 C, in the marked package orientation. System service intervals and
storage limits must use the more restrictive limit of every installed part.

### Temporary immersion configuration

The 3050303 is not documented as IP67. The design therefore does not rely on
it for immersion.

Each long wall has a continuously welded rectangular coaming outside both
coolers. Its 456 x 302 mm outside and 380 x 226 mm inside dimensions provide a
38 mm compression-flange land on every edge. Before planned immersion, one
deep gasketed pan is installed on each coaming. Each pan completely surrounds
the two ambient-side cooler sections and shifts the water boundary outward to:

- the welded enclosure wall and coaming;
- the cap pan and flange;
- the continuous cap gasket;
- the cap fasteners/compression stops;
- the service lid and seal;
- connector caps and seals; and
- the pressure vent.

Each modeled cap uses a true 4 mm formed 388 x 234 mm pan, a separate
458 x 310 x 6 mm compression flange, four external stiffening ribs, and 32 M6
flange holes. The flange starts outside the modeled 0.8 mm compressed-gasket
space, producing zero cap/body overlap. Fasteners engage blind welded
coaming studs/bosses; none penetrates the dry wall. The capped package is
approximately 591.6 mm across Y. Each modeled aluminum cap is approximately
2.88 kg and sees a conservative approximately 1.35 kN resultant at 1 m water
depth before local factors. Cap plate/rib deflection, flange rotation,
fastener/stud load, gasket compression, and handling require FEA or test.

The caps block ambient airflow. Each bank therefore has a two-channel,
fail-safe cap-present interlock. Seating either cap removes:

- all Peltier power;
- all cooler fan power;
- RF enable; and
- +50 V amplifier power.

Use clearly tagged captive covers and a keyed safety loop. A controller
software bit by itself is not sufficient. The immersion configuration is
unpowered, all connector caps are fitted, and restart after immersion requires
inspection.

This architecture can be qualified for planned unpowered immersion. It does
not make an accidental powered immersion with the caps removed acceptable.
If the requirement is survival of an unexpected immersion in the operating
configuration, the 3050303 is the wrong component unless Seifert supplies
written IPX7 evidence or the entire operating configuration passes a project
IPX7 test.

## Controls and protection

High-current cooler switching, four independent 4 A time-delay branches,
current sensing, and the 24 V supply are located in ground/support equipment.
The small modeled internal envelope is safety I/O only. Lead/lag order rotates
the TEC/ambient-fan pairs to equalize operating hours; every cabinet fan
continues to run while energized.
The following minimum sensors are required:

- AM59 case hot spot;
- AM59 inlet air;
- AM59 discharge air;
- each cooler cold-side outlet;
- external ambient inlet;
- cabinet relative humidity and dew point;
- four condensate detectors;
- four cooler branch currents; and
- two cap-interlock channels per bank.

Required fault actions:

| Event | Hardware/software action |
|---|---|
| Four coolers healthy | Allow qualified 300 W basis |
| One cooler failed | Limit estimated enclosure heat to 200 W |
| Two coolers failed | Limit estimated enclosure heat to 125 W |
| Three or four failed | RF inhibit and remove +50 V |
| Corrected AM59 case reaches 60 C | Begin monotonic RF-duty derating |
| Corrected AM59 case reaches 63 C | Complete derating to zero; independent hardware RF inhibit |
| Corrected AM59 case reaches 64 C | Remove +50 V and latch the fault |
| Any AM59 case point reaches 65 C | Qualification failure and engineering review |
| AM59 inlet air reaches 52 / 55 C | Begin derating / RF inhibit |
| Either cooler-bank inlet exceeds 60 C | RF inhibit regardless of cooler count |
| OEM 75 C trip | Backup only; never the intended first response |
| Dew-point margin below 3 C | Stage/derate, then inhibit before condensation |
| Any condensate detected | RF inhibit; inspect and dry before manual reset |
| Any immersion cap present | Remove TEC/fans, RF enable, and amplifier power |
| Sensor plausibility, watchdog, or controller fault | Fail-safe RF inhibit |

Automatic restart after immersion, detected condensate, repeated overheat, or
an unexplained seal fault is prohibited.

## RF and electrical penetrations

All factory AM59 connectors stay inside the dry volume. Short internal
pigtails terminate at purpose-selected fixed-wall feedthroughs.

The main RF-output keep-out is aligned to the STEP-derived AM59 output axis at
approximately Y = +25.0 mm and Z = +70.5 mm. The fixed +X wall is at X = 105 mm,
leaving approximately 87 mm of straight internal distance beyond the modeled
connector nose. This keeps the high-power path short while preserving a
straight connector departure.

At +64 dBm the matched path carries about 2.51 kW peak:

- approximately 354 V RMS;
- approximately 501 V peak;
- approximately 7.1 A RMS; and
- approximately 10 A peak

before mismatch and altitude margins.

A generic N bulkhead is not released. The selected output feedthrough,
pigtail, and external jumper must be approved for:

- 2998 MHz +/-20 MHz;
- +64 dBm pulse power and maximum duty;
- worst permitted VSWR;
- altitude and contamination;
- insertion loss and return loss;
- connector temperature rise;
- mated and capped ingress;
- straight departure and bend radius; and
- production strain relief.

The enclosure also needs separate qualified 24 V cooler-power,
+50 V/-8 V/control, and low-power RF feedthroughs. Exact holes remain blank in
the concept CAD until part numbers, shell sizes, contacts, panel seals, backshells,
and caps are selected.

## Materials, corrosion, and bonding

The starting construction is a continuously welded 5052-H32 aluminum shell,
aluminum doubler frames/coamings, 6061-T6 cartridge, and formed aluminum
immersion caps. Final alloy/temper depends on weld qualification and structural
analysis.

The Seifert housing is stainless steel against an aluminum enclosure. That
interface needs:

- a flat, continuous, defect-free land with the actual conversion-coat/paint
  stack qualified as compatible with Seifert's factory-attached seal;
- no second gasket or substituted gasket material without written Seifert
  approval;
- isolating sleeves/washers where required;
- no water-trapping crevice;
- compatible anti-seize used only where it cannot contaminate the seal;
- an intentional protected bonding strap or defined conductive interface; and
- galvanic/corrosion testing using actual salt, cleaner, humidity, and UV
  exposures.

Do not depend on random fastener contact for protective bonding or RF shield
continuity. Measure bond resistance in production and after environmental
testing.

For project-designed service-lid and immersion-cap seals, select material for
temperature, compression set, UV, cleaner, salt, ozone, lubricant, and storage
life. The drawing must explicitly define whether each land is bare,
conversion-coated, or top-coated; do not generically mask or coat it. Qualify
the exact surface preparation, coating thickness/adhesion, repair process,
flatness, finish, and seal together by first-article ingress and corrosion
testing.

## Preliminary enclosure BOM

| Qty | Item | Status |
|---:|---|---|
| 1 | Continuously welded 5052 enclosure body, 495 x 410 x 320 mm nominal | Concept geometry complete |
| 1 | 430 x 340 x 8 mm service lid with vertical ribs | Concept geometry complete; deflection analysis open |
| 1 | Continuous service-lid environmental seal | Supplier/gland release open |
| 32 | Captive M5 lid fasteners and blind replaceable inserts | Exact hardware open |
| 1 | Removable 6061 AM59 cartridge using 12 OEM points | Concept geometry complete |
| 2 | Welded cartridge support rails with fixed +X stops | Concept geometry complete; structural release open |
| 2 | Captive removable -X cartridge retainers and anti-lift hardware | Exact hardware open |
| 1 | Flexible protected cartridge bonding strap | Exact hardware open |
| 4 | Seifert 3050303, recessed, 24 VDC | Exact supplied STEP placed |
| 4 | Welded cooler-interface doubler frames | Concept geometry complete |
| 4 | Seifert-approved interface gaskets | Serial-number data required |
| 4 | Sealed monitored condensate pans, at least 100 mL each | Concept geometry complete |
| 2 | Welded cooler-bank immersion-cap coamings | Concept geometry complete |
| 2 | 4 mm formed immersion caps, approximately 2.88 kg each, with continuous seals | Concept geometry complete; FEA/test open |
| 64 | Captive M6 cap fasteners into blind coaming studs/bosses | Exact hardware open |
| 2 sets | Dual-channel cap interlocks | Exact safety hardware open |
| 1 | Internal low-power safety I/O module | Exact hardware/EMC release open |
| 1 | External four-branch safety/thermal controller | Functional specification defined |
| 4 | External 4 A time-delay cooler branch protection and current measurement | Exact parts open |
| 1 | External 24 VDC, at least 20 A cooler supply | Located outside enclosure |
| 1 set | Temperature, RH/dew-point, flow/pressure, and leak sensors | Exact parts open |
| 1 | Qualified high-power RF feedthrough/pigtail | Critical release item open |
| 1 set | Cooler power, amplifier power/control, and low-power RF feedthroughs | Exact parts open |
| 1 | IP68/IP69K pressure-equalization vent | Exact part and sizing open |
| 3 | Freely ventilated white solar shields | Concept geometry complete |

## Manufacturing controls

1. Laser/waterjet the cooler panels only from the current supplier template.
2. Weld the body, doublers, lid flange, and immersion coamings using a
   qualified low-distortion sequence and inspect all continuous seams.
3. Machine or dress gasket lands only as allowed by the structural drawing.
4. Verify cutout position, wall flatness, mounting-hole position, and coaming
   coplanarity on every first article.
5. Apply the released conversion-coat/paint/masking drawing. It must explicitly
   control every cooler, service-seal, immersion-seal, bond, thread, and weld
   inspection surface.
6. Install coolers using Seifert-supplied M6 nuts/nylon washers, documented
   seal condition, specified tightening sequence, and 4.5 N m torque.
7. Record cooler serials, gasket batches, torque, seal compression, insert
   batch, vent batch, connector suffixes, and leak-test result.
8. Use a correlated pressure-decay or tracer-gas screen on every production
   enclosure with the vent temporarily blocked.

## Qualification sequence

### A. Dimensional and fit

- CMM the welded body and all four cooler lands.
- Scan or measure the purchased cooler against the supplied STEP.
- Verify rail/stop/retainer contact, anti-lift retention, bond strap, and AM59
  removal through the supported service opening without disturbing coolers or
  fixed feedthroughs.
- Inspect every cable bend radius and tool/service clearance.
- Weigh the complete operating and capped configurations; establish CG,
  lift/handling points, service-cradle rating, and transport restraints.

### B. Airflow and thermal

- Instrument AM59 inlet, discharge, case map, all cooler inlets/outlets,
  ambient, humidity, branch current, and static pressure.
- Obtain fan curves where available, measure system resistance and branch
  operating points, and correlate a production pressure/flow limit to passing
  thermal results. Do not use 63 m3/h free-air flow as installed acceptance.
- Run a calibrated net 300 W dry-boundary load at 45 C maximum hottest-bank
  inlet with four healthy coolers. Equipment heat plus measured residual solar
  ingress must total 300 W.
- Run the 200 W and 125 W health/ambient corners in the operating-envelope
  table, including 55/60 C bank-inlet cases where applicable.
- Repeat at minimum allowed supply voltage and with production shields.
- Fail each cooler one at a time and verify automatic 200 W limiting.
- Fail two coolers and verify 125 W limiting.
- Confirm full-power steady-state inlet air is no greater than 52 C and
  corrected hottest case is below 60 C.
- Verify derating at 60 C case, hardware RF inhibit at 63 C, +50 V removal at
  64 C, and treat any 65 C case point as a qualification failure.
- Calorimeter-check the performance-curve assumptions.

### C. Condensation

- Begin with worst credible internal humidity.
- Sweep ambient/cabinet temperature across dew-point crossings.
- Verify at least 3 C cold-surface-to-dew-point margin in allowed modes.
- Inject sensor faults and prove fail-safe response.
- Deliberately create limited condensate and prove tray capture, detection,
  shutdown, and service recovery without leakage.

### D. Operating ingress

- Test production-equivalent, populated, cable-connected hardware.
- Perform IP6X.
- Perform IPX6 with all connectors both mated and capped as applicable.
- Inspect witness media, insulation resistance, bonds, coolers, connector
  backs, tray sensors, and the service seal.

### E. Immersion configuration

- De-energize and verify stored-energy discharge.
- Fit all connector caps and both cooler-bank immersion caps.
- Verify all cap safety channels prevent energization.
- Proof-load/inspect each approximately 1.35 kN cap load path and the service
  lid load path before ingress qualification.
- Perform 1 m / 30 min IPX7 on the full populated enclosure.
- Repeat after thermal cycling, vibration/shock qualification, seal aging, and
  service cycles.
- Accept only with no free water, wet witness, insulation loss, bond
  degradation, corrosion damage, thermal fault, or RF degradation.

### F. RF

- Measure complete old and new output-path insertion loss at 2998 MHz.
- Pulse-power test at maximum output, duty, mismatch, altitude, temperature,
  and bend state.
- Monitor connector/feedthrough temperature and evidence of arc or partial
  discharge.
- Qualify conducted/radiated emissions and susceptibility, TEC switching
  transients, interlock integrity, and bonding with the pulsed PA operating.

## Release gates

The concept is not fabrication-ready until all of the following are closed:

1. the purchased cooler dimensions and cutout template are reconciled;
2. AM59 thermal mapping proves full-power corrected case below 60 C and no
   case point reaches 65 C at the qualified 300 W/45 C-bank-inlet corner;
3. installed fan operating points are stable and a correlated production
   pressure/flow limit is established without using the 63 m3/h free-air sum;
4. lid and immersion-cap structural/seal analyses are complete;
5. Seifert mounting-land flatness, gasket, and control requirements are
   incorporated;
6. dew-point control and sealed condensate containment pass testing;
7. exact RF, power, control, vent, seal, and cap hardware is selected;
8. IP6X/IPX6 passes in the normal configuration;
9. IPX7 passes in the unpowered, capped immersion configuration; and
10. mass/CG, lifting, cartridge retention, cooler cantilever, cap/lid loads,
    corrosion, bonding, thermal cycling, vibration/shock, transport, service
    life, EMC/EMI, and RF performance are accepted.

Until those gates close, the CAD is an engineering packaging and test
definition—not an IP certification or production drawing.
