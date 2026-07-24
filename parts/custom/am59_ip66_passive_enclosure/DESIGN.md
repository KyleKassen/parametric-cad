# AM59 IP66 low-CG outdoor enclosure - V4 concept report

**Status:** Preliminary engineering concept. The CAD is suitable for
architecture review and prototype quotation, not production release. The
vendor-data and test gates in Section 13 must close before fabrication release.

## 1. Executive decision

Select **Architecture A: an intact AM59 straddling a welded dry bulkhead**.
The amplifier electronics and all future DIN components remain inside the
IP66 dry boundary. The complete OEM heatsink and three-fan bank remain outside
that boundary in a downward-open, freely drained rain hood. A one-piece molded
transition boot seals to a verified continuous band on the amplifier case, so
the concept does not depend on the OEM heatsink joint as the environmental
seal.

This is the best buildable architecture with the supplied vendor data:

- 45 W nominal / 51.75 W margin-adjusted heat remains in the dry chamber;
- passive rejection predicts 63.8 C dry air at 45 C ambient and zero wind;
- 7.64 kg complete empty mass including the 2.5 kg amplifier;
- empty CG 153.2 mm above the provisional rotator plane and 0.91 mm radially
  from the provisional axis;
- 9.14 kg and 141.2 mm vertical CG with a deliberately low 1.5 kg future DIN
  payload;
- 0.147 m2 frontal, 0.100 m2 side, and 0.172 m2 plan projected wind areas;
- USD 2,350-4,500 quantity-one prototype budget, excluding the AM59, future
  DIN equipment, ports, feedthroughs, pressure vent, and mounting hardware;
- no thermoelectric cooler, filter, cabin fan, refrigerant loop, or active
  condensate system is required.

Architecture B, a vendor-authorized separation of the amplifier body from its
heatsink at a cold wall, could ultimately be lighter and lower. It is not
selected because the supplied model and drawing do not define a separable
thermal interface, fastener torque, TIM, flatness, or warranty-approved split.
It remains a high-value vendor inquiry rather than a releasable design.

![Selected transparent concept](references/views/am59_ip66_passive_v4_transparent_iso.png)

## 2. Scope and source hierarchy

The design deliberately does **not** include connector ports, RF feedthroughs,
a pressure vent, mast adapters, rotator mounting hardware, or a final
load-transfer structure. Their locations must be selected only after the
thermal, seal-band, and rotator load gates close.

Controlling source order:

1. `parts/vendor/microwave-amps/datasheets/AM59-005D.pdf` controls model-
   specific electrical, thermal, environmental, outline, and mass data.
2. `parts/vendor/microwave-amps/AM59-3S-64-64.STEP` controls the packaging
   keep-out and the exact modeled configuration.
3. Supplied Seifert drawing/catalog and Hoffman specification control cooler
   ratings; their STEP files control exact packaging for modeled vendor parts.
4. Calculations in `params.json` and `model.py` are preliminary engineering
   estimates. Physical test controls where vendor calorimetry is absent.

The model-specific AM59 documentation gives 2998 MHz +/-20 MHz, +64 dBm
typical peak output, 3 percent maximum duty, +48 to +50 V at 4 A average,
-8 V at 80 mA, -10 to +70 C case operation, a 75 C overtemperature trip with
55 C reset, and 2.5 kg nominal mass. The nominal outline is
320 x 180 x 102 mm excluding its mounting flange.

The specification says a modular form is available for OEM integration, but
it provides no thermal/mechanical interface-control drawing for that form. Its
introductory prose also calls this AM59 model an "AM10 series" amplifier, an
apparent document inconsistency that the vendor should resolve.

The exact STEP contains 80 solids and has a native 364.12 x 102 x 200 mm
bounding box. The principal housing is approximately 320 x 48 x 180 mm; the
separate modeled flange is approximately 320 x 3 x 200 mm, and the forced-air
fin field is approximately 45 mm deep. Three 60 mm-class fans project about
25.4 mm beyond the fan end, while the output connector projects about 18.7 mm
beyond the opposite end. Inspection of the exact solids places the electronics
body on one side of the flange/heatsink transition and the fin/fan system on
the other.
In the selected vertical pose its accepted keep-out is:

