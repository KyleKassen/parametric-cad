# AM59 centered bridge mast head

Status: preliminary engineering concept. The geometry is suitable for packaging review and interface surveying, but it is not fabrication-ready until the lower plate, rotator, horn, and dynamic cable interfaces are resolved.

## Outcome

The recommended arrangement is a centered bridge pedestal installed between the user's existing castle-cut pipe/plate and the rotator:

```text
horn antenna
moving RF service loop
rotator
upper structural plate
four-post load-bypass bridge
  removable AM59 cartridge
  wet fan/fin airflow tunnel
  dry output-connector doghouse
lower structural plate
existing mounting plate and castle-cut pipe
BlueSky AL2 mast
```

The amplifier is horizontal, with its factory fan end at -X and output end at +X. The upper and lower plates are joined by four square-tube posts outside the amplifier envelope. Antenna and rotator forces bypass the amplifier and the sheet-metal cover completely.

This arrangement gives a short output jumper without:

- duplicating the proprietary BlueSky castle geometry;
- making the amplifier or weather cover structural;
- adding amplifier mass and inertia to the rotating stage; or
- placing a forced-air amplifier in a sealed box.

## Authoritative inputs

### AM59-3S-64-64

The model-specific `AM59-005D.pdf` supplied by the user is the governing electrical and mechanical source. The vendor STEP is the governing packaging source.

Key values:

| Item | Value |
|---|---:|
| Nominal amplifier body | 320 x 180 x 102 mm with heatsink |
| Overall STEP envelope | 364.12 x 102 x 200 mm including fans, flange, and connectors |
| Nominal mass | 2.5 kg |
| Frequency | 2998 MHz +/-20 MHz |
| Peak RF output | +63.8 dBm minimum, +64 dBm typical |
| Maximum duty | 3% |
| Nominal pulse | 30 us at 1000 Hz |
| Positive supply | +48 to +50 V, 4 A average at the nominal pulse condition |
| Negative supply | -8 V, 80 mA average |
| Operating case temperature | -10 to +70 C |
| Overtemperature action | off at 75 C, autoreset at 55 C |
| Main RF input | SMA female |
| Main RF output | N female |
| DC/control | 7W2 D-type |
| Mounting pattern | 12 x M4 tapped through, X = 5/65/125/195/255/315 mm and two rows 190 mm apart |

The STEP identifies three ebm-papst 612 NGLE fans. Each standard fan is 60 x 60 x 25 mm, 12 V, 0.6 W, and 21 m3/h free-air. The standard fan must not be assumed moisture-rated; ebm-papst lists IP54/IP68 as optional custom constructions, not as a base-model rating.

### BlueSky mast

The official BlueSky page and system datasheet identify:

- mast: `BSM2-M-M202-AL2-000`;
- mast outside diameter: 2.0 inches;
- nominal deployable load: 100 lb / 45.4 kg for the 2 m system;
- published mast wind rating: 70 mph;
- included 18-inch mounting pole: `BSM2-A-M118-00P-AL2`.

The user's second image labels the actual pipe/plate part
`BSM2-P-M201-AL2-00P`. No controlled drawing or CAD for that part was
provided, so v1 retains it as a surveyed interface and does not infer its
plate or castle geometry from the system's listed M118 pole.

The published weight and wind values are system limits, not automatic approval of this payload. The combined horn, rotator, pod, cable, projected area, soil, anchoring, and guying configuration must be checked against the BlueSky load tables.

Official references:

- [BlueSky BSM2-M-M202-AL2-000](https://blueskymast.com/product/bsm2-m-m202-al2-000/)
- [BlueSky 2 m AL2 system datasheet](https://blueskymast.com/wp-content/uploads/2014/07/BSM2-M-M202-AL2-000.pdf)
- [BlueSky Standard Series manual and accessory guide](https://blueskymast.com/wp-content/uploads/2014/04/User-Manual-AL2-Standard-200-Series.pdf)
- [Microwave Amps AM59 family](https://microwaveamps.co.uk/product/power-amplifiers-am59/)
- [ebm-papst 612 NGLE](https://img.ebmpapst.com/products/datasheets/DC-axial-fan-612NGLE-ENU.pdf)

## Alternatives considered

| Architecture | Benefits | Problems | Decision |
|---|---|---|---|
| Centered bridge below rotator | Centered mass, non-rotating amplifier, structural bypass, 0.3-0.6 m output jumper | Requires surveyed top/bottom plates and a moving RF loop | Selected |
| Vertical sidecar on the mounting pole | Easy prototype, output at top, existing mast interface untouched | Eccentric mass, larger broadside area, yaw torque, awkward balance | Prototype fallback |
| Amplifier above/on rotator | Shortest RF path and no moving output jumper | Rotator carries amplifier mass, polar inertia, wind load, plus moving power/input/control harnesses | Only if continuous rotation makes a fixed amplifier impossible and rotator margin is proven |
| Sealed inline box | Simple weather story in appearance | Approximately 125 W heat load cannot be rejected naturally at realistic ambient/solar conditions; box becomes safety-critical structure | Rejected |
| Half the amplifier through an enclosure wall | Attempts to expose the heatsink | AM59 uses a full-length forced-flow tunnel, not a separable cold-wall heatsink; difficult sealing and likely warranty risk | Rejected |
| Ground or mid-mast amplifier | Lowest mast-head complexity | Retains the long, lossy high-power output cable | Safe fallback |

## Mechanical configuration

### Structural load path

The v1 frame has:

- 260 x 320 x 8 mm lower plate;
- 260 x 320 x 8 mm upper plate;
- four 25 x 25 x 3 mm square-tube posts;
- 152 mm clear height between the lower-plate top and upper-plate bottom;
- two lower cartridge support crossbars; and
- no modeled interface holes.

The posts are outside the 200 mm AM59 flange width. The amplifier can be removed along X after the end/service panels and harnesses are removed. Removing the amplifier does not disturb the rotator load path.

The CAD fuses the frame into one validation body. This proves only topological
continuity and packaging; it does not prove the real tube-to-plate joints. The
production design needs modeled end blocks/feet, gussets, welds or angle
cleats, fasteners, and dowels after the load analysis. A bolted and doweled
assembly is preferred unless a qualified welding design accounts for the
heat-affected strength reduction of 6061-T6.

Recommended production details:

- use dowels or fitted shoulders to carry repeatable shear at the upper and lower plates;
- use preloaded locking fasteners for clamp force, not loose bolts in oversized holes as shear pins;
- add corner gussets after the real combined-load analysis;
- add formed feet or end blocks that provide adequate edge distance on both plates;
- provide captive fasteners and a secondary retention lanyard on the amplifier cartridge;
- mark every structural fastener with a torque stripe; and
- machine coating-free bonding pads, then reseal their perimeter after assembly.

### Removable cartridge

The cartridge is a 340 x 210 x 6 mm perimeter frame with four local lock ears
extending its width to 237 mm. It has:

- all twelve 4.5 mm clearance holes with preliminary 8.4 mm, 90-degree
  underside countersinks matching the AM59 M4 pattern;
- a large center opening to reduce weight;
- four preliminary 6.5 mm cartridge lock locations on accessible ears outside
  the 200 mm amplifier flange, aligned over modeled 5.0 mm M6 tap-drill
  provisions in the two support bars; and
- direct metal support under both 10 mm mounting-flange rails.

All twelve AM59 points should be used because the amplifier's mounting flange
is only 3 mm thick. Flush M4 flat-head screws are required so their heads do
not strike the support bars while the cartridge slides. Screw standard,
strength, countersink, length, engagement, and torque must be approved by
Microwave Amps. A preliminary stack suggests M4 x 10 hardware through the
6 mm cartridge, but that is not a released callout.

Do not suspend the amplifier from one or two end fasteners and do not clamp the heatsink body.
The revised support bars sit between AM59 screw columns, and the modeled
countersinks keep the screw heads flush during extraction. The M6 retention thread form,
insert type, engagement, locking method, wear strips, lead-in guides,
end-stop, anti-rattle clamp, and secondary lanyard remain production details.
For service, remove the positive-X doghouse/exhaust module and both side
skins, disconnect the harnesses, remove the four retention bolts, and extract
the complete amplifier/cartridge module in +X. The concept model provides
4 mm nominal clearance per side between the local lock ears and the posts.

### Safety-critical interfaces intentionally unresolved

The v1 top and bottom plates are blank. This is intentional.

Before adding holes, survey:

1. Existing lower plate X/Y size, thickness, material, coating, flatness, weld/pipe details, bolt pattern, and dowels.
2. Rotator base pattern, pilot diameter, dowels, fastener grade, required flatness, and cable exit.
3. Full castle insertion and pin clearance below the current plate.
4. Rotator and horn CG relative to mast axis.

The lower pattern should mate to the existing plate. The upper pattern should reproduce the rotator pattern. Do not create a new castle-cut coupling unless BlueSky supplies or approves it.

## Thermal and airflow design

### Heat estimate

At +64 dBm, peak RF output is:

`10^((64 - 30) / 10) = 2512 W peak`

At 3% maximum duty:

`2512 x 0.03 = 75.4 W average RF`

The model-specific supply value is about:

`50 V x 4 A + 8 V x 0.08 A = 200.6 W average electrical input`

The matched-load, first-order heat load is therefore approximately:

`200.6 - 75.4 = 125 W`

This excludes small fan/control losses and any off-nominal reflected-power
condition. The supplied specification shows an internal circulator and
termination for reflected power. If the OEM permits operation into a severe
mismatch, returned RF can be dissipated inside the amplifier instead of at the
horn. Until Microwave Amps supplies the shutdown threshold and time history,
use approximately the full 200 W electrical input as the conservative
enclosure heat-rejection test case. At 63 m3/h, even that case has an ideal
air rise of about 9.5 C before pressure losses, recirculation, solar load, and
fan derating.

The three fans provide 63 m3/h free-air in theory. At that flow, 125 W would produce an ideal air rise of roughly 6 C. The actual flow through the 320 mm long, 2.5 mm fin passages is lower, and the fans have only about 20 Pa available static pressure. Weather protection must therefore use very large, low-loss openings.

### Wet airflow bay

The fan and fin tunnel remains an ambient-air system:

- fan intake at -X;
- exhaust at +X;
- downward-open inlet rain plenum plus three baffled inlet windows;
- end exhaust windows with downward-sloping blades;
- side exhaust relief openings that require formed external rain hoods in the
  production shell;
- no dense filter in the released baseline;
- removable high-open-area insect screen;
- drain paths at every low point; and
- no recirculation path from hot exhaust back to the fan inlet.

Targets:

- absolute preliminary minimum net inlet and exhaust area: 17,000 mm2 each;
- preferred net area: 21,600 mm2 or greater each;
- pressure drop target: less than 5 Pa at operating flow, subject to OEM confirmation.

The CAD opening areas are packaging provisions, not a CFD or fan-curve
qualification. In v1 the 326 x 45 mm lower inlet plus three 80 x 40 mm
window provisions total about 24,270 mm2 gross. The two 115 x 70 mm end
exhaust windows plus two 90 x 65 mm side reliefs total about 27,800 mm2
gross. Final net free area must be recalculated from the selected screen,
louvers/hoods, fasteners, and edge geometry and remain at least 17,000 mm2 on
both sides. A duct pressure survey must also confirm that the openings feed
the fan plenum without a hot-exhaust recirculation shortcut.

### Dry connector doghouse

The output end is geometrically separable:

- heatsink exhaust occupies the upper half;
- N output, sample ports, DC/control, and fan harness occupy the lower connector half.

The doghouse uses a U-shaped bulkhead collar around the lower connector panel,
a gasketed cartridge/floor interface, and a removable positive-X end module.
It must be sealed with closed-cell conductive/weather gasket without blocking
the upper fin exhaust. It includes separate provisional penetrations for:

- the direct high-power RF output cable;
- the 7W2 DC/control harness; and
- the fan-power harness.

The end cover is removable. Cable penetrations should use split glands or boots so the factory connectorized harnesses remain serviceable.

The PDF shows both forward and reverse sample ports, while the current STEP represents the reverse-monitor region ambiguously. Reserve volume for both on the physical unit. A -30 dBc monitor can see about +34 dBm / 2.5 W peak at full output; use OEM-approved 50 ohm monitoring loads or weatherproof terminations.

### Fan-end RF-input boot

The SMA input is below the three fans at the nominal -X end and must not be
left exposed in the wet intake plenum. Use an OEM-approved molded connector
boot or a small gasketed lower vestibule with a downward cable exit, drip loop,
and independent strain relief. It must remain below/outside the fan discs and
must be included as an obstruction in the inlet-area and pressure-drop test.
The exact boot is not modeled because the mating SMA cable and permissible
sealing surface have not been selected.

### Solar load

Use a light gray or white outer cover if operational requirements allow it. The roof is separated from the AM59 by about 30 mm, providing a ventilated solar shield. A black enclosure in direct sun can consume much of the available 70 C case-temperature margin before RF heat is added.

### Production shell details

The v1 roof and side panels are flat packaging proxies, not released sheet
metal. A 510 mm-class, 1.5 mm flat roof would pond water and can flutter under
wind pressure/suction. The production shell needs:

- a crown or positive drainage slope;
- turned flanges, cross-breaks or hat-section stiffeners;
- drip edges and drains that cannot discharge onto the fan or connectors;
- flashed boots around all four structural-post penetrations;
- captive panel fasteners and bonded attachment brackets;
- formed hoods over the side exhaust reliefs; and
- enough removal clearance that no weather panel carries cartridge or
  rotator load.

Those features change obstruction area and wind envelope, so the airflow and
load calculations must be repeated from the released sheet-metal model.

## RF integration

The main N output is at the fixed amplifier's +X end. Route a direct flexible jumper through the dry doghouse, support it independently, then form a controlled service loop to the horn.

Requirements for the jumper:

- 2998 MHz +/-20 MHz performance;
- +64 dBm / 2.5 kW peak pulse rating at the worst expected VSWR;
- at least 75 W average RF plus ambient/solar derating;
- low insertion loss;
- repeated-flex qualification for the rotator travel;
- outdoor jacket and sealed connector boots;
- minimum bend radius maintained in every commanded position; and
- strain relief on both stationary and moving sides.

Avoid a convenience right-angle adapter unless its insertion loss, peak-power rating, and reflected-power behavior are qualified. The CAD doghouse gives approximately 76 mm beyond the N connector nose before the panel; the cable should leave straight and make its main bend outside the doghouse.

The exact recovered power depends on the present and proposed cable
assemblies. Use their measured 2998 MHz insertion loss:

`P_horn = P_amp x 10^(-cable_loss_dB / 10)`

For scale, eliminating 0.5 dB of output-path loss increases delivered power
by about 12%; eliminating 1.0 dB increases it by about 26%. These percentages
are not a cable selection or a prediction for the current installation.
Measure both complete assemblies, including connectors and the moving loop,
at the operating frequency and under the required bend states.

As an illustration only, Times Microwave publishes 0.23 dB/m at 2.5 GHz for
standard LMR-400. Removing 2 m of that class of line would avoid about
0.46 dB before connector differences, corresponding to roughly 11% more
delivered power. This is not approval to use LMR-400 here: the final assembly
must be qualified at 2998 MHz for peak pulse voltage/power, average heat,
worst VSWR, outdoor exposure, and repeated flex.
[Times Microwave LMR-400 datasheet](https://timesmicrowave.com/wp-content/uploads/2022/03/lmr-400-coax-cables-datasheet.pdf)

Rotation is a gating input:

- Limited azimuth/elevation: use a validated service loop plus mechanical and electrical travel stops.
- Continuous 360-degree azimuth: use a qualified 3 GHz, 2.5 kW-peak rotary joint, or move the amplifier above the azimuth bearing and revalidate rotator load/inertia. A free cable loop cannot support continuous rotation.

## DC, fan, and control harnessing

The 7W2 connector combines:

- A1: ground;
- A2: +48 to +50 V;
- pin 3: overtemperature alarm;
- pin 4: TTL control, low = enabled and high = off;
- pin 5: -8 V; and
- pins 1/2: not connected per the supplied specification.

Use the exact OEM mating connector, power contacts, backshell, pin crimp, and strain relief. Do not select a generic 7W2 only from its appearance in the STEP.

The average +50 V current is 4 A, but the source/harness must be checked for pulse droop and cable inductance. Do not add a local capacitor bank or precharge circuit without Microwave Amps approval. Put source breaker/fusing, contactor, emergency-off logic, current/voltage telemetry, and safe discharge at the power source.

The STEP fan identity implies a 12 V, approximately 1.8 W total fan load. The AM59 drawing names an `SMP-04V-NC` fan connector but does not provide its pinout. Obtain the fan harness and pinout from Microwave Amps before energizing it.

Route:

- high-power RF separately from DC/control;
- RF input down the opposite side of the frame from the output cable;
- DC/control down a protected mast-side chase;
- all stationary harness weight to structural P-clamps, never to connector shells; and
- every downward cable entry with a drip loop.

Use the overtemperature alarm and reflected-power protection in the RF-enable interlock. Add fan-current or tach/fan-fault monitoring if the OEM supports it.

## Bonding, grounding, corrosion, and lightning

- Bond amplifier chassis to cartridge, cartridge to structural frame, frame to the existing plate, rotator chassis to the upper plate, and antenna to the site bonding system.
- Use short, wide tinned-copper braids across removable joints and the rotator bearing if the bearing is not a qualified bond.
- Black anodize is insulating. Provide masked bond pads, approved serrated hardware, antioxidant compound, and environmental resealing.
- Electrically isolate stainless fasteners from broad wet aluminum interfaces except at intentional bond points.
- Keep protective bonding separate from decisions about +50 V, -8 V, and signal returns; follow the amplifier grounding scheme.
- Use the BlueSky grounding system or an engineered site equivalent.
- Coordinate surge protection on incoming RF input, DC, and control conductors at the mast/base boundary.
- Do not insert an arbitrary low-power coax surge suppressor in the 2.5 kW peak output path.
- Include storm shutdown, RF exclusion-zone, and mast-lowering procedures.

## Preliminary load picture

Including the current end-louver projections, use a preliminary pod broadside
envelope of approximately:

`0.555 m x 0.168 m = 0.0932 m2`

At 70 mph / 31.3 m/s, sea-level dynamic pressure is about 600 Pa. With a flat-body drag coefficient near 1.2, the pod alone is roughly:

`600 x 1.2 x 0.0932 = 67 N` or about 15 lbf

At 2 m, that is about 134 N m of added base overturning moment before horn,
rotator, mast, cable, gust, ice, and safety factors.

At 2.70 g/cm3, the current solid volumes imply approximately 4.18 kg for the
frame, 0.28 kg for the cartridge, 1.39 kg for the weather shell, and 0.26 kg
for the doghouse. With the 2.5 kg amplifier, that is about 8.6 kg before
fasteners, gaskets, screens, bond braids, and cables. Expect an integrated pod
near 9-10 kg until detailed weight optimization. This is below the published
45.4 kg deployable-load number by itself, but wind and combined CG govern.

Do not label the integrated system "70 mph rated" from the mast catalog alone.

## Preliminary BOM

| Qty | Item | Notes |
|---:|---|---|
| 1 | Existing castle-cut pipe and mounting plate | Retained; inspect and survey |
| 1 | Lower structural plate | 6061-T6, blank interface in v1 |
| 1 | Upper rotator plate | 6061-T6, blank interface in v1 |
| 4 | Structural square-tube posts | 25 x 25 x 3 mm preliminary |
| 2 | Cartridge support crossbars | Integrated into frame model |
| 1 | Removable AM59 cartridge | Uses all 12 M4 positions |
| 1 | AM59-3S-64-64 | Vendor unit |
| 1 set | 5052 rain/sun shell | Roof, service side, fixed side, inlet and exhaust baffles |
| 1 | Dry connector doghouse | Gasketed removable end cover |
| 1 set | Formed vent hoods, louvers, high-open-area screens, and drains | Pressure drop and water rejection must be tested |
| 1 | Qualified high-power flexible RF jumper | Horn end unresolved |
| 1 | Low-power SMA input cable, dry boot/mini-vestibule, clamps, and drip loop | Respect the PDF input-power survival limit |
| 1 | OEM 7W2 mating pigtail | Exact contacts/backshell required |
| 1 | Mast-run +50 V/-8 V/control harness and connector support | Voltage drop, pulse droop, and strain relief unresolved |
| 1 | OEM fan-power mating harness and approved 12 V feed | Pinout and supply source unresolved |
| 1 set | RF/sample terminations and weather caps | OEM approved |
| 1 set | Cable clamps, service-loop guides, and strain relief | Dynamic bend control |
| 1 set | Ground studs and tinned-copper bond braids | Masked conductive pads |
| 1 | Secondary amplifier retention lanyard | Rated and captive |
| 1 set | Structural fasteners, dowels, isolators, witness marks | Final selection after analysis |

## Verification and release plan

1. Survey the existing plate and rotator interfaces and add only verified holes/datums.
2. Obtain Microwave Amps answers for orientation, M4 torque/engagement, fan wiring, pressure drop, IP/moisture status, and supply cable impedance.
3. Obtain rotator mass, CG, inertia, travel, connector routing, and allowable moments.
4. Obtain horn mass, CG, projected area, N-connector location, and VSWR.
5. Update the complete weight/CG/projected-area model.
6. Run frame static, fatigue, bolt-preload, and modal analysis with combined antenna and wind loads.
7. Review the payload with BlueSky against the exact height, guying, soil, and operating-wind condition.
8. Build an airflow mule with the actual screens, baffles, harnesses, and covers.
9. Instrument inlet air, outlet air, AM59 case, +50 V connector, fan current, and overtemperature output.
10. Test at maximum permitted duty and worst ambient/solar simulation. Verify margin below the 70 C operating case limit.
11. Perform water-spray, wind-driven rain, drain, condensation, dust-ingress, and blocked-screen fault tests.
12. Exercise every rotator position while measuring jumper bend radius, connector force, insertion loss, and reflected power.
13. Pulse-power proof the complete output path--N mate, jumper, glands/boots,
    moving loop, horn transition or qualified load--at maximum permitted pulse,
    duty, and worst allowed VSWR while monitoring arcs, connector temperature,
    and reflected-power protection.
14. Proof-load the complete lowered mast head, inspect fastener witness marks, then conduct a controlled field deployment below the manual's deployment-wind limit.
15. Release drawings, torque table, inspection criteria, maintenance interval, and operational wind limit only after those tests pass.

## CAD deliverables

Running `model.py` exports:

- structural frame;
- removable cartridge;
- weather shell;
- connector doghouse;
- closed context assembly; and
- open-service context assembly.

The mast pipe/plate and rotator in the context assembly are explicit reference keep-outs. They are not fabrication geometry.
The fan-end SMA boot is also excluded pending selection of the mating cable
assembly and an OEM-approved sealing method.