| Axis | Minimum | Maximum | Span |
|---|---:|---:|---:|
| X, OEM airflow | -182.06 mm | +182.06 mm | 364.12 mm |
| Y, wet-to-dry | -53.00 mm | +49.00 mm | 102.00 mm |
| Z, up | 30.00 mm | 230.00 mm | 200.00 mm |

The STEP-derived volume centroid is used only as a mass-CG proxy. The vendor
must provide or approve the real mass centroid and support loads.

## 3. First-principles heat split

The enclosure is not sized for the full AM59 loss because its OEM sink remains
outside the conditioned volume.

| Quantity | Calculation | Result |
|---|---:|---:|
| Positive-rail input | 50 V x 4 A | 200 W |
| Negative-rail magnitude | 8 V x 0.08 A | 0.64 W |
| Typical average RF output | 10^(64/10) mW x 0.03 | 75.4 W |
| Matched AM59 heat estimate | approximately 200 W - 75 W | approximately 125 W |
| Severe engineering heat basis | rounded electrical input | 200 W |
| Assumed maximum heat entering dry side | 10 percent of severe basis | 20 W |
| Heat rejected directly in wet bay | 90 percent + fan input | 181.8 W |

The 125 W matched loss and 200 W severe basis are inferences, not vendor
calorimetry. The critical design variable is the dry/wet split. The current
10 percent dry-side allocation is conservative for concept sizing but is a
release gate, not a proven property.

Dry-chamber budget:

| Source | Heat |
|---|---:|
| AM59 dry-side leakage at severe basis | 20 W |
| Future DIN power/control/protection allowance | 15 W |
| Present monitoring/control allowance | 3 W |
| Residual solar and wet-to-dry conduction | 5 W |
| Model allowance | 2 W |
| **Nominal dry design load** | **45 W** |
| **With 15 percent selection margin** | **51.75 W** |

## 4. Architecture trade

The weighted penalty is a screening aid, not a substitute for the hard release
gates. Lower is better:

`4*weather risk + 4*vendor-interface risk + 2*thermal risk + 1.5*mass kg
+ 0.025*CG-Z mm + 12*frontal area m2 + 0.0005*prototype USD
- serviceability`.

Risk scales are 1 best to 5 worst; serviceability is 1 worst to 5 best.

| ID | Architecture | Dry heat | Mass | CG-Z | Radial CG | Front area | ROM cost | W/V/T risk | Service | Penalty |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|
| **A** | Intact AM59 straddles sealed bulkhead; wet OEM sink/fans; passive dry chamber | 45 W | **7.64 kg** | 153.2 mm | **0.91 mm** | 0.147 m2 | $2,850 | 2/3/3 | 4 | **40.48** |
| B | Vendor-approved body/sink split at cold wall | 30 W | 6.6 kg | **134 mm** | 6 mm | **0.135 m2** | $3,300 | 2/5/2 | 3 | 45.52 |
| C | Entire AM59 in ventilated wet bay; separate dry DIN pod | **23 W** | **6.0 kg** | **132 mm** | 5 mm | 0.140 m2 | **$2,200** | 5/4/2 | **5** | 50.08 |
| D | Complete AM59 in sealed active-cooled chamber | 225 W | 14.0 kg | 205 mm | 25 mm | 0.200 m2 | $5,200 | 2/2/3 | 3 | 50.12 |

### Architecture A - selected

It preserves the supplied amplifier assembly and its thermal path. Only the
electronics side is dry; the sink is outside. Its principal risks are the
case seal band, vertical mounting approval, wet fan build, and measured dry
heat split. Each is testable without redesigning the amplifier internals.

### Architecture B - lighter production opportunity, vendor-gated

Separating the amplifier body from the heatsink could create a continuous
metal cold-wall interface and reduce enclosure size, mass, and CG. It also
changes the vendor thermal stack and structure. Without a released modular
variant or interface-control drawing, using it would assume unknown TIM,
flatness, clamping, spreading resistance, RF stability, and warranty terms.

### Architecture C - rejected on weather reliability

A rain hood can block direct jets but cannot make an airflow-open bay
dust-tight. The supplied AM59 documentation gives no complete-unit IP rating,
and the standard ebm-papst fan datasheet does not establish an inherent IP
rating for the exact installed fans. This is the lightest concept, but it
cannot support a reliable complete-assembly IP66 claim for the electronics.

### Architecture D - rejected on requirements and system penalties

Putting the full AM59 and sink inside makes approximately 225 W a dry load,
violates the heatsink-outside requirement, and forces a large closed-loop
cooler. It approximately doubles concept mass and worsens CG, wind area,
input power, seal count, condensate behavior, and cost.

## 5. Cooling option comparison

### Passive enclosure - selected

The modeled 0.50 m2 effective area, including the finned service door, uses a
conservative overall coefficient of 5.5 W/m2-K:

- passive UA = 2.75 W/K;
- required UA at 45 C ambient and 65 C target = 51.75/20 = 2.59 W/K;
- preliminary UA margin = 6.28 percent;
- nominal dry-air prediction = 45 + 45/2.75 = 61.4 C;
- margin-load prediction = 45 + 51.75/2.75 = 63.8 C.

This is a deliberately narrow concept margin. A zero-wind, solar-shielded
prototype must demonstrate at least 2.59 W/K after coating, wiring, gasket
interfaces, and representative DIN population. Add external fin area before
adding active refrigeration if the prototype misses.

### Fans

An internal recirculation fan removes zero net heat; it can only reduce
temperature gradients. An external fan across the door fins could increase
UA, but it is not credited because passive safe-state operation is more
reliable. The three OEM fans are retained only for the AM59 heatsink.

The represented ebm-papst 612 NGLE is 60 x 60 x 25 mm, 12 V, 0.6 W,
21 m3/h free air, and approximately 20 Pa maximum static pressure. The
datasheet lists IP54/IP68 moisture protection only as possible custom
designs, so the exact moisture-protected suffix and unchanged installed
performance are hard gates.

### Seifert thermoelectric options

The supplied Seifert family is closed-loop and rated IP66/NEMA 4X. The exact
local 3050303 STEP is 153.5 x 134.93 x 206 mm. Catalog values:

| Model | Nominal capacity at 35/35 C | Input | Mass | Catalog price | Disposition |
|---|---:|---:|---:|---:|---|
| 3035303 | 30 W | 44-52 W | 1.81 kg | $611 | Insufficient margin at rating point |
| 3050303 | 50 W | 58-60 W | 3.18 kg | $811 | Thermally adequate at positive delta-T; unnecessary |
| 3102303 | 100 W | 115-118 W | 5.90 kg | $1,426 | Oversized |
| 3152303 | 150 W | 170-180 W | 9.07 kg | $1,861 | Grossly oversized |
| 3200303 | 200 W | 260-280 W | 9.98 kg | $1,771 | Grossly oversized |
| 6105313 / 6105323 | 100 W | 125-139 W | 9.53 kg | $1,864 | Oversized |

The 3050303 curve indicates substantially more than its 35/35 rating when
the dry side is hotter than 45 C outdoor air, but that does not justify its
3.18 kg, approximately 60 W parasitic input, added wind area, condensate
management, electrical infrastructure, and roughly $800 component cost.
The family uses AISI 304 stainless housings, is rated NEMA 4X/IP66, operates
from -20 to +65 C, is recessed by default, and cannot be roof mounted.
External-mount and condensate drain kits are separate accessories.

### Hoffman thermoelectric options

The supplied Hoffman TE09/TE12/TE16 family is closed-loop but only IP65.
Exact local models:

| Product | Nominal capacity 35/35 C | Approx. capacity at +15 K | Input | Mass | Exact/local envelope | Disposition |
|---|---:|---:|---:|---:|---|---|
| TE09 family | 52 W | approximately 85 W | 89 W | 2.7-3.6 kg | 123 x 176 x 230 mm unshrouded; 128 x 176 x 236 mm shrouded | Marginal smallest active option; IP65 gate |
| TE121024010, shrouded | 94 W | approximately 147 W | 162 W | 5.0 kg | **159.45 x 182.32 x 304.68 mm** | Oversized, heavy, painted shroud not Type 4X |
| TE162024020, unshrouded | 166 W | approximately 244 W | 295 W | 6.7 kg | **180.01 x 177.76 x 400.00 mm** | Grossly oversized |

TE12 and TE16 are mechanically verified against the supplied exact STEP
files. Neither improves the complete assembly enough to offset component
IP65, weight, power, wind, cost, two-loop fan failure modes, and condensate
risk.

### Hoffman filter fans and air-to-air products

A Type 4/4X fan-and-filter system can be built only from a specified matched
fan, filter, and shroud. It still exchanges outdoor humidity and dust, needs
filter service at height, and the vendor warns that upward-directed spray can
cause ingress. It is rejected for a dust-tight IP66 dry chamber.

The smallest relevant Hoffman ClimaGuard outdoor air-to-air exchanger
(TX23 class) is closed-loop and approximately 25 W/K, 13.6 kg,
584 x 305 x 180 mm, and 87 W at 48 VDC. It is more than the entire selected
assembly mass before the amplifier and is rejected.

Conclusion: active cooling is available but is not warranted by the residual
dry heat. Passive cooling minimizes failures, parasitic power, mass, cost,
wind area, penetrations, and condensation.

## 6. Selected mechanical concept

### Dry chamber

- Continuously welded 5052-H32 pressure body, accepted evaluated envelope
  416 x 128 x 286 mm.
- 1.5 mm shell and 3 mm amplifier bulkhead.
- 328 x 188 mm amplifier opening in the wet-facing bulkhead.
- No stitch seams, ordinary drains, filters, structural through-bolts, port
  holes, vent holes, or mounting holes.
- White UV-stable, high-emissivity powder coat over chromium-free conversion
  coating; gasket and bond lands masked.

### Amplifier boundary

- One-piece molded 50 Shore A EPDM transition boot.
- Outer boot flange axially compressed to the finish-machined welded
  bulkhead.
- Double continuous inner lip radially compressed over a verified
  uninterrupted AM59 case band at Y = 14-22 mm.
- Dry-side 6061-T6 clamp frame reacts into blind welded studs/bosses outside
  the opening; no wet-side backer and no through fasteners.
- M5 A4-80 fasteners at no more than 45 mm pitch, with supplier-defined
  compression stops and torque.
- Boot replacement required after amplifier removal.

The concept does not claim that the exact STEP alone proves the seal land.
A serial-number-controlled physical AM59 scan must show no cover seam,
fastener, label, coating discontinuity, connector, or lead under either lip.
The boot avoids using the narrow OEM flange as the annular wall seal, but it
cannot seal a hidden path through the amplifier itself. Microwave Amps must
also prove that the wet heatsink thermal wall, attachment fasteners, fan-lead
route, and any wet-side case joint cannot conduct water into the electronics
or dry chamber. If that proof fails, Architecture A is not releasable: use a
vendor-sealed modular/cold-wall variant or redesign the boundary.

### Service door and passive heat sink

- +Y removable 416 x 286 x 2 mm aluminum door.
- One continuous door gasket compressed against a 12 mm-wide welded collar.
- Captive M5 hardware into blind replaceable inserts, no more than 50 mm
  pitch.
- Fifteen vertical 1.2 mm fins, 30 mm projection and 240 mm height.
- Hard stops set production gasket squeeze.
- Door and fins remain beneath a ventilated solar shield.

### DIN reserve and service

- Removable internal carrier directly behind the service door.
- Two 300 mm EN 60715 35 mm rails at Z = 80 and 200 mm.
- Approximately 16 modules per rail, 32 total.
- Two 310 x 50 x 58 mm reserved component envelopes.
- Minimum exact-AM59 clearance: 5 mm to carrier and 13 mm to component
  reserve.
- Put future heavy protection and power hardware on the lower rail, closest
  to Y = 0; upper rail is for low-mass control.
- Final components must be rated for the qualified internal temperature,
  vibration, condensation, and duty.

![Service and weather parts exploded](references/views/am59_ip66_passive_v4_service_exploded_iso.png)

## 7. Wet-bay airflow and rain control

The wet bay is intentionally **not** the IP boundary. It is an aluminum
weather hood around outdoor-qualified thermal hardware:

- 510 mm airflow length, 150 mm wet depth, 270 mm useful height;
- large downward-facing inlet and outlet, each 145 x 150 mm gross;
- 0.85 guard free-area assumption gives 18,488 mm2 net at each end;
- 63 m3/h combined free-air reference gives 0.95 m/s aperture velocity;
- velocity pressure is only about 0.55 Pa;
- estimated complete labyrinth loss is 3 Pa; acceptance limit is 5 Pa at
  the approved fan operating point;
- end-turning walls block line-of-sight rain;
- the central splash floor receives positive fall toward both openings;
- hems, guards, and stiffeners must not trap water or ice;
- 520 x 330 mm sloped solar shield maintains at least a 12 mm ventilation
  gap.

Heat flow:

`AM59 devices -> OEM case/spreader -> OEM heatsink -> fan-driven wet air`

`dry-side AM59 leakage + DIN + solar -> dry air/walls -> white shell and
finned service door -> outdoor natural convection/radiation`

No exhaust-to-inlet recirculation is allowed. Qualification measures the
installed operating point, not the fan free-air value.

## 8. Mass, CG, and wind

Mass is computed from exact CAD volumes and material densities, plus explicit
allowances. The AM59 uses its 2.5 kg nominal mass and STEP volume centroid as
a proxy because the vendor mass centroid is unknown.

| Item | Mass | CG-Z |
|---|---:|---:|
| Welded pressure body | 1.346 kg | 150.5 mm |
| Finned service door | 0.985 kg | 145.0 mm |
| Rain hood | 0.847 kg | 172.9 mm |
| Solar shield | 0.460 kg | 310.0 mm |
| Clamp frame | 0.264 kg | 130.0 mm |
| Transition boot + door gasket | 0.131 kg | mixed |
| DIN carrier + two rails | 0.387 kg | approximately 142 mm |
| AM59 | 2.500 kg | 132.3 mm proxy |
| Fasteners, coating, bonding, wiring/sensors | 0.720 kg | allocated |
| **Complete empty concept** | **7.641 kg** | **153.2 mm** |

The provisional rotator axis is X = 0, Y = 25 mm at the Z = 0 reference
plane. It is a mass datum only, not a mounting design.

| Configuration | Total mass | CG from provisional axis | Radial offset |
|---|---:|---|---:|
| Empty concept | 7.641 kg | (-0.91, +0.05, +153.19) mm | 0.91 mm |
| +1.5 kg future payload at lower rail | 9.141 kg | (-0.76, +9.89, +141.18) mm | 9.91 mm |

Wind projection from the CAD envelope:

- front: 0.1472 m2;
- side: 0.1004 m2;
- plan/uplift: 0.1716 m2.

Actual drag, overturning moment, fatigue, and survival gust are deferred until
the mast/rotator interface, site wind basis, orientation, shielding, and
coefficient are defined.

## 9. Preliminary BOM and cost

The machine-readable BOM is `PRELIMINARY_BOM.csv`.

| Item | Material / selection | Mass | Prototype budget |
|---|---|---:|---:|
| Welded body + finned door | 5052-H32, continuous welds | 2.33 kg | $900-1,500 |
| Rain hood + solar shield | 5052-H32 | 1.31 kg | $250-500 |
| Dry clamp | 6061-T6, conversion coat/anodize | 0.264 kg | $300-600 |
| AM59 transition boot + door gasket | one-piece outdoor elastomers | 0.131 kg | $350-800 |
| DIN carrier + two rails | aluminum + zinc-plated steel | 0.387 kg | $100-200 |
| Fasteners/coating/bonding/insulation | A4/316 and qualified finish system | 0.54 kg allowance | $250-500 |
| Prototype instrumentation/leak setup | temporary test articles | not installed | $200-400 |
| **Concept total excluding AM59 and future items** | | **5.14 kg** | **$2,350-4,500** |

The working architecture midpoint is $2,850 and assumes a prototype boot
process rather than production mold tooling. Supplier quotations control.

## 10. Sealing and weatherproofing details

IP66 is a complete-populated-assembly qualification target, not a sum of
component labels.

- **Dry boundary:** welded shell, one service-door gasket, and one AM59
  transition boot.
- **Wet bay:** no environmental seal claim; it is floodable and freely
  drained.
- **Fasteners:** no structural or clamp fastener penetrates the dry boundary.
  External stainless hardware is isolated from aluminum except at deliberate
  bond lands.
- **Welds:** continuous and dye-penetrant/visual inspected before coating;
  gasket lands machined or locally finished after welding.
- **Door:** single gasket, hard squeeze stops, captive screws, blind inserts,
  no corner splice.
- **Boot:** single molded part, double lip, controlled axial and radial
  compression, supplier-qualified compound and coating compatibility.
- **Corrosion:** qualify conversion coat, white powder, wet heatsink coating,
  fan plastics, stainless/aluminum couples, cleaning chemistry, UV, salt, and
  freeze/thaw.
- **Condensation:** no active cooler creates a sub-dew surface. Future boards
  should use appropriate conformal coating and humidity monitoring.
- **Pressure:** no pressure vent is designed in this revision. Pressure
  cycling and gasket/door loads remain qualification items.

## 11. Controls and failure response reserved for later design

No power/control hardware is selected, but the future system should reserve
independent sensing and interlocks for:

- AM59 case temperature and dry-air temperature;
- fan tachometer/current plausibility for all three wet fans;
- humidity or condensation indication in the dry chamber;
- high-temperature RF inhibit before the OEM 75 C trip;
- persistent fan fault and thermal-rise shutdown;
- optional reduced-duty operation only after test establishes a safe map.

The passive dry chamber remains safe after loss of auxiliary cooling because
there is no active cabin cooler to lose. Loss of an AM59 wet fan is a separate
RF-operating fault and must inhibit or derate RF.

## 12. Qualification plan

1. **Dimensional first article:** 3D scan the exact AM59 seal band; verify
   bulkhead/door flatness, gasket squeeze, clamp torque, and service
   extraction.
2. **AM59 calorimetry:** measure total loss and dry/wet split at matched load,
   maximum qualified duty, reduced voltage, and worst permitted mismatch.
3. **Passive UA correlation:** 45 C ambient, zero wind, production coating and
   shield, 51.75 W dry load, representative DIN thermal simulators, and all
   production interfaces. Require UA >=2.59 W/K and dry air <=65 C.
4. **Wet thermal balance:** apply 181.8 W severe wet-side heat, reduced fan
   voltage, blocked-fan cases, and case mapping. Establish RF derate/inhibit
   thresholds below vendor limits.
5. **Airflow commissioning:** correlate each fan curve, differential pressure,
   delivered flow, hood loss, guard loading, and recirculation. Require
   production hood loss <=5 Pa at the accepted point.
6. **Wet-side endurance:** rain, condensation, freeze/thaw, dust loading,
   corrosion, restart, and fan-lead sealing using the released
   moisture-protected fan build.
7. **IEC 60529 IP6X:** complete populated dry boundary with production door,
   boot, clamp, and representative sealed blanks for intentionally deferred
   interfaces.
8. **IEC 60529 IPX6:** every service orientation, with jets directed at door
   seams, boot, underside openings, drains, fan side, and welds. No IP67 test
   or immersion claim is required.
9. **Production leak-screen correlation:** derive pressure-decay or tracer-gas
   limits from assemblies that pass IP6X/IPX6.
10. **Environmental cycling:** thermal/pressure cycling, hot shutdown, cold
    start, humidity soak, altitude transport, compression set, UV, corrosion,
    and cleaning agents.
11. **Mechanical:** transport shock, vibration, fan imbalance, clamp
    retention, door-fin fatigue, hood resonance, and later-defined rotator
    loads.
12. **Electrical/RF:** protective bonding, insulation resistance after wet
    testing, EMC/EMI, fault detection, and independent RF inhibit.

## 13. Assumptions and unresolved vendor-data gates

### Hard AM59 release gates

- Microwave Amps approval for the vertical bulkhead orientation, case seal
  contact, clamp/support loads, wet-side use, service method, and warranty.
- Vendor construction evidence plus a complete populated wet test proving no
  internal water bypass through the heatsink thermal wall, attachment
  fasteners, fan-lead route, or wet-side case joints. Otherwise replace
  Architecture A with a vendor-sealed modular/cold-wall interface.
- Serial-number-controlled physical outline and case-band measurement; STEP,
  drawing, and delivered unit must agree.
- Resolve the reverse-monitor connector ambiguity between the model/drawing
  regions, and reserve the complete documented connector keep-out until a
  delivered unit is scanned.
- Confirm which of the twelve modeled/drawn M4 locations carry structural
  load, with engagement, torque, orientation, and allowable interface loads.
- Vendor calorimetry or test confirmation of the 200 W severe basis, maximum
  10 percent dry-side heat, case temperature map, and 65 C design target.
- Definition of mismatch duty and whether the internal circulator/termination
  makes approximately 200 W the correct continuous fault basis.
- Exact wet-fan part suffix, IP/moisture protection, fan-lead sealing, life,
  and unchanged fan curve accepted by Microwave Amps and ebm-papst.

### Seal and enclosure gates

- Transition-boot supplier gland design, elastomer compound, continuous case
  band, coating compatibility, tolerance stack, compression, torque,
  replacement interval, and IP6X/IPX6 evidence.
- Production door-gasket gland, corner radii, compression stops, insert
  spacing, welding distortion, and flatness.
- Passive UA >=2.59 W/K in the final zero-wind configuration; otherwise add
  passive area.
- Hood loss <=5 Pa, no water/ice traps, no fan exhaust recirculation, and
  maintainable guards.

### Deferred system gates

- Actual future DIN heat/mass replaces the 18 W and 1.5 kg combined
  allowances and stays on the lower rail.
- Site minimum/maximum ambient, solar, altitude, salinity, ice, wind, and
  survival loads.
- Connector/feedthrough panel, pressure equalization strategy, protective
  earth/RF bonds, lightning/EMC approach, rotator/mast interface, and cable
  service loops.

## 14. CAD and analysis deliverables

- `model.py` - parametric CadQuery source of truth.
- `params.json` - dimensions, source data, budgets, gates, and test matrix.
- `spec.json` - geometry/fit evaluation contract.
- `fit_check.py` - exact AM59, vendor cooler, thermal, mass/CG, airflow, and
  architecture checks.
- `render_concept.py` - colored review renders.
- `exports/am59_ip66_passive_enclosure_v4.step` - evaluated welded dry body.
- `../../../assemblies/am59_ip66_passive_enclosure.py` - complete context
  assembly export driver.
- `PRELIMINARY_BOM.csv` - quotation-oriented preliminary BOM.

## 15. Vendor references

- Microwave Amps local model-specific drawing:
  `parts/vendor/microwave-amps/datasheets/AM59-005D.pdf`
- ebm-papst 612 NGLE official datasheet:
  <https://img.ebmpapst.com/products/datasheets/DC-axial-fan-612NGLE-ENU.pdf>
- nVent Hoffman thermoelectric specification:
  <https://www.nvent.com/sites/default/files/acquiadam/assets/Spec-00580.pdf>
- nVent Hoffman TE121024010 product:
  <https://www.nvent.com/eldon/sku?item_number=TE121024010&locale=en-GB>
- nVent Hoffman filter-fan shrouds:
  <https://www.nvent.com/en-us/hoffman/products/filter-fan-shrouds-type-44x-0>
- nVent Hoffman ClimaGuard air-to-air specification:
  <https://www.nvent.com/sites/default/files/acquiadam/assets/Spec-00624.pdf>
- Seifert 3050303 distributor page:
  <https://www.automationdirect.com/pn/3050303>
